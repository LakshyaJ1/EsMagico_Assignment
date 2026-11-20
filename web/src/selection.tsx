import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

export type Tone = "error" | "warn" | "ok" | "muted" | "info";

/** What the formula bar and the status bar show for the current grid selection. */
export interface SelectionInfo {
  ref: string;
  content: string;
  note?: string;
  tone?: Tone;
  numbers: number[];
  count: number;
}

type Jump = (row: number, column: number) => void;

interface SelectionContextValue {
  selection: SelectionInfo | null;
  /** Grids publish their selection; only the owning (last focused) grid is shown. */
  publish: (grid: string, info: SelectionInfo) => void;
  claim: (grid: string) => void;
  release: (grid: string) => void;
  registerJump: (grid: string, jump: Jump) => void;
  /** Move the owning grid's active cell (used by the Name Box). */
  jump: (row: number, column: number) => boolean;
}

const SelectionContext = createContext<SelectionContextValue | null>(null);

/**
 * Several grids can be on screen (the Evaluation sheet has two). Like a spreadsheet with
 * split panes, the formula bar follows the pane that has focus: the first grid to publish
 * owns it until another grid is focused.
 */
export function SelectionProvider({ children }: { children: ReactNode }) {
  const [selection, setSelection] = useState<SelectionInfo | null>(null);
  const owner = useRef<string | null>(null);
  const jumps = useRef(new Map<string, Jump>());

  const publish = useCallback((grid: string, info: SelectionInfo) => {
    if (owner.current === null) owner.current = grid;
    if (owner.current === grid) setSelection(info);
  }, []);
  const claim = useCallback((grid: string) => {
    owner.current = grid;
  }, []);
  const release = useCallback((grid: string) => {
    jumps.current.delete(grid);
    if (owner.current === grid) {
      owner.current = null;
      setSelection(null);
    }
  }, []);
  const registerJump = useCallback((grid: string, jump: Jump) => {
    jumps.current.set(grid, jump);
  }, []);
  const jump = useCallback((row: number, column: number) => {
    const target = owner.current ? jumps.current.get(owner.current) : undefined;
    target?.(row, column);
    return Boolean(target);
  }, []);

  const value = useMemo(
    () => ({ selection, publish, claim, release, registerJump, jump }),
    [selection, publish, claim, release, registerJump, jump],
  );
  return <SelectionContext.Provider value={value}>{children}</SelectionContext.Provider>;
}

export function useSelection(): SelectionContextValue {
  const context = useContext(SelectionContext);
  if (!context) throw new Error("useSelection must be used inside SelectionProvider");
  return context;
}
