import { useEffect, useMemo, useState } from "react";
import { api, ApiError, type EvalListing, type EvalReport, type FieldName } from "../api";
import { Grid, type GridCell, type GridColumn, type GridRow } from "../components/Grid";
import { percent, seconds, usd } from "../format";

const FIELDS: { field: FieldName; label: string }[] = [
  { field: "is_invoice", label: "is_invoice" },
  { field: "vendor", label: "vendor" },
  { field: "invoice_number", label: "inv. no." },
  { field: "invoice_date", label: "date" },
  { field: "currency", label: "currency" },
  { field: "line_items", label: "line items" },
  { field: "tax_total", label: "tax" },
  { field: "total", label: "total" },
];

/** Sequential error ramp (one hue, light to dark), validated with the dataviz validator. */
const ERROR_STEPS = [
  { max: 0.1, className: "err-1", label: "≤10%" },
  { max: 0.25, className: "err-2", label: "≤25%" },
  { max: 0.5, className: "err-3", label: "≤50%" },
  { max: 1, className: "err-4", label: ">50%" },
];

function errorClass(correct: number, total: number): string | undefined {
  if (!total) return undefined;
  const share = 1 - correct / total;
  if (share === 0) return undefined;
  return ERROR_STEPS.find((step) => share <= step.max)?.className;
}

const GROUP_ORDER = ["main", "repeat", "model", "mode", "stress", "ablation"];

function describe(listing: EvalListing): { title: string; condition: string; held: boolean } {
  const { tag, run } = listing;
  const perturbation = run.perturbation ?? "";
  const held = perturbation === "fax" || perturbation === "photo";
  const extras = [run.orientation_fix === false && "no orientation fix", run.second_read === false && "no second read"]
    .filter(Boolean)
    .join(", ");
  if (tag === "main") return { title: "Clean labelled set", condition: "as delivered", held };
  if (tag.startsWith("repeat")) return { title: `Repeat run ${tag.split("-")[1]}`, condition: "fresh calls, no cache", held };
  if (tag.startsWith("model")) return { title: run.model, condition: "model comparison", held };
  if (tag.startsWith("mode")) return { title: `Input: ${run.input_mode}`, condition: "input-mode ablation", held };
  if (tag.startsWith("ablation")) return { title: `Ablation: ${perturbation}`, condition: extras, held };
  if (perturbation) return { title: `Stress: ${perturbation}`, condition: held ? "held out" : "degraded copies", held };
  return { title: tag, condition: "", held };
}

function groupRank(tag: string): number {
  const index = GROUP_ORDER.findIndex((group) => tag.startsWith(group));
  return index === -1 ? GROUP_ORDER.length : index;
}

const OVERVIEW_COLUMNS: GridColumn[] = [
  { key: "run", width: "minmax(170px, 1.6fr)" },
  { key: "condition", width: "minmax(120px, 1.1fr)" },
  { key: "perfect", width: "80px" },
  ...FIELDS.map((f) => ({ key: f.field, width: "minmax(64px, 0.6fr)" })),
  { key: "flag", width: "minmax(118px, 1fr)" },
  { key: "cost", width: "78px" },
  { key: "latency", width: "64px" },
  { key: "failed", width: "62px" },
];

