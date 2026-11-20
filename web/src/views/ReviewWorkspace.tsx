import { Check, Columns2, Download, RefreshCw, RotateCcw, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, ApiError, type Issue, type ReviewPayload, type Review } from "../api";
import { DocumentPane } from "../components/DocumentPane";
import { Grid, type GridColumn } from "../components/Grid";
import { parseAmount, seconds, SOURCE_LABEL, statusLabel, usd } from "../format";
import { useMarks } from "../marks";
import { applyEdit, bindingId, buildSheet, type Draft } from "../worksheet";

interface ReviewWorkspaceProps {
  payload: ReviewPayload;
  apiReady: boolean;
  onStatus: (message: string) => void;
  onReextract?: () => void;
  reextracting?: boolean;
  nav?: ReactNode;
}

const BASE_COLUMNS: GridColumn[] = [
  { key: "label", width: "minmax(128px, 0.7fr)" },
  { key: "description", width: "minmax(176px, 2.4fr)" },
  { key: "qty", width: "minmax(52px, 0.45fr)" },
  { key: "unit", width: "minmax(84px, 0.75fr)" },
  { key: "amount", width: "minmax(100px, 0.85fr)" },
  { key: "check", width: "minmax(138px, 1.25fr)" },
];
const CHECK_COLUMN = 5;
const REVIEW_ROWS = /^(status|confidence|issue-\d+|no-issues)$/;
const TRUTH_COLUMN: GridColumn = { key: "truth", width: "minmax(108px, 0.9fr)" };

function initialDraft(payload: ReviewPayload): Draft | null {
  if (!payload.result) return null;
  return {
    result: payload.result,
    unitPrices: payload.meta?.evidence.unit_prices ?? (payload.result.line_items ?? []).map(() => null),
  };
}

function download(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: name });
  link.click();
  URL.revokeObjectURL(url);
}

