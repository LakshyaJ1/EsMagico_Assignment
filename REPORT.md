# Report: invoice extraction pipeline

**Headline.** On the 10 labelled documents the pipeline gets every field right: 80/80 fields,
66/66 line-item rows, reproduced in three independent runs, with two other input modes and with
a second model. It costs **$0.0025 per document** (about $2.46 per 1,000) and takes about 3 s.

That number is less informative than it looks. Ten clean documents cannot separate good
approaches from mediocre ones (with 10/10 correct, the 95% lower confidence bound on
per-document accuracy is still only 69%). So I also built a **stress suite**: 8 controlled
degradations of the labelled documents (80 extra scored documents). That is where the pipeline
fails, and it is what the failure analysis and the review-flag analysis below are based on:

| | Clean labelled set | 80 degraded copies |
|---|---|---|
| Documents fully correct | 10/10 | 71/80 (low-res scans: 3/10) |
| Documents flagged for review | 0 | 8, all 8 contain errors (0 false alarms) |
| Field errors inside flagged documents | n/a (no errors) | **15 of 16 (94%)** |

Numbers in this report come from `eval_results/` and can be regenerated with
`uv run python evaluate.py` and `uv run python scripts/run_experiments.py`.

---

## 1. Approach

### Model

`gemini-3.5-flash-lite` (Google Gemini API), thinking level `low`. It chose to spend no thinking
tokens on this task.

| Model tried | Clean set | Notes |
|---|---|---|
| **gemini-3.5-flash-lite** (chosen) | 10/10 | $0.0025/doc, ~3 s |
| gemini-3.1-flash-lite | 10/10 | $0.0024/doc, ~8 s; used as the fallback and the second reader |
| gemini-3.6-flash | 10/10 | $0.0037/doc, ~19 s; read low-res scans much better (5/6 vs 4/8 fully correct) but this key's quota ran out mid-run |
| gemini-3.8-flash, gemini-4-hydrogen | n/a | returned 503 / 504 for hours ("high demand"); gemini-4-neon is not on this key's tier |

I picked the cheapest model that saturates the labelled set and spent the effort on
self-checking instead: a stronger model costs more on every document, while the checks below only
spend extra on the documents that need it.

### What the model sees

**Page images (rendered at 170 DPI) plus, for digital PDFs, the PDF's text layer** ("hybrid").
The image tells the model which number belongs to which label (layout); the text layer gives
exact characters and digits. Scans and photos have no text layer, so they are image-only.

I measured this choice rather than assuming it: on the clean set, images-only and Gemini's native
PDF input also scored 10/10 at the same cost. Hybrid stays as cheap insurance for digital PDFs
(the text layer adds roughly 300 input tokens), but this data does not prove it necessary.

### Prompting

- A system prompt that restates the sample pack's **labelling conventions** (what counts as a
  line item, discounts are negative rows, tax is the sum of all tax lines, issue date rather than
  due date, `-` means a null quantity) plus generic rules for locale number formats and
  day/month order. See [prompts.py](src/invoice_extractor/prompts.py).
- **Constrained decoding**: the request carries a JSON Schema (`response_json_schema`), so every
  response parses.
- The model returns **more than the output schema**: the printed subtotal, each tax line, unit
  prices, the date exactly as printed, the due date, a legibility self-assessment and a list of
  fields it is unsure about. These are evidence for the validators. A deterministic projection
  then produces the exact output schema ([normalize.py](src/invoice_extractor/normalize.py)).
  The extra fields cost output tokens (about a third of the output), and they are what make the
  arithmetic and date checks possible.

### Pipeline

```
file -> type sniffing and bad-input checks -> render pages + text layer -> sideways-page fix
     -> Gemini (schema-constrained) -> project to output schema -> validate
     -> failed check? one corrective re-read with the failures as feedback, keep the better read
     -> doubtful? independent second read by a different model, compare field by field
     -> needs_review flag + confidence score + reasons
```

## 2. Validation, and what happens when a check fails

