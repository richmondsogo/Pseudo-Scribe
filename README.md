Lecture Notes Generator (V1)
=================================

This CLI generates complete university lecture notes (one PDF) from a course outline while maintaining terminology consistency across the course. It is designed to be simple, resumable, and cost-conscious for V1.

Important: This implementation is a V1 reference and relies on an LLM provider (OpenAI supported). Follow the setup steps below.

Quick overview
--------------

Pipeline:
COURSE INPUT -> Initial Terminology Extraction -> Chapter Generation -> Chapter QA -> Terminology Validation -> ... -> Final QA -> LaTeX Typesetting -> LaTeX Compilation -> PDF

Project structure (per course)

courses/\n  <COURSE_ID>/\n    course_profile.md\n    outline.json\n    terminology.json\n    generation_state.json\n    prompts/\n      <prompt templates copied at init time>\n    drafts/\n      ch01.md\n    tex/\n      ch01.tex\n    final/\n      final_course.md\n    main.tex\n    output.pdf

Requirements
------------
- Python 3.11+
- LaTeX distribution with pdflatex on PATH (for compile)
- OpenAI API key (or another provider if you extend the call_llm function)

Installation
------------

1. Create a Python virtualenv and install requirements:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create an .env file from .env.example and set your OPENAI_API_KEY.

Interactive usage
-----------------

Run the interactive setup and generation wizard (recommended for normal users):

```bash
python generate.py
```

This launches a simple guided setup that asks for course metadata, an outline file, and optional source materials, then automatically runs terminology extraction, chapter generation, chapter QA, final QA, typesetting and PDF compilation. It is resumable: if an incomplete course exists, the wizard offers to resume it.

Advanced commands (for debugging or scripting)
---------------------------------------------

If you prefer manual control, the existing commands remain available:

Initialize a new course folder template:

```bash
python generate.py init INS202_HCI
```

Run a single step (examples):

```bash
python generate.py terminology INS202_HCI
python generate.py chapter INS202_HCI 1
python generate.py all INS202_HCI
python generate.py qa INS202_HCI
python generate.py compile INS202_HCI
python generate.py build INS202_HCI
```

How terminology consistency works
--------------------------------
- terminology.json is the canonical, course-level registry.
- The terminology extractor initially populates it from the outline and sources.
- Each chapter's generation must declare any new terms in a [TERMINOLOGY] JSON block.
- The CLI validates proposed definitions against existing ones. If a conflict is detected the process stops and reports the conflict; the CLI never silently overwrites definitions.

Conflict handling
-----------------
- If a generated chapter proposes a definition that contradicts an existing definition, generation stops and the conflict is reported.
- The user must resolve the conflict by editing terminology.json or the draft and re-running generation.

Source materials
----------------
- Optional source materials may be used by prompt templates. Do not supply source citations unless supported by the materials.

Common errors and troubleshooting
--------------------------------
- Missing LaTeX: Ensure 'pdflatex' is on PATH. The compile step will fail otherwise.
- Invalid prompt responses: Raw LLM outputs are saved to *_raw.txt files for inspection if JSON parsing fails.
- API issues: Check OPENAI_API_KEY and network connectivity.

Extending and customizing
-------------------------
- To support another provider, modify call_llm in generate.py.
- Prompt templates are in prompts/*.txt; edit or replace them to tune output.

Example workflow
----------------

```bash
python generate.py init INS202_HCI
# edit course_profile.md and outline.json
python generate.py terminology INS202_HCI
python generate.py all INS202_HCI
python generate.py qa INS202_HCI
python generate.py compile INS202_HCI
```

License and safety
------------------
This tool delegates academic content generation to an LLM. Validate critical material before relying on it for assessment or teaching.