export function EvaluationView({ onStatus }: { onStatus: (message: string) => void }) {
  const [listings, setListings] = useState<EvalListing[] | null>(null);
  const [selected, setSelected] = useState<string>("main");
  const [report, setReport] = useState<EvalReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true; // ignore a response that lands after the user has left this sheet
    api
      .evaluations()
      .then((items) => {
        if (!live) return;
        const sorted = [...items].sort((a, b) => groupRank(a.tag) - groupRank(b.tag) || a.tag.localeCompare(b.tag));
        setListings(sorted);
        if (!sorted.some((item) => item.tag === "main") && sorted[0]) setSelected(sorted[0].tag);
        onStatus(`${sorted.length} evaluation runs`);
      })
      .catch((err: unknown) => live && setError(err instanceof ApiError ? err.message : "Could not load evaluations."));
    return () => {
      live = false;
    };
  }, [onStatus]);

  useEffect(() => {
    if (!listings?.length) return;
    let live = true;
    setReport(null);
    api
      .evaluation(selected)
      .then((report) => live && setReport(report))
      .catch(() => live && setReport(null));
    return () => {
      live = false;
    };
  }, [selected, listings]);

  const overviewRows = useMemo<GridRow[]>(() => {
    if (!listings) return [];
    const header: GridRow = {
      key: "head",
      heading: true,
      cells: [
        { text: "Run", strong: true },
        { text: "Condition", strong: true },
        { text: "All 8 right", strong: true, align: "right" },
        ...FIELDS.map((f): GridCell => ({ text: f.label, strong: true, align: "right" })),
        { text: "Flag caught / false", strong: true, align: "right" },
        { text: "$/doc", strong: true, align: "right" },
        { text: "Latency", strong: true, align: "right" },
        { text: "Failed", strong: true, align: "right" },
      ],
    };
    return [
      header,
      ...listings.map((listing): GridRow => {
        const { title, condition, held } = describe(listing);
        const perfect = listing.all_fields;
        const review = listing.review;
        return {
          key: listing.tag,
          onOpen: () => setSelected(listing.tag),
          cells: [
            {
              text: title,
              strong: listing.tag === selected,
              note: `${listing.tag} · ${listing.run.model} · prompt ${listing.run.prompt_version} · double-click to open`,
            },
            { text: condition, tone: held ? "info" : "muted" },
            {
              text: `${perfect.correct}/${perfect.total}`,
              value: perfect.correct,
              align: "right",
              strong: true,
              render: <span className={`heat ${errorClass(perfect.correct, perfect.total) ?? ""}`}>{perfect.correct}/{perfect.total}</span>,
            },
            ...FIELDS.map((f): GridCell => {
              const row = listing.field_accuracy[f.field];
              const heat = errorClass(row.correct, row.total);
              return {
                text: percent(row.accuracy),
                value: row.accuracy,
                align: "right",
                formula: `=${row.correct}/${row.total}`,
                note: `${f.field}: ${row.correct} of ${row.total} documents correct (${row.invoices_correct}/${row.invoices_total} invoices).`,
                render: <span className={`heat ${heat ?? ""}`}>{percent(row.accuracy)}</span>,
              };
            }),
            {
              text: `${review.errors_caught}/${review.documents_with_errors} · ${review.false_alarms}`,
              align: "right",
              tone: review.documents_with_errors && review.errors_caught < review.documents_with_errors ? "warn" : undefined,
              note: `Flagged ${review.flagged} of ${review.documents}. Docs with errors: ${review.documents_with_errors}, flagged: ${review.errors_caught}. False alarms: ${review.false_alarms}.${review.missed.length ? ` Missed: ${review.missed.join(", ")}.` : ""}`,
            },
            { text: usd(listing.cost?.avg_cost_usd), value: listing.cost?.avg_cost_usd ?? null, align: "right", tone: "muted" },
            { text: seconds(listing.cost?.avg_latency_ms), value: listing.cost?.avg_latency_ms ? listing.cost.avg_latency_ms / 1000 : null, align: "right", tone: "muted" },
            {
              text: String(listing.failed),
              value: listing.failed,
              align: "right",
              tone: listing.failed ? "warn" : "muted",
              note: listing.failed ? "API calls that failed after retries (rate limits), scored as all-wrong." : "No failed calls.",
            },
          ],
        };
      }),
    ];
  }, [listings, selected]);

  const detailRows = useMemo<GridRow[]>(() => {
    if (!report) return [];
    const header: GridRow = {
      key: "head",
      heading: true,
      cells: [
        { text: "Doc", strong: true },
        { text: "Source", strong: true },
        ...FIELDS.map((f): GridCell => ({ text: f.label, strong: true, align: "center" })),
        { text: "Flagged", strong: true },
        { text: "Conf.", strong: true, align: "right" },
        { text: "Why flagged / what went wrong", strong: true },
      ],
    };
    return [
      header,
      ...report.documents.map((doc): GridRow => {
        const wrong = doc.fields.filter((f) => !f.correct);
        const explanation = doc.error
          ? doc.error
          : wrong.length
            ? wrong.map((f) => `${f.field}: ${f.detail || `expected ${JSON.stringify(f.expected)}, got ${JSON.stringify(f.predicted)}`}`).join(" · ")
            : doc.review_reasons.join(" ") || "All fields correct.";
        return {
          key: doc.name,
          onOpen: () => (window.location.hash = `#/documents/${doc.name}`),
          cells: [
            { text: doc.name, strong: true, note: "Double-click to open the saved extraction." },
            { text: doc.source, tone: "muted" },
            ...FIELDS.map((f): GridCell => {
              const result = doc.fields.find((entry) => entry.field === f.field);
              if (doc.error) return { text: "failed", align: "center", tone: "warn" };
              const ok = result?.correct ?? false;
              return {
                text: ok ? "right" : "wrong",
                align: "center",
                tone: ok ? "ok" : "error",
                icon: ok ? "ok" : "error",
                note: ok ? "Matches ground truth." : `Expected ${JSON.stringify(result?.expected)} · got ${JSON.stringify(result?.predicted)} ${result?.detail ?? ""}`,
              };
            }),
            {
              text: doc.flagged ? "yes" : "no",
              tone: doc.flagged ? (wrong.length || doc.error ? "ok" : "warn") : wrong.length ? "error" : "muted",
              note: doc.flagged
                ? wrong.length || doc.error ? "Flagged, and it does contain errors: caught." : "Flagged, but every field is right: a false alarm."
                : wrong.length ? "Not flagged, but it contains errors: missed." : "Not flagged and correct.",
            },
            { text: doc.confidence === null ? "" : doc.confidence.toFixed(2), value: doc.confidence, align: "right", tone: "muted" },
            { text: explanation, tone: wrong.length || doc.error ? "error" : "muted", note: explanation },
          ],
        };
      }),
    ];
  }, [report]);

  if (error) return <div className="sheet-message" role="alert">{error}</div>;
  if (!listings) return <div className="sheet-message">Loading evaluation runs…</div>;
  if (listings.length === 0)
    return (
      <div className="sheet-message">
        <p>No evaluation runs yet.</p>
        <p className="drop-detail">
          Run <code>uv run python evaluate.py</code> to score the labelled documents.
        </p>
      </div>
    );

  const summary = report?.review;
  return (
    <div className="eval-view">
      <div className="toolbar">
        <span className="toolbar-title">Every run, every field</span>
        <span className="legend" aria-label="Color scale: share of documents with this field wrong">
          Wrong:
          <span className="legend-swatch heat">0%</span>
          {ERROR_STEPS.map((step) => (
            <span key={step.className} className={`legend-swatch heat ${step.className}`}>
              {step.label}
            </span>
          ))}
        </span>
      </div>
      <div className="eval-overview">
        <Grid label="Evaluation runs by field accuracy" columns={OVERVIEW_COLUMNS} rows={overviewRows} frozenRows={1} />
      </div>
      <div className="toolbar">
        <span className="toolbar-title">{report ? describe(listings.find((l) => l.tag === selected)!).title : "Loading…"}</span>
        {report && summary && (
          <span className="toolbar-hint">
            {report.run.model} · lines {report.line_items.matched_rows}/{report.line_items.expected_rows} rows exact ·
            flag holds {summary.field_errors_in_flagged}/{summary.field_errors} field errors · {usd(report.cost?.avg_cost_usd, 5)}/doc
          </span>
        )}
      </div>
      <div className="eval-detail">
        {report && (
          <Grid
            label="Per-document results"
            columns={[
              { key: "doc", width: "58px" },
              { key: "source", width: "70px" },
              ...FIELDS.map((f) => ({ key: f.field, width: "minmax(64px, 0.55fr)" })),
              { key: "flagged", width: "70px" },
              { key: "conf", width: "56px" },
              { key: "why", width: "minmax(280px, 3fr)" },
            ]}
            rows={detailRows}
            frozenRows={1}
          />
        )}
      </div>
    </div>
  );
}
