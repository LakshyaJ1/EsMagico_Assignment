# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T19:54:14+00:00
- Model: `gemini-3.5-flash-lite` · input mode `hybrid` · thinking `low` · prompt `v2`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 10/10 (100%) | 9/9 (100%) |
| `vendor` | 10/10 (100%) | 9/9 (100%) |
| `invoice_number` | 10/10 (100%) | 9/9 (100%) |
| `invoice_date` | 10/10 (100%) | 9/9 (100%) |
| `currency` | 10/10 (100%) | 9/9 (100%) |
| `line_items` | 9/10 (90%) | 8/9 (89%) |
| `tax_total` | 10/10 (100%) | 9/9 (100%) |
| `total` | 10/10 (100%) | 9/9 (100%) |
| **All 8 fields correct** | 9/10 (90%) | 8/9 (89%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 66 | 65 | 98% | 98% | 98% | 100% | 98% | 100% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0017 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0022 |
| L03 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0020 |
| L04 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0052 |
| L05 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | no | 1.00 | $0.0028 |
| L06 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0019 |
| L07 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0018 |
| L08 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0010 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0022 |
| L10 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |

## Errors

| Doc | Field | Expected | Predicted | Detail |
|---|---|---|---|---|
| L05 | `line_items` | [{'description': 'Hex bolt M10 x 60 (box of 100)', 'quantit… | [{'description': 'Hex bolt M10 x 60 (box of 100)', 'quantit… | 1 quantity mismatch(es) |

## Review flag vs. actual errors

- Flagged: 0/10
- Documents with at least one wrong field: 1; flagged: 0 (recall 0%)
- Flagged documents with no errors (false alarms): 0 (precision -)
- Share of all field errors that sit in flagged documents: 0/1 (0%)
- Missed (wrong but not flagged): L05

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 2106 | 1204 | 665 | 0 | 1.00 | $0.00229 | $0.0229 | $2.29 | 6.2s |
