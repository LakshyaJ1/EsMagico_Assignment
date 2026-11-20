# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T19:55:15+00:00
- Model: `gemini-3.5-flash-lite` · input mode `hybrid` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 8/10 (80%) | 7/9 (78%) |
| `vendor` | 8/10 (80%) | 7/9 (78%) |
| `invoice_number` | 7/10 (70%) | 6/9 (67%) |
| `invoice_date` | 6/10 (60%) | 5/9 (56%) |
| `currency` | 8/10 (80%) | 7/9 (78%) |
| `line_items` | 6/10 (60%) | 5/9 (56%) |
| `tax_total` | 7/10 (70%) | 6/9 (67%) |
| `total` | 7/10 (70%) | 6/9 (67%) |
| **All 8 fields correct** | 4/10 (40%) | 3/9 (33%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 50 | 46 | 92% | 70% | 79% | 96% | 94% | 92% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0017 |
| L02 | photo | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L03 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0020 |
| L04 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | yes | 0.00 | $0.0114 |
| L05 | digital | ERR | ERR | ERR | ERR | ERR | ERR | ERR | ERR | yes | - | - |
| L06 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes | 0.85 | $0.0019 |
| L07 | scan | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | yes | 0.85 | $0.0018 |
| L08 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0010 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | yes | 0.85 | $0.0022 |
| L10 | scan | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |

## Errors

| Doc | Field | Expected | Predicted | Detail |
|---|---|---|---|---|
| L04 | `line_items` | [{'description': 'Corrugated box 12x9x6 in (3-ply)', 'quant… | [{'description': 'Corrugated box 12x9x6 in (3-ply)', 'quant… | 1 quantity mismatch(es); 1 amount mismatch(es) |
| L07 | `invoice_number` | PHS-1042 | PHS-1842 |  |
| L07 | `invoice_date` | 2026-03-14 | 2020-03-14 |  |
| L09 | `line_items` | [{'description': 'King fish (seer), cleaned, kg', 'quantity… | [{'description': 'King fish (peeled), cleaned, kg', 'quanti… | 2 quantity mismatch(es); 3 amount mismatch(es); 2 description mismatch(es) |
| L09 | `tax_total` | 2032.5 | 2925.62 | off by +893.12 |
| L09 | `total` | 42682.5 | 61438.12 | off by +18,755.62 |
| L10 | `invoice_date` | 2026-09-03 | 2020-09-03 |  |

## Review flag vs. actual errors

- Flagged: 6/10
- Documents with at least one wrong field: 6; flagged: 5 (recall 83%)
- Flagged documents with no errors (false alarms): 1 (precision 83%)
- Share of all field errors that sit in flagged documents: 22/23 (96%)
- Missed (wrong but not flagged): L10

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 2765 | 1498 | 869 | 0 | 1.12 | $0.00300 | $0.0240 | $3.00 | 7.3s |
