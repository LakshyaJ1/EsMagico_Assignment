---
name: Invoice Worksheet
description: An accounts-payable invoice reviewer drawn as one spreadsheet workbook, where checks read as formulas and findings as conditional formats.
colors:
  sheet: "#ffffff"
  canvas: "#e4e8e5"
  header: "#f3f5f4"
  header-active: "#d9eadf"
  ink: "#17201b"
  ink-2: "#48524c"
  ink-3: "#66706a"
  header-ink: "#5a645e"
  header-active-ink: "#14533a"
  grid: "#dfe3e0"
  grid-strong: "#c3cbc6"
  accent: "#1f6f4a"
  accent-strong: "#185a3c"
  accent-soft: "rgb(31 111 74 / 0.09)"
  accent-ring: "rgb(31 111 74 / 0.35)"
  on-accent: "#ffffff"
  on-accent-muted: "#d3e7db"
  error-fill: "#f6d3cf"
  error-ink: "#8c1d13"
  warn-fill: "#fbeec4"
  warn-ink: "#6b4a00"
  ok-ink: "#1d6b45"
  info-ink: "#2f5d8a"
  err-1: "#ec9a90"
  err-2: "#da7466"
  err-3: "#c25244"
  err-4: "#9b3226"
typography:
  display:
    fontFamily: '"Archivo Variable", "Archivo", system-ui, sans-serif'
    fontSize: "21px"
    fontWeight: 650
    lineHeight: 1.4
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 106"
  title:
    fontFamily: '"Archivo Variable", "Archivo", system-ui, sans-serif'
    fontSize: "13px"
    fontWeight: 650
    lineHeight: 1.4
  body:
    fontFamily: '"Archivo Variable", "Archivo", system-ui, sans-serif'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "'tnum'"
  control:
    fontFamily: '"Archivo Variable", "Archivo", system-ui, sans-serif'
    fontSize: "12.5px"
    fontWeight: 600
    lineHeight: 1.4
  meta:
    fontFamily: '"Archivo Variable", "Archivo", system-ui, sans-serif'
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: '"Archivo Variable", "Archivo", system-ui, sans-serif'
    fontSize: "11.5px"
    fontWeight: 400
    lineHeight: 1.4
  formula:
    fontFamily: '"JetBrains Mono Variable", ui-monospace, "Cascadia Mono", monospace'
    fontSize: "12.5px"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  none: "0px"
  sm: "2px"
spacing:
  cell-height: "26px"
  row-header: "44px"
  cell-padding: "8px"
  control-gap: "6px"
  pane-inset: "10px"
  bar-inset: "12px"
  page-gutter: "18px"
  message-inset: "48px"
components:
  title-bar:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.title}"
    height: "30px"
    padding: "0 12px"
  formula-bar:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.formula}"
    height: "36px"
  name-box:
    textColor: "{colors.ink}"
    typography: "{typography.formula}"
    rounded: "{rounded.none}"
    width: "104px"
    padding: "0 10px"
  name-box-hover:
    backgroundColor: "{colors.header}"
  pane-head:
    backgroundColor: "{colors.header}"
    textColor: "{colors.ink}"
    height: "36px"
    padding: "0 10px"
  sheet-bar:
    backgroundColor: "{colors.header}"
    textColor: "{colors.ink-2}"
    typography: "{typography.meta}"
    height: "30px"
  sheet-tab:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.none}"
    padding: "0 18px"
  sheet-tab-hover:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
  sheet-tab-active:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.accent}"
  button:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "26px"
  button-hover:
    backgroundColor: "{colors.header}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.control}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "26px"
  button-primary-hover:
    backgroundColor: "{colors.accent-strong}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "26px"
  button-toggle-on:
    backgroundColor: "{colors.header-active}"
    textColor: "{colors.header-active-ink}"
  button-disabled:
    textColor: "{colors.ink-3}"
  icon-button:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    size: "24px"
  icon-button-hover:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
  filter:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "0 8px"
    height: "24px"
  filter-on:
    backgroundColor: "{colors.header-active}"
    textColor: "{colors.header-active-ink}"
  status-chip-ready:
    backgroundColor: "{colors.header-active}"
    textColor: "{colors.header-active-ink}"
    typography: "{typography.meta}"
    rounded: "{rounded.sm}"
    padding: "0 8px"
    height: "20px"
  status-chip-review:
    backgroundColor: "{colors.warn-fill}"
    textColor: "{colors.warn-ink}"
  status-chip-approved:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
  status-chip-rejected:
    backgroundColor: "{colors.error-fill}"
    textColor: "{colors.error-ink}"
  grid-header:
    backgroundColor: "{colors.header}"
    textColor: "{colors.header-ink}"
    typography: "{typography.label}"
  grid-header-active:
    backgroundColor: "{colors.header-active}"
    textColor: "{colors.header-active-ink}"
  cell:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0 8px"
    height: "26px"
  cell-heading:
    backgroundColor: "{colors.header}"
    textColor: "{colors.ink-2}"
  cell-error:
    backgroundColor: "{colors.error-fill}"
    textColor: "{colors.error-ink}"
  cell-warn:
    backgroundColor: "{colors.warn-fill}"
    textColor: "{colors.warn-ink}"
  cell-ok:
    textColor: "{colors.ok-ink}"
  cell-info:
    textColor: "{colors.info-ink}"
  cell-muted:
    textColor: "{colors.ink-3}"
  heat-1:
    backgroundColor: "{colors.err-1}"
    textColor: "{colors.ink}"
  heat-2:
    backgroundColor: "{colors.err-2}"
    textColor: "{colors.ink}"
  heat-3:
    backgroundColor: "{colors.err-3}"
    textColor: "{colors.on-accent}"
  heat-4:
    backgroundColor: "{colors.err-4}"
    textColor: "{colors.on-accent}"
