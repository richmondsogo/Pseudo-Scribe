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
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

# Load .env if present so environment variables in .env are available at runtime
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # If python-dotenv is not installed, continue — environment may be set externally
    pass

# Environment-driven configuration
# Default provider set to Gemini (Google) for this deployment
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
# Default model name is a Gemini text model. Override with GEMINI_MODEL or LLM_MODEL.
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
MAX_CHAPTER_RETRIES = int(os.getenv("MAX_CHAPTER_RETRIES", "2"))
# Retries for transient API failures (500/503/429/timeouts) on a single call_llm() call,
# separate from MAX_CHAPTER_RETRIES which re-runs a whole chapter after a QA failure.
MAX_API_RETRIES = int(os.getenv("MAX_API_RETRIES", "5"))
API_RETRY_BASE_DELAY = float(os.getenv("API_RETRY_BASE_DELAY", "2.0"))
# Cap on how much of each chapter is sent to the final course-wide QA pass. Keeps that single
# call's size predictable regardless of how many/how long the chapters are, instead of scaling
# with the whole course (which is what blew past a 6000 TPM free-tier limit in practice).
FINAL_QA_EXCERPT_CHARS = int(os.getenv("FINAL_QA_EXCERPT_CHARS", "1000"))
# Optional: route the two token-heavy calls (final QA, per-chapter typesetting) to a different
# provider than everything else. Useful because these two calls are infrequent but large
# (won't fit a small free-tier TPM budget), while chapter writing/QA calls are frequent but
# small — a low-TPM/high-RPD provider suits the latter, a high-context provider suits the
# former, and you may want different providers for each. Falls back to LLM_PROVIDER if unset.
HEAVY_CALL_PROVIDER = os.getenv("HEAVY_CALL_PROVIDER")
# Both default OFF to minimize LLM calls per chapter. Chapters are now written directly as
# LaTeX (see prompts/chapter_writer.txt), which already removes the separate typesetting call;
# these two remove the per-chapter QA call and the LLM-based conflict-check call. Conflicts are
# still detected and logged when this is off — they're just resolved by always keeping the
# first definition, without spending a call asking the model whether it's a "real" conflict.
# Turn either back on if you have quota to spare and want the extra scrutiny.
ENABLE_CHAPTER_QA = os.getenv("ENABLE_CHAPTER_QA", "0").lower() in ("1", "true", "yes")
ENABLE_CONFLICT_CHECK = os.getenv("ENABLE_CONFLICT_CHECK", "0").lower() in (
    "1",
    "true",
    "yes",
)
# Chapters can generate concurrently via a thread pool. Defaults to 1 (sequential) deliberately:
# concurrency doesn't reduce the *total* number of API calls a course needs (that's what actually
# trips daily-request quotas), and it makes several chapters' calls land in the same short window,
# which is exactly what trips per-minute (TPM/RPM) quotas. Raise this only if you have quota to
# spare (a paid tier, or a generous provider) and want faster wall-clock time.
try:
    MAX_CONCURRENT_CHAPTERS = max(1, int(os.getenv("MAX_CONCURRENT_CHAPTERS", "1")))
except ValueError:
    MAX_CONCURRENT_CHAPTERS = 1
# Protects generation_state.json read-modify-write cycles when chapters run concurrently.
STATE_LOCK = threading.Lock()
# Thread-safe count of LLM calls made this run, surfaced in the run summary.
LLM_CALL_COUNT = 0
_LLM_CALL_COUNT_LOCK = threading.Lock()

# Repository root assumed to be current working directory when running
REPO_ROOT = Path(__file__).resolve().parent
COURSES_DIR = REPO_ROOT / "courses"
PROMPTS_DIR = REPO_ROOT / "prompts"


# Simple logging
def info(msg: str) -> None:
    print(msg)


def error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


# --- Run-wide warnings ---
# Collected instead of hard-stopping the pipeline. Printed as a summary at the end
# of a hands-off run (interactive_setup / cmd_build) and saved to run_warnings.json
# in the course folder so nothing is silently lost.
RUN_WARNINGS: List[str] = []


def warn(msg: str) -> None:
    RUN_WARNINGS.append(msg)
    print(f"WARNING: {msg}", file=sys.stderr)


