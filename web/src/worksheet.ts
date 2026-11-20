// Builds the review worksheet (rows of cells) from an extraction. Pure: no React, no I/O.
//
// The check formulas shown here explain the arithmetic to the reviewer. The authoritative
// verdict (issues, needs_review) always comes from the backend validator via /api/validate;
// both apply the same rule (cent-level tolerance that grows with the number of values summed).

import type { Evidence, FieldComparison, InvoiceResult, Issue, Meta, Review } from "./api";
import type { GridCell, GridRow } from "./components/Grid";
import { cellRef, money, quantity } from "./format";
import type { Tone } from "./selection";

export type Binding =
  | { kind: "field"; field: "vendor" | "invoice_number" | "invoice_date" | "currency" | "tax_total" | "total" }
  | { kind: "line"; index: number; prop: "description" | "quantity" | "amount" | "unit_price" };

export interface Draft {
  result: InvoiceResult;
  unitPrices: (number | null)[];
}

export interface Sheet {
  rows: GridRow[];
  bindings: Map<string, Binding>;
}

export const COLUMN_KEYS = ["label", "description", "qty", "unit", "amount", "check", "truth"] as const;

export const moneyTolerance = (components: number) => Math.max(0.05, 0.01 * (components + 1));
const close = (a: number, b: number, tolerance: number) => Math.abs(a - b) <= tolerance;
const key = (r: number, c: number) => `${r}:${c}`;

const SEVERITY_TONE: Record<Issue["severity"], Tone> = { error: "error", warning: "warn", info: "info" };

const RULE_TEXT: Record<string, string> = {
  missing_field: "missing",
  currency_unknown: "not ISO 4217",
  date_inconsistent: "≠ printed date",
  date_stale: "> 1 year old",
  date_future: "future date",
  date_order: "≠ due-date order",
  model_uncertain: "model unsure",
  reads_disagree: "reads disagree",
  totals_mismatch: "≠ lines + tax",
  tax_lines_mismatch: "≠ tax lines",
};

function fieldTone(issues: Issue[], field: string): { tone?: Tone; note?: string; rule?: string } {
  const hit = issues.find((issue) => issue.field === field && issue.severity !== "info");
  return hit
    ? { tone: SEVERITY_TONE[hit.severity], note: hit.message, rule: RULE_TEXT[hit.code] ?? hit.code.replace(/_/g, " ") }
    : {};
}

function displayValue(value: unknown, currency: string | null): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "number") return money(value, currency);
  if (typeof value === "boolean") return value ? "TRUE" : "FALSE";
  if (Array.isArray(value)) return `${value.length} rows`;
  return String(value);
}

interface BuildOptions {
  draft: Draft;
  evidence: Evidence | null;
  meta: Meta | null;
  issues: Issue[];
  review: Review | null;
  comparison: FieldComparison[] | null;
  truth: InvoiceResult | null;
  showTruth: boolean;
  edited: Set<string>;
}

