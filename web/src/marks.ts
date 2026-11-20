import { useCallback, useEffect, useState } from "react";

/** A reviewer's decision on a document, kept in this browser (per-viewer convenience). */
export type Mark = "approved" | "rejected";

const STORAGE_KEY = "invoice-worksheet:marks";
const EVENT = "invoice-worksheet:marks-changed";

function read(): Record<string, Mark> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as Record<string, Mark>;
  } catch {
    return {};
  }
}

function write(marks: Record<string, Mark>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(marks));
  } catch {
    // Storage blocked (private mode): marks simply do not persist.
  }
  window.dispatchEvent(new Event(EVENT));
}

export function useMarks(): [Record<string, Mark>, (id: string, mark: Mark | null) => void] {
  const [marks, setMarks] = useState<Record<string, Mark>>(read);

  useEffect(() => {
    const refresh = () => setMarks(read());
    window.addEventListener(EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  const setMark = useCallback((id: string, mark: Mark | null) => {
    const next = { ...read() };
    if (mark) next[id] = mark;
    else delete next[id];
    write(next);
  }, []);

  return [marks, setMark];
}
