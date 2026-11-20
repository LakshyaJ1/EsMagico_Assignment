# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T20:43:07+00:00
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
| `line_items` | 9/10 (90%) | 8/9 (89%) |
| `tax_total` | 9/10 (90%) | 8/9 (89%) |
| `total` | 9/10 (90%) | 8/9 (89%) |
| **All 8 fields correct** | 9/10 (90%) | 8/9 (89%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 66 | 65 | 98% | 98% | 98% | 100% | 98% | 98% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0032 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0040 |
| L03 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0036 |
| L04 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0089 |
| L05 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0048 |
| L06 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0035 |
| L07 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0031 |
| L08 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0020 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | yes | 0.70 | $0.0038 |
| L10 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0037 |

## Errors

| Doc | Field | Expected | Predicted | Detail |
|---|---|---|---|---|
| L09 | `line_items` | [{'description': 'King fish (seer), cleaned, kg', 'quantity… | [{'description': 'King fish (seer), cleaned, kg', 'quantity… | 1 quantity mismatch(es); 1 amount mismatch(es) |
| L09 | `tax_total` | 2032.5 | 2030.5 | off by -2.00 |
| L09 | `total` | 42682.5 | 42640.5 | off by -42.00 |

## Review flag vs. actual errors

- Flagged: 1/10
- Documents with at least one wrong field: 1; flagged: 1 (recall 100%)
- Flagged documents with no errors (false alarms): 0 (precision 100%)
- Share of all field errors that sit in flagged documents: 3/3 (100%)
- Missed (wrong but not flagged): none

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 4329 | 2397 | 1344 | 108 | 2.00 | $0.00405 | $0.0405 | $4.05 | 7.3s |
