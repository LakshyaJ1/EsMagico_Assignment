# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T19:56:58+00:00
- Model: `gemini-3.5-flash-lite` · input mode `images` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 9/10 (90%) | 8/9 (89%) |
| `vendor` | 9/10 (90%) | 8/9 (89%) |
| `invoice_number` | 9/10 (90%) | 8/9 (89%) |
| `invoice_date` | 9/10 (90%) | 8/9 (89%) |
| `currency` | 9/10 (90%) | 8/9 (89%) |
| `line_items` | 9/10 (90%) | 8/9 (89%) |
| `tax_total` | 9/10 (90%) | 8/9 (89%) |
| `total` | 9/10 (90%) | 8/9 (89%) |
| **All 8 fields correct** | 9/10 (90%) | 8/9 (89%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 62 | 62 | 100% | 94% | 97% | 100% | 100% | 100% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0017 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0022 |
| L03 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0020 |
| L04 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0053 |
| L05 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0029 |
| L06 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0019 |
| L07 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L08 | digital | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0010 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |
| L10 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |

## Errors

No field errors.

## Review flag vs. actual errors

- Flagged: 1/10
- Documents with at least one wrong field: 1; flagged: 1 (recall 100%)
- Flagged documents with no errors (false alarms): 0 (precision 100%)
- Share of all field errors that sit in flagged documents: 8/8 (100%)
- Missed (wrong but not flagged): none

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 2110 | 1210 | 687 | 0 | 1.00 | $0.00235 | $0.0211 | $2.35 | 3.2s |
