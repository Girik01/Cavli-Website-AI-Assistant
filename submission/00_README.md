# Assignment 1 – Website AI Assistant & Product Discovery: submission package

| File | What it is |
|---|---|
| `03_technical_note.pdf` (source: `.html`) | Technical note, 3 pages: architecture and flow diagram, retrieval, citation checks, guardrails, privacy, security, latency, feedback, website embedding plan, limits |
| `02_test_questions_and_outputs.md` | The five required test questions (incl. one unsupported, one product selection) plus 12 edge cases, with real outputs; raw data in `test_outputs.json` |
| `01_sources.md` | Exactly which public pages were used, fetch dates, chunk counts, what was not used, known conflicts |
| `04_demo_script.md` | Script for the 5–10 minute demo, with what to show on screen |
| `../README.md` | Setup and run instructions, API, design summary |
| `../docs/chunking_strategy_26_pages.md` | How the 26 pages were chunked, conflicts found, retrieval comparison |
| `../app`, `../ingest`, `../frontend`, `../eval` | Source code (API, data pipeline, chat widget, retrieval evaluation) |

Run it: `uv sync`, copy `.env.example` to `.env` and add your own keys, `uv run python -m ingest.build26 --upsert`, `uv run app/main.py`, open http://localhost:8001.
No API keys are included in this package.
