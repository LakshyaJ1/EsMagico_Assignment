# Invoice extraction pipeline

Reads an invoice (digital PDF, scan or phone photo), returns JSON in the brief's schema,
checks its own work, and says when a human should look. Built for the Es Magico AI intern
assignment.

- **Extractor**: Gemini (`gemini-3.5-flash-lite` by default) reads the page images plus the PDF's
  text layer and answers in a constrained JSON schema.
- **Validation**: the brief's JSON Schema and a Pydantic model, totals that must reconcile
  (lines + tax = total, printed subtotal, tax lines), row arithmetic, date cross-checks. A failed
  check triggers one corrective re-read, then a `needs_review` flag. Bad data is never passed on silently.
- **Bad inputs**: non-invoices, corrupt/encrypted/empty/blank/oversized files, sideways scans,
  API timeouts, 503s and rate limits (retry with backoff, then a fallback model).
- **Eval harness**: one command scores the 10 labelled documents field by field and prints the table.
- **Web UI**: upload a document and review the extracted fields beside it in a spreadsheet-style
  worksheet; correct cells and the checks re-run live; browse the 20 samples and every eval run.

The write-up (approach, accuracy, failure analysis, cost, review-flag analysis) is in
**[REPORT.md](REPORT.md)**.

## Quick start

