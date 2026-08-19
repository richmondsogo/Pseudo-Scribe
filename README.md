# Pseudo-Scribe — University Lecture Note Generator

A command-line tool that generates a complete, professionally typeset PDF of university
lecture notes from a course outline. Terminology stays consistent across the whole course,
chapters are written directly as LaTeX, and the output is a single merged book with a title
page, a real table of contents, and correct page numbers.

This is a **V1 reference implementation** — deliberately simple, resumable, and cost-aware.
It uses an LLM (Gemini, Groq, or OpenRouter) for content generation and `pdflatex` for
typesetting.

---

## Features

- **Interactive wizard** — paste or point at a course outline, answer a few questions, and
  get a finished PDF end-to-end.
- **Resumable** — interrupted runs pick up exactly where they left off.
- **Cost-aware** — chapters are written directly as LaTeX (no separate typesetting call),
  final QA uses a bounded per-chapter excerpt, and every optional LLM call is off by default.
- **Terminology consistency** — a course-wide `terminology.json` registry is the single
  source of truth; later chapters must reuse existing definitions or add new ones.
- **Real book output** — title page, page-numbered table of contents, PDF bookmarks, and a
  merged single-file PDF built from per-chapter LaTeX.
- **Provider-agnostic** — works with Gemini (default), Groq, or OpenRouter; token-heavy calls
  can be routed to a different provider than chatty ones.

---

## Quick start

### 1. Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate          # Windows
pip install -r requirements.txt
```

Requirements: **Python 3.11+** and a **LaTeX distribution with `pdflatex` on PATH**
(MiKTeX on Windows, TeX Live on macOS/Linux).

### 2. Configure the LLM provider

Copy `.env.example` to `.env` and set at least one API key:

| Provider (set `LLM_PROVIDER`) | Key variable                |
| ----------------------------- | --------------------------- |
| `gemini` (default)            | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| `groq`                        | `GROQ_API_KEY`              |
| `openrouter`                  | `OPENROUTER_API_KEY`        |

Optionally set `LLM_MODEL` (default `gemini-3.6-flash`), `GROQ_MODEL`, or
`OPENROUTER_MODEL` to pin a specific model. See [Configuration](#configuration) for the full
list of environment variables.

### 3. Run the interactive generator

```powershell
python generate.py
```

The wizard collects course metadata and an outline (paste it or point at a `.md`, `.txt`,
`.docx`, or `.pdf` file), then runs the whole pipeline: terminology extraction → chapter
generation → final QA → typeset → PDF. If a previous run exists, it offers to resume it.

> **Source materials are optional.** The generator works from the outline and learning
> outcomes alone. If you have lecture slides or readings you want it to use, provide a path
> when prompted (or leave blank to skip).

---

## Command-line reference

| Command | What it does |
| ------- | ------------ |
| `python generate.py` | Interactive wizard (setup + full pipeline) |
| `python generate.py init <COURSE_ID>` | Create a course folder skeleton |
| `python generate.py profile <COURSE_ID>` | Create/edit `course_profile.md` |
| `python generate.py terminology <COURSE_ID>` | Run terminology extraction from the outline |
| `python generate.py chapter <COURSE_ID> <N>` | Generate a single chapter |
| `python generate.py all <COURSE_ID>` | Generate all missing chapters |
| `python generate.py qa <COURSE_ID>` | Run final course-wide QA |
| `python generate.py compile <COURSE_ID>` | Typeset + compile the final PDF |
| `python generate.py build <COURSE_ID>` | Full pipeline: terminology → chapters → QA → compile |

Example workflow:

```powershell
python generate.py init INS202_HCI
# edit course_profile.md and outline.json
python generate.py terminology INS202_HCI
python generate.py all INS202_HCI
python generate.py qa INS202_HCI
python generate.py compile INS202_HCI
```

---

## Project layout (per course)

Each course lives in its own folder under `courses/`:

```
courses/<COURSE_ID>/
  course_profile.md        # course metadata + style rules
  outline.json             # parsed course outline / chapter list
  terminology.json         # canonical term registry (single source of truth)
  generation_state.json    # progress tracking (enables resume)
  prompts/                 # prompt templates copied at init
  sources/                 # optional supplied source materials
  pasted_outline.md        # raw pasted outline, if provided (provenance)
  drafts/                  # chapter drafts as LaTeX body fragments (ch01.md, ...)
  tex/                     # per-chapter .tex / .pdf + front matter + compile logs
  final/                   # assembled markdown, QA report
  output.pdf               # the final merged book
  run_warnings.json        # warnings collected during the last run
