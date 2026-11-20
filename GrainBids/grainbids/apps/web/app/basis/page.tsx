import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

type BasisRow = {
  id?: string | null;
  rank?: number | null;
  commodity?: string | null;
  commodity_name?: string | null;
  location?: string | null;
  location_id?: string | null;
  source?: string | null;
  source_name?: string | null;
  delivery_label?: string | null;
  futures_month?: string | null;
  futures_price?: number | null;
  basis?: number | null;
  basis_change?: number | null;
  cash_price_bu?: number | null;
  quote_date?: string | null;
  captured_at?: string | null;
  distance_km?: number | null;
  missing_reason?: string | null;
  data_quality?: string | null;
};

type BasisHistoryPoint = {
  date?: string | null;
  quote_date?: string | null;
  captured_at?: string | null;
  commodity?: string | null;
  commodity_name?: string | null;
  location?: string | null;
  basis?: number | null;
  cash_price_bu?: number | null;
};

function rowsFrom(payload: unknown): BasisRow[] {
  if (Array.isArray(payload)) return payload as BasisRow[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.rows)) return obj.rows as BasisRow[];
    if (Array.isArray(obj.ranked)) return obj.ranked as BasisRow[];
    if (Array.isArray(obj.tracker)) return obj.tracker as BasisRow[];
    if (Array.isArray(obj.items)) return obj.items as BasisRow[];
  }
  return [];
}

function historyFrom(payload: unknown): BasisHistoryPoint[] {
  if (Array.isArray(payload)) return payload as BasisHistoryPoint[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.history)) return obj.history as BasisHistoryPoint[];
    if (Array.isArray(obj.points)) return obj.points as BasisHistoryPoint[];
    if (Array.isArray(obj.rows)) return obj.rows as BasisHistoryPoint[];
  }
  return [];
}

async function fetchTracker() {
  try {
    const res = await fetch(`${API_BASE}/api/basis/tracker?limit=100`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return { ranked: [] as BasisRow[], unranked: [] as BasisRow[], note: null as string | null };
    const payload = await res.json();
    const unranked =
      payload && typeof payload === "object" && Array.isArray((payload as Record<string, unknown>).unranked)
        ? ((payload as Record<string, unknown>).unranked as BasisRow[])
        : [];
    const note =
      payload && typeof payload === "object" && typeof (payload as Record<string, unknown>).note === "string"
        ? ((payload as Record<string, unknown>).note as string)
        : null;
    return { ranked: rowsFrom(payload), unranked, note };
  } catch {
    return { ranked: [] as BasisRow[], unranked: [] as BasisRow[], note: null as string | null };
  }
}

async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/basis/history?limit=100`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return [];
    return historyFrom(await res.json());
  } catch {
    return [];
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(2);
}

export default async function BasisPage() {
  const [tracker, history] = await Promise.all([fetchTracker(), fetchHistory()]);
  const ranked = tracker.ranked;
  const unranked = tracker.unranked;
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / Basis</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Basis Tracker
      </h1>
      <p className="mt-2 text-sm text-black/65">
        Cash price minus the futures price, by location and commodity. Basis is the local
        part of the price — it is what your elevator actually pays over or under the board.
        Every row is a real ingested bid; nothing is estimated.
        {tracker.note ? ` ${tracker.note}` : ""}
      </p>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Current basis — strongest first</h2>
        {ranked.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No basis data available yet. The basis tracker needs ingested cash bids — run an
            ingestion first. No numbers are shown until a real source provides them.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Rank</th>
                  <th className="px-2 py-2">Location</th>
                  <th className="px-2 py-2">Commodity</th>
                  <th className="px-2 py-2">Delivery</th>
                  <th className="px-2 py-2">Futures</th>
                  <th className="px-2 py-2 text-right">Futures price</th>
                  <th className="px-2 py-2 text-right">Basis</th>
                  <th className="px-2 py-2 text-right">Cash/bu</th>
                  <th className="px-2 py-2 text-right">Distance (km)</th>
                  <th className="px-2 py-2">Quote date</th>
                  <th className="px-2 py-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((row, idx) => (
                  <tr key={row.id ?? `${row.location}-${row.commodity_name}-${idx}`} className="border-b border-black/5">
                    <td className="px-2 py-2">{row.rank ?? idx + 1}</td>
                    <td className="px-2 py-2">{row.location ?? "-"}</td>
                    <td className="px-2 py-2">{row.commodity_name ?? row.commodity ?? "-"}</td>
                    <td className="px-2 py-2">{row.delivery_label ?? "-"}</td>
                    <td className="px-2 py-2">{row.futures_month ?? "-"}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(row.futures_price)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(row.basis)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(row.cash_price_bu)}</td>
                    <td className="px-2 py-2 text-right">{row.distance_km ?? "-"}</td>
                    <td className="px-2 py-2">{row.quote_date ?? row.captured_at ?? "-"}</td>
                    <td className="px-2 py-2">{row.source ?? row.source_name ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {unranked.length > 0 ? (
          <>
            <h3 className="mt-6 text-base font-semibold">Rows without a basis ({unranked.length})</h3>
            <p className="mt-1 text-sm text-black/55">
              These bids exist but cannot produce a basis — usually a missing cash or
              futures price. They are listed, not hidden, with the reason.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                    <th className="px-2 py-2">Location</th>
                    <th className="px-2 py-2">Commodity</th>
                    <th className="px-2 py-2">Delivery</th>
                    <th className="px-2 py-2">Reason</th>
                    <th className="px-2 py-2">Quote date</th>
                  </tr>
                </thead>
                <tbody>
                  {unranked.map((row, idx) => (
                    <tr key={`unranked-${row.location}-${row.commodity_name}-${idx}`} className="border-b border-black/5">
                      <td className="px-2 py-2">{row.location ?? "-"}</td>
                      <td className="px-2 py-2">{row.commodity_name ?? row.commodity ?? "-"}</td>
                      <td className="px-2 py-2">{row.delivery_label ?? "-"}</td>
                      <td className="px-2 py-2">{row.missing_reason ?? row.data_quality ?? "-"}</td>
                      <td className="px-2 py-2">{row.quote_date ?? row.captured_at ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </section>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Basis history</h2>
        {history.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No basis history yet. History accumulates as ingestion runs — nothing is
            backfilled or estimated.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Date</th>
                  <th className="px-2 py-2">Commodity</th>
                  <th className="px-2 py-2">Location</th>
                  <th className="px-2 py-2 text-right">Basis</th>
                  <th className="px-2 py-2 text-right">Cash/bu</th>
                </tr>
              </thead>
              <tbody>
                {history.map((point, idx) => (
                  <tr key={`${point.date ?? point.quote_date ?? point.captured_at ?? idx}-${idx}`} className="border-b border-black/5">
                    <td className="px-2 py-2">{point.date ?? point.quote_date ?? point.captured_at ?? "-"}</td>
                    <td className="px-2 py-2">{point.commodity ?? "-"}</td>
                    <td className="px-2 py-2">{point.location ?? "-"}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(point.basis)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(point.cash_price_bu)}</td>
                  </tr>
                ))}
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
