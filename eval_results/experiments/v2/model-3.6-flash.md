# Eval results: gemini-3.6-flash

- Evaluated: 2026-11-20T19:59:38+00:00
- Model: `gemini-3.6-flash` · input mode `hybrid` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 10/10 (100%) | 9/9 (100%) |
| `vendor` | 10/10 (100%) | 9/9 (100%) |
| `invoice_number` | 10/10 (100%) | 9/9 (100%) |
| `invoice_date` | 10/10 (100%) | 9/9 (100%) |
| `currency` | 10/10 (100%) | 9/9 (100%) |
| `line_items` | 10/10 (100%) | 9/9 (100%) |
| `tax_total` | 10/10 (100%) | 9/9 (100%) |
| `total` | 10/10 (100%) | 9/9 (100%) |
| **All 8 fields correct** | 10/10 (100%) | 9/9 (100%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 66 | 66 | 100% | 100% | 100% | 100% | 100% | 100% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0029 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0029 |
| L03 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0035 |
| L04 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0084 |
| L05 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0039 |
| L06 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0031 |
| L07 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0031 |
| L08 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0032 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0030 |
| L10 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0032 |

## Errors

No field errors.

## Review flag vs. actual errors

- Flagged: 0/10
- Documents with at least one wrong field: 0; flagged: 0 (recall -)
- Flagged documents with no errors (false alarms): 0 (precision -)
- Share of all field errors that sit in flagged documents: 0/0 (-)
- Missed (wrong but not flagged): none

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 2505 | 1198 | 464 | 23 | 1.00 | $0.00371 | $0.0371 | $3.71 | 19.1s |