Requirements: Python 3.11+ with [uv](https://docs.astral.sh/uv/), a Gemini API key
([get one](https://aistudio.google.com/apikey)), and Node 20.19+ only if you want the web UI.

```bash
uv sync                                    # install dependencies into .venv
cp .env.example .env                       # then put your key in GEMINI_API_KEY
uv run python scripts/fetch_data.py        # download the sample pack into data/ (checksum-verified)
```

The sample documents are confidential, so they are not in git; `fetch_data.py` downloads them
from the assignment's Drive folder and verifies every file's SHA-256.

### Extract one document

```bash
uv run python extract.py data/labelled/L01.pdf > out.json
```

stdout is exactly the schema JSON; a one-line summary (status, confidence, tokens, cost) and any
review reasons go to stderr. Add `--meta` to get `{"result": ..., "meta": ...}` with the issues,
evidence, attempts and usage.

| Exit code | Meaning |
|---|---|
| 0 | extracted, every check passed |
| 3 | extracted, but flagged `needs_review` (the JSON is still printed) |
| 1 | the document could not be processed (reason on stderr) |

### Extract many documents

```bash
uv run python extract.py data/labelled data/unlabelled --out outputs
```

Writes `outputs/<name>.json` (schema-exact), `outputs/_meta/<name>.json` (review decision,
issues, evidence, tokens, cost, latency) and `outputs/_summary.json`. The committed `outputs/`
folder holds the results for all 20 sample documents.

### Run the eval

```bash
uv run python evaluate.py
```

Runs the extractor on the 10 labelled documents, compares every field with the ground truth,
prints the per-document grid, field accuracy, line-item precision/recall, the review-flag
analysis and cost, and saves `eval_results/<model>.{json,md}`.

Useful options: `--model`, `--mode hybrid|images|pdf`, `--thinking`, `--no-cache` (identical
requests are cached in `.cache/` by default so re-runs cost nothing), `--predictions outputs`
(re-score saved outputs offline, no API key needed), `--perturb blur|lowres|rotate90|...`
(stress test on degraded copies), `--no-second-read`, `--no-orientation-fix`.

Everything behind REPORT.md is one script: `uv run python scripts/run_experiments.py`
(22 eval runs, about $0.50 at list price from an empty cache; one document at a time to stay under
free-tier rate limits).

### Web UI

```bash
cd web && npm ci && npm run build && cd ..
uv run python serve.py                     # http://127.0.0.1:8000
```

- **Extract**: drop a PDF or image anywhere (or *Open invoice*). The page sits on the left; the
  worksheet on the right shows each field, every line item, and each check written as a formula
  (`=SUM(E9:E12)`, `=E13+E16`). Select cells to see Sum/Count/Average in the status bar.
- **Correct**: double-click (or start typing in) a cell to fix a value; all checks re-run on the
  server as you edit, and the checks that changed flash once. Edited cells get a comment corner.
  Approve or reject, and download the corrected, schema-exact JSON.
- **Name Box** (top left): type a cell (`E12`) to jump to it, or a document code (`U04`) to open it.
- **Documents**: the 20 samples with their saved outputs; labelled ones show a field-by-field
  comparison with the ground truth. Works without an API key.
- **Evaluation**: every eval run (clean set, repeats, stress tests, ablations) against every field,
  with the per-document results underneath.

For UI development: `uv run python serve.py --reload` and, in `web/`, `npm run dev`
(Vite on :5173 proxies `/api` to :8000).

## Configuration

All optional, in `.env` (see [.env.example](.env.example)):

| Variable | Default | |
|---|---|---|
| `GEMINI_API_KEY` | | required for extraction |
| `INVOICE_MODEL` | `gemini-3.5-flash-lite` | primary model |
| `INVOICE_FALLBACK_MODEL` | `gemini-3.1-flash-lite` | used when the primary is unavailable after retries; `none` disables |
| `INVOICE_INPUT_MODE` | `hybrid` | `hybrid` (images + text layer), `images`, `pdf` (native PDF input) |
| `INVOICE_THINKING_LEVEL` | `low` | `minimal`, `low`, `medium`, `high` |
| `INVOICE_MAX_RETRIES` | `1` | corrective re-reads after a failed check |
| `INVOICE_SECOND_READ` | `on` | verify doubtful reads with an independent second read |
| `INVOICE_SECOND_READ_MODEL` | `gemini-3.1-flash-lite` | the independent second reader (a different model on purpose) |
| `INVOICE_REFERENCE_DATE` | today | "today" for the stale-invoice check; set `2026-11-21` to reproduce REPORT.md exactly |
| `INVOICE_REQUEST_TIMEOUT_S` | `60` | per-request timeout |

## HTTP API

`uv run python serve.py` also serves a JSON API (interactive docs at `/docs`):

| Method | Path | |
|---|---|---|
| `POST` | `/api/extract` | multipart `file`; returns result, meta, page previews |
| `POST` | `/api/validate` | re-run every check on a (corrected) result; no key needed |
| `GET` | `/api/documents`, `/api/documents/{code}` | sample documents with saved outputs and ground-truth comparison |
| `POST` | `/api/documents/{code}/extract` | fresh extraction of a sample |
| `GET` | `/api/evaluations`, `/api/evaluations/{tag}` | eval reports |
| `GET` | `/api/health` | model, prompt version, whether a key is configured |

Errors come back as `{"error": {"code": "corrupt_file", "message": "..."}}` with a matching
status (415 unsupported type, 413 too large, 422 bad input, 503 model unavailable).

## Tests

```bash
uv run pytest            # 83 tests, no network: the LLM is replaced by a scripted fake
uv run ruff check .
cd web && npm run typecheck
```

## Layout

```
extract.py, evaluate.py, serve.py     entry points
src/invoice_extractor/
  documents.py    file sniffing, corrupt/empty/blank checks, rendering, text layer, orientation
  prompts.py      system prompt (the sample pack's labelling conventions) and re-read prompts
  schema.py       output schema (Pydantic + the brief's JSON Schema) and the model's richer schema
  llm.py          Gemini client: constrained JSON, retries/backoff, fallback model, cost, cache
  normalize.py    model answer -> exact output schema
  validation.py   schema, arithmetic, date and field checks -> issues with severities
  review.py       needs_review flag and confidence score
  pipeline.py     orchestration: orient, extract, check, corrective re-read, second read
  matching.py     field matching rules (shared by the eval and the second-read check)
  evaluation/     harness, renderers, stress-test perturbations
  api/app.py      FastAPI app (also serves web/dist)
web/              React + TypeScript UI (Vite)
scripts/          fetch_data.py, run_experiments.py
outputs/          JSON for all 20 sample documents (+ _meta/)
eval_results/     eval reports; experiments/ holds every run behind REPORT.md
tests/            pytest suite
```
