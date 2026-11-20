import { Minus, Plus, RotateCw, ScanLine } from "lucide-react";
import { useState } from "react";
import type { PageRef } from "../api";

interface DocumentPaneProps {
  fileName: string;
  pages: PageRef[];
  caption?: string;
  rotations?: number[];
}

const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2];

/** The source document, pinned beside the worksheet like a frozen pane. */
export function DocumentPane({ fileName, pages, caption, rotations = [] }: DocumentPaneProps) {
  const [zoom, setZoom] = useState(2);
  const scale = ZOOMS[zoom] ?? 1;
  const rotated = rotations.some(Boolean);

  return (
    <section className="doc-pane" aria-label={`Source document ${fileName}`}>
      <header className="pane-head">
        <span className="pane-title" title={fileName}>
          {fileName}
        </span>
        {caption && <span className="pane-caption">{caption}</span>}
        <div className="pane-tools">
          <button
            type="button"
            className="icon-button"
            onClick={() => setZoom((z) => Math.max(0, z - 1))}
            disabled={zoom === 0}
            aria-label="Zoom out"
          >
            <Minus size={14} />
          </button>
          <output className="zoom-level" aria-label="Zoom">
            {Math.round(scale * 100)}%
          </output>
          <button
            type="button"
            className="icon-button"
            onClick={() => setZoom((z) => Math.min(ZOOMS.length - 1, z + 1))}
            disabled={zoom === ZOOMS.length - 1}
            aria-label="Zoom in"
          >
            <Plus size={14} />
          </button>
        </div>
      </header>
      {rotated && (
        <p className="pane-notice">
          <RotateCw size={13} aria-hidden /> Page was lying sideways and is shown the way it was read: rotated{" "}
          {rotations.find(Boolean)}° clockwise.
        </p>
      )}
      <div className="doc-scroll">
        {pages.length === 0 ? (
          <div className="doc-empty">
            <ScanLine size={22} strokeWidth={1.5} aria-hidden />
            <p>No page preview.</p>
          </div>
        ) : (
          pages.map((page) => (
            <figure key={page.url} className="doc-page" style={{ width: `${scale * 100}%` }}>
              <img
                src={page.url}
                alt={`${fileName}, page ${page.index + 1} of ${pages.length}`}
                width={page.width}
                height={page.height}
                loading="lazy"
                draggable={false}
              />
              {pages.length > 1 && <figcaption>Page {page.index + 1}</figcaption>}
            </figure>
          ))
        )}
      </div>
    </section>
  );
}