export function buildSheet(options: BuildOptions): Sheet {
  const { draft, evidence, meta, issues, review, comparison, truth, showTruth, edited } = options;
  const { result } = draft;
  const currency = result.currency;
  const rows: GridRow[] = [];
  const bindings = new Map<string, Binding>();
  const width = showTruth ? 7 : 6;
  const truthFor = (field: string) => comparison?.find((entry) => entry.field === field);

  const row = (keyName: string, cells: (GridCell | null)[], extra: Partial<GridRow> = {}) => {
    const padded = [...cells];
    while (padded.length < width) padded.push({ text: "" });
    rows.push({ key: keyName, cells: padded.slice(0, width), ...extra });
    return rows.length - 1;
  };
  const truthCell = (field: string): GridCell | null => {
    if (!showTruth) return null;
    const entry = truthFor(field);
    if (!entry) return { text: "" };
    return {
      text: displayValue(entry.expected, currency),
      align: typeof entry.expected === "number" ? "right" : "left",
      tone: entry.correct ? "ok" : "error",
      icon: entry.correct ? "ok" : "error",
      note: entry.correct ? "Matches ground truth." : `Ground truth differs. ${entry.detail}`.trim(),
    };
  };
  const bind = (r: number, c: number, binding: Binding) => bindings.set(key(r, c), binding);
  const editedMark = (binding: string) => (edited.has(binding) ? " · edited by you" : "");

  // ---- Header fields --------------------------------------------------------------
  row("head-fields", [{ text: "Field", strong: true }, { text: "Extracted value", strong: true, span: 4 }, null, null, null, { text: "Check", strong: true }, showTruth ? { text: "Ground truth", strong: true } : null], { heading: true });

  row("is_invoice", [
    { text: "is_invoice" },
    { text: result.is_invoice ? "TRUE" : "FALSE", span: 4, strong: true, tone: result.is_invoice ? undefined : "muted" },
    null, null, null,
    {
      text: meta ? meta.classification.document_type.replace(/_/g, " ") : "",
      tone: "muted",
      note: meta?.classification.reason,
      formula: meta ? `Classified as ${meta.classification.document_type.replace(/_/g, " ")}` : "",
    },
    truthCell("is_invoice"),
  ]);

  const headerFields = [
    ["vendor", "Seller name exactly as printed at the top."],
    ["invoice_number", "Exactly as printed, separators included."],
    ["invoice_date", "Issue date (not due date), ISO format."],
    ["currency", "ISO 4217 code."],
  ] as const;
  for (const [field, hint] of headerFields) {
    const value = result[field];
    const flag = fieldTone(issues, field);
    let check: GridCell = flag.note
      ? { text: flag.rule ?? "check", tone: flag.tone, icon: flag.tone === "error" ? "error" : "warn", note: flag.note, comment: true }
      : { text: value === null ? "" : "present", tone: value === null ? "muted" : "ok", icon: value === null ? undefined : "ok", note: hint };
    if (field === "invoice_date" && evidence?.invoice_date_as_printed) {
      check = {
        text: `printed “${evidence.invoice_date_as_printed}”`,
        tone: flag.tone ?? "muted",
        comment: true,
        note: flag.note ?? evidence.date_reasoning ?? "Read from the printed issue date.",
        formula: `=DATEVALUE("${evidence.invoice_date_as_printed}") → ${value ?? "null"}`,
      };
    }
    const r = row(field, [
      { text: field },
      {
        text: value ?? (result.is_invoice ? "" : "null"),
        span: 4,
        editable: result.is_invoice,
        tone: flag.tone ?? (value === null ? "muted" : undefined),
        note: `${hint}${editedMark(field)}`,
        comment: edited.has(field),
        title: result.is_invoice ? "Double-click or start typing to correct" : undefined,
      },
      null, null, null,
      check,
      truthCell(field),
    ]);
    bind(r, 1, { kind: "field", field });
  }

  row("gap-1", []);

  // ---- Line items -----------------------------------------------------------------
  row("head-lines", [
    { text: "#", strong: true, align: "center" },
    { text: "Description", strong: true },
    { text: "Qty", strong: true, align: "right" },
    { text: "Unit price", strong: true, align: "right" },
    { text: "Amount", strong: true, align: "right" },
    { text: "Check", strong: true },
    showTruth ? { text: "Ground truth amount", strong: true, align: "right" } : null,
  ], { heading: true });

  const lines = result.line_items ?? [];
  const firstLineRow = rows.length;
  const expectedLines = (truth?.line_items ?? []) as InvoiceResult["line_items"] & object;

  if (!result.is_invoice) {
    row("no-lines", [{ text: "" }, { text: "Not an invoice, so no line items are extracted.", span: 4, tone: "muted" }, null, null, null]);
  } else if (lines.length === 0) {
    row("no-lines", [{ text: "" }, { text: "No line items were extracted.", span: 4, tone: "warn" }, null, null, null]);
  }

  lines.forEach((line, index) => {
    const r = rows.length;
    const unit = draft.unitPrices[index] ?? null;
    let check: GridCell = { text: "" };
    if (line.quantity !== null && unit !== null) {
      const expected = line.quantity * unit;
      const ok = close(expected, line.amount, Math.max(0.05, 0.005 * Math.abs(line.amount)));
      check = {
        text: ok ? `=C${r + 1}×D${r + 1}` : `=C${r + 1}×D${r + 1} ≠ amount`,
        tone: ok ? "ok" : "warn",
        comment: !ok,
        icon: ok ? "ok" : "warn",
        formula: `=C${r + 1}*D${r + 1} → ${money(expected, currency)}`,
        note: ok ? "Quantity × unit price equals the amount." : `Quantity × unit price is ${money(expected, currency)}, but the amount is ${money(line.amount, currency)}.`,
      };
    } else if (line.amount < 0) {
      check = { text: "discount", tone: "muted", note: "Negative row: a discount printed in the item table." };
    }
    const expectedLine = showTruth ? expectedLines[index] : undefined;
    const truthLine: GridCell | null = showTruth
      ? expectedLine
        ? {
            text: money(expectedLine.amount, currency),
            align: "right",
            value: expectedLine.amount,
            tone: close(expectedLine.amount, line.amount, 0.01) && expectedLine.quantity === line.quantity ? "ok" : "error",
            note: `Ground truth: ${expectedLine.description} · qty ${quantity(expectedLine.quantity) || "null"} · ${money(expectedLine.amount, currency)}`,
          }
        : { text: "extra row", tone: "error", note: "Ground truth has no row here." }
      : null;
    row(`line-${index}`, [
      { text: String(index + 1), align: "center", tone: "muted" },
      { text: line.description, editable: true, comment: edited.has(`line-${index}-description`), note: `Description as printed${editedMark(`line-${index}-description`)}` },
      { text: quantity(line.quantity), value: line.quantity, align: "right", editable: true, note: line.quantity === null ? "No quantity printed on this row." : undefined },
      { text: unit === null ? "" : money(unit, currency), value: unit, align: "right", editable: true, tone: "muted", note: "Unit price (evidence used for the row check; not part of the output schema)." },
      { text: money(line.amount, currency), value: line.amount, align: "right", editable: true, comment: edited.has(`line-${index}-amount`) || edited.has(`line-${index}-quantity`), tone: line.amount < 0 ? "muted" : undefined, note: `Row total before tax${editedMark(`line-${index}-amount`)}` },
      check,
      truthLine,
    ]);
    bind(r, 1, { kind: "line", index, prop: "description" });
    bind(r, 2, { kind: "line", index, prop: "quantity" });
    bind(r, 3, { kind: "line", index, prop: "unit_price" });
    bind(r, 4, { kind: "line", index, prop: "amount" });
  });
  if (showTruth && expectedLines.length > lines.length) {
    for (let index = lines.length; index < expectedLines.length; index++) {
      const missing = expectedLines[index];
      if (!missing) continue;
      row(`missing-${index}`, [
        { text: String(index + 1), align: "center", tone: "error" },
        { text: missing.description, tone: "error", note: "Missing: this ground-truth row was not extracted." },
        { text: quantity(missing.quantity), align: "right", tone: "error" },
        { text: "" },
        { text: money(missing.amount, currency), align: "right", tone: "error" },
        { text: "missed row", tone: "error" },
        { text: money(missing.amount, currency), align: "right", tone: "error" },
      ], { struck: true });
    }
  }
  const lastLineRow = firstLineRow + lines.length - 1;

  if (!result.is_invoice) return { rows, bindings };

  // ---- Totals ---------------------------------------------------------------------
  const lineSum = lines.reduce((total, line) => total + line.amount, 0);
  const sumRange = lines.length ? `E${firstLineRow + 1}:E${lastLineRow + 1}` : "";
  const subtotal = evidence?.subtotal ?? null;
  const subtotalOk = subtotal === null || close(lineSum, subtotal, moneyTolerance(lines.length));
  const lineSumRow = row("line-sum", [
    { text: "" },
    { text: "Sum of line items", strong: true },
    { text: "" },
    { text: "" },
    { text: money(lineSum, currency), value: lineSum, align: "right", strong: true, formula: `=SUM(${sumRange})`, note: `${lines.length} rows` },
    subtotal === null
      ? { text: "no subtotal printed", tone: "muted" }
      : {
          text: subtotalOk ? "= printed subtotal" : `≠ printed ${money(subtotal, currency)}`,
          tone: subtotalOk ? "ok" : "error",
          icon: subtotalOk ? "ok" : "error",
          comment: !subtotalOk,
          formula: `=SUM(${sumRange}) = ${money(subtotal, currency)}`,
          note: subtotalOk
            ? `Matches the subtotal printed on the document (${money(subtotal, currency)}).`
            : `Printed subtotal is ${money(subtotal, currency)}; the rows sum to ${money(lineSum, currency)} (difference ${money(lineSum - subtotal, currency)}). A row was probably missed or misread.`,
        },
    showTruth ? { text: "" } : null,
  ]);

  const taxLines = evidence?.tax_lines ?? [];
  const firstTaxRow = rows.length;
  taxLines.forEach((tax, index) => {
    row(`tax-${index}`, [
      { text: "" },
      { text: tax.label, tone: "muted" },
      { text: "" },
      { text: tax.rate_percent === null ? "" : `${tax.rate_percent}%`, align: "right", tone: "muted" },
      { text: money(tax.amount, currency), value: tax.amount, align: "right", tone: "muted", comment: true, note: "Tax line as printed (evidence)." },
    ]);
  });
  const taxSum = taxLines.reduce((total, tax) => total + tax.amount, 0);
  const taxTotal = result.tax_total;
  const taxOk = taxLines.length === 0 || taxTotal === null || close(taxSum, taxTotal, moneyTolerance(taxLines.length));
  const taxRange = taxLines.length ? `E${firstTaxRow + 1}:E${firstTaxRow + taxLines.length}` : "";
  const taxFlag = fieldTone(issues, "tax_total");
  const taxRow = row("tax_total", [
    { text: "tax_total" },
    { text: taxLines.length ? `${taxLines.length} tax line${taxLines.length > 1 ? "s" : ""}` : "no tax printed", tone: "muted" },
    { text: "" },
    { text: "" },
    { text: money(taxTotal, currency), value: taxTotal, align: "right", strong: true, editable: true, comment: edited.has("tax_total"), tone: taxFlag.tone, note: `Sum of all tax lines${editedMark("tax_total")}` },
    taxLines.length
      ? { text: taxOk ? `=SUM(${taxRange})` : `≠ SUM(${taxRange})`, tone: taxOk ? "ok" : "error", icon: taxOk ? "ok" : "error", formula: `=SUM(${taxRange}) → ${money(taxSum, currency)}`, note: taxOk ? "Equals the sum of the printed tax lines." : `Tax lines sum to ${money(taxSum, currency)}.` }
      : { text: "0 when no tax is printed", tone: "muted" },
    truthCell("tax_total"),
  ]);
  bind(taxRow, 4, { kind: "field", field: "tax_total" });

  const total = result.total;
  const expectedTotal = lineSum + (taxTotal ?? 0);
  const totalOk = total !== null && close(expectedTotal, total, moneyTolerance(lines.length + Math.max(taxLines.length, 1)));
  const totalRow = row("total", [
    { text: "total" },
    { text: "Amount payable", strong: true },
    { text: "" },
    { text: currency ?? "", align: "right", tone: "muted" },
    { text: money(total, currency), value: total, align: "right", strong: true, editable: true, comment: edited.has("total"), tone: fieldTone(issues, "total").tone, note: `Final amount payable, tax included${editedMark("total")}` },
    total === null
      ? { text: "missing", tone: "error", icon: "error" }
      : {
          text: totalOk ? `=E${lineSumRow + 1}+E${taxRow + 1}` : `≠ E${lineSumRow + 1}+E${taxRow + 1}`,
          tone: totalOk ? "ok" : "error",
          icon: totalOk ? "ok" : "error",
          strong: true,
          formula: `=E${lineSumRow + 1}+E${taxRow + 1} → ${money(expectedTotal, currency)}`,
          note: totalOk
            ? "Line items plus tax equal the total."
            : `Line items + tax = ${money(expectedTotal, currency)}, but the total is ${money(total, currency)} (difference ${money(total - expectedTotal, currency)}).`,
        },
    truthCell("total"),
  ]);
  bind(totalRow, 4, { kind: "field", field: "total" });

  // ---- Review ---------------------------------------------------------------------
  row("gap-2", []);
  row("head-review", [{ text: "Review", strong: true }, { text: "Finding", strong: true, span: 4 }, null, null, null, { text: "Code", strong: true }, showTruth ? { text: "" } : null], { heading: true });
  if (review) {
    row("status", [
      { text: "status" },
      {
        text: review.needs_review ? "Needs review" : "Ready",
        span: 4,
        strong: true,
        tone: review.needs_review ? "warn" : "ok",
        note: review.needs_review ? review.reasons.join(" ") : "Every check passed.",
      },
      null, null, null,
      { text: "" },
    ]);
    const deductions = confidenceTerms(issues, meta);
    row("confidence", [
      { text: "confidence" },
      {
        text: deductions.length ? `=1.00 ${deductions.join(" ")}` : "=1.00 (no deductions)",
        span: 3,
        tone: "muted",
        formula: deductions.length ? `=1.00 ${deductions.join(" ")}` : "=1.00",
        note: "Not a probability: 1.00 minus 0.40 per error, 0.15 per warning, 0.05 after a corrective re-read.",
      },
      null, null,
      { text: review.confidence.toFixed(2), value: review.confidence, align: "right", strong: true },
      { text: "" },
    ]);
  }
  const visible = issues.filter((issue) => issue.severity !== "info" || issue.code.startsWith("second_read") || issue.code.startsWith("orientation") || issue.code === "fallback_model" || issue.code === "date_ambiguous");
  if (visible.length === 0) {
    row("no-issues", [{ text: "" }, { text: "No findings. Every check passed.", span: 4, tone: "ok" }, null, null, null]);
  }
  visible.forEach((issue, index) => {
    row(`issue-${index}`, [
      { text: issue.severity, tone: SEVERITY_TONE[issue.severity], icon: issue.severity === "error" ? "error" : issue.severity === "warning" ? "warn" : "info" },
      { text: issue.message, span: 4, tone: SEVERITY_TONE[issue.severity], note: issue.retryable ? "Triggered one corrective re-read." : undefined },
      null, null, null,
      { text: issue.code, tone: "muted" },
    ]);
  });

  // ---- Run ------------------------------------------------------------------------
  if (meta) {
    row("gap-3", []);
    row("head-run", [{ text: "Run", strong: true }, { text: "", span: 4 }, null, null, null, { text: "" }], { heading: true });
    const usage = meta.usage;
    const runRows: [string, string, number | null, string?][] = [
      ["model", meta.served_by.join(", ") || meta.model, null, `Requested ${meta.model}; input mode ${meta.input_mode}.`],
      ["calls", meta.attempts.map((a) => a.purpose).join(" → "), usage.calls],
      ["tokens in", `${usage.input_tokens.toLocaleString()} (${usage.image_tokens.toLocaleString()} image)`, usage.input_tokens],
      ["tokens out", `${usage.output_tokens.toLocaleString()} + ${usage.thinking_tokens.toLocaleString()} thinking`, usage.output_tokens + usage.thinking_tokens],
      ["cost (USD)", `$${usage.cost_usd.toFixed(5)}`, usage.cost_usd, "Paid-tier list price: input tokens × input rate + (output + thinking) × output rate."],
      ["latency", `${(meta.latency_ms / 1000).toFixed(1)} s`, meta.latency_ms / 1000],
    ];
    for (const [label, text, value, note] of runRows) {
      row(`run-${label}`, [{ text: label, tone: "muted" }, { text, span: 4, value, note }, null, null, null]);
    }
  }
  return { rows, bindings };
}

