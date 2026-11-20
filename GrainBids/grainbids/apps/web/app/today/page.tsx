import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

// ---------------------------------------------------------------------------
// Types (all fields optional — the page never assumes a shape the API
// did not actually return, and never invents a number).
// ---------------------------------------------------------------------------

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
};

type BasisRow = {
  id?: string | null;
  rank?: number | null;
  commodity?: string | null;
  commodity_name?: string | null;
  location?: string | null;
  delivery_label?: string | null;
  futures_month?: string | null;
  futures_price?: number | null;
  basis?: number | null;
  cash_price_bu?: number | null;
  quote_date?: string | null;
  captured_at?: string | null;
  source?: string | null;
  source_name?: string | null;
};

type CalendarEvent = {
  id?: string | null;
  report?: string | null;
  report_type?: string | null;
  title?: string | null;
  publisher?: string | null;
  release_at?: string | null;
  release_time_et?: string | null;
  scheduled_at?: string | null;
  next_release?: string | null;
  release_date?: string | null;
  frequency?: string | null;
  cadence?: string | null;
  description?: string | null;
  days_until?: number | null;
  is_past?: boolean | null;
  is_today?: boolean | null;
  source?: string | null;
  source_url?: string | null;
};

type FuturesStrip = {
  commodity?: string | null;
  exchange?: string | null;
  symbol_root?: string | null;
  unit?: string | null;
  currency?: string | null;
  contracts?: { id?: string | null; symbol?: string | null; contract?: string | null; contract_month?: string | null; price?: number | null; settle?: number | null; change?: number | null }[];
};

type SourceHealthCounts = {
  live?: number | null;
  stale?: number | null;
  broken?: number | null;
  unknown?: number | null;
  total?: number | null;
};

// ---------------------------------------------------------------------------
// Payload helpers (same defensive pattern as the other pages).
// ---------------------------------------------------------------------------

function arrayFrom(payload: unknown, keys: string[]): unknown[] {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    for (const key of keys) {
      if (Array.isArray(obj[key])) return obj[key] as unknown[];
    }
  }
  return [];
}

