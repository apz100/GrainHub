import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";
import { fetchResilient } from "@/lib/fetch-resilient";

const headers = buildApiHeaders();

async function fetchWasde() {
  try {
    const res = await fetchResilient(`${API_BASE}/api/research/wasde?limit=50`, { cache: "no-store", headers });
    if (!res.ok) return { reports: [], count: 0, failed: true };
    const json = await res.json();
    return { ...json, failed: false };
  } catch {
    return { reports: [], count: 0, failed: true };
  }
}

export default async function WasdePage() {
  const data = await fetchWasde();
  const reports = data.reports ?? [];
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainBids / Research / WASDE</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        WASDE — World Agricultural Supply &amp; Demand
      </h1>
      <p className="mt-2 text-sm text-black/65">
        Monthly, around the 10th at noon ET, from the USDA World Agricultural Outlook Board.
        US + world supply, demand and ending stocks for corn, soybeans, wheat and more.
      </p>
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Ending stocks (as published)</h2>
        {data.failed ? (
          <p className="mt-2 text-sm text-amber-900">
            Could not load WASDE data — the API did not respond (it may be waking up; free
            tier first load can take up to a minute).{" "}
            <Link href="/research/wasde" className="font-medium underline">
              Retry
            </Link>
          </p>
        ) : reports.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No WASDE data ingested yet. Ingest a public WASDE file via the research API, or
            configure a free NASS key — no numbers are shown until a real source provides them.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Commodity</th>
                  <th className="px-2 py-2">Report date</th>
                  <th className="px-2 py-2">Values</th>
                  <th className="px-2 py-2">Source</th>
                  <th className="px-2 py-2">Vintage</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((row: any) => (
                  <tr key={row.id} className="border-b border-black/5">
                    <td className="px-2 py-2">{row.commodity}</td>
                    <td className="px-2 py-2">{row.report_date}</td>
                    <td className="px-2 py-2">
                      {(row.payload?.values ?? [])
                        .map((v: any) => `${v.metric}: ${v.value} ${v.unit ?? ""}`)
                        .join("; ") || "No values parsed from the file"}
                    </td>
                    <td className="px-2 py-2">{row.source}</td>
                    <td className="px-2 py-2">{row.vintage ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Link href="/research" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
          Back to research
        </Link>
      </section>
    </main>
  );
}
