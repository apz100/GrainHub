"use client";

import { useState } from "react";
import Link from "next/link";

import { API_BASE, buildApiHeaders, getApiConfigError } from "@/lib/api";
import PrototypeBanner from "../_components/prototype-banner";

/**
 * Mobile-first Price Finder prototype (Cycle 3).
 *
 * Phone-width search UI wired to the real GET /api/best-bids and
 * GET /api/market-search endpoints. No prices are invented: when the
 * API returns nothing, the page shows an empty state; when the API
 * cannot be reached at all, it shows clearly-labelled EXAMPLE rows
 * (synthetic locations only — "Testville") so the layout can still
 * be reviewed. No real company branding anywhere.
 */

const GRAINS = [
  { value: "", label: "Any grain" },
  { value: "Corn", label: "Corn" },
  { value: "Soybeans", label: "Soybeans" },
  { value: "Wheat", label: "Wheat" },
  { value: "Canola", label: "Canola" },
  { value: "Barley", label: "Barley" },
  { value: "Oats", label: "Oats" },
];

const RADII = [
  { value: "", label: "Any distance" },
  { value: "25", label: "Within 25 km" },
  { value: "50", label: "Within 50 km" },
  { value: "100", label: "Within 100 km" },
  { value: "200", label: "Within 200 km" },
];

const MONTHS = [
  { value: "", label: "Any delivery month" },
  { value: "2026-11", label: "November 2026" },
  { value: "2026-12", label: "December 2026" },
  { value: "2027-01", label: "January 2027" },
  { value: "2027-02", label: "February 2027" },
  { value: "2027-03", label: "March 2027" },
  { value: "2027-07", label: "July 2027" },
  { value: "2027-11", label: "November 2027" },
];

type BidRow = {
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
  distance_km?: number | null;
};

type SearchGroup = {
  label?: string | null;
  row_count?: number | null;
  top_cash_price_bu?: number | null;
  rows?: BidRow[];
};

function rowsFrom(payload: unknown): BidRow[] {
  if (Array.isArray(payload)) return payload as BidRow[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    for (const key of ["bids", "rows", "best_bids", "items"]) {
      if (Array.isArray(obj[key])) return obj[key] as BidRow[];
    }
  }
  return [];
}

function groupsFrom(payload: unknown): SearchGroup[] {
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.groups)) return obj.groups as SearchGroup[];
  }
  return [];
}

/** Synthetic layout-only rows, shown ONLY when the API is unreachable. */
const EXAMPLE_ROWS: BidRow[] = [
  {
    id: "example-1",
    commodity_name: "Corn",
    location: "Testville",
    company_name: "Example Elevator Co.",
    cash_price_bu: 5.42,
    cash_price_mt: 213.38,
    basis: -0.18,
    delivery_label: "November 2026",
    futures_month: "Dec 2026",
    captured_at: "Example data — not a real bid",
  },
  {
    id: "example-2",
    commodity_name: "Corn",
    location: "Sampletown",
    company_name: "Example Grain Ltd.",
    cash_price_bu: 5.35,
    cash_price_mt: 210.63,
    basis: -0.25,
    delivery_label: "November 2026",
    futures_month: "Dec 2026",
    captured_at: "Example data — not a real bid",
  },
  {
    id: "example-3",
    commodity_name: "Soybeans",
    location: "Testville",
    company_name: "Example Elevator Co.",
    cash_price_bu: 11.87,
    cash_price_mt: 436.11,
    basis: -0.42,
    delivery_label: "November 2026",
    futures_month: "Nov 2026",
    captured_at: "Example data — not a real bid",
  },
];

function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(2);
}

