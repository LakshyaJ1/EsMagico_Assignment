# Eval results: gemini-3.6-flash

- Evaluated: 2026-11-20T20:13:59+00:00
- Model: `gemini-3.6-flash` · input mode `hybrid` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 6/10 (60%) | 5/9 (56%) |
| `vendor` | 6/10 (60%) | 5/9 (56%) |
| `invoice_number` | 6/10 (60%) | 5/9 (56%) |
| `invoice_date` | 6/10 (60%) | 5/9 (56%) |
| `currency` | 6/10 (60%) | 5/9 (56%) |
| `line_items` | 5/10 (50%) | 4/9 (44%) |
| `tax_total` | 6/10 (60%) | 5/9 (56%) |
| `total` | 6/10 (60%) | 5/9 (56%) |
| **All 8 fields correct** | 5/10 (50%) | 4/9 (44%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 48 | 47 | 98% | 71% | 82% | 100% | 98% | 100% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0049 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes | 0.85 | $0.0031 |
| L03 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0027 |
| L04 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0063 |
| L05 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | no | 0.95 | $0.0186 |
| L06 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L07 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L08 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |
| L09 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L10 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |

## Errors

| Doc | Field | Expected | Predicted | Detail |
|---|---|---|---|---|
| L05 | `line_items` | [{'description': 'Hex bolt M10 x 60 (box of 100)', 'quantit… | [{'description': 'Hex bolt M10 x 40 (box of 100)', 'quantit… | 1 quantity mismatch(es) |

## Review flag vs. actual errors

- Flagged: 5/10
- Documents with at least one wrong field: 5; flagged: 4 (recall 80%)
- Flagged documents with no errors (false alarms): 1 (precision 80%)
- Share of all field errors that sit in flagged documents: 32/33 (97%)
- Missed (wrong but not flagged): L05

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 2638 | 1456 | 606 | 540 | 1.17 | $0.00628 | $0.0377 | $6.28 | 35.3s |
