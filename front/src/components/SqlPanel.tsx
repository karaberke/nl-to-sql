const SQL_KEYWORDS = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP BY|ORDER BY|HAVING|LIMIT|INSERT|UPDATE|DELETE|AS|AND|OR|NOT|IN|IS|NULL|DISTINCT|COUNT|SUM|AVG|MAX|MIN|CASE|WHEN|THEN|ELSE|END|WITH|UNION|ALL|TOP|OVER|PARTITION|BY|ASC|DESC)\b/gi;

function SqlHighlight({ sql }: { sql: string }) {
  const parts = sql.split(SQL_KEYWORDS);
  const matches = sql.match(SQL_KEYWORDS) ?? [];
  return (
    <>
      {parts.map((p, i) => (
        <span key={i}>
          <span className="text-neutral-700">{p}</span>
          {matches[i] && <span className="font-semibold text-blue-700">{matches[i]}</span>}
        </span>
      ))}
    </>
  );
}

type Props = { sql: string; open: boolean; onToggle: () => void };

export default function SqlPanel({ sql, open, onToggle }: Props) {
  return (
    <div className="mb-3 shrink-0 overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <button
        onClick={onToggle}
        className="flex w-full cursor-pointer items-center justify-between px-5 py-3"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Generated SQL</span>
          <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700">SELECT</span>
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          className={`shrink-0 text-neutral-400 transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M3 5l4 4 4-4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="px-4 pb-4">
          <pre className="m-0 max-h-[22vh] overflow-auto whitespace-pre-wrap wrap-break-word rounded-lg bg-neutral-100 p-4 font-mono text-sm leading-relaxed text-neutral-900">
            <SqlHighlight sql={sql} />
          </pre>
        </div>
      )}
    </div>
  );
}
