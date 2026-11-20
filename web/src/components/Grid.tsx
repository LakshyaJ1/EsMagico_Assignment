import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { CircleAlert, CircleCheck, CircleX, Info } from "lucide-react";
import { columnLetter, rangeRef } from "../format";
import { useSelection, type Tone } from "../selection";

export interface GridCell {
  text: string;
  /** Numeric value used by the status bar's Sum/Average. */
  value?: number | null;
  align?: "left" | "right" | "center";
  tone?: Tone;
  strong?: boolean;
  /** Shown in the formula bar when this cell is active (defaults to `text`). */
  formula?: string;
  /** Secondary line in the formula bar: evidence, ground truth, reasons. */
  note?: string;
  editable?: boolean;
  /** Spans this many columns; the covered columns must be `null`. */
  span?: number;
  render?: ReactNode;
  title?: string;
  /** Status icon drawn before the text (check results, finding severity). */
  icon?: "ok" | "error" | "warn" | "info";
  /** Flash once: this check was just recomputed. */
  flash?: boolean;
  /** Comment corner: the cell carries a note worth reading (edited by a human, a finding). */
  comment?: boolean;
}

export interface GridRow {
  key: string;
  cells: (GridCell | null)[];
  /** Header-style row (column titles, section headings). */
  heading?: boolean;
  onOpen?: () => void;
  struck?: boolean;
}

export interface GridColumn {
  key: string;
  width: string;
}

interface Point {
  r: number;
  c: number;
}

interface GridProps {
  label: string;
  columns: GridColumn[];
  rows: GridRow[];
  onEdit?: (row: number, column: number, text: string) => void;
  /** Rows to freeze at the top (like "Freeze panes"). */
  frozenRows?: number;
  className?: string;
}

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

/** Find the cell that covers (r, c), walking left over spanned columns. */
function cellAt(rows: GridRow[], r: number, c: number): { cell: GridCell | null; c: number } {
  const row = rows[r];
  if (!row) return { cell: null, c };
  for (let col = c; col >= 0; col--) {
    const cell = row.cells[col];
    if (cell) return (cell.span ?? 1) > c - col ? { cell, c: col } : { cell: null, c };
  }
  return { cell: null, c };
}

/**
 * A spreadsheet grid: lettered columns, numbered rows, range selection by mouse or
 * keyboard, in-cell editing, copy as TSV. The current selection is published to the
 * formula bar and status bar through SelectionContext.
 */
