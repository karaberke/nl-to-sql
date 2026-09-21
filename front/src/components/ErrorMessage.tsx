export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-4">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="mt-0.5 shrink-0 text-red-600">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.4" />
        <path d="M8 4.5v4M8 10.5v1" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
      <span className="text-sm break-words text-red-700">{message}</span>
    </div>
  );
}
