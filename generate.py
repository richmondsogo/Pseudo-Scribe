"""
generate.py - V1 CLI for course lecture note generation

This CLI is an AI-driven pipeline that produces consistent, resumable, multi-chapter
lecture notes and compiles them to a single PDF using LaTeX.

Design goals and behavior are described in the project README.

Usage: python generate.py <command> <course_id> [chapter_number]

Commands:
  init       Create a new course folder skeleton
  profile    Create or edit course_profile.md (writes a template if missing)
  terminology Run initial terminology extraction
  chapter    Generate a single chapter (requires chapter number)
  all        Generate all missing chapters sequentially
  qa         Run final course QA
  compile    Typeset and compile final PDF
  build      Convenience: run terminology, missing chapters, final QA, typeset and compile

This file intentionally keeps a simple structure compatible with Python 3.11+.
"""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

# Environment-driven configuration
# Default provider set to Gemini (Google) for this deployment
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
# Default model name is a Gemini text model. Override with GEMINI_MODEL or LLM_MODEL.
LLM_MODEL = os.getenv("LLM_MODEL", "models/text-bison-001")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
MAX_CHAPTER_RETRIES = int(os.getenv("MAX_CHAPTER_RETRIES", "2"))

# Repository root assumed to be current working directory when running
REPO_ROOT = Path(__file__).resolve().parent
COURSES_DIR = REPO_ROOT / "courses"
PROMPTS_DIR = REPO_ROOT / "prompts"

# Simple logging
def info(msg: str) -> None:
    print(msg)

def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)

# --- LLM wrapper ---

