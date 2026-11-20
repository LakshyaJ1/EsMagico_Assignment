import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, ApiError, type DocumentRow, type ReviewPayload } from "../api";
import { Grid, type GridColumn, type GridRow } from "../components/Grid";
import { money, statusLabel, usd } from "../format";
import { useMarks, type Mark } from "../marks";
import { ReviewWorkspace } from "./ReviewWorkspace";

type Filter = "all" | "labelled" | "unlabelled" | "review" | "approved";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "labelled", label: "Labelled" },
  { id: "unlabelled", label: "Unlabelled" },
  { id: "review", label: "Needs review" },
  { id: "approved", label: "Approved" },
];

const COLUMNS: GridColumn[] = [
  { key: "code", width: "64px" },
  { key: "set", width: "92px" },
  { key: "source", width: "84px" },
  { key: "invoice", width: "70px" },
  { key: "vendor", width: "minmax(180px, 2fr)" },
  { key: "number", width: "minmax(120px, 1.2fr)" },
  { key: "date", width: "96px" },
  { key: "currency", width: "52px" },
  { key: "total", width: "minmax(104px, 1fr)" },
  { key: "status", width: "minmax(112px, 1fr)" },
  { key: "confidence", width: "64px" },
  { key: "truth", width: "84px" },
  { key: "cost", width: "76px" },
];

function statusCell(row: DocumentRow, mark: Mark | undefined) {
  if (mark === "approved") return { text: statusLabel(mark), tone: "ok" as const, icon: "ok" as const };
  if (mark === "rejected") return { text: statusLabel(mark), tone: "error" as const, icon: "error" as const };
  if (row.status === "needs_review")
    return { text: statusLabel(row.status), tone: "warn" as const, icon: "warn" as const, note: row.review_reasons.join(" ") };
  if (row.status === "ok") return { text: statusLabel(row.status), tone: "ok" as const };
  if (row.status === "error") return { text: statusLabel(row.status), tone: "error" as const, icon: "error" as const };
  return { text: statusLabel(row.status), tone: "muted" as const };
}

/** Empty ruled rows so the sheet runs to the bottom of the pane, like a real worksheet. */
const PAD_TO_ROWS = 40;

/** The document index: every sample addressed by its code, the sheet tabs are the only map. */
export function DocumentsIndex({ onStatus }: { onStatus: (message: string) => void }) {
  const [rows, setRows] = useState<DocumentRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [marks] = useMarks();

  useEffect(() => {
    let live = true; // ignore a response that lands after the user has left this sheet
    api
      .documents()
      .then((documents) => {
        if (!live) return;
        setRows(documents);
        onStatus(`${documents.length} documents`);
      })
      .catch((err: unknown) => live && setError(err instanceof ApiError ? err.message : "Could not load documents."));
    return () => {
      live = false;
    };
  }, [onStatus]);

  const visible = useMemo(
    () =>
      (rows ?? []).filter((row) => {
        if (filter === "labelled" || filter === "unlabelled") return row.set === filter;
        if (filter === "review") return row.status === "needs_review" && !marks[row.code];
        if (filter === "approved") return marks[row.code] === "approved";
        return true;
      }),
    [rows, filter, marks],
  );

  const gridRows: GridRow[] = useMemo(() => {
    const header: GridRow = {
      key: "head",
      heading: true,
      cells: ["Code", "Set", "Source", "Invoice?", "Vendor", "Invoice no.", "Date", "Cur.", "Total", "Status", "Conf.", "vs. truth", "Cost"].map(
        (text, index) => ({ text, strong: true, align: index >= 8 && index !== 9 ? "right" : "left" }),
      ),
    };
    return [
      header,
      ...visible.map((row): GridRow => {
        const result = row.result;
        const open = () => (window.location.hash = `#/documents/${row.code}`);
        const truthText = row.fields_total ? `${row.fields_correct}/${row.fields_total}` : "";
        return {
          key: row.code,
          onOpen: open,
          struck: marks[row.code] === "rejected",
          cells: [
            { text: row.code, strong: true, note: `${row.file_name} · double-click or press Enter to open` },
            { text: row.set, tone: "muted" },
            { text: row.kind, tone: "muted" },
            { text: result ? (result.is_invoice ? "TRUE" : "FALSE") : "", tone: result && !result.is_invoice ? "muted" : undefined },
            { text: result?.vendor ?? (result ? "null" : ""), tone: result?.vendor ? undefined : "muted" },
            { text: result?.invoice_number ?? "" },
            { text: result?.invoice_date ?? "" },
            { text: result?.currency ?? "" },
            { text: money(result?.total, result?.currency), value: result?.total ?? null, align: "right" },
            statusCell(row, marks[row.code]),
            { text: row.confidence === null ? "" : row.confidence.toFixed(2), value: row.confidence, align: "right", tone: "muted" },
            {
              text: truthText,
              align: "right",
              tone: row.fields_total ? (row.fields_correct === row.fields_total ? "ok" : "error") : "muted",
              note: row.fields_total ? "Fields matching the labelled ground truth." : "Unlabelled: no ground truth to compare.",
            },
            { text: usd(row.cost_usd), value: row.cost_usd, align: "right", tone: "muted" },
          ],
        };
      }),
      ...Array.from({ length: Math.max(0, PAD_TO_ROWS - visible.length) }, (_, index): GridRow => ({
        key: `pad-${index}`,
        cells: COLUMNS.map(() => ({ text: "" })),
      })),
    ];
  }, [visible, marks]);

  if (error) return <div className="sheet-message" role="alert">{error}</div>;
  if (!rows) return <div className="sheet-message">Loading documents…</div>;
  if (rows.length === 0)
    return (
      <div className="sheet-message">
        <p>The sample pack is not on this machine.</p>
        <p className="drop-detail">
          Run <code>uv run python scripts/fetch_data.py</code>, then reload.
        </p>
      </div>
    );

  return (
    <div className="index-view">
      <div className="toolbar" role="toolbar" aria-label="Filter documents">
        {FILTERS.map((option) => (
          <button
            key={option.id}
            type="button"
            className={`filter${filter === option.id ? " is-on" : ""}`}
            aria-pressed={filter === option.id}
            onClick={() => setFilter(option.id)}
          >
            {option.label}
            <span className="filter-count">
              {
                (rows ?? []).filter((row) =>
                  option.id === "all"
                    ? true
                    : option.id === "review"
                      ? row.status === "needs_review" && !marks[row.code]
                      : option.id === "approved"
                        ? marks[row.code] === "approved"
                        : row.set === option.id,
                ).length
              }
            </span>
          </button>
        ))}
        <span className="toolbar-hint">Double-click a row to open it. Select a range of totals to sum it.</span>
      </div>
      <Grid label="Document index" columns={COLUMNS} rows={gridRows} frozenRows={1} />
    </div>
  );
}