Every result is validated against the brief's JSON Schema (with `jsonschema`) and a Pydantic model,
then by business checks ([validation.py](src/invoice_extractor/validation.py)):

| Check | Severity | Triggers a re-read? |
|---|---|---|
| Output matches the schema | error | yes |
| Line items + tax = total | error | yes |
| Line items sum to the **printed subtotal** | error | yes |
| Tax lines sum to `tax_total` | error | yes |
| Due date on or after the issue date, within 180 days | error | yes |
| Total present | error | yes |
| Quantity × unit price = amount (per row) | warning | no |
| Invoice dated more than a year before processing, or in the future | warning | no |
| Printed date can be read as the ISO date; day/month ambiguity recorded | warning / info | no |
| Missing vendor, number, date or currency; unknown ISO currency; negative total | warning / error | no |
| Model reports degraded legibility or uncertain fields | warning | no (triggers the second read) |

**Rounding tolerance** is absolute and cent-level, growing with the number of values summed:
`max(0.05, 0.01 × (n + 1))`. A percentage tolerance would hide a missed ₹250 row on a ₹3,00,000
invoice.

**On failure:** one corrective re-read, where the model gets the failed checks verbatim and is
asked to re-read the table row by row; the better of the two reads is kept. If checks still fail,
the document is flagged `needs_review`. The JSON is still written (it is always schema-valid), but:

- the CLI prints the reasons to stderr and exits with code 3 instead of 0,
- `outputs/_meta/<doc>.json` records every issue, the evidence and each attempt,
- the API and the UI show the status and reasons next to the data.

**Second read (for doubtful documents).** When the model reports degraded legibility or uncertain
fields, or errors survive the corrective re-read, a *different* model (`gemini-3.1-flash-lite`)
reads the document independently and the two reads are compared field by field. Agreement
corroborates the read; disagreement flags the exact fields. Clean, confident documents never pay
for it: on the clean set it ran 0 times.

**Confidence** is `1.00` minus a fixed deduction per finding (error 0.40, warning 0.15, corrective
re-read 0.05). It is a transparent score, not a probability.

## 3. Bad inputs

**Non-invoices.** The model classifies first (invoice, purchase order, quotation, receipt, credit
note, delivery note, bank statement, letter, other); a non-invoice returns `is_invoice: false` with
every other field `null`, enforced by the schema. All three in the pack are handled: the purchase
order (L08), the bank statement that *mentions* invoice numbers (U06) and the cover letter (U10).

**The extra case I chose: broken or unusable files**, rejected before any API call is made, each
with a stable error code (CLI exit 1, HTTP 4xx with `{"error": {"code", "message"}}`):

| Input | Code |
|---|---|
| Not a PDF or image (sniffed from the bytes, never the extension) | `unsupported_file_type` (415) |
| Corrupt or truncated PDF or image | `corrupt_file` (422) |
| Password-protected PDF | `encrypted_pdf` (422) |
| Empty file, PDF with no pages, or a blank page | `empty_document` (422) |
| Over 20 MB | `file_too_large` (413) |
| More than 8 pages | processed, but flagged (never silently truncated) |

All of these are covered by tests ([test_documents.py](tests/test_documents.py),
[test_api.py](tests/test_api.py)).

Two more cases came from reality:

- **API failures.** During this work the API returned real 503s ("high demand"), 504s and 429s
  (rate limits). Requests use a 60 s timeout and up to 5 attempts with exponential backoff. If the
  model is still unavailable, a **fallback model** serves the request and the output records which
  model answered. If both fail, the error is typed (`llm_unavailable`, HTTP 503) instead of a crash.
  In the first experiment batch, 3 parallel workers on a free-tier key produced 11 rate-limited
  documents; running one document at a time removed them all.
- **Sideways scans** (U05 is rotated 90°). Detected with a projection-profile angle sweep (free, no
  API call; 0 errors on 140 test pages including 7°-skewed ones). The 90° vs 270° decision is a tiny
  model call comparing two thumbnails, because a pixel heuristic for it failed (section 8).