function confidenceTerms(issues: Issue[], meta: Meta | null): string[] {
  const terms = issues
    .filter((issue) => issue.severity !== "info")
    .map((issue) => `−${issue.severity === "error" ? "0.40" : "0.15"} ${issue.code}`);
  if (meta?.attempts.some((attempt) => attempt.purpose === "correction")) terms.push("−0.05 re-read");
  return terms;
}

/** Apply a typed edit to the draft; returns null when the text is not a valid value. */
export function applyEdit(draft: Draft, binding: Binding, text: string, parse: (text: string) => number | null): Draft | null {
  const result: InvoiceResult = { ...draft.result, line_items: draft.result.line_items?.map((line) => ({ ...line })) ?? null };
  const unitPrices = [...draft.unitPrices];
  const trimmed = text.trim();
  if (binding.kind === "field") {
    if (binding.field === "tax_total" || binding.field === "total") {
      const value = trimmed === "" ? null : parse(trimmed);
      if (trimmed !== "" && value === null) return null;
      result[binding.field] = value;
    } else if (binding.field === "currency") {
      result.currency = trimmed === "" ? null : trimmed.toUpperCase();
    } else {
      result[binding.field] = trimmed === "" ? null : trimmed;
    }
    return { result, unitPrices };
  }
  const line = result.line_items?.[binding.index];
  if (!line) return null;
  if (binding.prop === "description") {
    line.description = trimmed;
  } else if (binding.prop === "unit_price") {
    const value = trimmed === "" ? null : parse(trimmed);
    if (trimmed !== "" && value === null) return null;
    unitPrices[binding.index] = value;
  } else {
    const value = trimmed === "" ? null : parse(trimmed);
    if (binding.prop === "amount") {
      if (value === null) return null;
      line.amount = value;
    } else {
      if (trimmed !== "" && value === null) return null;
      line.quantity = value;
    }
  }
  return { result, unitPrices };
}

export function bindingId(binding: Binding): string {
  return binding.kind === "field" ? binding.field : `line-${binding.index}-${binding.prop}`;
}

export { cellRef };