function BidCard({ row, example }: { row: BidRow; example?: boolean }) {
  return (
    <article className="rounded-lg border border-black/10 bg-white/70 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">
            {row.commodity_name ?? row.commodity ?? "Grain"}
          </h3>
          <p className="text-sm text-black/60">
            {row.location ?? "-"}
            {row.distance_km != null ? ` · ${Math.round(row.distance_km)} km away` : ""}
          </p>
        </div>
        <p className="text-right">
          <span className="block text-lg font-semibold">
            ${formatNumber(row.cash_price_bu)}
            <span className="text-xs font-normal text-black/50"> /bu</span>
          </span>
          <span className="block text-xs text-black/50">
            ${formatNumber(row.cash_price_mt)} /MT
          </span>
        </p>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-xs text-black/60">
        <div>
          <dt className="uppercase tracking-wide">Buyer</dt>
          <dd className="mt-0.5 text-sm text-black/85">{row.company_name ?? row.buyer ?? "-"}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Delivery</dt>
          <dd className="mt-0.5 text-sm text-black/85">{row.delivery_label ?? row.delivery_month ?? "-"}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Basis</dt>
          <dd className="mt-0.5 text-sm text-black/85">{formatNumber(row.basis)}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-black/45">
        {example ? "Example row — not a real bid." : `Captured: ${row.captured_at ?? "-"}`}
        {row.futures_month ? ` · Futures: ${row.futures_month}` : ""}
      </p>
    </article>
  );
}

