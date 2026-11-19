import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

type SourceHealthRow = {
  id?: string | null;
  source_key?: string | null;
  source_name?: string | null;
  name?: string | null;
  status?: string | null;
  is_active?: boolean | null;
  last_success_at?: string | null;
  last_attempt_at?: string | null;
  last_error?: string | null;
  parse_success_rate?: number | null;
  rejected_row_count?: number | null;
  missing_required_count?: number | null;
  freshness?: string | null;
  stale?: boolean | null;
};

function rowsFrom(payload: unknown): SourceHealthRow[] {
  if (Array.isArray(payload)) return payload as SourceHealthRow[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.sources)) return obj.sources as SourceHealthRow[];
    if (Array.isArray(obj.rows)) return obj.rows as SourceHealthRow[];
    if (Array.isArray(obj.items)) return obj.items as SourceHealthRow[];
  }
  return [];
}

async function fetchSourceHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/source-health`, { cache: "no-store", headers });
    if (!res.ok) return { rows: [], summary: null as Record<string, unknown> | null };
    const payload = await res.json();
    const summary =
      payload && typeof payload === "object" && !Array.isArray(payload)
        ? (payload as Record<string, unknown>)
        : null;
    return { rows: rowsFrom(payload), summary };
  } catch {
    return { rows: [], summary: null as Record<string, unknown> | null };
  }
}

function statusTone(status: string | null | undefined, stale: boolean | null | undefined): string {
  const s = (status ?? "").toLowerCase();
  if (stale || s.includes("fail") || s.includes("error") || s.includes("down")) {
    return "border-rose-700/20 bg-rose-100 text-rose-900";
  }
  if (s.includes("stale") || s.includes("warn") || s.includes("degrad")) {
    return "border-amber-700/20 bg-amber-100 text-amber-900";
  }
  if (s.includes("ok") || s.includes("fresh") || s.includes("healthy") || s.includes("live")) {
    return "border-emerald-700/20 bg-emerald-100 text-emerald-900";
  }
  return "border-black/15 bg-white text-black/70";
}

function formatRate(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(1)}%`;
}

function summaryNumber(summary: Record<string, unknown> | null, key: string): string {
  const value = summary?.[key];
  return typeof value === "number" ? String(value) : "-";
}

export default async function SourceHealthPage() {
  const { rows, summary } = await fetchSourceHealth();
  const failing = rows.filter((r) => {
    const s = (r.status ?? "").toLowerCase();
    return r.stale || s.includes("fail") || s.includes("error") || s.includes("down");
  }).length;
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / Source Health</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Source Health
      </h1>
      <p className="mt-2 text-sm text-black/65">
        Every price source, its last successful pull, and whether it is fresh, stale or
        failing. A source only shows as healthy when a real ingestion run succeeded —
        nothing here is assumed.
      </p>

      <section className="mt-8 grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
          <p className="text-xs uppercase tracking-wide text-black/50">Sources tracked</p>
          <p className="mt-1 text-2xl font-semibold">
            {summaryNumber(summary, "total_sources") === "-"
              ? rows.length
              : summaryNumber(summary, "total_sources")}
          </p>
        </div>
        <div className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
          <p className="text-xs uppercase tracking-wide text-black/50">Fresh</p>
          <p className="mt-1 text-2xl font-semibold">
            {summaryNumber(summary, "fresh_sources") === "-"
              ? rows.length - failing
              : summaryNumber(summary, "fresh_sources")}
          </p>
        </div>
        <div className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
          <p className="text-xs uppercase tracking-wide text-black/50">Failing / stale</p>
          <p className="mt-1 text-2xl font-semibold">
            {summaryNumber(summary, "failing_sources") === "-"
              ? failing
              : summaryNumber(summary, "failing_sources")}
          </p>
        </div>
      </section>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Sources</h2>
        {rows.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No source health data available yet. The source-health endpoint reports on
            configured price sources once ingestion has run — no status is shown until a
            real run is recorded.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Source</th>
                  <th className="px-2 py-2">Status</th>
                  <th className="px-2 py-2">Last success</th>
                  <th className="px-2 py-2">Last attempt</th>
                  <th className="px-2 py-2 text-right">Parse success</th>
                  <th className="px-2 py-2 text-right">Rejected rows</th>
                  <th className="px-2 py-2">Last error</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr
                    key={row.id ?? row.source_key ?? `${row.source_name ?? row.name}-${idx}`}
                    className="border-b border-black/5"
                  >
                    <td className="px-2 py-2">{row.source_name ?? row.name ?? row.source_key ?? "-"}</td>
                    <td className="px-2 py-2">
                      <span
                        className={`inline-block rounded-md border px-2 py-1 text-xs ${statusTone(row.status, row.stale)}`}
                      >
                        {row.stale ? "stale" : row.status ?? (row.is_active === false ? "disabled" : "unknown")}
                      </span>
                    </td>
                    <td className="px-2 py-2">{row.last_success_at ?? "-"}</td>
                    <td className="px-2 py-2">{row.last_attempt_at ?? "-"}</td>
                    <td className="px-2 py-2 text-right">{formatRate(row.parse_success_rate)}</td>
                    <td className="px-2 py-2 text-right">{row.rejected_row_count ?? "-"}</td>
                    <td className="px-2 py-2">{row.last_error ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Link href="/sources" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
          Manage sources
        </Link>
      </section>
    </main>
  );
}
