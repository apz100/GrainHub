import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

type HistoryPoint = {
  date?: string | null;
  quote_date?: string | null;
  captured_at?: string | null;
  commodity?: string | null;
  commodity_name?: string | null;
  location?: string | null;
  company_name?: string | null;
  cash_price_bu?: number | null;
  cash_price_mt?: number | null;
  basis?: number | null;
  futures_price?: number | null;
};

type SeasonalRow = {
  commodity?: string | null;
  commodity_name?: string | null;
  month?: string | null;
  month_label?: string | null;
  average?: number | null;
  five_year_average?: number | null;
  current_year_average?: number | null;
  current_year?: number | null;
  years?: number | null;
  location?: string | null;
};

function historyFrom(payload: unknown): HistoryPoint[] {
  if (Array.isArray(payload)) return payload as HistoryPoint[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.history)) return obj.history as HistoryPoint[];
    if (Array.isArray(obj.points)) return obj.points as HistoryPoint[];
    if (Array.isArray(obj.rows)) return obj.rows as HistoryPoint[];
    if (Array.isArray(obj.items)) return obj.items as HistoryPoint[];
  }
  return [];
}

function seasonalFrom(payload: unknown): SeasonalRow[] {
  if (Array.isArray(payload)) return payload as SeasonalRow[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.seasonal)) return obj.seasonal as SeasonalRow[];
    if (Array.isArray(obj.rows)) return obj.rows as SeasonalRow[];
    if (Array.isArray(obj.items)) return obj.items as SeasonalRow[];
  }
  return [];
}

async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/prices/history?limit=100`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return [];
    return historyFrom(await res.json());
  } catch {
    return [];
  }
}

async function fetchSeasonal() {
  try {
    const res = await fetch(`${API_BASE}/api/prices/seasonal`, { cache: "no-store", headers });
    if (!res.ok) return [];
    return seasonalFrom(await res.json());
  } catch {
    return [];
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(2);
}

function formatSigned(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
}

export default async function HistoryPage() {
  const [history, seasonal] = await Promise.all([fetchHistory(), fetchSeasonal()]);
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / History</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Price History
      </h1>
      <p className="mt-2 text-sm text-black/65">
        Cash prices over time, and how each month of the year usually prices against its
        5-year average. Averages are computed only from real ingested prices — a month
        with no history shows no average, never a guessed one.
      </p>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Price history</h2>
        {history.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No price history available yet. History accumulates as ingestion runs — nothing
            is backfilled or estimated.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Date</th>
                  <th className="px-2 py-2">Commodity</th>
                  <th className="px-2 py-2">Location</th>
                  <th className="px-2 py-2">Company</th>
                  <th className="px-2 py-2 text-right">Cash/bu</th>
                  <th className="px-2 py-2 text-right">Cash/MT</th>
                  <th className="px-2 py-2 text-right">Basis</th>
                </tr>
              </thead>
              <tbody>
                {history.map((point, idx) => (
                  <tr key={`${point.date ?? point.quote_date ?? point.captured_at ?? idx}-${idx}`} className="border-b border-black/5">
                    <td className="px-2 py-2">{point.date ?? point.quote_date ?? point.captured_at ?? "-"}</td>
                    <td className="px-2 py-2">{point.commodity_name ?? point.commodity ?? "-"}</td>
                    <td className="px-2 py-2">{point.location ?? "-"}</td>
                    <td className="px-2 py-2">{point.company_name ?? "-"}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(point.cash_price_bu)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(point.cash_price_mt)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(point.basis)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Seasonal averages (5-year)</h2>
        {seasonal.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No seasonal averages yet. Five-year averages need five years of real ingested
            prices for a month — until then the table stays empty rather than showing a
            partial average as if it were five years.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Commodity</th>
                  <th className="px-2 py-2">Month</th>
                  <th className="px-2 py-2 text-right">5-year average</th>
                  <th className="px-2 py-2 text-right">Current year</th>
                  <th className="px-2 py-2 text-right">vs 5-year avg</th>
                  <th className="px-2 py-2 text-right">Years in avg</th>
                </tr>
              </thead>
              <tbody>
                {seasonal.map((row, idx) => {
                  const fiveYear = row.five_year_average ?? row.average ?? null;
                  const current = row.current_year_average ?? row.current_year ?? null;
                  const diff =
                    fiveYear != null && current != null ? current - fiveYear : null;
                  return (
                    <tr key={`${row.commodity_name ?? row.commodity}-${row.month_label ?? row.month}-${idx}`} className="border-b border-black/5">
                      <td className="px-2 py-2">{row.commodity_name ?? row.commodity ?? "-"}</td>
                      <td className="px-2 py-2">{row.month_label ?? row.month ?? "-"}</td>
                      <td className="px-2 py-2 text-right">{formatNumber(fiveYear)}</td>
                      <td className="px-2 py-2 text-right">{formatNumber(current)}</td>
                      <td className="px-2 py-2 text-right">{formatSigned(diff)}</td>
                      <td className="px-2 py-2 text-right">{row.years ?? "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <Link href="/bids" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
          Back to market
        </Link>
      </section>
    </main>
  );
}
