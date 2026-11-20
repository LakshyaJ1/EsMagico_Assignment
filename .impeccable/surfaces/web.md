---
version: 1
slug: "web"
primary_target: "web"
related_targets: []
---

# Surface brief: invoice reviewer web app (web/)

Scope: the whole web app (Extract, Documents, Evaluation, correction). Visitor mode: Operate.
Audience and job: an accounts-payable clerk checking extracted invoice data against the
source document, fixing what is wrong, and exporting only trusted JSON. Reviewers from
Es Magico use it the same way.
Constraints: data comes from the FastAPI backend; Documents and Evaluation work without an
API key; every number is real (from outputs/ and eval_results/), nothing invented.
Memorable moment: select a range of line amounts and the status bar sums it, exactly
where the clerk's eye already expects a total; the formula bar shows why a check passed.

## Direction contract

THESIS: Each extraction is a worksheet whose checks read as formulas. Refuses the sidebar, white-card, KPI-tile dashboard.
OWN-WORLD: White sheet ruled by 1px #dfe3e0 gridlines; grey A/B/C and 1/2/3 headers; ledger-green #1f6f4a selection; rose and wheat conditional fills for errors and warnings; tabular figures; 13px cells, 26px rows; corners 0-2px.
STORY: Drop an invoice, see the page pinned beside its worksheet, read each check, fix flagged cells, approve, export.
FIRST VIEWPORT: Formula bar across the top (cell reference, value, evidence). Document pane left, about 42%. Worksheet right: header fields, line items, checks block. Sheet tabs and a SUM status bar along the bottom. Primary action "Open invoice" sits in the formula bar row; dropping anywhere works.
FORM: Spreadsheet worksheet, my list #4, seed 0cf3f228.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Signature interaction: range selection with live SUM/COUNT in the status bar; the formula bar explains the active cell.
Motion grammar: instant state swaps; the selection rectangle glides (120ms); a recomputed check flashes once.

## Unresolved

None.
