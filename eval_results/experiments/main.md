# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T20:41:03+00:00
- Model: `gemini-3.5-flash-lite` · input mode `hybrid` · thinking `low` · prompt `v3`
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
| L01 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0019 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0023 |
| L03 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0022 |
| L04 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0057 |
| L05 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0031 |
| L06 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |
| L07 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0019 |
| L08 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0012 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0022 |
| L10 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |

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
| 2550 | 1198 | 678 | 0 | 1.00 | $0.00246 | $0.0246 | $2.46 | 2.8s |
