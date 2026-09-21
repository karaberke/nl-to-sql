import { useEffect, useRef } from "react";
import SpinIcon from "./SpinIcon";

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  /** Tightens the card once results are on screen, to give the table more height. */
  compact?: boolean;
};

export default function QueryBar({ value, onChange, onSubmit, loading, compact = false }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSubmit();
  };

  return (
    <div className={`rounded-2xl border border-neutral-200 bg-white shadow-md ${compact ? "p-4 pb-3" : "p-5 pb-4"}`}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={onKey}
        placeholder="Your question here..."
        rows={compact ? 2 : 3}
        className="block w-full resize-none border-none bg-transparent p-0 text-base leading-relaxed text-neutral-900 outline-none"
      />
      <div className="mt-3 flex items-center justify-between gap-3 border-t border-neutral-200 pt-3">
        <span className="text-xs text-neutral-400">⌘↵ to run</span>
        <button
          onClick={onSubmit}
          disabled={loading || !value.trim()}
          className="flex h-9 shrink-0 items-center gap-2 whitespace-nowrap rounded-lg bg-neutral-900 px-5 text-sm font-semibold text-white transition-colors hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-400"
        >
          {loading ? (
            <>
              <SpinIcon />
              Querying…
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
              Run query
            </>
          )}
        </button>
      </div>
    </div>
  );
}
