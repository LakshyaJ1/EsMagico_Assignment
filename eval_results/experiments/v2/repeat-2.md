# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T19:56:12+00:00
- Model: `gemini-3.5-flash-lite` · input mode `hybrid` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 8/10 (80%) | 7/9 (78%) |
| `vendor` | 8/10 (80%) | 7/9 (78%) |
| `invoice_number` | 8/10 (80%) | 7/9 (78%) |
| `invoice_date` | 8/10 (80%) | 7/9 (78%) |
| `currency` | 8/10 (80%) | 7/9 (78%) |
| `line_items` | 8/10 (80%) | 7/9 (78%) |
| `tax_total` | 8/10 (80%) | 7/9 (78%) |
| `total` | 8/10 (80%) | 7/9 (78%) |
| **All 8 fields correct** | 8/10 (80%) | 7/9 (78%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 38 | 38 | 100% | 58% | 73% | 100% | 100% | 100% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0019 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0022 |
| L03 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |
| L04 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L05 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0030 |
| L06 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L07 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0019 |
| L08 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0011 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0022 |
| L10 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |

## Errors

No field errors.

## Review flag vs. actual errors

- Flagged: 2/10
- Documents with at least one wrong field: 2; flagged: 2 (recall 100%)
- Flagged documents with no errors (false alarms): 0 (precision 100%)
- Share of all field errors that sit in flagged documents: 16/16 (100%)
- Missed (wrong but not flagged): none

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 2280 | 1088 | 550 | 0 | 1.00 | $0.00206 | $0.0165 | $2.06 | 6.2s |