async function fetchBestBids(): Promise<BestBidRow[]> {
  try {
    const res = await fetch(`${API_BASE}/api/best-bids?limit=10`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return [];
    return arrayFrom(await res.json(), ["bids", "rows", "best_bids", "items"]) as BestBidRow[];
  } catch {
    return [];
  }
}

async function fetchBasis(): Promise<{ rows: BasisRow[]; note: string | null }> {
  try {
    const res = await fetch(`${API_BASE}/api/basis/tracker?commodity=corn`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return { rows: [], note: null };
    const payload = await res.json();
    const note =
      payload && typeof payload === "object" && typeof (payload as Record<string, unknown>).note === "string"
        ? ((payload as Record<string, unknown>).note as string)
        : null;
    return {
      rows: arrayFrom(payload, ["rows", "ranked", "tracker", "items"]) as BasisRow[],
      note,
    };
  } catch {
    return { rows: [], note: null };
  }
}

async function fetchCalendar(): Promise<CalendarEvent[]> {
  try {
    const res = await fetch(`${API_BASE}/api/research/calendar`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return [];
    return arrayFrom(await res.json(), ["events", "upcoming", "calendar", "rows", "items"]) as CalendarEvent[];
  } catch {
    return [];
  }
}

async function fetchFutures(): Promise<{
  strips: FuturesStrip[];
  delay: string | null;
  note: string | null;
  available: boolean | null;
}> {
  try {
    const res = await fetch(`${API_BASE}/api/futures/strip`, { cache: "no-store", headers });
    if (!res.ok) return { strips: [], delay: null, note: null, available: null };
    const payload = await res.json();
    const obj = payload && typeof payload === "object" && !Array.isArray(payload)
      ? (payload as Record<string, unknown>)
      : {};
    const strips: FuturesStrip[] = [];
    if (Array.isArray(payload)) {
      const first = payload[0] as Record<string, unknown> | undefined;
      if (first && Array.isArray(first.contracts)) {
        strips.push(...(payload as FuturesStrip[]));
      } else {
        strips.push({ contracts: payload as FuturesStrip["contracts"] });
      }
    } else {
      if (Array.isArray(obj.strips)) strips.push(...(obj.strips as FuturesStrip[]));
      else if (Array.isArray(obj.commodities)) strips.push(...(obj.commodities as FuturesStrip[]));
      else {
        strips.push({
          commodity: typeof obj.commodity === "string" ? obj.commodity : null,
          contracts: arrayFrom(payload, ["contracts", "rows", "strip", "items"]) as FuturesStrip["contracts"],
        });
      }
    }
    return {
      strips,
      delay:
        typeof obj.delay === "string"
          ? obj.delay
          : typeof obj.delay_label === "string"
            ? obj.delay_label
            : null,
      note: typeof obj.note === "string" ? obj.note : null,
      available: typeof obj.available === "boolean" ? obj.available : null,
    };
  } catch {
    return { strips: [], delay: null, note: null, available: null };
  }
}

async function fetchSourceHealth(): Promise<{ counts: SourceHealthCounts | null; generatedAt: string | null }> {
  try {
    const res = await fetch(`${API_BASE}/api/source-health/summary`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return { counts: null, generatedAt: null };
    const payload = await res.json();
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return { counts: null, generatedAt: null };
    }
    const obj = payload as Record<string, unknown>;
    const counts =
      obj.counts && typeof obj.counts === "object" && !Array.isArray(obj.counts)
        ? (obj.counts as SourceHealthCounts)
        : null;
    return {
      counts,
      generatedAt: typeof obj.generated_at === "string" ? obj.generated_at : null,
    };
  } catch {
    return { counts: null, generatedAt: null };
  }
}

// ---------------------------------------------------------------------------
// Formatting helpers.
// ---------------------------------------------------------------------------

function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(2);
}

function eventDate(event: CalendarEvent): Date | null {
  const raw =
    event.release_at ?? event.scheduled_at ?? event.next_release ?? event.release_date ?? null;
  if (!raw) return null;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function eventName(event: CalendarEvent): string {
  if (event.report) return event.report;
  if (event.title) return event.title;
  if (event.report_type) {
    return event.report_type
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }
  return "Report";
}

function countdownLabel(event: CalendarEvent): string {
  if (typeof event.days_until === "number") {
    if (event.is_today || event.days_until === 0) return "Today";
    if (event.days_until < 0) {
      const past = -event.days_until;
      return `Released ${past} day${past === 1 ? "" : "s"} ago`;
    }
    if (event.days_until === 1) return "Tomorrow";
    return `in ${event.days_until} days`;
  }
  const date = eventDate(event);
  if (!date) return "No date scheduled";
  const diffMs = date.getTime() - Date.now();
  if (diffMs < 0) {
    const pastDays = Math.floor(-diffMs / 86_400_000);
    return pastDays === 0 ? "Released today" : `Released ${pastDays} day${pastDays === 1 ? "" : "s"} ago`;
  }
  const days = Math.floor(diffMs / 86_400_000);
  const hours = Math.floor((diffMs % 86_400_000) / 3_600_000);
  if (days === 0) {
    if (hours === 0) return "Releasing within the hour";
    return `in ${hours} hour${hours === 1 ? "" : "s"}`;
  }
  return `in ${days} day${days === 1 ? "" : "s"}${hours > 0 ? ` ${hours}h` : ""}`;
}

function countOrDash(value: number | null | undefined): string {
  return typeof value === "number" ? String(value) : "-";
}

function SectionLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40"
    >
      {label}
    </Link>
  );
}

export default async function TodayPage() {
  const [bids, basis, calendarEvents, futures, sourceHealth] = await Promise.all([
    fetchBestBids(),
    fetchBasis(),
    fetchCalendar(),
    fetchFutures(),
    fetchSourceHealth(),
  ]);

  const todayLabel = new Date().toLocaleDateString("en-CA", {
    timeZone: "America/Toronto",
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  // Next report-calendar event: the soonest event that has not already passed.
  const sortedEvents = [...calendarEvents].sort((a, b) => {
    const da = eventDate(a)?.getTime();
    const db = eventDate(b)?.getTime();
    if (da == null && db == null) return 0;
    if (da == null) return 1;
    if (db == null) return -1;
    return da - db;
  });
  const nextEvent = sortedEvents.find((e) => {
    if (typeof e.days_until === "number") return e.days_until >= 0;
    const d = eventDate(e);
    return d != null && d.getTime() >= Date.now();
  });

  const basisRows = basis.rows.slice(0, 5);
  const futuresContracts = futures.strips.flatMap((s) => s.contracts ?? []);
  const counts = sourceHealth.counts;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainBids / Today</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Today
      </h1>
      <p className="mt-2 text-sm text-black/65">
        {todayLabel} — the morning view: the best bids, the corn basis snapshot, the
        next report release, the futures strip, and source health. Every section shows
        real API data only; an empty section means the data is not there yet, not
        that it is zero.
      </p>

      {/* Top best bids */}
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Top best bids</h2>
        {bids.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No best bids available yet. Best bids appear here once cash bids have been
            ingested — no prices are shown until a real source provides them.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Commodity</th>
                  <th className="px-2 py-2">Location</th>
                  <th className="px-2 py-2">Buyer</th>
                  <th className="px-2 py-2">Delivery</th>
                  <th className="px-2 py-2 text-right">Cash/bu</th>
                  <th className="px-2 py-2 text-right">Basis</th>
                  <th className="px-2 py-2">Captured</th>
                </tr>
              </thead>
              <tbody>
                {bids.map((row, idx) => (
                  <tr
                    key={row.id ?? `${row.location}-${row.commodity_name}-${row.delivery_label}-${idx}`}
                    className="border-b border-black/5"
                  >
                    <td className="px-2 py-2">{row.commodity_name ?? row.commodity ?? "-"}</td>
                    <td className="px-2 py-2">{row.location ?? "-"}</td>
                    <td className="px-2 py-2">{row.company_name ?? row.buyer ?? "-"}</td>
                    <td className="px-2 py-2">{row.delivery_label ?? row.delivery_month ?? "-"}</td>
                    <td className="px-2 py-2 text-right font-semibold">{formatNumber(row.cash_price_bu)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(row.basis)}</td>
                    <td className="px-2 py-2">{row.captured_at ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <SectionLink href="/best-bids" label="View all best bids" />
      </section>

      {/* Basis snapshot — corn */}
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Basis snapshot — corn</h2>
        {basisRows.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No corn basis data available yet. The basis tracker needs ingested cash
            bids — run an ingestion first. No numbers are shown until a real source
            provides them.
            {basis.note ? ` ${basis.note}` : ""}
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Rank</th>
                  <th className="px-2 py-2">Location</th>
                  <th className="px-2 py-2">Delivery</th>
                  <th className="px-2 py-2">Futures</th>
                  <th className="px-2 py-2 text-right">Futures price</th>
                  <th className="px-2 py-2 text-right">Basis</th>
                  <th className="px-2 py-2 text-right">Cash/bu</th>
                  <th className="px-2 py-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {basisRows.map((row, idx) => (
                  <tr
                    key={row.id ?? `${row.location}-${row.commodity_name}-${idx}`}
                    className="border-b border-black/5"
                  >
                    <td className="px-2 py-2">{row.rank ?? idx + 1}</td>
                    <td className="px-2 py-2">{row.location ?? "-"}</td>
                    <td className="px-2 py-2">{row.delivery_label ?? "-"}</td>
                    <td className="px-2 py-2">{row.futures_month ?? "-"}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(row.futures_price)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(row.basis)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(row.cash_price_bu)}</td>
                    <td className="px-2 py-2">{row.source ?? row.source_name ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <SectionLink href="/basis" label="Open the basis tracker" />
      </section>

      {/* Next report-calendar event */}
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Next report release</h2>
        {!nextEvent ? (
          <p className="mt-2 text-sm text-black/55">
            No upcoming report release on the calendar. The calendar is populated from
            the official USDA and CFTC release schedules — no dates are shown until a
            real schedule provides them.
          </p>
        ) : (
          <div className="mt-2 text-sm">
            <p className="text-base font-semibold">
              {nextEvent.source_url ? (
                <a href={nextEvent.source_url} target="_blank" rel="noreferrer" className="underline hover:text-black">
                  {eventName(nextEvent)}
                </a>
              ) : (
                eventName(nextEvent)
              )}
            </p>
            <p className="mt-1 text-black/65">
              {(() => {
                const date = eventDate(nextEvent);
                return date
                  ? date.toLocaleString("en-CA", { timeZone: "America/Toronto" })
                  : "No release date on record";
              })()}
              {nextEvent.release_time_et ? ` (${nextEvent.release_time_et})` : ""}
              {" · "}
              <span className="font-medium">{countdownLabel(nextEvent)}</span>
            </p>
            <p className="mt-1 text-black/55">
              {nextEvent.description ?? nextEvent.frequency ?? nextEvent.cadence ?? nextEvent.publisher ?? ""}
            </p>
          </div>
        )}
        <SectionLink href="/calendar" label="Open the report calendar" />
      </section>

      {/* Futures strip status */}
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Futures strip</h2>
        <p className="mt-2 text-sm text-black/65">
          Feed status:{" "}
          {futures.available === false
            ? "not wired — no licensed/delayed feed connected yet"
            : futures.available
              ? "live"
              : "unknown"}
          {futures.delay ? ` · Delay: ${futures.delay}` : ""}
        </p>
        {futures.note ? <p className="mt-2 text-sm text-black/55">{futures.note}</p> : null}
        {futuresContracts.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No futures data available yet. The strip is populated from a real futures
            feed once one is configured — no prices are shown until then.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Commodity</th>
                  <th className="px-2 py-2">Contract</th>
                  <th className="px-2 py-2 text-right">Price</th>
                  <th className="px-2 py-2 text-right">Settle</th>
                  <th className="px-2 py-2 text-right">Change</th>
                </tr>
              </thead>
              <tbody>
                {futures.strips.flatMap((strip, sIdx) =>
                  (strip.contracts ?? []).slice(0, 3).map((contract, cIdx) => (
                    <tr
                      key={`${strip.commodity ?? sIdx}-${contract.symbol ?? contract.contract ?? cIdx}`}
                      className="border-b border-black/5"
                    >
                      <td className="px-2 py-2">
                        {strip.commodity ?? "-"}
                        {strip.exchange ? ` · ${strip.exchange}` : ""}
                      </td>
                      <td className="px-2 py-2">{contract.contract ?? contract.contract_month ?? contract.symbol ?? "-"}</td>
                      <td className="px-2 py-2 text-right">{formatNumber(contract.price)}</td>
                      <td className="px-2 py-2 text-right">{formatNumber(contract.settle)}</td>
                      <td className="px-2 py-2 text-right">{formatNumber(contract.change)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        <SectionLink href="/futures" label="Open the futures strip" />
      </section>

      {/* Source-health summary */}
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Source health</h2>
        {counts == null ? (
          <p className="mt-2 text-sm text-black/55">
            No source health data available yet. The source-health endpoint reports on
            configured price sources once ingestion has run — no status is shown until
            a real run is recorded.
          </p>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-5">
            <div>
              <p className="text-xs uppercase tracking-wide text-black/50">Sources tracked</p>
              <p className="mt-1 text-2xl font-semibold">{countOrDash(counts.total)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-black/50">Live</p>
              <p className="mt-1 text-2xl font-semibold">{countOrDash(counts.live)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-black/50">Stale</p>
              <p className="mt-1 text-2xl font-semibold">{countOrDash(counts.stale)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-black/50">Broken</p>
              <p className="mt-1 text-2xl font-semibold">{countOrDash(counts.broken)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-black/50">Unknown</p>
              <p className="mt-1 text-2xl font-semibold">{countOrDash(counts.unknown)}</p>
            </div>
          </div>
        )}
        {sourceHealth.generatedAt ? (
          <p className="mt-2 text-xs text-black/50">Checked {sourceHealth.generatedAt}</p>
        ) : null}
        <SectionLink href="/source-health" label="Open source health" />
      </section>
    </main>
  );
}