export function DocumentDetail({
  code,
  apiReady,
  onStatus,
}: {
  code: string;
  apiReady: boolean;
  onStatus: (message: string) => void;
}) {
  const [payload, setPayload] = useState<ReviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [codes, setCodes] = useState<string[]>([]);
  const [reextracting, setReextracting] = useState(false);

  useEffect(() => {
    let live = true;
    setPayload(null);
    setError(null);
    api
      .document(code)
      .then((document) => {
        if (!live) return;
        setPayload(document);
        onStatus(`${document.file_name}: ${statusLabel(document.meta?.status)}`);
      })
      .catch((err: unknown) => live && setError(err instanceof ApiError ? err.message : "Could not load the document."));
    return () => {
      live = false;
    };
  }, [code, onStatus]);

  useEffect(() => {
    let live = true;
    api
      .documents()
      .then((rows) => live && setCodes(rows.map((row) => row.code)))
      .catch(() => live && setCodes([]));
    return () => {
      live = false;
    };
  }, []);

  const position = codes.indexOf(code);
  const previous = position > 0 ? codes[position - 1] : undefined;
  const next = position >= 0 && position < codes.length - 1 ? codes[position + 1] : undefined;

  const reextract = async () => {
    setReextracting(true);
    onStatus(`Re-extracting ${code}…`);
    try {
      const fresh = await api.reextract(code);
      setPayload(fresh);
      onStatus(`${code} re-extracted: ${statusLabel(fresh.meta?.status)}`);
    } catch (err) {
      onStatus(err instanceof ApiError ? err.message : "Re-extraction failed.");
    } finally {
      setReextracting(false);
    }
  };

  if (error) return <div className="sheet-message" role="alert">{error}</div>;
  if (!payload) return <div className="sheet-message">Opening {code}…</div>;

  const nav = (
    <nav className="doc-nav" aria-label="Document navigation">
      <a href="#/documents" className="doc-nav-index">
        Index
      </a>
      <a href={previous ? `#/documents/${previous}` : undefined} aria-disabled={!previous} className="icon-button" aria-label="Previous document">
        <ChevronLeft size={14} />
      </a>
      <strong className="doc-code">{code}</strong>
      <a href={next ? `#/documents/${next}` : undefined} aria-disabled={!next} className="icon-button" aria-label="Next document">
        <ChevronRight size={14} />
      </a>
    </nav>
  );

  return (
    <ReviewWorkspace
      payload={payload}
      apiReady={apiReady}
      onStatus={onStatus}
      onReextract={reextract}
      reextracting={reextracting}
      nav={nav}
    />
  );
}
