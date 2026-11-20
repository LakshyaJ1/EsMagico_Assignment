import { FileUp, FunctionSquare } from "lucide-react";
import { useState, type ReactNode } from "react";
import { money } from "../format";
import { useSelection } from "../selection";

const DOCUMENT_CODE = /^[LU]\d{2}$/;
const CELL_REF = /^([A-Z]{1,2})(\d{1,4})$/;

function columnIndex(letters: string): number {
  return [...letters].reduce((index, letter) => index * 26 + letter.charCodeAt(0) - 64, 0) - 1;
}

/**
 * The formula bar. Its Name Box shows the active cell and, like a spreadsheet's, takes input:
 * a cell reference (E12) moves there; a document code (U04) opens that document.
 */
export function FormulaBar({ actions }: { actions?: ReactNode }) {
  const { selection, jump } = useSelection();
  const [draft, setDraft] = useState<string | null>(null);

  const go = (text: string) => {
    const target = text.trim().toUpperCase();
    const cell = CELL_REF.exec(target);
    if (DOCUMENT_CODE.test(target)) window.location.hash = `#/documents/${target}`;
    else if (cell?.[1] && cell[2]) jump(Number(cell[2]) - 1, columnIndex(cell[1]));
  };

  return (
    <div className="formula-bar">
      <input
        className="name-box"
        aria-label="Name box: type a cell such as E12, or a document code such as U04, then press Enter"
        title="Type a cell (E12) or a document code (U04), then Enter"
        spellCheck={false}
        value={draft ?? selection?.ref ?? ""}
        onFocus={(event) => {
          setDraft(selection?.ref ?? "");
          event.currentTarget.select();
        }}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => setDraft(null)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            go(event.currentTarget.value);
            setDraft(null);
            event.currentTarget.blur();
          } else if (event.key === "Escape") {
            setDraft(null);
            event.currentTarget.blur();
          }
        }}
      />
      <FunctionSquare className="fx" size={16} strokeWidth={1.75} aria-hidden />
      <div className={`formula${selection?.tone ? ` tone-${selection.tone}` : ""}`} aria-live="polite">
        <span className="formula-content">{selection?.content || " "}</span>
        {selection?.note && <span className="formula-note">{selection.note}</span>}
      </div>
      {actions && <div className="formula-actions">{actions}</div>}
    </div>
  );
}

export type SheetId = "extract" | "documents" | "evaluation";

const SHEETS: { id: SheetId; label: string }[] = [
  { id: "extract", label: "Extract" },
  { id: "documents", label: "Documents" },
  { id: "evaluation", label: "Evaluation" },
];

/** Sheet tabs on the left, a live status line on the right (Ready · Sum · Count · Average). */
export function SheetBar({ active, status }: { active: SheetId; status: ReactNode }) {
  const { selection } = useSelection();
  const numbers = selection?.numbers ?? [];
  const sum = numbers.reduce((total, value) => total + value, 0);
  return (
    <footer className="sheet-bar">
      <nav className="sheet-tabs" aria-label="Sheets">
        {SHEETS.map((sheet) => (
          <a
            key={sheet.id}
            href={`#/${sheet.id}`}
            className={`sheet-tab${sheet.id === active ? " is-active" : ""}`}
            aria-current={sheet.id === active ? "page" : undefined}
          >
            {sheet.label}
          </a>
        ))}
      </nav>
      <div className="status-line">
        <span className="status-message">{status}</span>
        {numbers.length > 1 && (
          <>
            <span>
              Average <strong>{money(sum / numbers.length)}</strong>
            </span>
            <span>
              Count <strong>{selection?.count}</strong>
            </span>
            <span>
              Sum <strong>{money(sum)}</strong>
            </span>
          </>
        )}
        {numbers.length <= 1 && selection && selection.count > 1 && (
          <span>
            Count <strong>{selection.count}</strong>
          </span>
        )}
      </div>
    </footer>
  );
}

export function OpenButton({ onFile, busy }: { onFile: (file: File) => void; busy?: boolean }) {
  return (
    <label className={`button button-primary${busy ? " is-busy" : ""}`}>
      <FileUp size={15} strokeWidth={2} aria-hidden />
      <span className="button-label">{busy ? "Reading…" : "Open invoice"}</span>
      <input
        type="file"
        accept="application/pdf,image/jpeg,image/png,image/webp,image/tiff"
        className="visually-hidden"
        disabled={busy}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
    </label>
  );
}
