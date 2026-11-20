# Eval results: gemini-3.6-flash

- Evaluated: 2026-11-20T20:17:15+00:00
- Model: `gemini-3.6-flash` · input mode `hybrid` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 0/10 (0%) | 0/9 (0%) |
| `vendor` | 0/10 (0%) | 0/9 (0%) |
| `invoice_number` | 0/10 (0%) | 0/9 (0%) |
| `invoice_date` | 0/10 (0%) | 0/9 (0%) |
| `currency` | 0/10 (0%) | 0/9 (0%) |
| `line_items` | 0/10 (0%) | 0/9 (0%) |
| `tax_total` | 0/10 (0%) | 0/9 (0%) |
| `total` | 0/10 (0%) | 0/9 (0%) |
| **All 8 fields correct** | 0/10 (0%) | 0/9 (0%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 0 | 0 | 0% | 0% | 0% | 0% | 0% | 0% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L02 | photo | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L03 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L04 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L05 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L06 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L07 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L08 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L09 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L10 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |

## Errors

No field errors.

## Review flag vs. actual errors

- Flagged: 10/10
- Documents with at least one wrong field: 10; flagged: 10 (recall 100%)
- Flagged documents with no errors (false alarms): 0 (precision 100%)
- Share of all field errors that sit in flagged documents: 80/80 (100%)
- Missed (wrong but not flagged): none
