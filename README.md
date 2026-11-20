# Cavli Website AI Assistant (Assignment 1 PoC)

Grounded Q&A and product discovery over 26 public Cavli pages (7 category pages, 19 module pages).
Stack: FastAPI, LangChain (LCEL), Qdrant, OpenAI (`gpt-5.4-mini`, `text-embedding-3-small`).

## Setup and run
```bash
uv sync
cp .env.example .env          # put OPENAI_API_KEY (and QDRANT_URL / QDRANT_API_KEY for Qdrant Cloud) in .env, never commit it
uv run python -m ingest.build26 --upsert    # fetch -> parse -> chunk -> profiles -> embed -> Qdrant collection `cavli_modules`
uv run app/main.py                          # starts uvicorn itself on http://localhost:8001
```
Other ingest options: no flag = parse and chunk only (no LLM, no embedding); `--profile` adds the LLM product profiles;
`--refresh` re-downloads the pages. With `QDRANT_URL` empty an embedded Qdrant in `./qdrant_data` is used (one process at a time).

## Data pipeline (`ingest/`)
- `cavli26.py`: the 26 URLs, section-aware HTML parsing, one chunk per page section, whole tables, context header on every chunk.
- `cavli26_spec.py`: per-product spec records (each value tagged with its source), conflict detection, LLM product profiles
  (number-checked), category lineups.
- `build26.py`: the command above. Outputs in `data/cavli26/` (`chunks.json`, `specs.json`, `conflicts.json`, ...).
- Strategy, chunk counts, conflicts found and retrieval numbers: [docs/chunking_strategy_26_pages.md](docs/chunking_strategy_26_pages.md).

## Answering (`app/`)
- **Retrieval:** one embedding + one Qdrant dense search (top 12, cosine gate), no metadata filter, no query rewriting.
  Dense beat hybrid on the frozen eval (pass@8 96.6% vs 92.9%): `uv run python -m eval.retrieval26`.
- **Streaming:** `POST /api/chat/stream` (SSE) sends sources, tokens and `[n]` citation links as they arrive; the final event is authoritative.
  `POST /api/chat` returns the same result in one response.
- **Answers:** facts carry `[n]` links to the source page; `inference` is shown separately; `unverified` lists requirements the
  sources do not confirm; vague questions get a follow-up question. When the site's own sources disagree, both values are reported.
- **Checks:** cited ids must be retrieved ids; every figure must appear in the cited chunks (repaired from another retrieved chunk, else
  the answer falls back); if the question names modules, cited chunks must be about those modules.
- **Response kinds:** `answer`, `not_verified` (closest source + module page + contact link), `out_of_scope`, `blocked` (pasted code/SQL/shell/HTML,
  prompt injection, encoded blobs), `smalltalk`, `clarify`. Price/stock/lead-time questions get the standard not-verified reply.
  Emails and phone numbers are stripped before retrieval and the LLM. 500-character cap, 20 requests/min per IP.
- **Other endpoints:** `POST /api/feedback` (appends to `data/feedback.jsonl`), `GET /api/metrics` (count, avg/p50/p95 latency), `GET /api/health`.
- **Config:** secrets only in `.env`; thresholds in `app/config.py`.
- **UI:** `frontend/widget.js` is a floating chat widget (Shadow DOM) loaded by `frontend/index.html`; to embed it on cavliwireless.com add the script tag,
  host the API behind HTTPS and add auth and rate limiting at the gateway.

## Limits
- Single-turn by design (a simple chatbot): each question is answered on its own, with no conversation memory.
- "List everything" questions only see the top 12 chunks, so answers can be incomplete; rare-keyword selection questions
  (e.g. "Wi-Fi 6 and Bluetooth 5.4") can miss under dense-only retrieval.
- The eval question set is generated from the indexed chunks, so it is friendlier than real traffic; it measures retrieval, not answer quality.
- Hardware Manual and AT Command Manual need a login and are not indexed; brochures are not indexed.