## 4. Eval harness

`uv run python evaluate.py` runs the extractor on the 10 labelled documents, compares every field
with the ground truth, prints a per-document grid and a field-accuracy table, line-item
precision/recall, the review-flag analysis and the cost, and saves `eval_results/<model>.{json,md}`.
`--predictions outputs` re-scores saved outputs offline.

**Matching rules** ([matching.py](src/invoice_extractor/matching.py)): strict where a finance team
would be hurt by a difference, lenient only where the difference is cosmetic.

| Field | Rule |
|---|---|
| `is_invoice`, `currency`, `invoice_date` | exact (dates compared as ISO) |
| `vendor` | case- and punctuation-insensitive, legal suffixes ignored ("Acme Pvt Ltd" = "Acme"), then equal or token-set similarity ≥ 90 |
| `invoice_number` | exact after trimming and case-folding; **separators matter** (`KOM/26-27/00418` ≠ `KOM-26-27-00418`, they are different references) |
| `tax_total`, `total` | numeric within 0.01; strings like `"1,200.00"` are parsed first, so `"1,200.00"` = `1200` |
| `line_items` | same row count, and every row matches in order: description similarity ≥ 90 after normalising case, whitespace and punctuation; quantity equal (`null` = `null`); amount within 0.01 |

`null` on both sides is a match (that is how a non-invoice's empty fields score). Accuracy is
reported over all 10 documents and over the 9 invoices. Row-level precision, recall and
description/quantity/amount accuracy are reported separately, so one missed row does not hide how
the other rows did. A document whose API call failed scores as wrong on every field.

## 5. Accuracy

### Labelled set (10 documents)

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 10/10 (100%) | 9/9 |
| `vendor` | 10/10 (100%) | 9/9 |
| `invoice_number` | 10/10 (100%) | 9/9 |
| `invoice_date` | 10/10 (100%) | 9/9 |
| `currency` | 10/10 (100%) | 9/9 |
| `line_items` | 10/10 (100%) | 9/9 |
| `tax_total` | 10/10 (100%) | 9/9 |
| `total` | 10/10 (100%) | 9/9 |
| **All 8 fields correct** | **10/10** | **9/9** |

Line items: 66/66 rows fully correct (precision, recall, description, quantity and amount all 100%).
The same result held in 2 more uncached runs, with images-only and native-PDF input, and with
`gemini-3.1-flash-lite`. Full table: [eval_results/experiments/SUMMARY.md](eval_results/experiments/SUMMARY.md).

### Stress suite (final configuration)

| Degradation | Fully correct | Mean field accuracy | Flagged (all with errors) | Avg cost/doc |
|---|---|---|---|---|
| Rotated 90° / 180° / 270° | 10/10 each | 100% | 0 | $0.0025-0.0031 |
| Skewed 7° | 10/10 | 100% | 0 | $0.0024 |
| Phone photo (keystone, uneven light, soft focus) *held out* | 10/10 | 100% | 0 | $0.0024 |
| Gaussian blur | 9/10 | 96% | 1 | $0.0040 |
| Fax (1-bit, 100 DPI, speckle) *held out* | 9/10 | 99% | 1 | $0.0027 |
| Low resolution (~55 DPI, JPEG-crushed) | **3/10** | 85% | 6 | $0.0043 |

Unlabelled documents: the outputs for all 10 are in `outputs/`. I checked each by eye against the
document: all fields look right, including the blurry US photo (U02, month-first date) and the
sideways scan (U05). One is flagged: **U04's own arithmetic is inconsistent** (it prints
1440 × 0.09 = 122.40, but that is 129.60; the unit price was probably rounded from 0.085). That is
the kind of document a clerk should look at.

## 6. Failure analysis

All errors come from the stress suite; the clean set has none. Grouped by cause, from most to
least common:

**A. Single-character misreads on low-resolution text (5 documents).** `NWL-88213` read as
`NWL-68213` (lowres L01), `OHS-0261-26` as `DHS-0261-26` (fax L05), quantity `16` as `18`
(lowres L04), a line amount off by 100 (lowres L02).
*Caught when the digit feeds arithmetic* (L04: the row and subtotal checks failed). *Missed when it
does not*: an invoice number has nothing to check against, and the model reported L01 as "clear".
L01 is the only error in the whole suite that went unflagged.

**B. Systematic misreads that fool cross-checks (2 documents).** On the low-res copies of L07 and
L10 the year `2026` became `2020` on **both** the issue date and the due date. I had added a
due-date cross-check precisely for misread years, but it passes when both dates are misread the
same way. What catches it is an accounts-payable control: an invoice dated six years before
processing is stale or misread (`date_stale`).

**C. Self-consistent hallucination (2 documents).** On blurred L09 the model read quantity `18` as
`20` and amount `14,040` as `14,000`, then produced a tax and total that **add up** around the
misread. On skewed L05 (earlier version) it read quantity `6` as `3` *and* unit price `1,120` as
`2,240`. Arithmetic checks are blind to this by construction. Only an independent second read
catches it, and only if it is a *different* model (see section 7).

**D. The reconciliation picked the wrong read (1 document).** On low-res L02 the first read had a
wrong line amount (so its subtotal check failed); the second model's read was internally
consistent but had the wrong tax and total. My rule "keep the read with fewer validation errors"
picked the second. The document stayed flagged ("two reads disagree on tax_total, total"), so no
bad data passed silently, but the stored values got worse.

**E. Infrastructure (no model error).** Rate limits on a free-tier key (11 documents in the first
batch), 503/504 on the larger models, and an exhausted quota on gemini-3.6-flash. Fixed with
one-at-a-time processing, retries with backoff and the fallback model.

**What I would fix first**

1. **Escalate degraded scans to a stronger reader** (causes A and C, the bulk of the errors). Every
   failure involves an image the model itself rated "degraded" or a low-resolution source.
   gemini-3.6-flash read the low-res copies far better (5 of 6 fully correct, vs 4 of 8). Routing
   only "degraded" pages to it would cost roughly $0.006 extra on perhaps 5-10% of real traffic.
2. **Field-level reconciliation instead of whole-read selection** (cause D): when two reads
   disagree, keep each field from the read whose checks it participates in pass, and flag the rest.
3. **Vendor master data** (cause A, invoice numbers): in production, the vendor's past invoice
   numbers and GSTIN would catch `NWL-68213` and `DHS-...` instantly. The sample pack has no such
   registry, so I did not build one.

## 7. Human-review flag: does it point at the errors?

`needs_review` is raised by any error or warning. Measured against ground truth:

- **Clean labelled set:** 0 errors, 0 flags (no false alarms).
- **80 degraded documents:** 9 contain at least one wrong field. 8 are flagged, all 8 of which have
  errors. **The flagged documents hold 15 of the 16 field errors (94%).** Mean confidence is 0.66
  on documents with errors and 1.00 on documents without.

The second-read policy decides this trade-off. Same 30 documents (blur, fax, low-res), same final
code, only the policy changes:

