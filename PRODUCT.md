# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript single-page app in `web/`, built to static files and served by the
Python FastAPI backend (`src/invoice_extractor/api`). Chosen by the user.

## Users

Primary: a finance clerk at a company that receives hundreds of vendor invoices a month (clean
PDFs, phone photos, scans, and the occasional non-invoice). Today they retype each invoice by
hand. Their job in this tool is to get an invoice's data out, check it against the document,
fix anything wrong, and pass on only data they trust.

Secondary: the Es Magico reviewers assessing this internship assignment. They evaluate the
product by using it as the clerk would, then look at how well it measures itself.

## Product Purpose

Turn an invoice document into validated, structured JSON (vendor, invoice number, date,
currency, line items, tax, total) and make it obvious when the result should not be trusted.
Success means the clerk spends their attention only on documents that need it, and bad data
is never passed on silently.

## Positioning

The extractor checks its own work instead of just returning JSON: totals must reconcile,
printed subtotal and tax lines must agree, dates must be consistent, and every result carries a
review decision with the concrete reasons. The same checks run live while a human corrects a
field. Accuracy, failure modes and cost per document are measured against ground truth and shown
in the product, not hidden in a notebook.

## Operating Context

- Inputs: PDF (digital or scanned) and images (JPEG/PNG/WebP/TIFF), one document at a time in
  the UI; batches via the CLI.
- The clerk works side by side: the document on one side, the extracted fields on the other.
- A sample pack of 20 documents (10 with ground-truth JSON) ships with the assignment; it is
  confidential and fetched locally, never committed.
- The model provider is Google Gemini; the API key lives in `.env` on the server.

## Capabilities and Constraints

- Screens: Extract (upload), Sample documents (with ground-truth diff), Eval dashboard,
  Human correction (edit fields, re-run checks live, export corrected JSON).
- Output must match the brief's JSON schema exactly; non-invoices return `is_invoice: false`
  and nulls.
- Every extraction reports tokens, cost in USD, latency and the model that served it.
- Sample documents and eval results must be browsable without an API key.
- Terminology: "needs review" (flag), "confidence" (transparent penalty score, not a
  probability), "issues" (error / warning / info).

## Evidence on Hand

- `data/` sample pack (after `scripts/fetch_data.py`), `outputs/` with JSON for all 20 documents,
  `eval_results/` with measured accuracy, stress tests and cost.
- No customers, testimonials or production usage exist; none may be implied.

## Product Principles

1. Never pass bad data silently: every doubt becomes a visible, specific reason.
2. The document is the source of truth: always show it next to what was extracted.
3. Measure honestly: show real accuracy, failures and cost, including the unflattering parts.
4. Spend the reviewer's attention where it matters: flags must be precise enough to trust.