```

---

## Configuration

All settings are read from environment variables (see `.env.example` for a template).

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `LLM_PROVIDER` | `gemini` | Provider: `gemini`, `groq`, or `openrouter` |
| `LLM_MODEL` / `GEMINI_MODEL` | `gemini-3.6-flash` | Model name for Gemini |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model name for Groq |
| `OPENROUTER_MODEL` | `openrouter/free` | Model name for OpenRouter |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature for generation |
| `HEAVY_CALL_PROVIDER` | *(unset)* | Route final QA + legacy typesetting to a different provider |
| `MAX_CHAPTER_RETRIES` | `2` | Re-runs of a chapter after a failed/refused generation |
| `MAX_API_RETRIES` | `5` | Retries for transient API errors (429/500/timeouts) |
| `API_RETRY_BASE_DELAY` | `2.0` | Base backoff seconds between API retries |
| `MAX_AUTO_RETRY_WAIT_SECONDS` | `90` | Fail fast (with a suggested time) if a quota wait exceeds this |
| `FINAL_QA_EXCERPT_CHARS` | `1000` | Per-chapter excerpt length sent to final QA |
| `ENABLE_CHAPTER_ENHANCE` | `0` | Optional second LLM pass per chapter (adds diagrams/polish) — doubles chapter call count |
| `ENABLE_CONFLICT_CHECK` | `0` | LLM-verify whether a redefined term is a genuine conflict (vs. always keeping the first definition) |
| `MAX_CONCURRENT_CHAPTERS` | `1` | Parallel chapter generation. Keep at 1 unless you have quota to spare |
| `HTTP_TIMEOUT_SECONDS` | `180` | HTTP timeout for OpenAI-compatible providers |
| `DRY_RUN` | *(unset)* | `1`/`true` → use canned responses for a smoke test (no API calls) |

> **Token-budget tips.** The two biggest LLM calls are final QA and (for legacy markdown
> drafts) typesetting. Set `HEAVY_CALL_PROVIDER` to a high-context model if your normal
> provider has a small per-minute token budget. Keep `MAX_CONCURRENT_CHAPTERS = 1` — parallel
> chapters don't reduce total API calls (what actually trips daily quotas); they just make
> several calls land in the same minute window, which trips per-minute (TPM/RPM) quotas.

---

## How it works

1. **Terminology extraction** — reads the outline (and optional sources) and seeds
   `terminology.json` with the course's canonical terms.
2. **Chapter generation** — each chapter is written by the LLM **directly as a LaTeX body
   fragment** (starting with `\section`, no `\documentclass`/`\chapter` — the scaffolding is
   added programmatically). New terms are declared in a `[TERMINOLOGY]` JSON block and merged
   into the registry before the next chapter runs, so terminology stays consistent across the
   whole book. Conflicts never overwrite the first definition — they're logged (and, if
   `ENABLE_CONFLICT_CHECK=1`, verified by a second LLM call).
3. **Final QA** — a bounded excerpt of every chapter is checked for coverage, terminology
   consistency, and cross-chapter consistency. The report is saved to `final/final_qa.json`;
   issues are warnings, not hard stops.
4. **Compile** — each chapter is compiled standalone, the title page + contents are compiled,
   and every chapter is recompiled once more with its true starting page number so the
   contents page matches the printed page numbers. The pieces are merged with `pypdf` into a
   single book with PDF bookmarks.

### Why chapters sometimes look wrong (and what the tool does about it now)

- **Unescaped `%` in prose (e.g. `90%`)** silently truncates the rest of the line in LaTeX —
  the single most common cause of "the chapter came out broken". Generated body fragments are
  now sanitized (bare `%` outside `verbatim` blocks is escaped to `\%`).
- **Refused or one-line model responses** ("User Safety: safe") are detected and treated as a
  failed attempt, so they're never saved as a chapter.
- **Malformed delimiters** — a model closing the chapter with `\end{CHAPTER}` instead of
  `[/CHAPTER]` used to leak the raw `[TERMINOLOGY]` JSON into the chapter. That's now handled,
  and old drafts carrying the delimiters are self-healed at compile time.
- **Learning outcomes mistaken for chapters** — outline parsing now aggressively rejects
  "Learning Outcomes" as chapter titles and cleans remaining titles into proper noun phrases.
- **pdflatex errors** are detected by scanning the `.log` for real errors even when
  `pdflatex` exits 0 (nonstopmode does that), instead of silently shipping a broken PDF.

---

## Terminology & conflict handling

- `terminology.json` is the course-wide source of truth for terms and definitions.
- Chapter writers must declare new terms in a `[TERMINOLOGY]` JSON block in their output.
- A redefined term never silently overwrites the original definition:
  - the original (first) definition is always kept,
  - a warning is recorded (`run_warnings.json`), and
  - with `ENABLE_CONFLICT_CHECK=1`, an extra LLM call verifies whether the redefinition is a
    genuine conflict before warning.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `'pdflatex' isn't installed or isn't on PATH` | Install a LaTeX distribution (MiKTeX / TeX Live) and add `pdflatex` to PATH. |
| **"LaTeX error compiling ..."** (a chapter was skipped) | Read `<chapter>_error.log` in `tex/` — it captures the exact `!` error line. The most common cause is an unescaped `%` or a stray delimiter in the generated content; the `.tex` source is kept for manual fixing. |
| **Chapter content is a refusal / one-liner** | The pipeline retries automatically (up to `MAX_CHAPTER_RETRIES`). If it persists, check your model and prompt; you can also re-run just that chapter: `python generate.py chapter <COURSE_ID> <N>`. |
| **Chapter titles look like learning outcomes** (`"discuss the appropriate use of..."`) | Existing `outline.json` files keep their titles. Edit `outline.json` (or re-run the wizard with the raw outline) to get cleaned titles. |
| **JSON parse failures from the LLM** | Raw responses are saved as `*_raw.txt` next to outputs for inspection; the pipeline continues without that step. |
| **API failures / rate limits** | Check your key and network connectivity. Transient errors auto-retry with backoff; if a provider's quota wait exceeds `MAX_AUTO_RETRY_WAIT_SECONDS`, the run fails fast with a suggested resume time — completed work is saved, so just re-run the same command. |
| **`pypdf` not installed** | `pip install -r requirements.txt` (or just `pip install pypdf`). Individual chapter PDFs are still produced without it. |

---

## Extending the tool

- **Add an LLM provider** — implement a `_call_<name>` function and register it in
  `call_llm` in `generate.py`.
- **Change the writing style** — edit `prompts/chapter_writer.txt` (the template copied into
  each course at init; existing courses keep their own copy under `courses/<ID>/prompts/`).
- **Tune the output rules** — the LaTeX scaffold (fonts, margins, packages) lives in
  `_shared_preamble()` in `generate.py`.

---

## Safety & license

This tool uses an LLM to generate academic material. **Always review generated content before
use in teaching or assessment.** See `LICENSE` for license details.

## Contributing

Contributions are welcome. Open an issue or a pull request with a clear description of the
change and motivation. The repository is a V1 reference implementation intended as a starting
point for research and experimentation.