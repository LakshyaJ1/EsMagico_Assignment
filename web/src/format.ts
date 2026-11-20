// Number, money and label formatting. Figures always use tabular numerals (see CSS).

const grouping = new Map<string, Intl.NumberFormat>();

/** Format an amount the way the document's currency is usually written (₹ uses lakh grouping). */
export function money(value: number | null | undefined, currency?: string | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  const locale = currency === "INR" ? "en-IN" : "en-US";
  let formatter = grouping.get(locale);
  if (!formatter) {
    formatter = new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    grouping.set(locale, formatter);
  }
  return formatter.format(value);
}

export function quantity(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)));
}

export function usd(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined) return "";
  return `$${value.toFixed(digits)}`;
}

export function percent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "–";
  return `${(value * 100).toFixed(digits)}%`;
}

export function seconds(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "";
  return `${(ms / 1000).toFixed(1)}s`;
}

export function tokens(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return Math.round(value).toLocaleString("en-US");
}

/** Spreadsheet column letters: 0 -> A, 25 -> Z, 26 -> AA. */
export function columnLetter(index: number): string {
  let letters = "";
  let n = index + 1;
  while (n > 0) {
    const rem = (n - 1) % 26;
    letters = String.fromCharCode(65 + rem) + letters;
    n = Math.floor((n - 1) / 26);
  }
  return letters;
}

export function cellRef(row: number, column: number): string {
  return `${columnLetter(column)}${row + 1}`;
}

export function rangeRef(r1: number, c1: number, r2: number, c2: number): string {
  const a = cellRef(Math.min(r1, r2), Math.min(c1, c2));
  const b = cellRef(Math.max(r1, r2), Math.max(c1, c2));
  return a === b ? a : `${a}:${b}`;
}

/** Parse what a clerk types into a number cell: "1,200.50", "₹ 3,00,000", "-450". */
export function parseAmount(text: string): number | null {
  const cleaned = text.replace(/[^\d.,-]/g, "");
  if (!cleaned) return null;
  const normalized =
    cleaned.includes(",") && cleaned.includes(".")
      ? cleaned.lastIndexOf(",") > cleaned.lastIndexOf(".")
        ? cleaned.replace(/\./g, "").replace(",", ".")
        : cleaned.replace(/,/g, "")
      : cleaned.replace(/,(?=\d{3}(\D|$))/g, "").replace(",", ".");
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

export const SOURCE_LABEL: Record<string, string> = {
  digital: "Digital PDF",
  scan: "Scanned PDF",
  photo: "Photo",
};

/** One vocabulary for a document's state, used by every sheet and the status bar. */
export function statusLabel(status: string | null | undefined): string {
  switch (status) {
    case "ok":
      return "Ready";
    case "needs_review":
      return "Needs review";
    case "error":
      return "Failed";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    default:
      return "Not run";
  }
}