/** Source document pinned left, its worksheet right; edits re-run every check live. */
export function ReviewWorkspace({ payload, apiReady, onStatus, onReextract, reextracting, nav }: ReviewWorkspaceProps) {
  const [draft, setDraft] = useState<Draft | null>(() => initialDraft(payload));
  const [edited, setEdited] = useState<Set<string>>(new Set());
  const [issues, setIssues] = useState<Issue[]>(payload.meta?.issues ?? []);
  const [review, setReview] = useState<Review | null>(payload.meta?.review ?? null);
  const [showTruth, setShowTruth] = useState(Boolean(payload.ground_truth));
  const [marks, setMark] = useMarks();
  const validation = useRef(0);
  const [recomputed, setRecomputed] = useState<Set<string>>(new Set());
  const checkSnapshot = useRef(new Map<string, string>());
  const flashArmed = useRef(false);

  useEffect(() => {
    setDraft(initialDraft(payload));
    setEdited(new Set());
    setIssues(payload.meta?.issues ?? []);
    setReview(payload.meta?.review ?? null);
    setShowTruth(Boolean(payload.ground_truth));
  }, [payload]);

  const markId = payload.source === "sample" ? payload.id : payload.file_name;
  const mark = marks[markId];
  const hasEdits = edited.size > 0;
  const truthAvailable = Boolean(payload.ground_truth && payload.comparison);

  const sheet = useMemo(
    () =>
      draft
        ? buildSheet({
            draft,
            evidence: payload.meta?.evidence ?? null,
            meta: payload.meta,
            issues,
            review,
            // Ground truth compares against the model's output; hide it once the clerk edits.
            comparison: hasEdits ? null : payload.comparison,
            truth: payload.ground_truth,
            showTruth: showTruth && truthAvailable && !hasEdits,
            edited,
          })
        : null,
    [draft, payload, issues, review, showTruth, truthAvailable, hasEdits, edited],
  );
  const columns = showTruth && truthAvailable && !hasEdits ? [...BASE_COLUMNS, TRUTH_COLUMN] : BASE_COLUMNS;

  // When the server's recheck lands, each check or review cell whose own result changed
  // flashes once. Cells the clerk types into are never check cells, so they never flash.
  useEffect(() => {
    if (!sheet) return;
    const current = new Map<string, string>();
    for (const row of sheet.rows) {
      const reviewBlock = REVIEW_ROWS.test(row.key);
      row.cells.forEach((cell, column) => {
        if (cell && (column === CHECK_COLUMN || reviewBlock)) current.set(`${row.key}:${column}`, `${cell.text}|${cell.tone ?? ""}`);
      });
    }
    if (flashArmed.current) {
      flashArmed.current = false;
      const changed = new Set([...current].filter(([key, value]) => checkSnapshot.current.get(key) !== value).map(([key]) => key));
      if (changed.size) {
        setRecomputed(changed);
        window.setTimeout(() => setRecomputed(new Set()), 700);
      }
    }
    checkSnapshot.current = current;
  }, [sheet]);

  const rows = useMemo(
    () =>
      sheet?.rows.map((row) =>
        row.cells.some((_, column) => recomputed.has(`${row.key}:${column}`))
          ? { ...row, cells: row.cells.map((cell, column) => (cell && recomputed.has(`${row.key}:${column}`) ? { ...cell, flash: true } : cell)) }
          : row,
      ) ?? [],
    [sheet, recomputed],
  );

  const revalidate = useCallback(
    (next: Draft) => {
      const ticket = ++validation.current;
      window.setTimeout(async () => {
        if (ticket !== validation.current) return;
        try {
          const evidence = payload.meta ? { ...payload.meta.evidence, unit_prices: next.unitPrices } : { unit_prices: next.unitPrices };
          const response = await api.validate(next.result, evidence, payload.meta?.classification ?? null);
          if (ticket !== validation.current) return;
          flashArmed.current = true;
          setIssues(response.issues);
          setReview(response.review);
          onStatus(
            response.review.needs_review
              ? `Rechecked: ${statusLabel("needs_review")}, ${response.review.reasons.length} finding(s)`
              : `Rechecked: ${statusLabel("ok")}, every check passes`,
          );
        } catch (error) {
          onStatus(error instanceof ApiError ? error.message : "Could not re-run the checks.");
        }
      }, 250);
    },
    [payload.meta, onStatus],
  );

  const onEdit = useCallback(
    (row: number, column: number, text: string) => {
      if (!sheet || !draft) return;
      const binding = sheet.bindings.get(`${row}:${column}`);
      if (!binding) return;
      const next = applyEdit(draft, binding, text, parseAmount);
      if (!next) {
        onStatus(`“${text}” is not a valid value for that cell.`);
        return;
      }
      setDraft(next);
      setEdited((previous) => new Set(previous).add(bindingId(binding)));
      setMark(markId, null);
      revalidate(next);
    },
    [sheet, draft, onStatus, revalidate, setMark, markId],
  );

  const reset = () => {
    const original = initialDraft(payload);
    setDraft(original);
    setEdited(new Set());
    setIssues(payload.meta?.issues ?? []);
    setReview(payload.meta?.review ?? null);
    onStatus("Edits discarded");
  };

  const meta = payload.meta;
  const source = meta ? (meta.document.kind === "image" ? "photo" : meta.document.scanned ? "scan" : "digital") : null;
  const caption = [source && SOURCE_LABEL[source], payload.set && `${payload.set} sample`].filter(Boolean).join(" · ");
  const stem = payload.file_name.replace(/\.[^.]+$/, "");

  return (
    <div className="workspace">
      <DocumentPane
        fileName={payload.file_name}
        pages={payload.pages}
        caption={caption}
        rotations={meta?.document.rotations_applied}
      />
      <section className="sheet-pane" aria-label="Extracted data">
        <header className="pane-head sheet-head">
          {nav}
          <span className={`status-chip ${mark ? `is-${mark}` : review?.needs_review ? "is-review" : "is-ready"}`}>
            {statusLabel(mark ?? (review?.needs_review ? "needs_review" : "ok"))}
          </span>
          {meta && (
            <span className="pane-caption">
              {usd(meta.usage.cost_usd, 5)} · {seconds(meta.latency_ms)} · {meta.served_by.join(", ")}
            </span>
          )}
          <div className="pane-tools">
            {truthAvailable && (
              <button
                type="button"
                className={`button button-quiet${showTruth && !hasEdits ? " is-on" : ""}`}
                aria-pressed={showTruth && !hasEdits}
                disabled={hasEdits}
                title={hasEdits ? "Ground truth compares the model's output; reset edits to compare again." : undefined}
                onClick={() => setShowTruth((on) => !on)}
              >
                <Columns2 size={14} aria-hidden /> <span className="button-label">Ground truth</span>
              </button>
            )}
            {onReextract && (
              <button
                type="button"
                className="button button-quiet"
                onClick={onReextract}
                disabled={!apiReady || reextracting}
                title={apiReady ? "Run a fresh extraction with the live model" : "Set GEMINI_API_KEY on the server to run extractions"}
              >
                <RefreshCw size={14} className={reextracting ? "spin" : undefined} aria-hidden /> <span className="button-label">{reextracting ? "Extracting…" : "Re-extract"}</span>
              </button>
            )}
            {hasEdits && (
              <button type="button" className="button button-quiet" onClick={reset}>
                <RotateCcw size={14} aria-hidden /> <span className="button-label">Reset edits</span>
              </button>
            )}
            <button
              type="button"
              className="button button-quiet"
              onClick={() => setMark(markId, mark === "rejected" ? null : "rejected")}
              aria-pressed={mark === "rejected"}
            >
              <X size={14} aria-hidden /> <span className="button-label keep">Reject</span>
            </button>
            <button
              type="button"
              className="button button-primary"
              onClick={() => {
                setMark(markId, mark === "approved" ? null : "approved");
                onStatus(mark === "approved" ? "Approval removed" : `${payload.file_name} approved`);
              }}
              aria-pressed={mark === "approved"}
            >
              <Check size={14} aria-hidden /> {mark === "approved" ? "Approved" : "Approve"}
            </button>
            {draft && (
              <button
                type="button"
                className="button button-quiet"
                onClick={() => download(`${stem}${hasEdits ? ".corrected" : ""}.json`, draft.result)}
                title="Download the schema-exact JSON"
              >
                <Download size={14} aria-hidden /> <span className="button-label">JSON</span>
              </button>
            )}
          </div>
        </header>
        {sheet ? (
          <Grid label={`Worksheet for ${payload.file_name}`} columns={columns} rows={rows} onEdit={onEdit} />
        ) : (
          <div className="sheet-empty">
            <p>No extraction for this document yet.</p>
          </div>
        )}
      </section>
    </div>
  );
}
