import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

type FuturesContract = {
  id?: string | null;
  symbol?: string | null;
  commodity?: string | null;
  commodity_name?: string | null;
  contract?: string | null;
  contract_month?: string | null;
  month?: string | null;
  month_code?: string | null;
  year?: number | null;
  exchange?: string | null;
  price?: number | null;
  settle?: number | null;
  change?: number | null;
  open_interest?: number | null;
  volume?: number | null;
  delay_label?: string | null;
  source?: string | null;
  as_of?: string | null;
};

type FuturesStrip = {
  commodity?: string | null;
  exchange?: string | null;
  symbol_root?: string | null;
  unit?: string | null;
  currency?: string | null;
  contracts?: FuturesContract[];
};

function contractsFrom(payload: unknown): FuturesContract[] {
  if (Array.isArray(payload)) return payload as FuturesContract[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.contracts)) return obj.contracts as FuturesContract[];
    if (Array.isArray(obj.rows)) return obj.rows as FuturesContract[];
    if (Array.isArray(obj.strip)) return obj.strip as FuturesContract[];
    if (Array.isArray(obj.items)) return obj.items as FuturesContract[];
  }
  return [];
}

function stripsFrom(payload: unknown): FuturesStrip[] {
  if (Array.isArray(payload)) {
    // Either a flat contract list or a list of per-commodity strips.
    const first = payload[0] as Record<string, unknown> | undefined;
    if (first && Array.isArray(first.contracts)) return payload as FuturesStrip[];
    return [{ contracts: payload as FuturesContract[] }];
  }
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.strips)) return obj.strips as FuturesStrip[];
    if (Array.isArray(obj.commodities)) return obj.commodities as FuturesStrip[];
    return [{ commodity: typeof obj.commodity === "string" ? obj.commodity : null, contracts: contractsFrom(payload) }];
  }
  return [];
}

function feedMeta(payload: unknown): { delay: string | null; note: string | null; available: boolean | null } {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { delay: null, note: null, available: null };
  }
  const obj = payload as Record<string, unknown>;
  return {
    delay:
      typeof obj.delay === "string"
        ? obj.delay
        : typeof obj.delay_label === "string"
          ? obj.delay_label
          : null,
    note: typeof obj.note === "string" ? obj.note : null,
    available: typeof obj.available === "boolean" ? obj.available : null,
  };
}

async function fetchStrip() {
  try {
    const res = await fetch(`${API_BASE}/api/futures/strip`, { cache: "no-store", headers });
    if (!res.ok) return { strips: [] as FuturesStrip[], delay: null as string | null, note: null as string | null, available: null as boolean | null };
    const payload = await res.json();
    const meta = feedMeta(payload);
    return { strips: stripsFrom(payload), delay: meta.delay, note: meta.note, available: meta.available };
  } catch {
    return { strips: [] as FuturesStrip[], delay: null as string | null, note: null as string | null, available: null as boolean | null };
  }
}

async function fetchCanola() {
  try {
    const res = await fetch(`${API_BASE}/api/futures/canola`, { cache: "no-store", headers });
    if (!res.ok) return { contracts: [] as FuturesContract[], delay: null as string | null, note: null as string | null, available: null as boolean | null, desk: null as string | null, unit: null as string | null, currency: null as string | null };
    const payload = await res.json();
    const meta = feedMeta(payload);
    const obj = payload as Record<string, unknown>;
    return {
      contracts: contractsFrom(payload),
      delay: meta.delay,
      note: meta.note,
      available: meta.available,
      desk: typeof obj.desk === "string" ? obj.desk : null,
      unit: typeof obj.unit === "string" ? obj.unit : null,
      currency: typeof obj.currency === "string" ? obj.currency : null,
    };
  } catch {
    return { contracts: [] as FuturesContract[], delay: null as string | null, note: null as string | null, available: null as boolean | null, desk: null as string | null, unit: null as string | null, currency: null as string | null };
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

function toneForDelta(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value) || value === 0) return "text-black/70";
  return value > 0 ? "text-emerald-700" : "text-rose-700";
}

