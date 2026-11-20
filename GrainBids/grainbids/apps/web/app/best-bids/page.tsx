import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

type BestBidRow = {
  id?: string | null;
  commodity?: string | null;
  commodity_name?: string | null;
  location?: string | null;
  company_name?: string | null;
  buyer?: string | null;
  cash_price_bu?: number | null;
  cash_price_mt?: number | null;
  basis?: number | null;
  delivery_label?: string | null;
  delivery_month?: string | null;
  futures_month?: string | null;
  captured_at?: string | null;
  source_name?: string | null;
  source_attribution?: string | null;
  distance_km?: number | null;
};

function rowsFrom(payload: unknown): BestBidRow[] {
  if (Array.isArray(payload)) return payload as BestBidRow[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.bids)) return obj.bids as BestBidRow[];
    if (Array.isArray(obj.rows)) return obj.rows as BestBidRow[];
    if (Array.isArray(obj.best_bids)) return obj.best_bids as BestBidRow[];
    if (Array.isArray(obj.items)) return obj.items as BestBidRow[];
  }
  return [];
}

async function fetchBestBids() {
  try {
    // Public page: no login required. Headers only carry org/role env vars when set.
    const res = await fetch(`${API_BASE}/api/best-bids?limit=100`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return [];
    return rowsFrom(await res.json());
  } catch {
    return [];
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(2);
}

export default async function BestBidsPage() {
  const bids = await fetchBestBids();
  const commodities = [...new Set(bids.map((b) => b.commodity_name ?? b.commodity ?? "Unknown"))];
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / Best Bids</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Best Bids — Free
      </h1>
      <p className="mt-2 text-sm text-black/65">
        The best cash bid for each commodity and delivery month, free for everyone — no
        account, no login. Every bid is a real ingested price with its buyer, location
        and capture time shown.
      </p>

      {bids.length === 0 ? (
        <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
          <h2 className="text-lg font-semibold">No best bids yet</h2>
          <p className="mt-2 text-sm text-black/55">
            No best bids are available yet. Best bids appear here once cash bids have been
            ingested — no prices are shown until a real source provides them.
          </p>
          <Link href="/bids" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
            View the market dashboard
          </Link>
        </section>
      ) : (
        commodities.map((commodity) => {
          const group = bids.filter(
            (b) => (b.commodity_name ?? b.commodity ?? "Unknown") === commodity
          );
          return (
            <section
              key={commodity}
              className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur"
            >
              <h2 className="text-lg font-semibold">{commodity}</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                      <th className="px-2 py-2">Location</th>
                      <th className="px-2 py-2">Buyer</th>
                      <th className="px-2 py-2">Delivery</th>
                      <th className="px-2 py-2">Futures</th>
                      <th className="px-2 py-2 text-right">Cash/bu</th>
                      <th className="px-2 py-2 text-right">Cash/MT</th>
                      <th className="px-2 py-2 text-right">Basis</th>
                      <th className="px-2 py-2">Captured</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.map((row, idx) => (
                      <tr key={row.id ?? `${row.location}-${row.delivery_label}-${idx}`} className="border-b border-black/5">
                        <td className="px-2 py-2">{row.location ?? "-"}</td>
                        <td className="px-2 py-2">
                          {row.company_name ?? row.buyer ?? "-"}
                          {row.source_attribution ? (
                            <span className="block text-xs text-black/50">
                              Source: {row.source_attribution}
                            </span>
                          ) : null}
                        </td>
                        <td className="px-2 py-2">{row.delivery_label ?? row.delivery_month ?? "-"}</td>
                        <td className="px-2 py-2">{row.futures_month ?? "-"}</td>
                        <td className="px-2 py-2 text-right font-semibold">{formatNumber(row.cash_price_bu)}</td>
                        <td className="px-2 py-2 text-right">{formatNumber(row.cash_price_mt)}</td>
                        <td className="px-2 py-2 text-right">{formatNumber(row.basis)}</td>
                        <td className="px-2 py-2">{row.captured_at ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          );
        })
      )}
    </main>
  );
}