| Second read | Documents with errors caught | False alarms |
|---|---|---|
| None (the model's legibility doubt flags on its own) | 8/9 | 12 |
| Same model reads again | 6/9 | 0 |
| **Different model reads again** (default) | **8/9** | **0** |

The model's own "degraded" self-report is sensitive but imprecise: it flagged all 10 blurred
documents, 9 of them correctly read. A second read by the **same** model removes those false alarms
but agrees with its own misreads, so real errors get through: two reads of the same model share
the same blind spots. A **different** model's read keeps the recall and removes the false alarms.

## 8. Things I tried that did not work

1. **A pixel heuristic for upside-down vs upright** (ascender/descender ink balance). It gave the
   wrong sign on 3 of 18 upright digital documents and no signal at all on photos. Replaced with a
   small model call that picks between two rotated thumbnails, used only for pages the free
   detector flags as sideways.
2. **The orientation correction itself did not improve accuracy.** The model read every 90°, 180°
   and 270° rotated document correctly *without* it (ablation: 10/10). I kept it because previews
   are upright for the reviewer and it costs about $0.0006 per sideways page, but the honest result
   is that this model does not need it.
3. **My first sideways detector** (compare text-line sharpness at exactly 0° and 90°) flagged
   3 of 5 pages skewed by just 7° as sideways, which would have rotated nearly upright pages by 90°.
   Replaced with an angle sweep (0 errors on 140 pages).
4. **The same-model second read** (section 7): perfect precision, but it hid real errors.
5. **The due-date cross-check** did not catch the misread years it was built for (section 6B).
6. **Prompt v1 leaked test data**: its number-format and date examples were copied from sample
   documents, one of them labelled (L04). I replaced them with generic examples before measuring
   anything I report.

## 9. Cost per document

**Method.** Each API response reports `prompt_token_count` (text plus image tokens),
`candidates_token_count` (answer) and `thoughts_token_count` (thinking, billed as output). Cost =
input × input price + (output + thinking) × output price, at the paid-tier list prices on
2026-11-21 ([pricing.py](src/invoice_extractor/pricing.py)): gemini-3.5-flash-lite $0.30 input /
$2.50 output per million tokens; gemini-3.1-flash-lite $0.25 / $1.50. Every call is summed
per document, including corrective re-reads, second reads and orientation calls. The key used
here is on the free tier, so these are what the calls would cost when billed.

**Clean labelled set (default configuration):**

| | Per document |
|---|---|
| Input tokens | 2,550 (1,198 of them image: about 1,100 per page) |
| Output tokens | 678 (+ 0 thinking) |
| API calls | 1.00 |
| **Cost** | **$0.00246** |
| Latency | 2.9 s average, 5.1 s max |

- Output is 69% of the cost although it is a quarter of the tokens (output tokens cost 8× more).
- Cost scales with pages and rows: the 2-page, 24-row invoice (L04) costs $0.0057; the purchase
  order (no line items extracted) $0.0012.
- Doubtful documents pay for the second read: blurred and low-res copies average about $0.004.
- All 20 sample documents: $0.043 in total ($0.0022 each). At "hundreds a month", say 500
  invoices, that is about **$1.25 a month**; $2.46 per 1,000.
- **Total spend for the whole project**, including development, every experiment and the model
  comparisons: about **$0.85** at list price (340 distinct calls plus the uncached repeat runs,
  summed from the usage recorded on every call).

## 10. Overfitting and honesty notes

- **I looked at all 20 documents** (labelled and unlabelled) before writing the prompt, so the
  prompt anticipates the kinds of traps present (European number formats, `-` quantities, split
  taxes). Its rules come from the sample pack's published labelling conventions, not from the
  answer files. No prompt change was made in response to a labelled-set error; there were none.
- **v3's changes** (due-date check, stale-date control, second read, cross-model second read) were
  designed **after seeing stress-test failures** on degraded copies of the labelled documents, so the
  blur, low-res, rotation and skew numbers are optimistic. The **fax and photo** degradations were
  added after v3 was designed and give cleaner estimates. I did use the fax results when choosing
  between the same-model and cross-model second read, so only the photo set is fully untouched
  (and it produced no errors).
- **10 labelled documents is a small sample.** 10/10 documents correct gives a 95% lower bound of
  69% per document; 80/80 fields gives 95.5% per field. Real traffic will be messier than this pack.
- The stale-date control depends on the processing date. Results here use 2026-11-21; set
  `INVOICE_REFERENCE_DATE` to reproduce them later.

## 11. Limitations

- Handwritten invoices, multi-currency invoices and invoices longer than 8 pages are untested.
- `is_invoice` is a single model judgment. A pro-forma invoice or a credit note could be argued
  either way, and the labelled set has no such example.
- Upside-down (180°) pages are not detected by the free detector; the model reads them fine, but
  a weaker model might not.
- The UI keeps uploads in memory and approval marks in the browser. A production system needs a
  database, authentication and an audit trail.