function ContractTable({ contracts }: { contracts: FuturesContract[] }) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
            <th className="px-2 py-2">Symbol</th>
            <th className="px-2 py-2">Contract month</th>
            <th className="px-2 py-2">Commodity</th>
            <th className="px-2 py-2 text-right">Price</th>
            <th className="px-2 py-2 text-right">Settle</th>
            <th className="px-2 py-2 text-right">Change</th>
            <th className="px-2 py-2 text-right">Open interest</th>
          </tr>
        </thead>
        <tbody>
          {contracts.map((row, idx) => (
            <tr key={row.id ?? `${row.symbol ?? row.contract ?? row.contract_month}-${idx}`} className="border-b border-black/5">
              <td className="px-2 py-2">{row.symbol ?? "-"}</td>
              <td className="px-2 py-2">{row.contract ?? row.contract_month ?? row.month ?? "-"}</td>
              <td className="px-2 py-2">{row.commodity_name ?? row.commodity ?? "-"}</td>
              <td className="px-2 py-2 text-right">{formatNumber(row.price)}</td>
              <td className="px-2 py-2 text-right">{formatNumber(row.settle)}</td>
              <td className={`px-2 py-2 text-right ${toneForDelta(row.change)}`}>{formatSigned(row.change)}</td>
              <td className="px-2 py-2 text-right">
                {row.open_interest == null ? "-" : row.open_interest.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function FuturesPage() {
  const [strip, canola] = await Promise.all([fetchStrip(), fetchCanola()]);
  const stripContracts = strip.strips.flatMap((s) => s.contracts ?? []);
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainBids / Futures</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Futures Strip
      </h1>
      <p className="mt-2 text-sm text-black/65">
        CBOT corn, soybeans and wheat plus the ICE canola desk. Every quote carries its
        delay label and source — free futures data is delayed, and this page says so
        instead of pretending it is live.
      </p>
      <p className="mt-2 rounded-md border border-amber-700/20 bg-amber-100 px-3 py-2 text-sm text-amber-900">
        Feed status: {strip.available === false ? "not wired — no licensed/delayed feed connected yet" : strip.available ? "live" : "unknown"}
        {strip.delay ? ` · Delay: ${strip.delay}` : ""}
      </p>
      {strip.note ? <p className="mt-2 text-sm text-black/55">{strip.note}</p> : null}

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Futures strip</h2>
        {stripContracts.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No futures data available yet. The strip is populated from a real futures feed
            once one is configured — no prices are shown until then.
          </p>
        ) : (
          strip.strips.map((s, idx) => (
            <div key={s.commodity ?? `strip-${idx}`} className="mt-4">
              <h3 className="text-sm font-semibold">
                {s.commodity ?? "Commodity"}
                {s.exchange ? ` · ${s.exchange}` : ""}
                {s.unit ? ` · ${s.unit}` : ""}
                {s.currency ? ` · ${s.currency}` : ""}
              </h3>
              <ContractTable contracts={s.contracts ?? []} />
            </div>
          ))
        )}
      </section>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">{canola.desk ?? "Canola desk"}</h2>
        <p className="mt-1 text-sm text-black/65">
          ICE canola futures, quoted in Canadian dollars per tonne.
          {canola.unit ? ` Unit: ${canola.unit}.` : ""}
          {canola.currency ? ` Currency: ${canola.currency}.` : ""}
          {canola.delay ? ` Delay: ${canola.delay}.` : ""}
          {canola.available === false ? " Feed not wired — prices are null until a feed is connected." : ""}
        </p>
        {canola.note ? <p className="mt-2 text-sm text-black/55">{canola.note}</p> : null}
        {canola.contracts.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No canola futures data available yet. The canola desk is populated from a real
            futures feed once one is configured — no prices are shown until then.
          </p>
        ) : (
          <ContractTable contracts={canola.contracts} />
        )}
        <Link href="/basis" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
          Basis tracker
        </Link>
      </section>
    </main>
  );
}
