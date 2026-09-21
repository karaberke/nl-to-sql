import { useCallback, useRef, useState } from "react";

const MIN_COL = 80;
const DEFAULT_COL = 160;

type ColWidths = Record<string, number>;

type Props = {
  rows: Record<string, unknown>[];
  zoom: number;
};

/**
 * Scrollable results grid with draggable column widths. Column widths are local
 * state, so App remounts this with a `key` per query to reset them.
 */
export default function ResultsTable({ rows, zoom }: Props) {
  const [colWidths, setColWidths] = useState<ColWidths>({});
  const dragRef = useRef<{ col: string; startX: number; startW: number } | null>(null);

  const cols = rows.length ? Object.keys(rows[0]) : [];
  const colW = useCallback((c: string) => colWidths[c] ?? DEFAULT_COL, [colWidths]);

  // Natural width of the table; it still stretches to fill a wider viewport.
  const tableW = cols.reduce((sum, c) => sum + colW(c), 0);

  const startDrag = useCallback((e: React.MouseEvent, col: string) => {
    e.preventDefault();
    dragRef.current = { col, startX: e.clientX, startW: colW(col) };

    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const { col: c, startX, startW } = dragRef.current;
      const next = Math.max(MIN_COL, startW + (ev.clientX - startX));
      setColWidths(prev => ({ ...prev, [c]: next }));
    };
    const onUp = () => {
      dragRef.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [colW]);

  return (
    <div className="min-h-30 flex-1 cursor-default overflow-auto rounded-2xl border border-neutral-200 bg-white shadow-sm">
      {/* zoom is a runtime value, so it stays an inline transform */}
      <div className="origin-top-left" style={{ transform: `scale(${zoom})`, width: `${100 / zoom}%` }}>
        <table className="table-fixed border-collapse text-sm" style={{ width: tableW, minWidth: "100%" }}>
          <colgroup>
            {cols.map(c => <col key={c} style={{ width: colW(c) }} />)}
          </colgroup>
          <thead>
            <tr className="bg-neutral-50">
              {cols.map((c, i) => (
                <th
                  key={c}
                  className="sticky top-0 z-10 overflow-hidden text-ellipsis whitespace-nowrap border-b border-neutral-200 bg-neutral-50 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 select-none"
                >
                  {c}
                  {i < cols.length - 1 && (
                    <span
                      onMouseDown={e => startDrag(e, c)}
                      className="absolute inset-y-0 right-0 flex w-2 cursor-col-resize items-center justify-center"
                    >
                      <span className="block h-1/2 w-px bg-neutral-300" />
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri} className="border-b border-neutral-100 hover:bg-neutral-50">
                {cols.map(c => <Cell key={c} value={row[c]} />)}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && (
          <p className="px-4 py-10 text-center text-sm text-neutral-400">No rows returned.</p>
        )}
      </div>
    </div>
  );
}

function Cell({ value }: { value: unknown }) {
  return (
    <td className="overflow-hidden text-ellipsis whitespace-nowrap px-4 py-2.5 align-middle text-neutral-900">
      {value === null || value === undefined
        ? <span className="text-neutral-400 italic">null</span>
        : typeof value === "number"
          ? <span className="font-mono tabular-nums">{value.toLocaleString()}</span>
          : String(value)}
    </td>
  );
}
