import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";
import { fetchResilient } from "@/lib/fetch-resilient";

const headers = buildApiHeaders();

// USDA FAS PSD commodity codes (the PSD catalogue's own identifiers;
// corn 0440000 verified live 2026-11-20).
const COMMODITIES = [
  { code: "0440000", label: "Corn" },
  { code: "2222000", label: "Soybeans" },
  { code: "0410000", label: "Wheat" },
];

type PsdRow = {
  metric?: string;
  value?: number | null;
  unit?: string;
  market_year?: string | number;
};

async function fetchWorld(code: string, year: string) {
  try {
    const res = await fetchResilient(
      `${API_BASE}/api/research/fas-psd/world?commodity_code=${code}&year=${year}`,
      { cache: "no-store", headers },
    );
    if (res.status === 503) return { rows: [] as PsdRow[], state: "key-required" as const };
    if (!res.ok) return { rows: [] as PsdRow[], state: "failed" as const };
    const json = await res.json();
    return {
      rows: (json.rows ?? []) as PsdRow[],
      state: "ok" as const,
      cache: json.cache as { state?: string; fetched_at?: string } | undefined,
    };
  } catch {
    return { rows: [] as PsdRow[], state: "failed" as const };
  }
}

export default async function PsdWorldPage({
  searchParams,
}: {
  searchParams: Promise<{ commodity_code?: string; year?: string }>;
}) {
  const params = await searchParams;
  const code = params.commodity_code || "0440000";
  const year = params.year || "2026";
  const active = COMMODITIES.find((c) => c.code === code);
  const data = await fetchWorld(code, year);
  const rows = data.rows ?? [];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">
        GrainBids / Research / World Supply &amp; Demand (PSD)
      </p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        World Supply &amp; Demand
      </h1>
      <p className="mt-2 text-sm text-black/65">
        World totals from USDA FAS Production, Supply &amp; Distribution — the same
        balance-sheet lines WASDE reports, for the world aggregate. Values are exactly
        as published; the API caches each table for 24 hours and labels its age below.
      </p>

      <nav className="mt-6 flex flex-wrap gap-2" aria-label="PSD commodity">
        {COMMODITIES.map((c) => (
          <Link
            key={c.code}
            href={`/research/psd?commodity_code=${c.code}&year=${year}`}
            className={`rounded-full border px-3 py-1 text-sm ${
              c.code === code
                ? "border-black bg-black text-white"
                : "border-black/20 text-black/70 hover:border-black/50"
            }`}
          >
            {c.label}
          </Link>
        ))}
      </nav>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">
          {active ? active.label : `Commodity ${code}`} — world, {year} marketing year
        </h2>
        {data.state === "key-required" ? (
          <p className="mt-2 text-sm text-black/55">
            The FAS PSD key is not configured on the API yet, so no data can be fetched.
            Nothing is shown rather than placeholder numbers.
          </p>
        ) : data.state === "failed" ? (
          <p className="mt-2 text-sm text-amber-900">
            Could not load PSD data — the API did not respond (it may be waking up; free
            tier first load can take up to a minute).{" "}
            <Link
              href={`/research/psd?commodity_code=${code}&year=${year}`}
              className="font-medium underline"
            >
              Retry
            </Link>
          </p>
        ) : rows.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            USDA returned no world rows for this commodity and year. No numbers are
            shown until a real source provides them.
          </p>
        ) : (
          <>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-black/10 text-black/55">
                    <th className="py-2 pr-4 font-medium">Metric</th>
                    <th className="py-2 pr-4 font-medium">Value</th>
                    <th className="py-2 font-medium">Unit</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} className="border-b border-black/5">
                      <td className="py-2 pr-4">{row.metric ?? "—"}</td>
                      <td className="py-2 pr-4 tabular-nums">
                        {row.value == null ? "—" : row.value.toLocaleString("en-US")}
                      </td>
                      <td className="py-2">{row.unit ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.cache ? (
              <p className="mt-3 text-xs text-black/50">
                Source: USDA FAS PSD · cache: {data.cache.state ?? "—"}
                {data.cache.fetched_at
                  ? ` · fetched ${new Date(data.cache.fetched_at).toLocaleString("en-US")}`
                  : ""}
              </p>
            ) : null}
          </>
        )}
      </section>
    </main>
  );
}
