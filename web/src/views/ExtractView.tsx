import { FileWarning, KeyRound } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import type { ReviewPayload } from "../api";
import { OpenButton } from "../components/Chrome";
import { Grid, type GridColumn, type GridRow } from "../components/Grid";
import { ReviewWorkspace } from "./ReviewWorkspace";

export interface ExtractState {
  phase: "idle" | "reading" | "done" | "failed";
  fileName?: string;
  payload?: ReviewPayload;
  error?: { code: string; message: string };
}

interface ExtractViewProps {
  state: ExtractState;
  apiReady: boolean;
  samplesAvailable: boolean;
  model?: string;
  onFile: (file: File) => void;
  onStatus: (message: string) => void;
}

const ERROR_HELP: Record<string, string> = {
  unsupported_file_type: "Upload a PDF or an image (JPEG, PNG, WebP, TIFF).",
  corrupt_file: "The file is damaged or truncated. Re-export or re-scan it and try again.",
  encrypted_pdf: "Remove the PDF password, then upload it again.",
  empty_document: "There is nothing to read on this page. Check you picked the right file.",
  file_too_large: "Compress the file or split it, then try again.",
  llm_unavailable: "The model is busy or unreachable. Nothing was lost; try again in a minute.",
  not_configured: "The server has no GEMINI_API_KEY. Add it to .env and restart the server.",
};

const BLANK_COLUMNS: GridColumn[] = ["A", "B", "C", "D", "E", "F"].map((key) => ({ key, width: "minmax(96px, 1fr)" }));
const BLANK_ROWS: GridRow[] = Array.from({ length: 40 }, (_, index) => ({
  key: `blank-${index}`,
  cells: BLANK_COLUMNS.map(() => ({ text: "" })),
}));

const SAMPLES = [
  { code: "L03", label: "Digital tax invoice" },
  { code: "L09", label: "Scanned invoice" },
  { code: "L02", label: "Phone photo" },
  { code: "U05", label: "Sideways scan" },
  { code: "U04", label: "Flagged for review" },
  { code: "U06", label: "Bank statement, not an invoice" },
];

interface Box {
  top: number;
  left: number;
  width: number;
  minHeight: number;
}

/** Place the drop range exactly over cells B4:E13 (A4 to the pane edge when narrow). */
function useCellRange(reading: boolean) {
  const pane = useRef<HTMLElement>(null);
  const [box, setBox] = useState<Box | null>(null);
  useLayoutEffect(() => {
    const host = pane.current;
    if (!host) return;
    const measure = () => {
      const narrow = host.clientWidth < 700;
      const first = host.querySelector(`[data-cell="3:${narrow ? 0 : 1}"]`);
      const last = host.querySelector(`[data-cell="12:${narrow ? 5 : 4}"]`);
      if (!first || !last) return;
      const origin = host.getBoundingClientRect();
      const a = first.getBoundingClientRect();
      const b = last.getBoundingClientRect();
      const right = Math.min(b.right, origin.right - 8);
      setBox({ top: a.top - origin.top, left: a.left - origin.left, width: right - a.left, minHeight: b.bottom - a.top });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(host);
    return () => observer.disconnect();
  }, [reading]);
  return { pane, box };
}

/** Upload an invoice; while it reads, the drop range runs marching ants like a copied range. */
export function ExtractView({ state, apiReady, samplesAvailable, model, onFile, onStatus }: ExtractViewProps) {
  const reading = state.phase === "reading";
  const { pane, box } = useCellRange(reading);

  if (state.phase === "done" && state.payload) {
    return <ReviewWorkspace payload={state.payload} apiReady={apiReady} onStatus={onStatus} />;
  }

  return (
    <div className="workspace">
      <section className="doc-pane doc-pane-empty" aria-label="Source document">
        <header className="pane-head">
          <span className="pane-title">{state.fileName ?? "No document"}</span>
        </header>
        <div className="doc-scroll">
          <div className="doc-empty">
            <p className="doc-empty-note">The document appears here, pinned beside its worksheet.</p>
            {samplesAvailable && (
              <nav className="sample-list" aria-label="Open a sample document">
                <p className="sample-list-title">Or open a sample</p>
                <ul>
                  {SAMPLES.map((sample) => (
                    <li key={sample.code}>
                      <a href={`#/documents/${sample.code}`}>
                        <code>{sample.code}</code>
                        <span>{sample.label}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            )}
          </div>
        </div>
      </section>
      <section ref={pane} className="sheet-pane sheet-blank" aria-label="Empty worksheet">
        <Grid label="Empty worksheet" columns={BLANK_COLUMNS} rows={BLANK_ROWS} />
        <div
          className={`drop-range${reading ? " is-reading" : ""}`}
          style={box ? { top: box.top, left: box.left, width: box.width, minHeight: box.minHeight } : { visibility: "hidden" }}
        >
          {reading ? (
            <div className="drop-copy" role="status">
              <p className="drop-title">Reading {state.fileName}</p>
              <p className="drop-detail">
                Rendering pages, then asking {model ?? "the model"}. Every value is checked before it lands
                in the sheet.
              </p>
            </div>
          ) : (
            <div className="drop-copy">
              <p className="drop-title">Drop an invoice anywhere</p>
              <p className="drop-detail">
                PDF, scan or phone photo. The extracted fields land in this sheet with every check written
                out as a formula.
              </p>
              <OpenButton onFile={onFile} />
              {!apiReady && (
                <p className="drop-note">
                  <KeyRound size={14} aria-hidden /> Extraction needs <code>GEMINI_API_KEY</code> on the server. The
                  Documents and Evaluation sheets work without it.
                </p>
              )}
            </div>
          )}
        </div>
        {state.phase === "failed" && state.error && (
          <div
            className="drop-error"
            role="alert"
            style={box ? { top: box.top + box.minHeight + 26, left: box.left, width: box.width } : undefined}
          >
            <FileWarning size={18} aria-hidden />
            <div>
              <p>
                <strong>{state.fileName}</strong> could not be processed: {state.error.message}
              </p>
              <p className="drop-detail">{ERROR_HELP[state.error.code] ?? "Try another file."}</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
