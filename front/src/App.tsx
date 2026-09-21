import { useState } from "react";
import NavBar from "./components/NavBar";
import QueryBar from "./components/QueryBar";
import ErrorMessage from "./components/ErrorMessage";
import SqlPanel from "./components/SqlPanel";
import TableToolbar from "./components/TableToolbar";
import ResultsTable from "./components/ResultsTable";
import type { QueryResult } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const DB_NAME = import.meta.env.VITE_DB_NAME || "Your Database";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<QueryResult | null>(null);
  const [runId, setRunId] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [sqlOpen, setSqlOpen] = useState(true);

  const submit = async () => {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError(null);
    setData(null);
    setSqlOpen(true);
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail ?? `HTTP ${res.status}`);
      }
      const j: QueryResult = await res.json();
      setData(j);
      setRunId(n => n + 1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const zoomIn = () => setZoom(z => Math.min(2, +(z + 0.1).toFixed(1)));
  const zoomOut = () => setZoom(z => Math.max(0.5, +(z - 0.1).toFixed(1)));
  const zoomReset = () => setZoom(1);

  const hasResults = data !== null;
  const rows = data?.results ?? [];
  const cols = rows.length ? Object.keys(rows[0]) : [];

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-neutral-100 font-sans">
      <NavBar rowCount={hasResults ? rows.length : null} />

      {/* Everything below the nav shares the remaining viewport height */}
      <div className={`flex min-h-0 flex-1 flex-col ${hasResults ? "overflow-y-hidden" : "overflow-y-auto"}`}>

        <main
          className={`mx-auto flex w-full max-w-3xl flex-col justify-center px-4 sm:px-6 lg:px-8 ${
            hasResults ? "shrink-0 pt-5 pb-3" : "flex-1 pt-8 pb-8 sm:pt-16"
          }`}
        >
          {!hasResults && (
            <div className="mb-8 text-center">
              <h1 className="mb-3 text-3xl leading-tight font-bold tracking-tight text-neutral-900 sm:text-4xl lg:text-5xl">
                Query {DB_NAME}
              </h1>
              <p className="text-base text-neutral-500">
                Type a question in plain English — to query the database.
              </p>
            </div>
          )}

          <QueryBar
            value={prompt}
            onChange={setPrompt}
            onSubmit={submit}
            loading={loading}
            compact={hasResults}
          />

          {error && <ErrorMessage message={error} />}
        </main>

        {data && (
          <section className="flex min-h-0 flex-1 flex-col px-4 pb-4 sm:px-6 sm:pb-6 lg:px-8 lg:pb-8">
            <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col">
              <SqlPanel sql={data.sql} open={sqlOpen} onToggle={() => setSqlOpen(o => !o)} />
              <TableToolbar
                columns={cols.length}
                rows={rows.length}
                zoom={zoom}
                onZoomIn={zoomIn}
                onZoomOut={zoomOut}
                onZoomReset={zoomReset}
              />
              {/* key resets the per-query column widths */}
              <ResultsTable key={runId} rows={rows} zoom={zoom} />
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
