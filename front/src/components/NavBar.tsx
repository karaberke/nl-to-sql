export default function NavBar({ rowCount }: { rowCount: number | null }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-neutral-200 bg-neutral-100/85 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-2">
        {/* Same mark as public/favicon.svg — keep the two in sync */}
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" className="shrink-0" aria-hidden="true">
          <rect x="2" y="2" width="8" height="8" rx="2" className="fill-neutral-900" />
          <rect x="12" y="2" width="8" height="8" rx="2" className="fill-neutral-900/30" />
          <rect x="2" y="12" width="8" height="8" rx="2" className="fill-neutral-900/30" />
          <rect x="12" y="12" width="8" height="8" rx="2" className="fill-neutral-900" />
        </svg>
        <span className="whitespace-nowrap text-sm font-semibold tracking-tight text-neutral-900">
          SQL Agent
        </span>
      </div>
      {rowCount !== null && (
        <span className="whitespace-nowrap text-sm text-neutral-500">
          {rowCount.toLocaleString()} {rowCount === 1 ? "row" : "rows"}
        </span>
      )}
    </header>
  );
}
