# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T19:53:18+00:00
- Model: `gemini-3.5-flash-lite` · input mode `hybrid` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 6/10 (60%) | 6/9 (67%) |
| `vendor` | 6/10 (60%) | 6/9 (67%) |
| `invoice_number` | 6/10 (60%) | 6/9 (67%) |
| `invoice_date` | 6/10 (60%) | 6/9 (67%) |
| `currency` | 6/10 (60%) | 6/9 (67%) |
| `line_items` | 6/10 (60%) | 6/9 (67%) |
| `tax_total` | 6/10 (60%) | 6/9 (67%) |
| `total` | 6/10 (60%) | 6/9 (67%) |
| **All 8 fields correct** | 6/10 (60%) | 6/9 (67%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 34 | 34 | 100% | 52% | 68% | 100% | 100% | 100% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0024 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0030 |
| L03 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0027 |
| L04 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L05 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0035 |
| L06 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L07 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L08 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes | 0.85 | $0.0022 |
| L10 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0028 |

## Errors

No field errors.

## Review flag vs. actual errors

- Flagged: 5/10
- Documents with at least one wrong field: 4; flagged: 4 (recall 100%)
- Flagged documents with no errors (false alarms): 1 (precision 80%)
- Share of all field errors that sit in flagged documents: 32/32 (100%)
- Missed (wrong but not flagged): none

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 3842 | 2898 | 644 | 0 | 1.83 | $0.00276 | $0.0166 | $2.76 | 13.0s |