export function Grid({ label, columns, rows, onEdit, frozenRows = 0, className }: GridProps) {
  const { publish, claim, release, registerJump } = useSelection();
  const [focusTick, setFocusTick] = useState(0);
  const [anchor, setAnchor] = useState<Point>({ r: 0, c: 0 });
  const [focus, setFocus] = useState<Point>({ r: 0, c: 0 });
  const [editing, setEditing] = useState<{ p: Point; draft: string } | null>(null);
  const [rect, setRect] = useState<{ top: number; left: number; width: number; height: number } | null>(null);
  const dragging = useRef(false);
  const surface = useRef<HTMLDivElement>(null);
  const gridId = useRef(`grid-${Math.random().toString(36).slice(2, 8)}`).current;

  const lastRow = rows.length - 1;
  const lastCol = columns.length - 1;
  const top = Math.min(anchor.r, focus.r);
  const bottom = Math.max(anchor.r, focus.r);
  const left = Math.min(anchor.c, focus.c);
  const right = Math.max(anchor.c, focus.c);

  // Keep the selection inside the grid when the rows change (new document, edits).
  useEffect(() => {
    setAnchor((p) => ({ r: clamp(p.r, 0, Math.max(lastRow, 0)), c: clamp(p.c, 0, lastCol) }));
    setFocus((p) => ({ r: clamp(p.r, 0, Math.max(lastRow, 0)), c: clamp(p.c, 0, lastCol) }));
  }, [lastRow, lastCol]);

  // Publish what the formula bar and status bar should show.
  useEffect(() => {
    const { cell } = cellAt(rows, focus.r, focus.c);
    const numbers: number[] = [];
    let count = 0;
    for (let r = top; r <= bottom; r++) {
      for (let c = left; c <= right; c++) {
        const target = rows[r]?.cells[c];
        if (!target || rows[r]?.heading) continue;
        if (target.text !== "") count++;
        if (typeof target.value === "number") numbers.push(target.value);
      }
    }
    publish(gridId, {
      ref: rangeRef(anchor.r, anchor.c, focus.r, focus.c),
      content: cell ? (cell.formula ?? cell.text) : "",
      note: cell?.note,
      tone: cell?.tone,
      numbers,
      count,
    });
  }, [rows, anchor, focus, top, bottom, left, right, publish, gridId, focusTick]);

  useEffect(() => () => release(gridId), [release, gridId]);

  // The selection rectangle glides between cells instead of jumping.
  useLayoutEffect(() => {
    const host = surface.current;
    if (!host) return;
    const first = host.querySelector<HTMLElement>(`[data-cell="${top}:${left}"]`) ??
      host.querySelector<HTMLElement>(`[data-cell="${top}:${cellAt(rows, top, left).c}"]`);
    const last = host.querySelector<HTMLElement>(`[data-cell="${bottom}:${right}"]`) ??
      host.querySelector<HTMLElement>(`[data-cell="${bottom}:${cellAt(rows, bottom, right).c}"]`);
    if (!first || !last) return setRect(null);
    setRect({
      top: first.offsetTop,
      left: first.offsetLeft,
      width: last.offsetLeft + last.offsetWidth - first.offsetLeft,
      height: last.offsetTop + last.offsetHeight - first.offsetTop,
    });
  }, [top, left, bottom, right, rows, columns]);

  useEffect(() => {
    const stop = () => (dragging.current = false);
    window.addEventListener("mouseup", stop);
    return () => window.removeEventListener("mouseup", stop);
  }, []);

  const scrollIntoView = useCallback((p: Point) => {
    surface.current?.querySelector(`[data-cell="${p.r}:${p.c}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, []);

  const moveTo = (p: Point, extend: boolean) => {
    const next = { r: clamp(p.r, 0, lastRow), c: clamp(p.c, 0, lastCol) };
    setFocus(next);
    if (!extend) setAnchor(next);
    scrollIntoView(next);
  };

  // The Name Box can move this grid's active cell when this grid owns the selection.
  useEffect(() => {
    registerJump(gridId, (r, c) => {
      const next = { r: clamp(r, 0, lastRow), c: clamp(c, 0, lastCol) };
      setAnchor(next);
      setFocus(next);
      surface.current?.focus();
      scrollIntoView(next);
    });
  }, [registerJump, gridId, lastRow, lastCol, scrollIntoView]);

  const startEdit = (p: Point, initial?: string) => {
    const { cell, c } = cellAt(rows, p.r, p.c);
    if (!cell?.editable || !onEdit) return false;
    setEditing({ p: { r: p.r, c }, draft: initial ?? cell.text });
    return true;
  };

  const commit = () => {
    if (editing && onEdit) onEdit(editing.p.r, editing.p.c, editing.draft);
    setEditing(null);
    surface.current?.focus();
  };

  const copySelection = () => {
    const lines: string[] = [];
    for (let r = top; r <= bottom; r++) {
      const values: string[] = [];
      for (let c = left; c <= right; c++) values.push(rows[r]?.cells[c]?.text ?? "");
      lines.push(values.join("\t"));
    }
    void navigator.clipboard?.writeText(lines.join("\n"));
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (editing) return;
    const extend = event.shiftKey;
    const step: Record<string, Point> = {
      ArrowUp: { r: focus.r - 1, c: focus.c },
      ArrowDown: { r: focus.r + 1, c: focus.c },
      ArrowLeft: { r: focus.r, c: focus.c - 1 },
      ArrowRight: { r: focus.r, c: focus.c + 1 },
      Tab: { r: focus.r, c: focus.c + (event.shiftKey ? -1 : 1) },
      Home: { r: focus.r, c: 0 },
      End: { r: focus.r, c: lastCol },
    };
    const target = step[event.key];
    if (target) {
      event.preventDefault();
      moveTo(target, extend && event.key !== "Tab");
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "c") {
      copySelection();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "a") {
      event.preventDefault();
      setAnchor({ r: 0, c: 0 });
      setFocus({ r: lastRow, c: lastCol });
      return;
    }
    if (event.key === "Enter" || event.key === "F2") {
      event.preventDefault();
      if (!startEdit(focus)) rows[focus.r]?.onOpen?.();
      return;
    }
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      if (startEdit(focus, event.key)) event.preventDefault();
    }
  };

  const template = useMemo(() => `var(--row-head) ${columns.map((column) => column.width).join(" ")}`, [columns]);

  return (
    <div
      ref={surface}
      className={`grid ${className ?? ""}`}
      role="grid"
      aria-label={label}
      aria-rowcount={rows.length}
      aria-colcount={columns.length}
      aria-activedescendant={`${gridId}-${focus.r}-${cellAt(rows, focus.r, focus.c).c}`}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onFocus={() => {
        claim(gridId);
        setFocusTick((tick) => tick + 1);
      }}
      style={{ gridTemplateColumns: template }}
    >
      <div className="grid-corner" aria-hidden />
      {columns.map((column, c) => (
        <div key={column.key} className={`grid-colhead${c >= left && c <= right ? " is-active" : ""}`} aria-hidden>
          {columnLetter(c)}
        </div>
      ))}

      {rows.map((row, r) => {
        const frozen = r < frozenRows;
        return (
          <div key={row.key} role="row" className={`grid-row${row.heading ? " is-heading" : ""}${row.struck ? " is-struck" : ""}`}>
            <div
              className={`grid-rowhead${r >= top && r <= bottom ? " is-active" : ""}${frozen ? " is-frozen" : ""}`}
              style={frozen ? { top: `calc(var(--cell-h) * ${r + 1})` } : undefined}
              aria-hidden
            >
              {r + 1}
            </div>
            {row.cells.map((cell, c) => {
              if (cell === null) return null;
              const span = cell.span ?? 1;
              const selected = r >= top && r <= bottom && c + span - 1 >= left && c <= right;
              const isEditing = editing?.p.r === r && editing.p.c === c;
              return (
                <div
                  key={c}
                  id={`${gridId}-${r}-${c}`}
                  role="gridcell"
                  aria-selected={selected}
                  data-cell={`${r}:${c}`}
                  title={cell.title}
                  className={[
                    "cell",
                    cell.align && `align-${cell.align}`,
                    cell.tone && `tone-${cell.tone}`,
                    cell.strong && "is-strong",
                    cell.editable && "is-editable",
                    cell.flash && "is-recomputed",
                    cell.comment && "has-comment",
                    selected && "in-range",
                    frozen && "is-frozen",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  style={{
                    gridColumn: span > 1 ? `span ${span}` : undefined,
                    top: frozen ? `calc(var(--cell-h) * ${r + 1})` : undefined,
                  }}
                  onMouseDown={(event) => {
                    if (event.button !== 0 || isEditing) return;
                    event.preventDefault();
                    surface.current?.focus();
                    dragging.current = true;
                    setFocus({ r, c });
                    if (!event.shiftKey) setAnchor({ r, c });
                  }}
                  onMouseEnter={() => dragging.current && setFocus({ r, c })}
                  onDoubleClick={() => {
                    if (!startEdit({ r, c })) row.onOpen?.();
                  }}
                >
                  {isEditing ? (
                    <input
                      className="cell-input"
                      autoFocus
                      value={editing.draft}
                      aria-label={`Edit ${columnLetter(c)}${r + 1}`}
                      onChange={(event) => setEditing({ ...editing, draft: event.target.value })}
                      onBlur={commit}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === "Tab") {
                          event.preventDefault();
                          commit();
                          moveTo({ r: event.key === "Enter" ? r + 1 : r, c: event.key === "Tab" ? c + 1 : c }, false);
                        } else if (event.key === "Escape") {
                          setEditing(null);
                          surface.current?.focus();
                        }
                      }}
                    />
                  ) : (
                    (cell.render ?? (
                      <>
                        {cell.icon && <CellIcon kind={cell.icon} />}
                        <span className="cell-text">{cell.text}</span>
                      </>
                    ))
                  )}
                </div>
              );
            })}
          </div>
        );
      })}

      {rect && (
        <div
          className="grid-selection"
          aria-hidden
          style={{ transform: `translate(${rect.left}px, ${rect.top}px)`, width: rect.width, height: rect.height }}
        />
      )}
    </div>
  );
}

const ICONS = { ok: CircleCheck, error: CircleX, warn: CircleAlert, info: Info } as const;

function CellIcon({ kind }: { kind: keyof typeof ICONS }) {
  const Icon = ICONS[kind];
  return <Icon className={`cell-icon icon-${kind}`} size={13} strokeWidth={2.25} aria-hidden />;
}