def save_run_warnings(c: "Course") -> None:
    if RUN_WARNINGS:
        (c.path / "run_warnings.json").write_text(
            json.dumps(RUN_WARNINGS, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# --- Retry helper for transient API errors ---


def _is_transient_error(exc: Exception) -> bool:
    """Heuristic: retry on server-side / rate-limit / connectivity errors, not on
    things like bad API keys or malformed requests, which will never succeed on retry.
    """
    msg = str(exc).lower()
    transient_markers = (
        "500",
        "internal",
        "502",
        "503",
        "504",
        "unavailable",
        "429",
        "rate limit",
        "resource_exhausted",
        "quota",
        "timeout",
        "timed out",
        "deadline",
        "connection",
        "reset",
    )
    return any(marker in msg for marker in transient_markers)


def call_with_retry(
    fn, max_retries: int = MAX_API_RETRIES, base_delay: float = API_RETRY_BASE_DELAY
):
    """Call fn() with exponential backoff + jitter on transient errors.
    Re-raises immediately on non-transient errors, and re-raises the last error
    once retries are exhausted."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as e:
            attempt += 1
            if attempt > max_retries or not _is_transient_error(e):
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            info(
                f"  Transient API error ({e}). Retrying in {delay:.1f}s... (attempt {attempt}/{max_retries})"
            )
            time.sleep(delay)


# --- LLM wrapper ---


def call_llm(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    provider: Optional[str] = None,
) -> str:
    """Call the configured LLM provider (LLM_PROVIDER env var: 'gemini' or 'groq').
    Pass provider= to override LLM_PROVIDER for just this call (see HEAVY_CALL_PROVIDER).

    This function supports a DRY_RUN mode via the environment variable DRY_RUN=1|true which returns canned responses
    for a quick smoke test without making external API calls.
    """
    provider = (provider or LLM_PROVIDER).lower()
    global LLM_CALL_COUNT
    with _LLM_CALL_COUNT_LOCK:
        LLM_CALL_COUNT += 1
    # Deliberately NOT applying a generic model fallback here — each provider has its own
    # default model name, and leaking one provider's default into another would silently
    # send the wrong model name (e.g. a Gemini model string to the Groq API).
    temperature = temperature if temperature is not None else LLM_TEMPERATURE

    dry = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
    if dry:
        low = (prompt or "").lower()
        # Terminology conflict checker canned response
        if (
            "terminology conflict checker" in low
            or "decide whether the two definitions" in low
        ):
            return json.dumps(
                {"conflict": False, "reasoning": "Dry-run: assume no conflict."}
            )
        # Outline chapter extractor canned response
        if "outline chapter extractor" in low:
            return json.dumps(
                {
                    "chapters": [
                        {
                            "number": 1,
                            "title": "Dry-run Chapter One",
                            "topic": "sample topic A, sample topic B",
                        },
                        {
                            "number": 2,
                            "title": "Dry-run Chapter Two",
                            "topic": "sample topic C",
                        },
                        {
                            "number": 3,
                            "title": "Dry-run Chapter Three",
                            "topic": "sample topic D, sample topic E",
                        },
                    ]
                }
            )
        # Terminology extractor canned response
        if "terminology extractor" in low or "extract a compact terminology" in low:
            return json.dumps(
                {
                    "terms": {
                        "example_term": {
                            "preferred_term": "example_term",
                            "definition": "An example term used in dry run.",
                            "definition_status": "defined",
                            "introduced_in": 1,
                        }
                    }
                }
            )
        # Chapter writer canned response (terminology + chapter)
        if (
            "you are writing one chapter" in low
            or "[terminology]" in prompt
            or "[chapter]" in prompt
        ):
            term_json = {
                "new_term": {
                    "preferred_term": "new_term",
                    "definition": "A dry-run example term.",
                    "definition_status": "defined",
                    "introduced_in": None,
                }
            }
            chapter_md = "# Sample Chapter\n\nThis is a short sample chapter generated in dry-run mode.\n\n## Section 1\nSample content.\n\n## Conclusion\nShort conclusion.\n\n### Tutorial Questions\n1. Sample recall question\n2. Sample conceptual question\n3. Sample application question\n4. Sample comparison question\n5. Sample problem-solving question\n6. Sample extension question\n"
            return (
                "[TERMINOLOGY]\n"
                + json.dumps(term_json)
                + "\n[/TERMINOLOGY]\n\n[CHAPTER]\n"
                + chapter_md
                + "\n[/CHAPTER]"
            )
        # Chapter QA canned pass
        if "chapter qa assistant" in low or "chapter_markdown" in low:
            return json.dumps({"status": "PASS", "issues": [], "warnings": []})
        # Final QA canned pass
        if (
            "final-course qa" in low
            or "final course markdown" in low
            or "final_course_markdown" in low
        ):
            return json.dumps(
                {
                    "status": "PASS",
                    "critical_issues": [],
                    "warnings": [],
                    "coverage": {"complete": True, "missing": []},
                    "terminology_consistent": True,
                    "cross_chapter_consistent": True,
                }
            )
        # Typesetter canned LaTeX fragment
        if "typeset" in low or "latex" in low or "chapter_markdown" in low:
            return (
                "\\chapter{Sample Chapter}\n\\section{Introduction}\nSample content.\n"
            )
        return "DRY_RUN"

    if provider in ("gemini", "google", "googleai"):
        return _call_gemini(prompt, model, temperature)
    elif provider == "groq":
        return _call_groq(prompt, model, temperature)
    else:
        raise RuntimeError(
            f"Unsupported LLM_PROVIDER '{provider}'. Supported values: 'gemini', 'groq'. "
            f"Set it in your .env file."
        )


def _call_gemini(prompt: str, model: Optional[str], temperature: float) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY or GOOGLE_API_KEY must be set to use the gemini provider"
        )

    gmodel = (
        model
        or os.getenv("GEMINI_MODEL")
        or os.getenv("LLM_MODEL")
        or "gemini-3.6-flash"
    )

    try:
        from google import genai
    except Exception as e:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from e

    try:
        client = genai.Client(api_key=api_key)
        resp = call_with_retry(
            lambda: client.models.generate_content(model=gmodel, contents=prompt)
        )
    except Exception as e:
        raise RuntimeError(f"Gemini (google.genai) call failed: {e}")

    out = getattr(resp, "text", None)
    if not out:
        out = str(resp)
    return out


def _call_groq(prompt: str, model: Optional[str], temperature: float) -> str:
    """Groq (https://groq.com) hosts open models (Llama 3.3, GPT-OSS, Qwen, etc.) with a free
    tier that, at the time of writing, allows far more requests/day than Gemini's free tier
    for its current flagship Flash model. OpenAI-compatible endpoint, called here with stdlib
    urllib so no extra dependency is required. Sign up at https://console.groq.com for a key.
    Rate/quota numbers change over time — check https://console.groq.com/docs/rate-limits for
    current figures before relying on a specific model's daily allowance."""
    import urllib.request
    import urllib.error

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY must be set to use the groq provider")

    gmodel = model or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"

    body = json.dumps(
        {
            "model": gmodel,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
    ).encode("utf-8")

    def do_request() -> str:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                # Cloudflare (which fronts Groq's API) blocks urllib's default
                # "Python-urllib/x.y" User-Agent as a bot signature (HTTP 403, error 1010).
                # Any normal-looking UA avoids that; this doesn't need to be literally accurate.
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PseudoScribe/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as http_resp:
                data = json.loads(http_resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"{e.code} {e.reason}. {err_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Groq request failed: {e.reason}")
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected Groq response shape: {data}") from e

    try:
        return call_with_retry(do_request)
    except Exception as e:
        raise RuntimeError(f"Groq call failed: {e}")


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
def definitions_conflict(
    existing_def: Optional[str], new_def: Optional[str]
) -> Tuple[bool, str]:
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
    try:
        resp = call_llm(prompt, temperature=0.0)
    except Exception as e:
        # Can't verify either way. Since the caller always keeps the first definition
        # regardless of this result, default to "no conflict" to avoid noisy false alarms.
        return False, f"conflict check unavailable ({e}); keeping existing definition"
    # Try to extract JSON (tolerates ```json fences or stray commentary around the object)
    try:
        parsed = _extract_json(resp)
        if isinstance(parsed, dict):
            return bool(parsed.get("conflict")), parsed.get("reasoning", "")
        # fallback simple parsing on the raw text if it wasn't a JSON object at all
        lc = resp.strip().lower()
        if "conflict" in lc and "true" in lc:
            return True, resp
        if "conflict" in lc and "false" in lc:
            return False, resp
        # otherwise be conservative
        return True, "Unclear from checker response; conservatively flagging conflict"
    except Exception:
        return (
            True,
            "Failed to parse checker response; conservatively flagging conflict",
        )


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
    outline = {"course_code": course_id, "course_title": "", "chapters": []}
    save_json(p / "outline.json", outline)
    # empty terminology
    save_json(p / "terminology.json", {"terms": {}})
    # generation_state
    state = {
        "status": "not_started",
        "chapters": {},
        "final_qa": False,
        "compiled": False,
    }
    save_json(p / "generation_state.json", state)
    # copy prompt templates from repo prompts if present
    repo_prompts = PROMPTS_DIR
    if repo_prompts.exists():
        for file in repo_prompts.iterdir():
            if file.is_file():
                shutil.copy(file, p / "prompts" / file.name)
    info(
        "Initialization complete. Edit course_profile.md and outline.json then run terminology extraction."
    )


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
        """)
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
        save_json(
            c.generation_state_path,
            {
                "status": "in_progress",
                "chapters": {},
                "final_qa": False,
                "compiled": False,
            },
        )


def cmd_terminology(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    outline = load_json(c.outline_path)
    profile = c.profile_path.read_text(encoding="utf-8")
    terminology_template = load_prompt("terminology_extractor.txt")
    context = {
        "course_profile": profile,
        "outline_json": outline,
        "source_materials": "",
    }
    prompt = render_prompt(terminology_template, context)
    info("Calling LLM for initial terminology extraction (cost-conscious prompt)...")
    try:
        resp = call_llm(prompt)
    except Exception as e:
        # Non-fatal: chapters still declare their own terms as they're written,
        # so a failed upfront extraction just means terminology.json starts empty.
        warn(
            f"Terminology extraction call failed ({e}). Continuing with empty terminology; "
            f"terms will still be captured as chapters declare them."
        )
        return
    # Expect JSON list or object: try to extract JSON
    terms = {}
    try:
        # model should return JSON structure {"terms": {...}}
        data = _extract_json(resp)
        if isinstance(data, dict) and "terms" in data:
            terms = data["terms"]
        else:
            # allow list of entries
            if isinstance(data, list):
                for entry in data:
                    term_key = entry.get("term") or entry.get("preferred_term")
                    if term_key:
                        terms[term_key] = entry
    except Exception:
        # Non-fatal: save raw response for inspection and move on with no pre-seeded terms.
        (c.path / "terminology_raw.txt").write_text(resp, encoding="utf-8")
        warn(
            "Failed to parse terminology extractor output as JSON. Saved raw response to "
            "terminology_raw.txt. Continuing with empty terminology."
        )
        return
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
            "definition_status": (
                v.get("definition_status") if isinstance(v, dict) else "undefined"
            ),
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
        raw = text[term_start + len("[TERMINOLOGY]") : term_end].strip()
        # try JSON
        try:
            parsed = _extract_json(raw)
            # allow {"terms": {...}}
            if isinstance(parsed, dict) and "terms" in parsed:
                terms = parsed["terms"]
            elif isinstance(parsed, dict):
                terms = parsed
        except Exception:
            # Non-fatal: this chapter just won't contribute new terms this round.
            terms = {}
    if chap_start != -1 and chap_end != -1:
        chapter = text[chap_start + len("[CHAPTER]") : chap_end].strip()
    else:
        # If markers not present, assume whole response is chapter
        chapter = text.strip()
    return terms, chapter


def _set_chapter_state(c: Course, chapter_number: int, status: str) -> None:
    """Thread-safe read-modify-write of generation_state.json's per-chapter status."""
    with STATE_LOCK:
        state = load_json(c.generation_state_path)
        state.setdefault("chapters", {})[str(chapter_number)] = status
        save_json(c.generation_state_path, state)


TERMINOLOGY_LOCK = threading.Lock()


def _merge_chapter_terms(
    c: Course, chapter_number: int, proposed_terms: Dict[str, Any]
) -> int:
    """Thread-safe: merge one chapter's proposed terms into terminology.json immediately, so
    later chapters (even running concurrently) see the growing registry. Auto-resolves conflicts
    by always keeping the first definition — the LLM-based check (ENABLE_CONFLICT_CHECK) only
    changes whether that's logged as a genuine conflict or silently accepted as a restatement,
    never which definition wins. Returns the count of newly added terms."""
    with TERMINOLOGY_LOCK:
        terminology_json = load_terminology(c.terminology_path)
        loaded_terms = terminology_json.get("terms", {})
        added = 0
        for term_key, term_val in proposed_terms.items():
            if isinstance(term_val, str):
                pref = term_val
                ddef = None
                status = "undefined"
            elif isinstance(term_val, dict):
                pref = term_val.get("preferred_term") or term_key
                ddef = term_val.get("definition")
                status = term_val.get("definition_status") or (
                    "defined" if ddef else "undefined"
                )
            else:
                continue
            if pref in loaded_terms:
                existing = loaded_terms[pref]
                if ENABLE_CONFLICT_CHECK:
                    cflag, reasoning = definitions_conflict(
                        existing.get("definition"), ddef
                    )
                    if cflag:
                        warn(
                            f"Chapter {chapter_number}: term '{pref}' was redefined differently "
                            f"({reasoning}). Keeping the original definition from chapter "
                            f"{existing.get('introduced_in')}."
                        )
                elif ddef and ddef != existing.get("definition"):
                    warn(
                        f"Chapter {chapter_number}: term '{pref}' was redefined. Keeping the "
                        f"original definition from chapter {existing.get('introduced_in')}."
                    )
                # Existing definition is always kept — no overwrite either way.
            else:
                loaded_terms[pref] = {
                    "preferred_term": pref,
                    "definition": ddef,
                    "definition_status": status,
                    "introduced_in": int(chapter_number),
                }
                added += 1
        terminology_json["terms"] = loaded_terms
        save_terminology(c.terminology_path, terminology_json)
        return added


def generate_chapter_content(
    c: Course,
    chapter_number: int,
    chap: Dict[str, Any],
    total_chapters: int,
    max_retries: int = MAX_CHAPTER_RETRIES,
) -> Dict[str, Any]:
    """Generates one chapter directly as LaTeX (no separate typesetting call). Thread-safe:
    reads a fresh terminology snapshot each attempt and merges its own proposed terms back in
    under a lock immediately after generating, so this is safe to run concurrently across
    chapters via cmd_all's thread pool (default concurrency is 1 — see MAX_CONCURRENT_CHAPTERS).
    Never raises for recoverable failures — returns a result dict so a batch runner can collect
    outcomes without one chapter's failure affecting the others."""
    title = chap.get("title") or f"Chapter {chapter_number}"
    profile = c.profile_path.read_text(encoding="utf-8")
    outline = load_json(c.outline_path)
    chapter_writer_template = load_prompt("chapter_writer.txt")

    attempts = 0
    last_issues: Any = None
    chapter_body: Optional[str] = None
    while attempts < max_retries:
        attempts += 1
        info(
            f"[chapter {chapter_number}] [Attempt {attempts}/{max_retries}] Generating ..."
        )
        terminology_snapshot = load_terminology(c.terminology_path)
        context = {
            "course_profile": profile,
            "outline_json": outline,
            "terminology_json": terminology_snapshot,
            "chapter_number": chapter_number,
            "chapter_title": chap.get("title"),
            "chapter_topic": chap.get("topic"),
            "source_materials": "",
        }
        prompt = render_prompt(chapter_writer_template, context)
        try:
            resp = call_llm(prompt)
        except Exception as e:
            last_issues = f"LLM call failed: {e}"
            warn(
                f"[chapter {chapter_number}] generation attempt {attempts} failed ({e})."
            )
            continue
        proposed_terms, chapter_body = parse_generation_output(resp)
        if not chapter_body.strip():
            last_issues = "Response had no usable chapter content"
            warn(
                f"[chapter {chapter_number}] attempt {attempts} produced no chapter content; retrying."
            )
            chapter_body = None
            continue

        new_term_count = _merge_chapter_terms(c, chapter_number, proposed_terms)
        # Save the chapter (LaTeX). Kept at drafts/chXX.md so the rest of the pipeline (state
        # tracking, final assembly) doesn't need to change; only the content format changed.
        ch_filename = f"ch{int(chapter_number):02d}.md"
        (c.drafts_path / ch_filename).write_text(chapter_body, encoding="utf-8")
        info(
            f"[chapter {chapter_number}] Draft written to {c.drafts_path / ch_filename}"
        )

        if not ENABLE_CHAPTER_QA:
            info(
                f"[{chapter_number}/{total_chapters}] {title}\n  - Generated\n  - {new_term_count} new terms added"
            )
            _set_chapter_state(c, chapter_number, "complete")
            return {"status": "complete", "chapter": chapter_number}

        # Optional: per-chapter QA call, only if explicitly enabled.
        try:
            qa_result = run_chapter_qa(c, chapter_body, chapter_number)
        except Exception as e:
            warn(
                f"[chapter {chapter_number}] QA call failed ({e}). Keeping the draft as generated."
            )
            qa_result = {
                "status": "PASS",
                "issues": [],
                "warnings": [f"QA call failed: {e}"],
            }
        if qa_result.get("status") == "PASS":
            info(
                f"[{chapter_number}/{total_chapters}] {title}\n  - Generated\n  - {new_term_count} new terms added\n  - Chapter QA passed"
            )
            _set_chapter_state(c, chapter_number, "complete")
            return {"status": "complete", "chapter": chapter_number}
        else:
            issues = qa_result.get("issues", [])
            warnings_list = qa_result.get("warnings", [])
            last_issues = issues if issues else warnings_list
            info(
                f"[{chapter_number}/{total_chapters}] {title}\n  - Generated\n  - {new_term_count} new terms added\n  - Chapter QA flagged: {last_issues}"
            )
            _set_chapter_state(c, chapter_number, "failed")
            # loop retries if attempts remain

    # Retries exhausted: never kill the run. Keep whatever we have and move on.
    if chapter_body:
        warn(
            f"[chapter {chapter_number}] did not pass QA after {attempts} attempts ({last_issues}). "
            f"Keeping the last draft and moving on."
        )
        _set_chapter_state(c, chapter_number, "complete_with_warnings")
        return {"status": "complete_with_warnings", "chapter": chapter_number}
    else:
        warn(
            f"[chapter {chapter_number}] could not be generated after {attempts} attempts ({last_issues}). "
            f"No draft available — it will be skipped when assembling the final document."
        )
        _set_chapter_state(c, chapter_number, "failed")
        return {
            "status": "failed",
            "chapter": chapter_number,
            "error": str(last_issues),
        }


def run_chapter_qa(
    c: Course, chapter_markdown: str, chapter_number: Optional[int] = None
) -> Dict[str, Any]:
    template = load_prompt("chapter_qa.txt")
    outline = load_json(c.outline_path)
    profile = c.profile_path.read_text(encoding="utf-8")
    terminology = load_terminology(c.terminology_path)
    context = {
        "course_profile": profile,
        "outline_json": outline,
        "terminology_json": terminology,
        "chapter_markdown": chapter_markdown,
    }
    prompt = render_prompt(template, context)
    resp = call_llm(prompt, temperature=0.0)
    # Expect JSON object
    try:
        parsed = _extract_json(resp)
        if not isinstance(parsed, dict):
            raise ValueError("QA response was not a JSON object")
        return parsed
    except Exception:
        # Save raw — suffixed per-chapter so concurrent chapters don't clobber each other's debug file.
        suffix = f"_ch{chapter_number:02d}" if chapter_number else ""
        (c.path / f"chapter_qa_raw{suffix}.txt").write_text(resp, encoding="utf-8")
        warn(
            f"Failed to parse chapter QA response as JSON. Saved raw output to chapter_qa_raw{suffix}.txt"
        )
        return {"status": "FAIL", "issues": ["Invalid QA response format"]}


def cmd_chapter(course_id: str, chapter_number: int) -> None:
    c = Course.load(course_id)
    if not c.path.exists():
        error("Course not found. Run 'init' first.")
        sys.exit(1)
    try:
        require_course_files(c)
        outline = load_json(c.outline_path)
        chapters = outline.get("chapters", [])
        chap = next(
            (ch for ch in chapters if int(ch.get("number")) == int(chapter_number)),
            None,
        )
        if not chap:
            error(f"Chapter {chapter_number} not found in outline.json")
            sys.exit(1)
        result = generate_chapter_content(c, chapter_number, chap, len(chapters))
    except Exception as e:
        error(str(e))
        sys.exit(1)
    if result.get("status") == "failed":
        error(f"Chapter {chapter_number} failed: {result.get('error')}")
        sys.exit(1)


def cmd_all(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    outline = load_json(c.outline_path)
    chapters = outline.get("chapters", [])
    total = len(chapters)
    state = load_json(c.generation_state_path)
    chapter_state = state.get("chapters", {})
    to_generate = [
        ch
        for ch in chapters
        if chapter_state.get(str(int(ch.get("number"))))
        not in ("complete", "complete_with_warnings")
    ]
    already_done = total - len(to_generate)
    if already_done:
        info(f"{already_done} chapter(s) already complete, skipping.")
    if not to_generate:
        info("No chapters need generation.")
        return
    info(
        f"Generating {len(to_generate)} chapter(s) for {course_id} "
        f"(concurrency={MAX_CONCURRENT_CHAPTERS})"
    )
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CHAPTERS) as ex:
        future_map = {
            ex.submit(
                generate_chapter_content, c, int(ch.get("number")), ch, total
            ): int(ch.get("number"))
            for ch in to_generate
        }
        for fut in as_completed(future_map):
            num = future_map[fut]
            try:
                fut.result()
            except Exception as e:
                # generate_chapter_content shouldn't raise for recoverable failures, but if
                # something unexpected slips through, don't let it kill the other chapters.
                warn(
                    f"Chapter {num} raised an unexpected error ({e}). Skipping and continuing."
                )
    info("All chapters generation finished (or were already complete).")


# Final QA


def cmd_qa(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    # assemble final course markdown (this is the real, complete deliverable — untouched below)
    outline = load_json(c.outline_path)
    chapters = outline.get("chapters", [])
    final_md = []
    qa_excerpt_md = []
    included = 0
    for ch in chapters:
        fname = c.drafts_path / f"ch{int(ch.get('number')):02d}.md"
        if not fname.exists():
            warn(
                f"Missing chapter draft: {fname}. Excluding chapter {ch.get('number')} from the final document."
            )
            continue
        text = fname.read_text(encoding="utf-8")
        final_md.append(f"# Chapter {ch.get('number')}: {ch.get('title')}\n\n")
        final_md.append(text)
        final_md.append("\n\n")
        # For the QA call only: a bounded excerpt, not the full chapter. Full text scales with
        # course length and will eventually exceed any free-tier per-minute token budget — the
        # excerpt still lets the model judge terminology use, tone, and coverage per chapter.
        excerpt = text[:FINAL_QA_EXCERPT_CHARS]
        if len(text) > FINAL_QA_EXCERPT_CHARS:
            excerpt += "\n...[chapter truncated for this QA pass; the full chapter is complete in final_course.md]..."
        qa_excerpt_md.append(
            f"# Chapter {ch.get('number')}: {ch.get('title')}\n\n{excerpt}\n\n"
        )
        included += 1
    final_content = "\n".join(final_md)
    (c.final_path / "final_course.md").write_text(final_content, encoding="utf-8")
    if included == 0:
        warn("No chapter drafts were available to assemble. Skipping final QA.")
        return
    qa_content = "\n".join(qa_excerpt_md)
    # Run final QA prompt
    template = load_prompt("final_qa.txt")
    terminology = load_terminology(c.terminology_path)
    profile = c.profile_path.read_text(encoding="utf-8")
    context = {
        "course_profile": profile,
        "outline_json": outline,
        "terminology_json": terminology,
        "final_course_markdown": qa_content,
    }
    prompt = render_prompt(template, context)
    info("Running final course QA. This may be a longer call.")
    state = load_json(c.generation_state_path)
    heavy_provider = os.getenv("HEAVY_CALL_PROVIDER") or LLM_PROVIDER
    try:
        resp = call_llm(prompt, temperature=0.0, provider=heavy_provider)
    except Exception as e:
        warn(
            f"Final QA call failed ({e}). Proceeding to compile without a final QA report."
        )
        state["final_qa"] = True
        state["final_qa_passed"] = None
        save_json(c.generation_state_path, state)
        return
    try:
        report = _extract_json(resp)
        if not isinstance(report, dict):
            raise ValueError("Final QA response was not a JSON object")
        (c.final_path / "final_qa.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        status = report.get("status", "FAIL")
        state["final_qa"] = True
        state["final_qa_passed"] = status == "PASS"
        save_json(c.generation_state_path, state)
        if status != "PASS":
            warn(
                f"Final QA flagged issues (proceeding anyway): {report.get('critical_issues', [])}"
            )
        else:
            info("Final QA passed.")
    except Exception:
        (c.final_path / "final_qa_raw.txt").write_text(resp, encoding="utf-8")
        warn(
            "Failed to parse final QA response as JSON. Saved raw output to final_qa_raw.txt. Proceeding to compile."
        )
        state["final_qa"] = True
        state["final_qa_passed"] = None
        save_json(c.generation_state_path, state)


# Typesetting: ask LLM to convert markdown chapter into LaTeX chapter file according to rules.


def _looks_like_latex(text: str) -> bool:
    """Detects whether a draft is already LaTeX (written directly by the current
    chapter_writer.txt) vs. old-style Markdown from before that change."""
    head = text.strip()[:300]
    return bool(re.search(r"\\(chapter|section)\s*\{", head))


def typeset_chapter(c: Course, chapter_number: int) -> bool:
    """Returns True if a .tex file was written for this chapter, False if it had to be skipped."""
    texfile = c.tex_path / f"ch{int(chapter_number):02d}.tex"
    if texfile.exists():
        info(f"Chapter {chapter_number} already typeset. Skipping (no LLM call).")
        return True
    fname = c.drafts_path / f"ch{int(chapter_number):02d}.md"
    if not fname.exists():
        warn(f"No draft for chapter {chapter_number}; skipping it in the compiled PDF.")
        return False
    draft_content = fname.read_text(encoding="utf-8")

    if _looks_like_latex(draft_content):
        # Chapter was already written directly as LaTeX — just place it, no LLM call needed.
        c.tex_path.mkdir(parents=True, exist_ok=True)
        texfile.write_text(draft_content, encoding="utf-8")
        info(f"Wrote LaTeX chapter {texfile} (no LLM call — chapter was already LaTeX)")
        return True

    # Fallback for older Markdown drafts (from before chapters were written directly as LaTeX):
    # one LLM call to convert, same as the original pipeline. One-time cost per such chapter.
    template = load_prompt("typesetter.txt")
    outline = load_json(c.outline_path)
    chap = next(
        (
            ch
            for ch in outline.get("chapters", [])
            if int(ch.get("number")) == int(chapter_number)
        ),
        None,
    )
    context = {
        "chapter_number": chapter_number,
        "chapter_title": chap.get("title") if chap else f"Chapter {chapter_number}",
        "chapter_markdown": draft_content,
        "terminology_json": load_terminology(c.terminology_path),
    }
    prompt = render_prompt(template, context)
    try:
        resp = call_llm(
            prompt,
            temperature=0.0,
            provider=os.getenv("HEAVY_CALL_PROVIDER") or LLM_PROVIDER,
        )
    except Exception as e:
        warn(
            f"Typesetting chapter {chapter_number} failed ({e}). Skipping it in the compiled PDF "
            f"(the markdown draft is still available at {fname})."
        )
        return False
    texfile.write_text(resp, encoding="utf-8")
    info(f"Wrote LaTeX chapter {texfile}")
    return True


def cmd_compile(course_id: str) -> None:
    c = Course.load(course_id)
    require_course_files(c)
    state = load_json(c.generation_state_path)
    if not state.get("final_qa"):
        warn("Final QA wasn't run before compiling. Proceeding anyway.")
    # Typeset all chapters; collect which ones actually produced a .tex file.
    outline = load_json(c.outline_path)
    chapters = outline.get("chapters", [])
    typeset_ok: List[Dict[str, Any]] = []
    for ch in chapters:
        if typeset_chapter(c, int(ch.get("number"))):
            typeset_ok.append(ch)
    if not typeset_ok:
        warn(
            "No chapters could be typeset to LaTeX. No PDF will be produced this run — your "
            f"chapter drafts are still available as markdown in {c.drafts_path}."
        )
        return
    # Create main.tex (only for chapters that were successfully typeset)
    main = []
    main.append("\\documentclass[12pt]{report}\n")
    main.append("\\usepackage[a4paper,margin=1in]{geometry}\n")
    main.append(
        "\\usepackage{lmodern}\n\\usepackage{microtype}\n\\usepackage{graphicx}\n\\usepackage{booktabs}\n\\usepackage{tabularx}\n\\usepackage{longtable}\n\\usepackage{array}\n\\usepackage{float}\n\\usepackage{enumitem}\n\\usepackage{amsmath}\n\\usepackage{amssymb}\n\\usepackage{parskip}\n\\usepackage{hyperref}\n\n"
    )
    # Title page data from profile
    profile_text = c.profile_path.read_text(encoding="utf-8")
    title = "Lecture Notes"
    for line in profile_text.splitlines():
        if line.lower().startswith("course title:"):
            title = line.split(":", 1)[1].strip() or title
    main.append("\\begin{document}\n")
    main.append("\\begin{titlepage}\n\\centering\n")
    main.append(f"\\Huge\\textbf{{{title}}}\\\\\n")
    main.append("\\vspace{1cm}\n\\end{titlepage}\n\\tableofcontents\n\\newpage\n")
    # Inputs
    for ch in typeset_ok:
        fname = f"tex/ch{int(ch.get('number')):02d}.tex"
        main.append(f"\\input{{{fname}}}\n")
    main.append("\\end{document}\n")
    main_tex_path = c.path / "main.tex"
    main_tex_path.write_text("".join(main), encoding="utf-8")
    info(f"Wrote main.tex at {main_tex_path}")
    if len(typeset_ok) < len(chapters):
        warn(
            f"Only {len(typeset_ok)}/{len(chapters)} chapters made it into the PDF; "
            f"the rest are still available as markdown/tex where they got to."
        )
    # Respect DRY_RUN: skip actual pdflatex and write a placeholder PDF
    if os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"):
        placeholder = c.output_pdf
        placeholder.parent.mkdir(parents=True, exist_ok=True)
        placeholder.write_bytes(b"%PDF-1.4\n% Dummy PDF produced in DRY_RUN mode\n")
        info(f"DRY_RUN: created placeholder PDF at {placeholder}")
        state["compiled"] = True
        save_json(c.generation_state_path, state)
        return
    # Run pdflatex twice in course dir. pdflatex in -interaction=nonstopmode typically still
    # emits a PDF even when it hits recoverable errors, so we don't bail on a non-zero return
    # code alone — we check whether main.pdf actually exists afterward.
    old_cwd = os.getcwd()
    try:
        os.chdir(c.path)
        cmd = ["pdflatex", "-interaction=nonstopmode", "main.tex"]
        pdflatex_missing = False
        for i in range(2):
            info(f"Running LaTeX pass {i+1}...")
            try:
                res = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            except FileNotFoundError:
                warn(
                    "'pdflatex' isn't installed or isn't on PATH, so the PDF can't be compiled. "
                    "Install a LaTeX distribution (e.g. MiKTeX on Windows, TeX Live on macOS/Linux) "
                    f"to compile it yourself later — your LaTeX source is ready at {main_tex_path}."
                )
                pdflatex_missing = True
                break
            if res.returncode != 0:
                (c.path / "latex_error.log").write_bytes(
                    res.stdout + b"\n\n" + res.stderr
                )
                warn(
                    f"LaTeX pass {i+1} reported errors (see latex_error.log). Continuing to check "
                    f"whether a PDF was still produced."
                )
        if pdflatex_missing:
            return
        # Move output to output.pdf
        built = c.path / "main.pdf"
        if built.exists():
            built.replace(c.output_pdf)
            info(f"PDF compiled: {c.output_pdf}")
            state["compiled"] = True
            save_json(c.generation_state_path, state)
        else:
            warn(
                f"pdflatex did not produce a PDF. See latex_error.log in {c.path}. "
                f"Your LaTeX source is still available at {main_tex_path} to fix and compile manually."
            )
    finally:
        os.chdir(old_cwd)


def cmd_build(course_id: str) -> None:
    run_pipeline(course_id)


def print_run_summary(c: Course) -> None:
    """Hands-off runs never hard-stop, so this is the one place that tells you what you
    actually got: a PDF, a LaTeX source fallback, or markdown drafts — plus any warnings.
    """
    save_run_warnings(c)
    state = load_json(c.generation_state_path)
    chapters_state = state.get("chapters", {})
    outline_chapters = load_json(c.outline_path).get("chapters", [])
    total = len(outline_chapters)
    complete = sum(
        1
        for v in chapters_state.values()
        if v in ("complete", "complete_with_warnings")
    )
    with_warnings = sum(
        1 for v in chapters_state.values() if v == "complete_with_warnings"
    )
    print("\n" + "─" * 50)
    print("Run summary")
    print("─" * 50)
    suffix = f" ({with_warnings} with QA warnings)" if with_warnings else ""
    print(f"Chapters generated: {complete}/{total}{suffix}")
    print(f"LLM calls made this run: {LLM_CALL_COUNT}")
    if state.get("compiled") and c.output_pdf.exists():
        print(f"PDF ready:   {c.output_pdf}")
    elif (c.path / "main.tex").exists():
        print("PDF compile didn't complete, but LaTeX source is ready:")
        print(f"   {c.path / 'main.tex'}")
        print(f"   {c.tex_path} (per-chapter .tex files)")
    else:
        print("No PDF or .tex output this run. Markdown drafts are available:")
        print(f"   {c.drafts_path}")
    if RUN_WARNINGS:
        print(f"\n{len(RUN_WARNINGS)} warning(s) were recorded:")
        for w in RUN_WARNINGS[:10]:
            print(f"   - {w}")
        if len(RUN_WARNINGS) > 10:
            print(f"   ... and {len(RUN_WARNINGS) - 10} more.")
        print(f"Full list saved to {c.path / 'run_warnings.json'}")
    print("─" * 50)


# --- Interactive mode and CLI ---
import re
from typing import Iterable


def format_course_dir_name(course_code: str, course_title: str) -> str:
    safe_code = "".join(ch for ch in course_code if ch.isalnum())
    safe_title = "".join(
        ch if (ch.isalnum() or ch.isspace()) else "" for ch in course_title
    )
    title_slug = "_".join(safe_title.strip().split())
    name = f"{safe_code}_{title_slug}" if title_slug else safe_code
    return name


def parse_outline_text_to_chapters_heuristic(text: str) -> List[Dict[str, Any]]:
    # Regex-based fallback only. Used when the LLM-based extractor (the primary path) is
    # unavailable or fails to parse. See parse_outline_text_to_chapters_llm below.
    chapters: List[Dict[str, Any]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    chapter_re = re.compile(r"^(?:Chapter\s+)?(\d{1,3})[:\.)\s-]*(.*)$", re.IGNORECASE)
    md_heading_re = re.compile(r"^#{1,3}\s+(.*)$")
    numbered_re = re.compile(r"^(\d{1,3})[\.:]\s+(.*)$")
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
            m2 = re.match(r"^(\d{1,3})[\s\-:\.)]+(.*)$", title)
            if m2:
                num = int(m2.group(1))
                t = m2.group(2).strip() or f"Chapter {num}"
                chapters.append({"number": num, "title": t, "topic": ""})
            else:
                # treat as a heading; if no explicit number assign next
                chapters.append(
                    {"number": len(chapters) + 1, "title": title, "topic": ""}
                )
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


def _extract_json(text: str) -> Any:
    """Best-effort JSON extraction from an LLM response: strips ```json fences if present,
    and if that still doesn't parse, grabs the first balanced {...} block. Raises ValueError
    if nothing parseable is found."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    start = t.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(t)):
            if t[i] == "{":
                depth += 1
            elif t[i] == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(t[start : i + 1])
    raise ValueError("No JSON object found in response")


def parse_outline_text_to_chapters_llm(text: str) -> List[Dict[str, Any]]:
    """Primary outline parser. Pasted/uploaded course outlines arrive in wildly inconsistent
    shapes — one unbroken paragraph, bullet lists, numbered learning outcomes mixed in with
    course content, headings, etc. — and no regex reliably handles all of that. This asks the
    model to read the raw text the way a human would and segment it into a sensible chapter
    list, distinguishing actual teachable content from things like numbered learning outcomes.
    Falls back to the regex heuristic if the call or the parse fails, so outline parsing itself
    is never a hard stop."""
    prompt = f"""You are an outline chapter extractor for a university course lecture-note generator.

You will be given raw, possibly badly formatted, pasted course outline or syllabus text (it may
have no line breaks, run-on sentences, or mixed sections). Your job is to identify the actual
TEACHABLE CHAPTERS the lecture notes should be organized into.

Course outlines typically mix together things like:
- Learning Outcomes (a numbered list of things students should be able to do) — these describe
  goals, NOT chapters. Do not turn each learning outcome into its own chapter.
- Course Contents / Course Description (the actual topics to be taught) — this is what chapters
  should be built from.

Break the taught content into a logical sequence of chapters. Group closely related short topics
into one chapter; split large topic lists into multiple chapters where they're distinct enough to
teach separately. Order chapters in a sensible teaching sequence (foundational topics first).

Respond with ONLY a JSON object, no markdown fences, no commentary, in exactly this shape:
{{
  "chapters": [
    {{"number": 1, "title": "Short chapter title", "topic": "Comma-separated subtopics this chapter covers"}},
    {{"number": 2, "title": "...", "topic": "..."}}
  ]
}}

Raw outline text:
---
{text}
---
"""
    try:
        resp = call_llm(prompt, temperature=0.0)
        data = _extract_json(resp)
        chapters_raw = data.get("chapters") if isinstance(data, dict) else None
        if not isinstance(chapters_raw, list) or not chapters_raw:
            raise ValueError("Response had no usable 'chapters' array")
        chapters: List[Dict[str, Any]] = []
        for i, ch in enumerate(chapters_raw, start=1):
            if not isinstance(ch, dict):
                continue
            try:
                num = int(ch.get("number"))
            except (TypeError, ValueError):
                num = i
            title = str(ch.get("title") or f"Chapter {num}").strip() or f"Chapter {num}"
            topic = str(ch.get("topic") or "").strip()
            chapters.append({"number": num, "title": title, "topic": topic})
        # De-dupe/sort in case the model skipped or repeated numbers
        seen = set()
        unique: List[Dict[str, Any]] = []
        for ch in sorted(chapters, key=lambda c: c["number"]):
            if ch["number"] in seen:
                continue
            seen.add(ch["number"])
            unique.append(ch)
        if not unique:
            raise ValueError("Chapter list was empty after normalization")
        return unique
    except Exception as e:
        warn(
            f"LLM-based outline parsing failed ({e}); falling back to basic text parsing. "
            f"Check outline.json afterward — the chapter list may need manual adjustment."
        )
        return parse_outline_text_to_chapters_heuristic(text)


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
            raise RuntimeError(
                "python-docx is required to parse .docx outlines. Install via requirements.txt"
            )
        doc = docx.Document(str(path))
        text = "\n".join(p.text for p in doc.paragraphs)
    elif ext == ".pdf":
        try:
            from PyPDF2 import PdfReader
        except Exception:
            raise RuntimeError(
                "PyPDF2 is required to parse .pdf outlines. Install via requirements.txt"
            )
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
    chapters = parse_outline_text_to_chapters_llm(text)
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


def run_pipeline(course_dir_name: str) -> str:
    """Runs terminology -> all chapters -> final QA -> compile for an existing course
    folder, hands-off, then prints the run summary. Used for both fresh and resumed courses.
    """
    c = Course.load(course_dir_name)
    terminology = load_terminology(c.terminology_path)
    if not terminology.get("terms"):
        cmd_terminology(course_dir_name)
    cmd_all(course_dir_name)
    cmd_qa(course_dir_name)
    cmd_compile(course_dir_name)
    print_run_summary(c)
    return course_dir_name


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
                    total_complete = sum(
                        1
                        for v in chapters.values()
                        if v in ("complete", "complete_with_warnings")
                    )
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
                resume_id = incomplete[idx][0]
                print(
                    f"\nResuming {resume_id} — this runs straight through to the end.\n"
                )
                return run_pipeline(resume_id)
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
    paste_choice = (
        input(
            "Paste the outline into the terminal instead of providing a file? [y/N]: "
        )
        .strip()
        .lower()
    )
    if paste_choice in ("y", "yes"):
        print(
            "Paste your outline below. End with a single line containing only END (or Ctrl+D/Ctrl+Z):"
        )
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
    print(
        "\nSource materials are optional. The generator works from the course outline and learning outcomes alone."
    )
    print(
        "If you have slides or readings you want the generator to use, provide a path. Otherwise press Enter to skip."
    )
    source_materials = None
    while True:
        s = input(
            "Path to file or directory with source materials (leave blank to skip): "
        ).strip()
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
    if "outline_path" in locals() and outline_path:
        outline_display = outline_path.name
    elif "outline_name" in locals() and outline_name:
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
        print(
            f"Course directory {course_dir} already exists. Resuming or using existing data."
        )
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
            "chapters": parse_outline_text_to_chapters_llm(outline_text or ""),
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
    (course_dir / "outline.json").write_text(
        json.dumps(parsed_outline, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # If outline was pasted, save the original text for provenance
    if not outline_path and outline_text:
        (course_dir / (outline_name or "pasted_outline.md")).write_text(
            outline_text, encoding="utf-8"
        )
    # Save profile
    write_course_profile_from_metadata(course_dir / "course_profile.md", parsed_outline)
    # Ensure terminology and generation_state exist
    save_json(course_dir / "terminology.json", {"terms": {}})
    save_json(
        course_dir / "generation_state.json",
        {"status": "in_progress", "chapters": {}, "final_qa": False, "compiled": False},
    )
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
    print(
        "Generating your lecture note now — this runs straight through, start to finish.\n"
    )
    return run_pipeline(course_dir_name)


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