def call_llm(prompt: str, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
    """Call configured LLM provider. This deployment uses Google Gemini (google.generativeai).

    This function supports a DRY_RUN mode via the environment variable DRY_RUN=1|true which returns canned responses
    for a quick smoke test without making external API calls.
    """
    provider = LLM_PROVIDER
    model = model or LLM_MODEL
    temperature = temperature if temperature is not None else LLM_TEMPERATURE

    dry = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
    if dry:
        low = (prompt or "").lower()
        # Terminology conflict checker canned response
        if "terminology conflict checker" in low or "decide whether the two definitions" in low:
            return json.dumps({"conflict": False, "reasoning": "Dry-run: assume no conflict."})
        # Terminology extractor canned response
        if "terminology extractor" in low or "extract a compact terminology" in low:
            return json.dumps({
                "terms": {
                    "example_term": {
                        "preferred_term": "example_term",
                        "definition": "An example term used in dry run.",
                        "definition_status": "defined",
                        "introduced_in": 1
                    }
                }
            })
        # Chapter writer canned response (terminology + chapter)
        if "you are writing one chapter" in low or "[terminology]" in prompt or "[chapter]" in prompt:
            term_json = {"new_term": {"preferred_term": "new_term", "definition": "A dry-run example term.", "definition_status": "defined", "introduced_in": None}}
            chapter_md = "# Sample Chapter\n\nThis is a short sample chapter generated in dry-run mode.\n\n## Section 1\nSample content.\n\n## Conclusion\nShort conclusion.\n\n### Tutorial Questions\n1. Sample recall question\n2. Sample conceptual question\n3. Sample application question\n4. Sample comparison question\n5. Sample problem-solving question\n6. Sample extension question\n"
            return "[TERMINOLOGY]\n" + json.dumps(term_json) + "\n[/TERMINOLOGY]\n\n[CHAPTER]\n" + chapter_md + "\n[/CHAPTER]"
        # Chapter QA canned pass
        if "chapter qa assistant" in low or "chapter_markdown" in low:
            return json.dumps({"status": "PASS", "issues": [], "warnings": []})
        # Final QA canned pass
        if "final-course qa" in low or "final course markdown" in low or "final_course_markdown" in low:
            return json.dumps({
                "status": "PASS",
                "critical_issues": [],
                "warnings": [],
                "coverage": {"complete": True, "missing": []},
                "terminology_consistent": True,
                "cross_chapter_consistent": True
            })
        # Typesetter canned LaTeX fragment
        if "typeset" in low or "latex" in low or "chapter_markdown" in low:
            return "\\chapter{Sample Chapter}\n\\section{Introduction}\nSample content.\n"
        return "DRY_RUN"

    if provider not in ("gemini", "google", "googleai"):
        raise RuntimeError("LLM_PROVIDER must be set to 'gemini' for this deployment. Remove references to OpenAI.")

    # Support for Google's Gemini (via google-generativeai client)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY must be set to use Gemini provider")
    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError("google-generativeai package not installed. Add it to requirements.txt and install.") from e
    # Configure library
    try:
        genai.configure(api_key=api_key)
    except Exception:
        # older/newer clients may differ; try setting attribute
        try:
            genai.api_key = api_key
        except Exception:
            pass
    # Choose a text model name if not provided
    gmodel = model or os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "models/text-bison-001"
    # The client may offer a simple generate_text API
    try:
        # predict using text generation
        resp = genai.generate_text(model=gmodel, text=prompt)
        # response object may contain .text or .output
        out = getattr(resp, "text", None) or resp.get("text") if isinstance(resp, dict) else None
        if not out:
            # try string conversion
            out = str(resp)
        return out
    except Exception:
        # Fallback: try the 'chat' style
        try:
            resp = genai.chat(model=gmodel, messages=[{"role": "user", "content": prompt}])
            # extract from resp
            if isinstance(resp, dict):
                return resp.get("candidates", [])[0].get("content", "")
            return str(resp)
        except Exception as e:
            raise RuntimeError(f"Gemini provider call failed: {e}")

# --- File utilities ---

def load_json(path: Path) -> Any:
    # Use utf-8-sig to tolerate files with BOM (e.g., written from Windows editors)
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# --- Course layout helpers ---

def course_path(course_id: str) -> Path:
    return COURSES_DIR / course_id

@dataclass
class Course:
    id: str
    path: Path
    profile_path: Path
    outline_path: Path
    terminology_path: Path
    generation_state_path: Path
    prompts_path: Path
    drafts_path: Path
    tex_path: Path
    final_path: Path
    output_pdf: Path

    @classmethod
    def load(cls, course_id: str) -> "Course":
        p = course_path(course_id)
        return cls(
            id=course_id,
            path=p,
            profile_path=p / "course_profile.md",
            outline_path=p / "outline.json",
            terminology_path=p / "terminology.json",
            generation_state_path=p / "generation_state.json",
            prompts_path=p / "prompts",
            drafts_path=p / "drafts",
            tex_path=p / "tex",
            final_path=p / "final",
            output_pdf=p / "output.pdf",
        )

# --- Template rendering ---

def render_prompt(template: str, context: Dict[str, Any]) -> str:
    # Very small placeholder replacement
    result = template
    for k, v in context.items():
        placeholder = f"{{{{{k}}}}}"
        if isinstance(v, (dict, list)):
            repl = json.dumps(v, indent=2, ensure_ascii=False)
        else:
            repl = str(v)
        result = result.replace(placeholder, repl)
    return result

# --- Prompt loading ---

def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")

# --- Terminology utilities ---

def load_terminology(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"terms": {}}
    return load_json(path)

def save_terminology(path: Path, data: Dict[str, Any]) -> None:
    # Do not overwrite lightly; write atomically
    tmp = path.with_suffix(".tmp.json")
    save_json(tmp, data)
    tmp.replace(path)

# Compare definitions using LLM: returns True if conflict
def definitions_conflict(existing_def: Optional[str], new_def: Optional[str]) -> Tuple[bool, str]:
    # If either is None or empty, consider non-conflict unless both are present and clearly contradictory
    if not existing_def or not new_def:
        return False, "one or both definitions empty -> no conflict"
    prompt = f"""
You are a terminology conflict checker. Decide whether the two definitions below describe the same technical concept or are in substantive conflict.

Existing definition:
{existing_def}

New proposed definition:
{new_def}

Answer with a JSON object with fields:
- conflict: true|false
- reasoning: short explanation (one or two sentences)

Be conservative: if uncertain, set conflict=true.
"""
    resp = call_llm(prompt, temperature=0.0)
    # Try to extract JSON
    try:
        first = resp.strip()
        # allow the model to respond with plain 'conflict: true' or JSON. Try json loads by locating first '{'
        if first.startswith("{"):
            parsed = json.loads(first)
            return bool(parsed.get("conflict")), parsed.get("reasoning", "")
        # fallback simple parsing
        lc = first.lower()
        if "conflict" in lc and "true" in lc:
            return True, first
        if "conflict" in lc and "false" in lc:
            return False, first
        # otherwise be conservative
        return True, "Unclear from checker response; conservatively flagging conflict"
    except Exception:
        return True, "Failed to parse checker response; conservatively flagging conflict"

# --- Core operations ---

def cmd_init(course_id: str) -> None:
    p = course_path(course_id)
    if p.exists():
        error(f"Course {course_id} already exists at {p}")
        sys.exit(1)
    # create folder structure
    (p / "prompts").mkdir(parents=True)
    (p / "drafts").mkdir()
    (p / "tex").mkdir()
    (p / "final").mkdir()
    info(f"Created course skeleton at {p}")
    # write minimal outline.json template
    outline = {
        "course_code": course_id,
        "course_title": "",
        "chapters": []
    }
    save_json(p / "outline.json", outline)
    # empty terminology
    save_json(p / "terminology.json", {"terms": {}})
    # generation_state
    state = {"status": "not_started", "chapters": {}, "final_qa": False, "compiled": False}
    save_json(p / "generation_state.json", state)
    # copy prompt templates from repo prompts if present
    repo_prompts = PROMPTS_DIR
    if repo_prompts.exists():
        for file in repo_prompts.iterdir():
            if file.is_file():
                shutil.copy(file, p / "prompts" / file.name)
    info("Initialization complete. Edit course_profile.md and outline.json then run terminology extraction.")

def cmd_profile(course_id: str) -> None:
    c = Course.load(course_id)
    if not c.path.exists():
        error("Course not found. Run 'init' first.")
        sys.exit(1)
    if not c.profile_path.exists():
        template = textwrap.dedent(f"""
        # Course Profile

        Course Code: {course_id}
        Course Title: 
        University: 
        Department: 
        Academic Session: 
        Level: 

        ## Style Rules

        * Use clear academic English.
        * Explain concepts before assuming familiarity.
        * Prefer explanation over memorization.
        * Avoid filler.
        * Use consistent terminology.
        * Do not use conversational language.
        """
        )
        c.profile_path.write_text(template, encoding="utf-8")
        info(f"Wrote template profile to {c.profile_path}")
    else:
        info(f"Profile exists at {c.profile_path}. Open and edit as required.")

def require_course_files(c: Course) -> None:
    if not c.path.exists():
        raise FileNotFoundError(f"Course not found: {c.path}")
    if not c.outline_path.exists():
        raise FileNotFoundError(f"Missing outline.json at {c.outline_path}")
    if not c.profile_path.exists():
        raise FileNotFoundError(f"Missing course_profile.md at {c.profile_path}")
    if not c.terminology_path.exists():
        # create empty
        save_json(c.terminology_path, {"terms": {}})
    if not c.generation_state_path.exists():
        save_json(c.generation_state_path, {"status": "in_progress", "chapters": {}, "final_qa": False, "compiled": False})

def cmd_terminology(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    outline = load_json(c.outline_path)
    profile = c.profile_path.read_text(encoding="utf-8")
    terminology_template = load_prompt("terminology_extractor.txt")
    context = {
        "course_profile": profile,
        "outline_json": outline,
        "source_materials": ""
    }
    prompt = render_prompt(terminology_template, context)
    info("Calling LLM for initial terminology extraction (cost-conscious prompt)...")
    resp = call_llm(prompt)
    # Expect JSON list or object: try to extract JSON
    terms = {}
    try:
        # model should return JSON structure {"terms": {...}}
        data = json.loads(resp)
        if "terms" in data:
            terms = data["terms"]
        else:
            # allow list of entries
            if isinstance(data, list):
                for entry in data:
                    term_key = entry.get("term") or entry.get("preferred_term")
                    if term_key:
                        terms[term_key] = entry
    except Exception:
        # fallback: save raw response into terminology_raw.json for inspection and fail conservatively
        (c.path / "terminology_raw.txt").write_text(resp, encoding="utf-8")
        error("Failed to parse terminology extractor output as JSON. Saved raw response to terminology_raw.txt")
        sys.exit(1)
    # Merge with existing but do not overwrite
    existing = load_terminology(c.terminology_path)
    existing_terms = existing.get("terms", {})
    added = 0
    for k, v in terms.items():
        if k in existing_terms:
            continue
        # normalize v
        entry = {
            "preferred_term": v.get("preferred_term") if isinstance(v, dict) else k,
            "definition": v.get("definition") if isinstance(v, dict) else None,
            "definition_status": v.get("definition_status") if isinstance(v, dict) else "undefined",
            "introduced_in": v.get("introduced_in") if isinstance(v, dict) else None,
        }
        existing_terms[k] = entry
        added += 1
    existing["terms"] = existing_terms
    save_terminology(c.terminology_path, existing)
    info(f"Terminology extraction complete. {added} new terms added.")

# Parse LLM chapter generation output into terminology and chapter
def parse_generation_output(text: str) -> Tuple[Dict[str, Any], str]:
    # Expect [TERMINOLOGY] ... [/TERMINOLOGY] and [CHAPTER] ... [/CHAPTER]
    term_start = text.find("[TERMINOLOGY]")
    term_end = text.find("[/TERMINOLOGY]")
    chap_start = text.find("[CHAPTER]")
    chap_end = text.rfind("[/CHAPTER]")
    terms = {}
    chapter = ""
    if term_start != -1 and term_end != -1:
        raw = text[term_start + len("[TERMINOLOGY]"):term_end].strip()
        # try JSON
        try:
            parsed = json.loads(raw)
            # allow {"terms": {...}}
            if "terms" in parsed:
                terms = parsed["terms"]
            else:
                terms = parsed
        except Exception:
            # try to extract lines of form key: {...}
            # Save raw for inspection and continue
            # Write a fallback file
            terms = {}
    if chap_start != -1 and chap_end != -1:
        chapter = text[chap_start + len("[CHAPTER]"):chap_end].strip()
    else:
        # If markers not present, assume whole response is chapter
        chapter = text.strip()
    return terms, chapter

def generate_chapter_content(c: Course, chapter_number: int, max_retries: int = MAX_CHAPTER_RETRIES) -> None:
    require_course_files(c)
    outline = load_json(c.outline_path)
    chapters = outline.get("chapters", [])
    chap = next((ch for ch in chapters if int(ch.get("number")) == int(chapter_number)), None)
    if not chap:
        raise ValueError(f"Chapter {chapter_number} not found in outline")
    state = load_json(c.generation_state_path)
    chapter_state = state.get("chapters", {})
    if str(chapter_number) in chapter_state and chapter_state[str(chapter_number)] == "complete":
        info(f"Chapter {chapter_number} already complete. Skipping.")
        return
    profile = c.profile_path.read_text(encoding="utf-8")
    terminology = load_terminology(c.terminology_path)
    terminology_json = terminology
    chapter_writer_template = load_prompt("chapter_writer.txt")

    attempts = 0
    last_error = None
    while attempts < max_retries:
        attempts += 1
        info(f"[Attempt {attempts}/{max_retries}] Generating chapter {chapter_number} ...")
        context = {
            "course_profile": profile,
            "outline_json": outline,
            "terminology_json": terminology_json,
            "chapter_number": chapter_number,
            "chapter_title": chap.get("title"),
            "chapter_topic": chap.get("topic"),
            "source_materials": ""
        }
        prompt = render_prompt(chapter_writer_template, context)
        resp = call_llm(prompt)
        # Parse
        proposed_terms, chapter_md = parse_generation_output(resp)
        # Validate proposed_terms
        conflict_found = False
        conflict_messages: List[str] = []
        loaded_terms = terminology_json.get("terms", {})
        existing_term_count = len(loaded_terms)
        for term_key, term_val in proposed_terms.items():
            # Normalize incoming
            if isinstance(term_val, str):
                pref = term_val
                ddef = None
                status = "undefined"
            elif isinstance(term_val, dict):
                pref = term_val.get("preferred_term") or term_key
                ddef = term_val.get("definition")
                status = term_val.get("definition_status") or ("defined" if ddef else "undefined")
            else:
                continue
            if pref in loaded_terms:
                existing = loaded_terms[pref]
                existing_def = existing.get("definition")
                # If both have definitions, check for conflict
                cflag, reasoning = definitions_conflict(existing_def, ddef)
                if cflag:
                    conflict_found = True
                    conflict_messages.append(f"Term {pref} conflicts: {reasoning}")
            else:
                # add new term
                loaded_terms[pref] = {
                    "preferred_term": pref,
                    "definition": ddef,
                    "definition_status": status,
                    "introduced_in": int(chapter_number)
                }
        if conflict_found:
            last_error = "; ".join(conflict_messages)
            error(f"Terminology conflict: {last_error}")
            # Stop generation and surface error to user
            state["chapters"][str(chapter_number)] = "failed"
            save_json(c.generation_state_path, state)
            raise RuntimeError(f"Terminology conflict during generation of chapter {chapter_number}: {last_error}")
        # Save updated terminology (merge)
        terminology_json["terms"] = loaded_terms
        save_terminology(c.terminology_path, terminology_json)
        # Write draft
        ch_filename = f"ch{int(chapter_number):02d}.md"
        (c.drafts_path / ch_filename).write_text(chapter_md, encoding="utf-8")
        info(f"Draft written to {c.drafts_path / ch_filename}")
        # Run chapter QA
        qa_result = run_chapter_qa(c, chapter_md)
        # Summarize progress
        new_term_count = len(loaded_terms) - existing_term_count
        total_chapters = len(chapters)
        title = chap.get("title") or f"Chapter {chapter_number}"
        if qa_result.get("status") == "PASS":
            info(f"[{chapter_number}/{total_chapters}] {title}\n  - Generated\n  - {new_term_count} new terms added\n  - Chapter QA passed")
            state["chapters"][str(chapter_number)] = "complete"
            save_json(c.generation_state_path, state)
            return
        else:
            issues = qa_result.get("issues", [])
            warnings = qa_result.get("warnings", [])
            brief_issues = issues if issues else warnings
            info(f"[{chapter_number}/{total_chapters}] {title}\n  - Generated\n  - {new_term_count} new terms added\n  - Chapter QA failed: {brief_issues}")
            error(f"Chapter QA failed: {issues}")
            last_error = str(issues)
            # Leave draft intact, mark failed and retry if possible
            state["chapters"][str(chapter_number)] = "failed"
            save_json(c.generation_state_path, state)
    # After retries
    raise RuntimeError(f"Chapter {chapter_number} generation failed after {attempts} attempts: {last_error}")

def run_chapter_qa(c: Course, chapter_markdown: str) -> Dict[str, Any]:
    template = load_prompt("chapter_qa.txt")
    outline = load_json(c.outline_path)
    profile = c.profile_path.read_text(encoding="utf-8")
    terminology = load_terminology(c.terminology_path)
    context = {
        "course_profile": profile,
        "outline_json": outline,
        "terminology_json": terminology,
        "chapter_markdown": chapter_markdown
    }
    prompt = render_prompt(template, context)
    resp = call_llm(prompt, temperature=0.0)
    # Expect JSON object
    try:
        parsed = json.loads(resp)
        return parsed
    except Exception:
        # Save raw
        (c.path / "chapter_qa_raw.txt").write_text(resp, encoding="utf-8")
        error("Failed to parse chapter QA response as JSON. Saved raw output to chapter_qa_raw.txt")
        return {"status": "FAIL", "issues": ["Invalid QA response format"]}

def cmd_chapter(course_id: str, chapter_number: int) -> None:
    c = Course.load(course_id)
    if not c.path.exists():
        error("Course not found. Run 'init' first.")
        sys.exit(1)
    try:
        generate_chapter_content(c, chapter_number)
    except Exception as e:
        error(str(e))
        sys.exit(1)

def cmd_all(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    outline = load_json(c.outline_path)
    chapters = outline.get("chapters", [])
    total = len(chapters)
    info(f"Generating missing chapters for {course_id} ({total} chapters in outline)")
    for ch in chapters:
        num = int(ch.get("number"))
        try:
            generate_chapter_content(c, num)
        except Exception as e:
            error(f"Stopped: {e}")
            sys.exit(1)
    info("All chapters generation finished (or were already complete).")

# Final QA

def cmd_qa(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    # assemble final course markdown
    outline = load_json(c.outline_path)
    chapters = outline.get("chapters", [])
    final_md = []
    for ch in chapters:
        fname = c.drafts_path / f"ch{int(ch.get('number')):02d}.md"
        if not fname.exists():
            error(f"Missing chapter draft: {fname}. Run chapter generation first.")
            sys.exit(1)
        text = fname.read_text(encoding="utf-8")
        final_md.append(f"# Chapter {ch.get('number')}: {ch.get('title')}\n\n")
        final_md.append(text)
        final_md.append("\n\n")
    final_content = "\n".join(final_md)
    (c.final_path / "final_course.md").write_text(final_content, encoding="utf-8")
    # Run final QA prompt
    template = load_prompt("final_qa.txt")
    terminology = load_terminology(c.terminology_path)
    profile = c.profile_path.read_text(encoding="utf-8")
    context = {
        "course_profile": profile,
        "outline_json": outline,
        "terminology_json": terminology,
        "final_course_markdown": final_content
    }
    prompt = render_prompt(template, context)
    info("Running final course QA. This may be a longer call.")
    resp = call_llm(prompt, temperature=0.0)
    try:
        report = json.loads(resp)
        (c.final_path / "final_qa.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        status = report.get("status", "FAIL")
        if status != "PASS":
            error(f"Final QA failed: {report.get('critical_issues', [])}")
            sys.exit(1)
        else:
            info("Final QA passed.")
            state = load_json(c.generation_state_path)
            state["final_qa"] = True
            save_json(c.generation_state_path, state)
    except Exception:
        (c.final_path / "final_qa_raw.txt").write_text(resp, encoding="utf-8")
        error("Failed to parse final QA response as JSON. Saved raw output to final_qa_raw.txt")
        sys.exit(1)

# Typesetting: ask LLM to convert markdown chapter into LaTeX chapter file according to rules.

def typeset_chapter(c: Course, chapter_number: int) -> None:
    fname = c.drafts_path / f"ch{int(chapter_number):02d}.md"
    if not fname.exists():
        raise FileNotFoundError(f"Draft not found: {fname}")
    md = fname.read_text(encoding="utf-8")
    template = load_prompt("typesetter.txt")
    outline = load_json(c.outline_path)
    chap = next((ch for ch in outline.get("chapters", []) if int(ch.get("number")) == int(chapter_number)), None)
    context = {
        "chapter_number": chapter_number,
        "chapter_title": chap.get("title") if chap else f"Chapter {chapter_number}",
        "chapter_markdown": md,
        "terminology_json": load_terminology(c.terminology_path)
    }
    prompt = render_prompt(template, context)
    resp = call_llm(prompt, temperature=0.0)
    # Expect LaTeX content (no documentclass or begin/end document)
    texfile = c.tex_path / f"ch{int(chapter_number):02d}.tex"
    texfile.write_text(resp, encoding="utf-8")
    info(f"Wrote LaTeX chapter {texfile}")

def cmd_compile(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    state = load_json(c.generation_state_path)
    if not state.get("final_qa"):
        error("Final QA not completed. Run 'qa' before compiling.")
        sys.exit(1)
    # Typeset all chapters
    outline = load_json(c.outline_path)
    chapters = outline.get("chapters", [])
    for ch in chapters:
        typeset_chapter(c, int(ch.get("number")))
    # Create main.tex
    main = []
    main.append("\\documentclass[12pt]{report}\n")
    main.append("\\usepackage[a4paper,margin=1in]{geometry}\n")
    main.append("\\usepackage{lmodern}\n\\usepackage{microtype}\n\\usepackage{graphicx}\n\\usepackage{booktabs}\n\\usepackage{tabularx}\n\\usepackage{longtable}\n\\usepackage{array}\n\\usepackage{float}\n\\usepackage{enumitem}\n\\usepackage{amsmath}\n\\usepackage{amssymb}\n\\usepackage{parskip}\n\\usepackage{hyperref}\n\n")
    # Title page data from profile
    profile_text = c.profile_path.read_text(encoding="utf-8")
    title = "Lecture Notes"
    for line in profile_text.splitlines():
        if line.lower().startswith("course title:"):
            title = line.split(":",1)[1].strip() or title
    main.append("\\begin{document}\n")
    main.append("\\begin{titlepage}\n\\centering\n")
    main.append(f"\\Huge\\textbf{{{title}}}\\\\\n")
    main.append("\\vspace{1cm}\n\\end{titlepage}\n\\tableofcontents\n\\newpage\n")
    # Inputs
    for ch in chapters:
        fname = f"tex/ch{int(ch.get('number')):02d}.tex"
        main.append(f"\\input{{{fname}}}\n")
    main.append("\\end{document}\n")
    main_tex_path = c.path / "main.tex"
    main_tex_path.write_text("".join(main), encoding="utf-8")
    info(f"Wrote main.tex at {main_tex_path}")
    # Respect DRY_RUN: skip actual pdflatex and write a placeholder PDF
    if os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"):
        placeholder = c.output_pdf
        placeholder.parent.mkdir(parents=True, exist_ok=True)
        placeholder.write_bytes(b"%PDF-1.4\n% Dummy PDF produced in DRY_RUN mode\n")
        info(f"DRY_RUN: created placeholder PDF at {placeholder}")
        state["compiled"] = True
        save_json(c.generation_state_path, state)
        return
    # Run pdflatex twice in course dir
    old_cwd = os.getcwd()
    try:
        os.chdir(c.path)
        cmd = ["pdflatex", "-interaction=nonstopmode", "main.tex"]
        for i in range(2):
            info(f"Running LaTeX pass {i+1}...")
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode != 0:
                (c.path / "latex_error.log").write_bytes(res.stdout + b"\n\n" + res.stderr)
                error("LaTeX compilation failed. See latex_error.log in course folder.")
                sys.exit(1)
        # Move output to output.pdf
        built = c.path / "main.pdf"
        if built.exists():
            built.replace(c.output_pdf)
            info(f"PDF compiled: {c.output_pdf}")
            state["compiled"] = True
            save_json(c.generation_state_path, state)
        else:
            error("main.pdf not found after compilation")
            sys.exit(1)
    finally:
        os.chdir(old_cwd)

def cmd_build(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    # Run terminology if empty
    terminology = load_terminology(c.terminology_path)
    if not terminology.get("terms"):
        info("Running initial terminology extraction...")
        cmd_terminology(course_id)
    # Generate all missing chapters
    cmd_all(course_id)
    # Final QA
    cmd_qa(course_id)
    # Compile
    cmd_compile(course_id)

# --- Interactive mode and CLI ---
import re
from typing import Iterable


def format_course_dir_name(course_code: str, course_title: str) -> str:
    safe_code = "".join(ch for ch in course_code if ch.isalnum())
    safe_title = "".join(ch if (ch.isalnum() or ch.isspace()) else "" for ch in course_title)
    title_slug = "_".join(safe_title.strip().split())
    name = f"{safe_code}_{title_slug}" if title_slug else safe_code
    return name


def parse_outline_text_to_chapters(text: str) -> List[Dict[str, Any]]:
    # Heuristic parsing: look for lines starting with 'Chapter' or numeric headings or markdown headings
    chapters: List[Dict[str, Any]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    chapter_re = re.compile(r'^(?:Chapter\s+)?(\d{1,3})[:\.)\s-]*(.*)$', re.IGNORECASE)
    md_heading_re = re.compile(r'^#{1,3}\s+(.*)$')
    numbered_re = re.compile(r'^(\d{1,3})[\.:]\s+(.*)$')
    # First pass: collect candidate headings
    for ln in lines:
        m = chapter_re.match(ln)
        if m:
            num = int(m.group(1))
            title = m.group(2).strip() or f"Chapter {num}"
            chapters.append({"number": num, "title": title, "topic": ""})
            continue
        m = md_heading_re.match(ln)
        if m:
            title = m.group(1).strip()
            # try to see if title begins with a number
            m2 = re.match(r'^(\d{1,3})[\s\-:\.)]+(.*)$', title)
            if m2:
                num = int(m2.group(1))
                t = m2.group(2).strip() or f"Chapter {num}"
                chapters.append({"number": num, "title": t, "topic": ""})
            else:
                # treat as a heading; if no explicit number assign next
                chapters.append({"number": len(chapters) + 1, "title": title, "topic": ""})
            continue
        m = numbered_re.match(ln)
        if m:
            num = int(m.group(1))
            title = m.group(2).strip()
            chapters.append({"number": num, "title": title, "topic": ""})
    # If still empty, fallback: split by blank lines take first sentence as title
    if not chapters:
        paragraphs = re.split(r"\n\s*\n", text)
        for i, p in enumerate(paragraphs[:50], start=1):
            first_line = p.strip().splitlines()[0][:120]
            if len(first_line) > 0:
                chapters.append({"number": i, "title": first_line, "topic": ""})
    # Ensure unique, sorted by number
    seen = set()
    unique: List[Dict[str, Any]] = []
    for ch in sorted(chapters, key=lambda x: x["number"]):
        if ch["number"] in seen:
            continue
        seen.add(ch["number"])
        unique.append(ch)
    return unique


def parse_outline_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Outline file not found: {path}")
    ext = path.suffix.lower()
    text = ""
    if ext == ".json":
        data = load_json(path)
        # If JSON already has chapters and metadata, return as-is
        return data
    elif ext in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8")
    elif ext == ".docx":
        try:
            import docx
        except Exception:
            raise RuntimeError("python-docx is required to parse .docx outlines. Install via requirements.txt")
        doc = docx.Document(str(path))
        text = "\n".join(p.text for p in doc.paragraphs)
    elif ext == ".pdf":
        try:
            from PyPDF2 import PdfReader
        except Exception:
            raise RuntimeError("PyPDF2 is required to parse .pdf outlines. Install via requirements.txt")
        reader = PdfReader(str(path))
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                pages.append("")
        text = "\n".join(pages)
    else:
        # attempt to read as text
        text = path.read_text(encoding="utf-8", errors="ignore")
    chapters = parse_outline_text_to_chapters(text)
    outline = {
        "course_code": "",
        "course_title": "",
        "department": "",
        "university": "",
        "academic_session": "",
        "level": "",
        "chapters": chapters,
    }
    return outline


def write_course_profile_from_metadata(path: Path, metadata: Dict[str, Any]) -> None:
    template = textwrap.dedent(f"""
    # Course Profile

    Course Code: {metadata.get('course_code','')}
    Course Title: {metadata.get('course_title','')}
    University: {metadata.get('university','')}
    Department: {metadata.get('department','')}
    Academic Session: {metadata.get('academic_session','')}
    Level: {metadata.get('level','')}
    Prepared by: {metadata.get('prepared_by','')}

    ## Style Rules

    * Use clear academic English.
    * Explain concepts before assuming familiarity.
    * Prefer explanation over memorization.
    * Avoid filler.
    * Do not use em dashes.
    * Use consistent terminology.
    * Do not use conversational language.
    * Do not unnecessarily repeat explanations.
    """)
    path.write_text(template, encoding="utf-8")


def interactive_setup() -> str:
    # Welcome box
    print("╭" + "─" * 42 + "╮")
    print("│       University Lecture Note Generator  │")
    print("╰" + "─" * 42 + "╯\n")
    print("Let's create your lecture note. Press Ctrl+C to exit at any time.\n")
    # Check for resumable courses
    COURSES_DIR.mkdir(exist_ok=True)
    incomplete = []
    for p in COURSES_DIR.iterdir():
        if p.is_dir():
            state_file = p / "generation_state.json"
            if state_file.exists():
                try:
                    st = load_json(state_file)
                    chapters = st.get("chapters", {})
                    total_complete = sum(1 for v in chapters.values() if v == "complete")
                    if chapters and total_complete < max(1, len(chapters)):
                        incomplete.append((p.name, total_complete, len(chapters)))
                except Exception:
                    pass
    if incomplete:
        print("An incomplete course was found:\n")
        for i, (name, done, total) in enumerate(incomplete, start=1):
            print(f"[{i}] {name} — {done} of {total} chapters completed")
        choice = input("Resume an existing course? [y/N]: ").strip().lower()
        if choice == "y" or choice == "yes":
            sel = input("Enter the number of the course to resume: ").strip()
            try:
                idx = int(sel) - 1
                return incomplete[idx][0]
            except Exception:
                print("Invalid selection; starting a new course.")
    # New course setup
    course_code = input("Course code: ").strip()
    course_title = input("Course title: ").strip()
    level = input("Your year/level: ").strip()
    prepared_by = input("Your name: ").strip()
    department = input("Department: ").strip()
    academic_session = input("Academic session: ").strip()
    university = input("University: ").strip()
    # Outline input: offer paste option or file path
    outline_path = None
    outline_text: Optional[str] = None
    outline_name = ""
    paste_choice = input("Paste the outline into the terminal instead of providing a file? [y/N]: ").strip().lower()
    if paste_choice in ("y", "yes"):
        print("Paste your outline below. End with a single line containing only END (or Ctrl+D/Ctrl+Z):")
        lines: List[str] = []
        try:
            while True:
                ln = input()
                if ln.strip() == "END":
                    break
                lines.append(ln)
        except EOFError:
            # user finished input with EOF
            pass
        outline_text = "\n".join(lines).strip()
        if not outline_text:
            print("No outline text detected. Please provide an outline file instead.")
            # fall back to file prompt
        else:
            outline_name = "pasted_outline.md"
    if not outline_text:
        # ask for a file path
        while True:
            p = input("Course outline file: ").strip()
            ppath = Path(p)
            if ppath.exists():
                outline_path = ppath
                outline_name = ppath.name
                break
            print(f"File not found: {p}. Please try again.")
    # Source materials (optional)
    print("\nSource materials are optional. The generator works from the course outline and learning outcomes alone.")
    print("If you have slides or readings you want the generator to use, provide a path. Otherwise press Enter to skip.")
    source_materials = None
    while True:
        s = input("Path to file or directory with source materials (leave blank to skip): ").strip()
        if not s:
            # user chose to skip
            break
        spath = Path(s)
        if spath.exists():
            source_materials = spath
            break
        print(f"Path not found: {s}. Enter a valid path or press Enter to skip.")
    # Confirmation
    print("\nCourse\n" + "─" * 40)
    print(f"Code:       {course_code}")
    print(f"Title:      {course_title}")
    print(f"Level:      {level}")
    print(f"Prepared by: {prepared_by}")
    print(f"Department: {department}")
    print(f"University: {university}")
    print(f"Session:    {academic_session}")
    # Outline may have been pasted (outline_path is None). Use outline_name if available.
    outline_display = None
    if 'outline_path' in locals() and outline_path:
        outline_display = outline_path.name
    elif 'outline_name' in locals() and outline_name:
        outline_display = outline_name
    else:
        outline_display = "none provided"
    print(f"Outline:    {outline_display}")
    print("─" * 40)
    ready = input("Ready to generate your lecture note? [Y/n]: ").strip().lower()
    if ready in ("n", "no"):
        print("Aborted by user.")
        sys.exit(0)
    # Create course dir name
    course_dir_name = format_course_dir_name(course_code, course_title)
    course_dir = COURSES_DIR / course_dir_name
    if course_dir.exists():
        print(f"Course directory {course_dir} already exists. Resuming or using existing data.")
    else:
        cmd_init(course_dir_name)
    # Parse outline and write outline.json
    if outline_path:
        parsed_outline = parse_outline_file(outline_path)
    else:
        # outline_text was provided via paste; parse heuristically
        parsed_outline = {
            "course_code": "",
            "course_title": "",
            "department": "",
            "university": "",
            "academic_session": "",
            "level": "",
            "chapters": parse_outline_text_to_chapters(outline_text or "")
        }
    # populate metadata
    parsed_outline["course_code"] = course_code
    parsed_outline["course_title"] = course_title
    parsed_outline["department"] = department
    parsed_outline["university"] = university
    parsed_outline["academic_session"] = academic_session
    parsed_outline["level"] = level
    parsed_outline["prepared_by"] = prepared_by
    # Save outline.json
    (course_dir / "outline.json").write_text(json.dumps(parsed_outline, indent=2, ensure_ascii=False), encoding="utf-8")
    # If outline was pasted, save the original text for provenance
    if not outline_path and outline_text:
        (course_dir / (outline_name or "pasted_outline.md")).write_text(outline_text, encoding="utf-8")
    # Save profile
    write_course_profile_from_metadata(course_dir / "course_profile.md", parsed_outline)
    # Ensure terminology and generation_state exist
    save_json(course_dir / "terminology.json", {"terms": {}})
    save_json(course_dir / "generation_state.json", {"status": "in_progress", "chapters": {}, "final_qa": False, "compiled": False})
    # Copy prompts
    repo_prompts = PROMPTS_DIR
    if repo_prompts.exists():
        for file in repo_prompts.iterdir():
            if file.is_file():
                shutil.copy(file, course_dir / "prompts" / file.name)
    # Optionally copy source materials path into course folder for later use
    if source_materials:
        dest = course_dir / "sources"
        if source_materials.is_dir():
            shutil.copytree(source_materials, dest, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source_materials, dest / source_materials.name)
    print("\nCourse initialized\n")
    # Run initial terminology extraction
    try:
        cmd_terminology(course_dir_name)
    except Exception as e:
        error(f"Initial terminology extraction failed: {e}")
        sys.exit(1)
    # Generate all chapters
    try:
        cmd_all(course_dir_name)
    except Exception as e:
        error(f"Chapter generation stopped: {e}")
        sys.exit(1)
    # Final QA
    try:
        cmd_qa(course_dir_name)
    except Exception as e:
        error(f"Final QA failed: {e}")
        sys.exit(1)
    # Compile
    try:
        cmd_compile(course_dir_name)
    except Exception as e:
        error(f"Compilation failed: {e}")
        sys.exit(1)
    print("\nAll done. Your lecture note is ready.")
    print(f"Output: {COURSES_DIR / course_dir_name / 'output.pdf'}")
    return course_dir_name


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Lecture note generator CLI")
    subparsers = parser.add_subparsers(dest="cmd")

    sp_init = subparsers.add_parser("init")
    sp_init.add_argument("course_id")

    sp_profile = subparsers.add_parser("profile")
    sp_profile.add_argument("course_id")

    sp_term = subparsers.add_parser("terminology")
    sp_term.add_argument("course_id")

    sp_ch = subparsers.add_parser("chapter")
    sp_ch.add_argument("course_id")
    sp_ch.add_argument("chapter_number", type=int)

    sp_all = subparsers.add_parser("all")
    sp_all.add_argument("course_id")

    sp_qa = subparsers.add_parser("qa")
    sp_qa.add_argument("course_id")

    sp_compile = subparsers.add_parser("compile")
    sp_compile.add_argument("course_id")

    sp_build = subparsers.add_parser("build")
    sp_build.add_argument("course_id")

    args = parser.parse_args(argv)
    # If no command provided, run interactive setup and generation
    if not args.cmd:
        try:
            interactive_setup()
            return
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(1)
    if args.cmd == "init":
        cmd_init(args.course_id)
    elif args.cmd == "profile":
        cmd_profile(args.course_id)
    elif args.cmd == "terminology":
        cmd_terminology(args.course_id)
    elif args.cmd == "chapter":
        cmd_chapter(args.course_id, args.chapter_number)
    elif args.cmd == "all":
        cmd_all(args.course_id)
    elif args.cmd == "qa":
        cmd_qa(args.course_id)
    elif args.cmd == "compile":
        cmd_compile(args.course_id)
    elif args.cmd == "build":
        cmd_build(args.course_id)
    else:
        error(f"Unknown command: {args.cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
