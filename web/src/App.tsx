import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Health } from "./api";
import { FormulaBar, OpenButton, SheetBar, type SheetId } from "./components/Chrome";
import { SelectionProvider } from "./selection";
import { DocumentDetail, DocumentsIndex } from "./views/DocumentsView";
import { EvaluationView } from "./views/EvaluationView";
import { ExtractView, type ExtractState } from "./views/ExtractView";

interface Route {
  sheet: SheetId;
  code?: string;
}

function parseRoute(hash: string): Route {
  const [sheet, code] = hash.replace(/^#\/?/, "").split("/");
  if (sheet === "documents") return { sheet, code: code ? decodeURIComponent(code) : undefined };
  if (sheet === "evaluation") return { sheet };
  return { sheet: "extract" };
}

function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function App() {
  const route = useRoute();
  const [health, setHealth] = useState<Health | null>(null);
  const [status, setStatus] = useState("Ready");
  const [extract, setExtract] = useState<ExtractState>({ phase: "idle" });
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setStatus("Server not reachable: start it with python serve.py"));
  }, []);

  const apiReady = Boolean(health?.api_key_configured);

  // Each sheet reports its own status; start clean when switching.
  useEffect(() => setStatus("Ready"), [route.sheet, route.code]);

  const runExtraction = useCallback(async (file: File) => {
    window.location.hash = "#/extract";
    setExtract({ phase: "reading", fileName: file.name });
    setStatus(`Reading ${file.name}…`);
    try {
      const payload = await api.extract(file);
      setExtract({ phase: "done", fileName: file.name, payload });
      const review = payload.meta?.review;
      setStatus(
        review?.needs_review
          ? `${file.name}: Needs review, ${review.reasons.length} finding${review.reasons.length === 1 ? "" : "s"}`
          : `${file.name}: Ready, every check passed`,
      );
    } catch (error) {
      const failure =
        error instanceof ApiError ? { code: error.code, message: error.message } : { code: "unknown", message: String(error) };
      setExtract({ phase: "failed", fileName: file.name, error: failure });
      setStatus(`${file.name}: ${failure.message}`);
    }
  }, []);

  // Drop a file anywhere in the window to extract it.
  useEffect(() => {
    let depth = 0;
    const hasFiles = (event: DragEvent) => Array.from(event.dataTransfer?.types ?? []).includes("Files");
    const enter = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth++;
      setDragging(true);
    };
    const leave = () => {
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDragging(false);
    };
    const over = (event: DragEvent) => hasFiles(event) && event.preventDefault();
    const drop = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      depth = 0;
      setDragging(false);
      const file = event.dataTransfer?.files[0];
      if (file) void runExtraction(file);
    };
    window.addEventListener("dragenter", enter);
    window.addEventListener("dragleave", leave);
    window.addEventListener("dragover", over);
    window.addEventListener("drop", drop);
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("dragover", over);
      window.removeEventListener("drop", drop);
    };
  }, [runExtraction]);

  return (
    <SelectionProvider>
      <div className={`app${dragging ? " is-dropping" : ""}`}>
        <header className="title-bar">
          <a className="wordmark" href="#/extract">
            <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden>
              <rect x="0.75" y="0.75" width="14.5" height="14.5" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <path d="M0.75 5.5h14.5M0.75 10.5h14.5M6 0.75v14.5" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            Invoice Worksheet
          </a>
          <span className="title-meta">
            {health ? (
              <>
                {health.model} · {health.input_mode} · prompt {health.prompt_version}
                {!apiReady && <span className="title-warning"> · no API key: browsing only</span>}
              </>
            ) : (
              "connecting…"
            )}
          </span>
        </header>

        <FormulaBar actions={<OpenButton onFile={(file) => void runExtraction(file)} busy={extract.phase === "reading"} />} />

        <main className="app-body">
          {route.sheet === "extract" && (
            <ExtractView state={extract} apiReady={apiReady} samplesAvailable={Boolean(health?.sample_pack_present)} model={health?.model} onFile={(file) => void runExtraction(file)} onStatus={setStatus} />
          )}
          {route.sheet === "documents" &&
            (route.code ? (
              <DocumentDetail code={route.code} apiReady={apiReady} onStatus={setStatus} />
            ) : (
              <DocumentsIndex onStatus={setStatus} />
            ))}
          {route.sheet === "evaluation" && <EvaluationView onStatus={setStatus} />}
        </main>

        <SheetBar active={route.sheet} status={status} />
        {dragging && (
          <div className="drop-overlay" aria-hidden>
            <span>Drop to extract</span>
          </div>
        )}
      </div>
    </SelectionProvider>
  );
}
