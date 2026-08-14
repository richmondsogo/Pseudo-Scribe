Lecture Notes Generator (V1)
=================================

Summary
-------
A command-line tool that generates a single PDF of lecture notes for a course from a course outline. The tool keeps course-wide terminology consistent. This repository is a V1 reference implementation and uses an LLM (OpenAI by default).

Design goals (V1)
-----------------
- Simple: an interactive wizard for common tasks.
- Resumable: runs can be resumed after interruptions.
- Cost-aware: prompts and steps reduce unnecessary LLM calls.

What the tool does
------------------
- Extracts key terms from the course outline and optional sources.
- Generates draft chapters in Markdown.
- Runs QA passes on chapters and the assembled course.
- Produces LaTeX and compiles a PDF with pdflatex.

Quick start (recommended)
-------------------------
1. Create a Python virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

2. Copy .env.example to .env and set GEMINI_API_KEY (or GOOGLE_API_KEY). Configure GEMINI_MODEL if you want a specific Gemini model.

3. Run the interactive generator:

```powershell
python generate.py
```

The wizard asks for course metadata and an outline, then runs terminology extraction, chapter generation, QA, typesetting, and PDF compilation. If a previous run exists the wizard offers to resume.

Source materials (optional)
---------------------------
You only need to provide the course outline and learning outcomes for the generator to produce full lecture notes. Supplying additional source materials (lecture slides, readings, or notes) is optional and may improve coverage or example content. If you do not have extra materials, leave the source materials prompt blank when running the interactive wizard.

Requirements
------------
- Python 3.11 or later
- A LaTeX distribution with pdflatex on PATH
- GEMINI_API_KEY or GOOGLE_API_KEY set (or update call_llm to use another provider)

Project layout (per course)
---------------------------
Each course uses a folder under courses/:

- courses/<COURSE_ID>/
  - course_profile.md         # Course metadata
  - outline.json              # Course outline
  - terminology.json          # Canonical term registry
  - generation_state.json     # Tracks progress
  - prompts/                  # Prompt templates copied at init
  - drafts/                   # Draft Markdown chapters (ch01.md)
  - tex/                      # Generated LaTeX files (ch01.tex)
  - final/                    # Final assembled Markdown/LaTeX
  - main.tex                  # LaTeX entry file
  - output.pdf                # Final PDF

Commands
--------
- Init a course skeleton:

```powershell
python generate.py init <COURSE_ID>
```

- Run terminology extraction:

```powershell
python generate.py terminology <COURSE_ID>
```

- Generate a chapter:

```powershell
python generate.py chapter <COURSE_ID> <CHAPTER_NUM>
```

- Run all generation steps:

```powershell
python generate.py all <COURSE_ID>
```

- Run QA only:

```powershell
python generate.py qa <COURSE_ID>
```

- Produce PDF (typeset + compile):

```powershell
python generate.py compile <COURSE_ID>
python generate.py build <COURSE_ID>
```

Terminology and consistency
---------------------------
- terminology.json is the course-wide source of truth for terms and definitions.
- The extractor seeds terminology.json from the outline and optional sources.
- Chapter generators must declare new terms in a [TERMINOLOGY] JSON block inside the chapter output.
- The CLI validates proposed definitions against the registry. On conflict, the process stops and reports the issue. The tool never silently overwrites definitions.

Conflict handling
-----------------
If a chapter proposes a conflicting definition:
- Generation stops and prints the conflicting term and sources.
- Resolve the conflict by editing terminology.json or the draft, then re-run the step.

Troubleshooting
---------------
- pdflatex not found: install a LaTeX distribution and add pdflatex to PATH.
- JSON parse failures from the LLM: check *_raw.txt files saved next to outputs for the raw responses.
- API failures: check GEMINI_API_KEY/GOOGLE_API_KEY and network connectivity.

Extending the tool
------------------
- Add another LLM provider by updating call_llm in generate.py.
- Change prompts by editing the prompts/ templates used at init.

Example workflow
----------------
```powershell
python generate.py init INS202_HCI
# edit course_profile.md and outline.json
python generate.py terminology INS202_HCI
python generate.py all INS202_HCI
python generate.py qa INS202_HCI
python generate.py compile INS202_HCI
```

Safety and license
------------------
This tool uses an LLM to generate academic material. Review generated content before use in teaching or assessment. See LICENSE for license details.

Contributing
------------
Contributions are welcome. Open an issue or a pull request with a clear description of the change and motivation.

Acknowledgements
----------------
This repository provides a V1 reference implementation intended as a starting point for research and experimentation.