---

# Design System: Invoice Worksheet

Source of truth: `web/src/styles/tokens.css` (every custom property), `web/src/styles/app.css` (all component styles), `web/src/components/Grid.tsx` (the grid primitive) and `web/src/worksheet.ts` (how an extraction becomes rows, checks and tones).

## Overview

**Creative North Star: "The Worksheet"**

The whole app is one spreadsheet workbook. A ledger-green title bar sits on top, then a formula bar (Name Box, fx, the active cell's content and its explanation, the primary action), then the body, then sheet tabs and a live status line along the bottom. Each extraction is a worksheet: lettered columns, numbered rows, header fields, line items, totals, a Review block and a Run block. Every check is written out as a formula in its Check cell, every finding is a conditional format, and the clerk's range selection sums in the status bar exactly where a spreadsheet user looks for a total. The source document is pinned beside the sheet like a frozen pane, on a grey canvas.

Density is the point: 13px type, 26px rows, 1px rules, tabular figures. Nothing floats, nothing is a card. Depth comes from rules and header fills; colour comes almost entirely from meaning (selection green, rose and wheat findings, the red heat ramp on the Evaluation sheet). The system is light only (`color-scheme: light`): a clerk reading figures at a daylight desk for hours.

The build has no sidebar, no white cards and no KPI tiles. Metrics on the Evaluation sheet are cells in run rows, and the document list is itself a grid.

**Key Characteristics:**
- One workbook frame on every view: title bar, formula bar, body, sheet bar. The page never scrolls; panes and grids do.
- A white sheet ruled by 1px gridlines, grey A/B/C and 1/2/3 headers, sticky headers and frozen first rows.
- Ledger green marks where you are and what you do: selection, active headers, active tab, focus, primary action, title bar.
- Conditional formats carry meaning: rose fill = wrong, wheat fill = look at this, green/blue/grey ink = passed / info / evidence.
- Checks read as formulas (`=C9×D9`, `=SUM(E15:E16)`, `≠ printed 40,650.00`); the formula bar explains the active cell in a sentence.
- Corners are square or 2px. One soft shadow, under the document page.
- Motion is functional and short: the selection glides (120ms), a recomputed check flashes once, reading shows marching ants.

## Colors

A near-white, green-tinted neutral sheet with a single ledger-green accent, plus a small conditional-format palette whose fills are reserved for findings.

### Primary
- **Ledger Green** (#1f6f4a, `accent`): the title bar, the selection rectangle and fill handle, the active sheet tab's text and 3px underline, the focus outline, the primary button, links, the comment corner on neutral cells, document codes in the sample list.
- **Deep Ledger** (#185a3c, `accent-strong`): primary button hover and pressed (Approve while approved).
- **Selection Wash** (`accent-soft`, green at 9%): the tint over every cell inside the selected range; laid as a background image so a rose or wheat fill underneath still shows.
- **Edit Ring** (`accent-ring`, green at 35%): the 2px inset underline on an editable cell under the pointer.
- **On Green** (#ffffff, `on-accent`) and **Title Mist** (#d3e7db, `on-accent-muted`): text on green; the mist is only for the title bar's secondary meta (model, input mode, prompt version).

### Secondary: Conditional Formats
- **Rose Fill / Oxblood Ink** (#f6d3cf / #8c1d13, `error-fill` / `error-ink`): a value is wrong or a check failed: mismatched totals, wrong vs ground truth, a missed row, a rejected document, an unflagged error on the Evaluation sheet.
- **Wheat Fill / Umber Ink** (#fbeec4 / #6b4a00, `warn-fill` / `warn-ink`): a person should look: needs review, a row check that does not reconcile, a failed run, a flag that missed errors, the no-API-key notice under a pane head.
- **Pass Ink** (#1d6b45, `ok-ink`): a check that passed, a field matching ground truth, an approved status in the index. Ink only.
- **Note Ink** (#2f5d8a, `info-ink`): informational findings and held-out conditions. Ink only.

### Tertiary: Evaluation Heat Ramp
- **Error Heat 1-4** (#ec9a90, #da7466, #c25244, #9b3226, `err-1`..`err-4`): one hue, light to dark, for the share of documents with a field wrong: ≤10%, ≤25%, ≤50%, >50%. 0% leaves the white sheet. Labels are ink on steps 1-2 and white on steps 3-4. The ramp passed a sequential-ramp check (monotone lightness, single hue, even steps, visible against the sheet); change it only as a whole and re-check it.

### Neutral
- **Sheet** (#ffffff): cells, the formula bar, toolbars, active tab, empty-sheet prompt.
- **Header Grey** (#f3f5f4, `header`): column letters, row numbers, heading rows, pane heads, the sheet bar, button hover, scrollbar track.
- **Active Header** (#d9eadf, `header-active`) with **Active Header Ink** (#14533a): headers of the selected rows/columns, pressed toggles, active filters, the Ready chip, sample-list hover.
- **Canvas** (#e4e8e5): only behind the pinned document, like the grey around a page.
- **Ink** (#17201b), **Ink 2** (#48524c), **Ink 3** (#66706a), **Header Ink** (#5a645e): primary text; secondary text (status line, notes, heading rows); muted evidence, captions and hints; header letters and numbers.
- **Gridline** (#dfe3e0, `grid`) and **Strong Rule** (#c3cbc6, `grid-strong`): cell rules; pane, bar and control borders, header bottoms, scrollbar thumb.

### Named Rules
**The Green Means Here Rule.** Ledger green marks position and action only. A passed check uses Pass Ink (#1d6b45), never the accent and never a fill.

**The Two Fills Rule.** Inside the worksheet, only rose and wheat fill a cell, and a fill always means a person should look. Ok, info and muted are ink-only; the heat ramp is the one other fill set and lives only in the Evaluation matrix.

**The Paired Tone Rule.** Tones are applied as fill+ink pairs through the tone classes. Every pair clears 4.5:1; the one pair that would not (Ink 3 on wheat, 4.43:1) is never combined, so never put muted text on a warn fill.

## Typography

**UI Font:** Archivo Variable (with Archivo, system-ui, sans-serif), loaded with its width axis.
**Formula Font:** JetBrains Mono Variable (with ui-monospace, Cascadia Mono, monospace).

**Character:** A slightly grotesque, adjustable-width sans that reads like a spreadsheet's UI face, paired with a mono that appears only where a spreadsheet would show code: references and identifiers.

### Hierarchy
- **Display** (650, 21px, width 106%, -0.01em): the prompt on an empty or blocked sheet ("Drop an invoice anywhere"). Nowhere else.
- **Title** (650, 13px): toolbar titles and the wordmark (the wordmark widens to 112%).
- **Body** (400, 13px, 1.4, tabular figures): every cell and all running text. `body` sets `tabular-nums` globally.
- **Control** (600, 12.5px): buttons; pane heads use the same size at 400 with a 600 title.
- **Meta** (400, 12px): the status line, title-bar meta, hints, legend, notices; status chips use it at 650.
- **Label** (400, 11.5px): column letters, row numbers, page captions, legend swatches.
- **Formula** (500, 12.5px mono): the Name Box, the formula bar content, document codes (L09, U04) and inline code.

### Named Rules
**The Weight Not Size Rule.** Inside the sheet, emphasis is weight (650 for totals, headings, verdicts), never a larger size. Heading rows are condensed to 94% width and set in Ink 2 on Header Grey.

**The Mono Is For References Rule.** Mono is for the Name Box, the formula bar, document codes and inline code. Cell text, including the formulas in the Check column, stays in Archivo.

**The Tabular Rule.** Figures are tabular and money is right-aligned in its column; the shared formatter (`format.ts`) renders money and quantities.

## Layout

**Frame.** `.app` is a four-row grid at `100dvh`: title bar (30px), formula bar (36px), body (fills), sheet bar (30px). The body clips; only panes and grids scroll.

**Workspace.** Two columns: the document pane at `minmax(300px, 40%)` on the left, the sheet pane on the right, divided by a 1px strong rule. Each pane opens with a 36px pane head on Header Grey (title, caption, tools pushed right). List views (Documents, Evaluation) drop the document pane and put a 38px toolbar row (title, filters or legend, hint) above full-width grids; Evaluation stacks two grids (overview over detail, 1.15 : 1).

**The grid.** A CSS grid: a 44px row-header column, then the view's columns. Rows are 26px (`grid-auto-rows`), cells pad 8px horizontally. Fixed pixel widths for codes and short numbers, `minmax(min, fr)` for text, with the description/explanation column taking the largest fraction. Column letters, row numbers and the corner are sticky; views freeze their first row as a header. Long text ellipsizes; it never wraps a row taller.

**Worksheet anatomy** (`worksheet.ts`). Column A labels, B the value (header fields span B:E), C qty, D unit price, E amount, F check, optional G ground truth. Blocks in order: header fields, a blank row, line items, Sum of line items, tax lines, tax_total, total, a blank row, Review (status, confidence, findings), a blank row, Run (model, calls, tokens, cost, latency). Blank rows and grey heading rows are the only section separators.

**Spacing rhythm.** 6px between controls, 10px pane and toolbar insets, 12px bar insets, 18px gutter around the document pages and between status-line items, 48px around sheet messages. Nothing finer than the cell grid is used for alignment: the empty Extract prompt is measured onto real cells (B4:E13, or A4 to the edge when the pane is under 700px).

**Responsive.**
- At 900px and below, panes stack: document on top (`minmax(200px, 38%)`), sheet below. The title-bar meta, formula note, toolbar hint and pane caption hide; the Name Box narrows to 76px; pane heads wrap. On an empty Extract the document pane collapses to a wrapping row of sample-document chips.
- At 560px and below, quiet buttons and formula-bar actions go icon-only (labels stay in the accessibility tree), except Reject, which keeps its word beside Approve. The status line keeps its message and its last figure (Sum, or Count for a non-numeric range).
- Grids scroll horizontally inside their pane; the page never does.

## Elevation & Depth

Flat. Depth is 1px rules, header fills and sticky stacking (corner above column letters above frozen rows above cells). The document pane is the only lifted thing: each page image sits on the grey canvas with the page shadow. Inset shadows exist only as state marks inside cells.

### Shadow Vocabulary
- **Page** (`box-shadow: 0 1px 2px rgb(23 32 27 / 0.08), 0 8px 24px rgb(23 32 27 / 0.08)`, `--shadow-page`): the rendered pages of the source document. Nothing else.
- **Edit underline** (`box-shadow: inset 0 -2px 0 var(--accent-ring)`): editable cell under the pointer.
- **Recompute flash** (`inset 0 0 0 999px`, green 24% fading to 0): a check that was just recomputed; an overlay, so its fill survives.

### Named Rules
**The One Shadow Rule.** Only paper casts a shadow. Panels, menus, chips and buttons stay flat and are separated by rules.

## Shapes

Two corner values: square (0px) for structure (cells, panes, bars, sheet tabs, the Name Box, the drop range) and 2px for things you press or read as tags (buttons, icon buttons, filters, status chips, inline code). The worksheet's own marks are the recurring shapes: a 2px selection rectangle with a 7px square fill handle bottom-right, a 7px comment triangle in a cell's top-right corner, a 3px underline on the active sheet tab, a 2px dashed range on the empty sheet that becomes marching ants while reading. The 6px scrollbar thumb is browser chrome, not a radius for surfaces.

## Components

### Title Bar
Ledger green band, 30px. A 16px drawn grid mark plus "Invoice Worksheet" (Title, width 112%) on the left; model, input mode and prompt version in Title Mist on the right, with "no API key: browsing only" in white 600 when the backend has no key.

### Formula Bar and Name Box
- **Structure:** 36px white band, strong rule below. Name Box (104px, mono 12.5px, square, strong rule on its right), an `fx` icon in Ink 3, the active cell's formula or text in mono, then its note in Ink 2, then the actions (Open invoice).
- **Behaviour:** the Name Box shows the selection reference (`E12:E16`) and takes input: a cell reference jumps there, a document code (U04) opens that document. Hover fills Header Grey; focus draws a 2px inset green outline.
- **Tone:** the formula region takes the active cell's tone class, so an error cell's explanation reads in Oxblood, a warning's in Umber. It is `aria-live="polite"`.

### Sheet Bar
- **Tabs:** Extract, Documents, Evaluation. Header Grey, Ink 2 at 500, separated by strong rules. Hover: white with Ink. Active: white, green text at 650, 3px green underline, `aria-current="page"`.
- **Status line** (Meta, Ink 2, right-aligned): a status message ("L09.pdf: Ready"), then Average, Count and Sum (values in Ink 600) whenever two or more numeric cells are selected, or Count alone for non-numeric ranges.

### Buttons
- **Shape:** 26px tall, 2px corners, 1px strong-rule border, Control type, 6px icon gap, 14-15px Lucide icons.
- **Default:** white with Ink; hover Header Grey.
- **Primary** (Open invoice, Approve): Ledger Green with white; hover and pressed Deep Ledger. One per region.
- **Quiet** (Ground truth, Re-extract, Reset edits, Reject, JSON): transparent, borderless until hover.
- **Toggle on** (`aria-pressed="true"`, e.g. Ground truth shown, Reject chosen): Active Header fill, Active Header Ink, pressed border #b5d3c1.
- **Disabled:** Ink 3 text, `not-allowed`. **Busy:** `progress` cursor, label changes ("Reading…"), the Re-extract icon spins.
- **Icon button** (zoom, previous/next document): 24px, transparent, Ink 2; hover white with a strong-rule border; disabled drops to Strong Rule colour.
- **Focus:** a 2px Ledger Green outline at 1px offset on every control, including the file input's label.

### Filters
24px, 2px corners, white with Ink 2 at 500 and a trailing count in Ink 3. On: Active Header fill, #b5d3c1 border, Active Header Ink at 600. They sit in the 38px toolbar row and are `aria-pressed` toggles.

### Status Chips
20px, 2px corners, Meta at 650, in the sheet pane head: **Ready** (Active Header), **Needs review** (wheat), **Approved** (Ledger Green, white), **Rejected** (rose).

### Panes
- **Pane head:** 36px, Header Grey, strong rule below, 10px inset. Title in 600, caption in Ink 3, tools right.
- **Document pane:** Canvas background, pages scaled by zoom with an 18px gutter and 14px between pages, each page under the Page shadow with an 11.5px caption. A wheat notice strip can sit under the head.
- **Empty document pane:** a centred Ink 3 note and a sample list drawn as a bordered column of 26px cells (mono green code, then a label; hover Active Header).

### Grid and Cells (signature)
- **Cell:** white, 1px Gridline right and bottom, 8px padding, Body type, single line with ellipsis. Alignment classes: right for figures, centre for row indices.
- **Heading row:** Header Grey, Ink 2, 94% width, 650 labels.
- **Tones:** `error` (rose + Oxblood), `warn` (wheat + Umber), `ok` (Pass Ink), `info` (Note Ink), `muted` (Ink 3: evidence such as tax lines, unit prices, cost).
- **Verdict icons:** 13px Lucide circle icons at stroke 2.25 before the text: check (ok), x (error), alert (warn), info. A verdict is never colour alone.
- **Comment corner:** a 7px triangle top-right meaning "this cell carries a note worth reading" (a finding, an evidence line, or an edit by the clerk). Green on plain cells, Oxblood or Umber on toned cells.
- **Struck row:** text line-through in Oxblood for ground-truth rows the extractor missed.
- **Editable:** hover shows the Edit underline; Enter, F2, double-click or typing opens an in-cell input (white, 2px inset green outline). Enter commits and moves down, Tab commits and moves right, Escape cancels.
- **Selection:** a 2px Ledger Green rectangle that glides between cells (transform, width, height at 120ms) with a 7px fill handle; cells inside take the Selection Wash; the matching column letters and row numbers switch to Active Header at 650. When the grid loses focus the rectangle dims to #8fb7a2.
- **Keyboard:** arrows move, Shift extends, Tab, Home/End, Ctrl+A selects all, Ctrl+C copies the range as tab-separated text. On a non-editable list row, Enter or double-click opens that row (a document, a run).

### Check Formulas
Every check renders as a formula the clerk can read. Passing: the formula itself with an ok icon (`=C9×D9`, `=SUM(E15:E16)`, `=E14+E17`, `= printed subtotal`). Failing: the same relation with `≠` and an error or warn tone (`≠ printed 40,650.00`, `=C9×D9 ≠ amount`). The formula bar shows the evaluated form (`=C9*D9 → 6,160.00`) and a plain sentence that names both numbers and the difference. Booleans read `TRUE`/`FALSE`, missing values read `null`, confidence reads as its own arithmetic (`=1.00 −0.15 line_arithmetic`).

### Heat Cells and Legend
On the Evaluation overview, accuracy cells are filled by the heat ramp: the fill is the whole cell, figures right-aligned. A legend in the toolbar shows "Wrong:" followed by 50×20px swatches for 0%, ≤10%, ≤25%, ≤50%, >50%. A selected heat cell keeps its fill under the Selection Wash.

### Empty Sheet and Drop
- **Drop range:** on the empty Extract sheet, a white block with a 2px dashed strong-rule border, laid exactly over cells, holding the Display prompt, a one-line explanation and the primary button. While reading it becomes 2px green marching ants (600ms loop), like a copied range.
- **Drop error:** a rose block with Oxblood text placed below the range.
- **Drag overlay:** dragging a file anywhere draws a fixed 3px Ledger Green frame with an 8% green wash and a solid green "Drop to extract" label.

### Motion
Content state swaps are instant. The only moving things: the selection glide and header, tab and button colour changes (120ms, `cubic-bezier(0.16, 1, 0.3, 1)`); the recompute flash (700ms, once, only on check cells, never on the cell the clerk typed into); marching ants while reading; the Re-extract spinner (900ms linear). Under `prefers-reduced-motion` every transition and animation drops to 0ms and the ants stop.

### Accessibility Behaviours
- The grid is `role="grid"` with row and column counts, `aria-activedescendant` on the active cell and `aria-selected` on cells in range; headers are `aria-hidden` decoration.
- Verdicts carry an icon and a word ("wrong", "≠ …"), not colour alone; findings repeat as sentences in the formula bar and the Review block.
- Focus is always a visible 2px green outline. Icon-only buttons keep their labels for assistive tech.
- `forced-colors`: the selection uses `Highlight`, and rose and wheat cells gain a 1px `CanvasText` border so the finding survives without fills.
- Contrast: every text/fill pair is at least 4.5:1, with the single exception of Ink 3 on wheat (4.43:1), which no tone combines.

## Do's and Don'ts

### Do:
- **Do** put every new number in a cell: 13px tabular figures, right-aligned, formatted by `format.ts`, with a `value` so range Sum/Average works.
- **Do** write a new check as a formula in the Check column (`=…` with an ok icon when it holds, `≠ …` with an error or warn tone and a comment corner when it does not) and give the cell a `note` sentence for the formula bar.
- **Do** separate sections inside a sheet with a blank row and a grey heading row, and freeze a list's header row.
- **Do** add a new view as a sheet tab with its own Grid, a 38px toolbar row for its title and filters, and the shared title bar, formula bar and sheet bar.
- **Do** keep chrome on the existing heights: 30px bars, 36px formula bar and pane heads, 26px rows and buttons, 24px icon buttons and filters, 20px chips.
- **Do** add any new colour to `tokens.css` and contrast-check it against every fill it can sit on before use.
- **Do** keep the document pinned beside the sheet whenever a single document is open.

### Don't:
- **Don't** add cards, KPI tiles or a sidebar; a metric is a cell in a row, as on the Evaluation sheet.
- **Don't** fill a cell green for success or use Ledger Green to mean "correct"; pass is ink-only, and green means selection and action.
- **Don't** fill cells with any colour beyond rose, wheat and (on the Evaluation matrix only) the heat ramp; header and selection tints are the only other fills.
- **Don't** put Ink 3 text on the wheat fill.
- **Don't** round anything past 2px or give anything but the document page an outer shadow.
- **Don't** set cell text in the mono face or enlarge type to emphasize inside the sheet; use weight 650.
- **Don't** animate content in or out; motion is limited to the selection glide, the once-only recompute flash and progress indicators, and all of it must stop under reduced motion.
- **Don't** let the page scroll or overflow horizontally; scrolling belongs to panes and grids.
- **Don't** treat the hex literals in `app.css` (#cfe5d8 text selection, #b5d3c1 pressed border, #8fb7a2 idle selection) as precedent; reuse means promoting them to `tokens.css` first.
