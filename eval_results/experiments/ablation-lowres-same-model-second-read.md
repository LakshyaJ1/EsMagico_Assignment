# Eval results: gemini-3.5-flash-lite

- Evaluated: 2026-11-20T20:44:04+00:00
- Model: `gemini-3.5-flash-lite` · input mode `hybrid` · thinking `low` · prompt `v3`
- Documents: 10 labelled

## Field-level accuracy

| Field | All labelled docs | Invoices only |
|---|---|---|
| `is_invoice` | 10/10 (100%) | 9/9 (100%) |
| `vendor` | 10/10 (100%) | 9/9 (100%) |
| `invoice_number` | 9/10 (90%) | 8/9 (89%) |
| `invoice_date` | 8/10 (80%) | 7/9 (78%) |
| `currency` | 10/10 (100%) | 9/9 (100%) |
| `line_items` | 6/10 (60%) | 5/9 (56%) |
| `tax_total` | 7/10 (70%) | 6/9 (67%) |
| `total` | 8/10 (80%) | 7/9 (78%) |
| **All 8 fields correct** | 3/10 (30%) | 2/9 (22%) |

## Line items (row level)

| Rows expected | Rows predicted | Fully correct | Precision | Recall | F1 | Description | Quantity | Amount |
|---|---|---|---|---|---|---|---|---|
| 66 | 66 | 58 | 88% | 88% | 88% | 97% | 94% | 91% |

## Per document

| Doc | Source | is_inv | vendor | inv_no | date | cur | lines | tax | total | Flagged | Confidence | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | scan | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0018 |
| L02 | photo | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | yes | 0.65 | $0.0071 |
| L03 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0020 |
| L04 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | yes | 0.55 | $0.0108 |
| L05 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | yes | 0.50 | $0.0088 |
| L06 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0039 |
| L07 | scan | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | yes | 0.85 | $0.0019 |
| L08 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | no | 1.00 | $0.0021 |
| L09 | scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | yes | 0.50 | $0.0069 |
| L10 | scan | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | yes | 0.85 | $0.0022 |

## Errors

| Doc | Field | Expected | Predicted | Detail |
|---|---|---|---|---|
| L01 | `invoice_number` | NWL-88213 | NWL-68213 |  |
| L02 | `line_items` | [{'description': 'Exam pad A4 (200 pages)', 'quantity': 150… | [{'description': 'Exam pad A4 (200 pages)', 'quantity': 150… | 1 amount mismatch(es) |
| L02 | `tax_total` | 3529.8 | 3511.8 | off by -18.00 |
| L02 | `total` | 23139.8 | 23021.8 | off by -118.00 |
| L04 | `line_items` | [{'description': 'Corrugated box 12x9x6 in (3-ply)', 'quant… | [{'description': 'Corrugated box 12x9x6 in (3-ply)', 'quant… | 1 quantity mismatch(es) |
| L05 | `line_items` | [{'description': 'Hex bolt M10 x 60 (box of 100)', 'quantit… | [{'description': 'Hex bolt M16 x 60 (box of 100)', 'quantit… | 1 quantity mismatch(es); 2 amount mismatch(es) |
| L05 | `tax_total` | 12708.9 | 12628.9 | off by -80.00 |
| L07 | `invoice_date` | 2026-03-14 | 2020-03-14 |  |
| L09 | `line_items` | [{'description': 'King fish (seer), cleaned, kg', 'quantity… | [{'description': 'King fish (peel.), cleaned, kg', 'quantit… | 2 quantity mismatch(es); 3 amount mismatch(es); 2 description mismatch(es) |
| L09 | `tax_total` | 2032.5 | 2917.5 | off by +885.00 |
| L09 | `total` | 42682.5 | 61267.5 | off by +18,585.00 |
| L10 | `invoice_date` | 2026-09-03 | 2020-09-03 |  |

## Review flag vs. actual errors

- Flagged: 6/10
- Documents with at least one wrong field: 7; flagged: 6 (recall 86%)
- Flagged documents with no errors (false alarms): 0 (precision 100%)
- Share of all field errors that sit in flagged documents: 11/12 (92%)
- Missed (wrong but not flagged): L01

## Cost

| Avg input tokens | of which image | Avg output tokens | Avg thinking tokens | Calls/doc | Avg cost/doc | Total | Per 1,000 docs | Avg latency |
|---|---|---|---|---|---|---|---|---|
| 4394 | 2290 | 1368 | 0 | 1.90 | $0.00474 | $0.0474 | $4.74 | 6.6s |
