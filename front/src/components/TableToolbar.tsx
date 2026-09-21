type Props = {
  columns: number;
  rows: number;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
};

export default function TableToolbar({ columns, rows, zoom, onZoomIn, onZoomOut, onZoomReset }: Props) {
  return (
    <div className="mb-2.5 flex shrink-0 flex-wrap items-center justify-between gap-2 px-0.5">
      <span className="text-sm font-medium text-neutral-500">
        {columns} column{columns !== 1 ? "s" : ""} · {rows.toLocaleString()} row{rows !== 1 ? "s" : ""}
      </span>
      <div className="flex items-center gap-1.5">
        <span className="mr-1 text-xs text-neutral-400">Zoom</span>
        <ZoomBtn onClick={onZoomOut} label="−" />
        <button
          onClick={onZoomReset}
          className="h-8 cursor-pointer rounded-lg border border-neutral-200 bg-white px-2.5 text-xs font-medium text-neutral-900 hover:bg-neutral-50"
        >
          {Math.round(zoom * 100)}%
        </button>
        <ZoomBtn onClick={onZoomIn} label="+" />
      </div>
    </div>
  );
}

function ZoomBtn({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className="flex size-8 cursor-pointer items-center justify-center rounded-lg border border-neutral-200 bg-white text-base leading-none text-neutral-900 hover:bg-neutral-50"
    >
      {label}
    </button>
  );
}