export default function PriceFinderPrototypePage() {
  const headers = buildApiHeaders();
  const [location, setLocation] = useState("");
  const [grain, setGrain] = useState("");
  const [radius, setRadius] = useState("");
  const [deliveryMonth, setDeliveryMonth] = useState("");
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [apiUnreachable, setApiUnreachable] = useState(false);
  const [radiusNote, setRadiusNote] = useState("");
  const [error, setError] = useState("");
  const [bestBids, setBestBids] = useState<BidRow[]>([]);
  const [groups, setGroups] = useState<SearchGroup[]>([]);

  async function runSearch(event: React.FormEvent) {
    event.preventDefault();
    const configError = getApiConfigError({ requireOrg: false });
    if (configError) {
      setError(configError);
      setSearched(true);
      return;
    }
    setLoading(true);
    setError("");
    setRadiusNote("");
    setApiUnreachable(false);
    setBestBids([]);
    setGroups([]);
    try {
      // Best bids: public endpoint, commodity filter only.
      const bestParams = new URLSearchParams({ limit: "30" });
      if (grain) bestParams.set("commodity", grain);
      const bestRes = await fetch(`${API_BASE}/api/best-bids?${bestParams}`, {
        cache: "no-store",
        headers,
      });
      if (!bestRes.ok) throw new Error(`Best bids API returned ${bestRes.status}`);
      setBestBids(rowsFrom(await bestRes.json()));

      // Market search: location + grain + radius + delivery month.
      // Radius needs an origin with coordinates; if the API rejects the
      // radius (e.g. unknown location), retry without it and say so.
      const searchParams = new URLSearchParams({ top_n: "30", limit: "250" });
      if (grain) searchParams.set("commodity", grain);
      if (location.trim()) searchParams.set("location", location.trim());
      if (deliveryMonth) searchParams.set("delivery_month", deliveryMonth);
      if (radius) searchParams.set("radius_km", radius);
      let searchRes = await fetch(`${API_BASE}/api/market-search?${searchParams}`, {
        cache: "no-store",
        headers,
      });
      if (!searchRes.ok && radius) {
        searchParams.delete("radius_km");
        searchRes = await fetch(`${API_BASE}/api/market-search?${searchParams}`, {
          cache: "no-store",
          headers,
        });
        if (searchRes.ok) {
          setRadiusNote(
            "Radius search needs a location with stored coordinates, so results below are not radius-filtered. Try a location the API knows, or leave the radius off."
          );
        }
      }
      if (!searchRes.ok) throw new Error(`Market search API returned ${searchRes.status}`);
      setGroups(groupsFrom(await searchRes.json()));
    } catch (err) {
      // Network-level failure (API down / unreachable): show the
      // clearly-labelled example layout instead of inventing prices.
      setApiUnreachable(true);
      setError(String(err));
    } finally {
      setLoading(false);
      setSearched(true);
    }
  }

  const searchRows = groups.flatMap((group) => group.rows ?? []);
  const hasRealResults = bestBids.length > 0 || searchRows.length > 0;

  return (
    <main className="mx-auto w-full max-w-md px-4 py-6 sm:max-w-2xl sm:px-6">
      <PrototypeBanner
        title="Price Finder prototype — mobile-first"
        blurb="Prototype — not production. Searches the real /api/best-bids and /api/market-search endpoints. No prices are invented: empty results stay empty, and example rows (when the API is unreachable) are labelled as examples."
      />
      <p className="mt-6 text-xs uppercase tracking-[0.16em] text-black/50">GrainBids / Prototypes / Price Finder</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-3xl leading-tight">
        Find the best bid near you
      </h1>
      <p className="mt-2 text-sm text-black/65">
        Search real cash bids by location, grain, radius and delivery month.
        Bids are grouped by delivery month, best price first.
      </p>

      <form onSubmit={runSearch} className="mt-6 space-y-4 rounded-lg border border-black/10 bg-white/65 p-4 backdrop-blur">
        <div>
          <label htmlFor="pf-location" className="text-sm font-medium">Your location</label>
          <input
            id="pf-location"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Testville"
            autoComplete="off"
            className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
          />
          <p className="mt-1 text-xs text-black/50">Town, county, or elevator location.</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="pf-grain" className="text-sm font-medium">Grain</label>
            <select
              id="pf-grain"
              value={grain}
              onChange={(e) => setGrain(e.target.value)}
              className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
            >
              {GRAINS.map((g) => (
                <option key={g.value} value={g.value}>{g.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="pf-radius" className="text-sm font-medium">Radius</label>
            <select
              id="pf-radius"
              value={radius}
              onChange={(e) => setRadius(e.target.value)}
              className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
            >
              {RADII.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="pf-month" className="text-sm font-medium">Delivery month</label>
          <select
            id="pf-month"
            value={deliveryMonth}
            onChange={(e) => setDeliveryMonth(e.target.value)}
            className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
          >
            {MONTHS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-black px-4 py-3 text-base font-medium text-white disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search bids"}
        </button>
      </form>

      {radiusNote ? (
        <p className="mt-4 rounded border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {radiusNote}
        </p>
      ) : null}

      {searched && !loading ? (
        <div className="mt-6 space-y-6">
          {apiUnreachable ? (
            <section>
              <p className="rounded border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                The GrainBids API could not be reached{error ? ` (${error})` : ""}, so no
                real bids are shown. The rows below are <strong>example data only</strong> —
                synthetic prices at synthetic locations, shown just to preview the layout.
              </p>
              <h2 className="mt-6 text-lg font-semibold">Example results — not real bids</h2>
              <div className="mt-3 space-y-3">
                {EXAMPLE_ROWS.map((row) => (
                  <BidCard key={row.id} row={row} example />
                ))}
              </div>
            </section>
          ) : !hasRealResults ? (
            <section className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
              <h2 className="text-lg font-semibold">No bids found</h2>
              <p className="mt-2 text-sm text-black/55">
                No cash bids matched this search. Try a different grain, a wider
                radius, or another delivery month. No prices are shown until a
                real source provides them.
              </p>
              <Link href="/best-bids" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
                View the free best-bid page
              </Link>
            </section>
          ) : (
            <>
              {groups.length > 0 ? (
                <section>
                  <h2 className="text-lg font-semibold">By delivery month</h2>
                  {groups.map((group) => (
                    <div key={group.label ?? "unspecified"} className="mt-4">
                      <h3 className="text-sm font-semibold uppercase tracking-wide text-black/60">
                        {group.label ?? "Unspecified"}
                        {group.top_cash_price_bu != null
                          ? ` · top $${formatNumber(group.top_cash_price_bu)}/bu`
                          : ""}
                      </h3>
                      <div className="mt-2 space-y-3">
                        {(group.rows ?? []).map((row, idx) => (
                          <BidCard key={row.id ?? `${group.label}-${idx}`} row={row} />
                        ))}
                      </div>
                    </div>
                  ))}
                </section>
              ) : null}
              {bestBids.length > 0 ? (
                <section>
                  <h2 className="text-lg font-semibold">Best bids{grain ? ` — ${grain}` : ""}</h2>
                  <p className="mt-1 text-xs text-black/50">
                    Top cash bid per company, from the public best-bids endpoint.
                  </p>
                  <div className="mt-3 space-y-3">
                    {bestBids.map((row, idx) => (
                      <BidCard key={row.id ?? `${row.location}-${row.commodity_name}-${idx}`} row={row} />
                    ))}
                  </div>
                </section>
              ) : null}
            </>
          )}
        </div>
      ) : null}

      <p className="mt-8 text-xs text-black/45">
        Prototype note: searches and results are never sold to buyers. Confirm
        every bid with the buyer before hauling — prices change through the day.
      </p>
    </main>
  );
}
