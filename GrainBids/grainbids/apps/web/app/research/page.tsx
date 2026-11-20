import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

type ResearchReport = {
  id: string;
  report_type: string;
  commodity: string;
  report_date: string;
  vintage?: string | null;
  source: string;
  source_url?: string | null;
  delay_label?: string | null;
  payload?: { values?: Array<Record<string, unknown>> };
};

async function fetchReports(reportType: string) {
  try {
    const res = await fetch(`${API_BASE}/api/research/reports?report_type=${reportType}&limit=50`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return { reports: [], count: 0 };
    return await res.json();
  } catch {
    return { reports: [], count: 0 };
  }
}

async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/research/status`, { cache: "no-store", headers });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function ReportTable({ reports }: { reports: ResearchReport[] }) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
            <th className="px-2 py-2">Commodity</th>
            <th className="px-2 py-2">Report date</th>
            <th className="px-2 py-2">Values</th>
            <th className="px-2 py-2">Source</th>
            <th className="px-2 py-2">Vintage</th>
            <th className="px-2 py-2">Delay</th>
          </tr>
        </thead>
        <tbody>
          {reports.length === 0 ? (
            <tr>
              <td className="px-2 py-4 text-black/55" colSpan={6}>
                No data ingested yet. Research data appears here only after a public USDA file
                is ingested or a free NASS / FAS key is configured — nothing is invented.
              </td>
            </tr>
          ) : (
            reports.map((row) => {
              const values = row.payload?.values ?? [];
              const summary = values
                .map((v) => `${v.commodity} ${v.metric}: ${v.value} ${v.unit ?? ""}`)
                .join("; ");
              return (
                <tr key={row.id} className="border-b border-black/5">
                  <td className="px-2 py-2">{row.commodity}</td>
                  <td className="px-2 py-2">{row.report_date}</td>
                  <td className="px-2 py-2">{summary || "No values parsed from the file"}</td>
                  <td className="px-2 py-2">{row.source}</td>
                  <td className="px-2 py-2">{row.vintage ?? "-"}</td>
                  <td className="px-2 py-2">{row.delay_label ?? "-"}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

export default async function ResearchIndexPage() {
  const [status, wasde, cropProgress, grainStocks, exportSales, commitments] = await Promise.all([
    fetchStatus(),
    fetchReports("wasde"),
    fetchReports("crop_progress"),
    fetchReports("grain_stocks"),
    fetchReports("export_sales"),
    fetchReports("commitments_of_traders"),
  ]);
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainBids / Research</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        USDA Research
      </h1>
      <p className="mt-2 text-sm text-black/65">
        Official reports, by report and by commodity. Every number carries its source, vintage
        and delay. NASS Quick Stats: {status?.nass_configured ? "key configured" : "key required"}.
        FAS PSD: {status?.fas_configured ? "key configured" : "key required"}.
      </p>
      <section className="mt-8 grid gap-4 md:grid-cols-2">
        <Link href="/research/wasde" className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur hover:border-black/40">
          <h2 className="text-lg font-semibold">WASDE — Supply &amp; Demand</h2>
          <p className="mt-1 text-sm text-black/65">Monthly, ~10th, noon ET. US + world ending stocks.</p>
          <p className="mt-2 text-sm">{wasde.count} report(s) ingested</p>
        </Link>
        <Link href="/research/crop-progress" className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur hover:border-black/40">
          <h2 className="text-lg font-semibold">Crop Progress</h2>
          <p className="mt-1 text-sm text-black/65">Weekly, Mondays 4pm ET. Planting / harvest progress and conditions.</p>
          <p className="mt-2 text-sm">{cropProgress.count} report(s) ingested</p>
        </Link>
        <Link href="/research/grain-stocks" className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur hover:border-black/40">
          <h2 className="text-lg font-semibold">Grain Stocks</h2>
          <p className="mt-1 text-sm text-black/65">Quarterly, from USDA NASS. Actual grain in bins — the physical count.</p>
          <p className="mt-2 text-sm">{grainStocks.count} report(s) ingested · value parser not built yet</p>
        </Link>
        <Link href="/research/export-sales" className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur hover:border-black/40">
          <h2 className="text-lg font-semibold">Export Sales</h2>
          <p className="mt-1 text-sm text-black/65">Weekly, Thursdays 8:30am ET, USDA FAS. Sales and shipments by destination.</p>
          <p className="mt-2 text-sm">{exportSales.count} report(s) ingested · value parser not built yet</p>
        </Link>
        <Link href="/research/commitments-of-traders" className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur hover:border-black/40">
          <h2 className="text-lg font-semibold">Commitments of Traders</h2>
          <p className="mt-1 text-sm text-black/65">Weekly, Fridays 3:30pm ET, CFTC. Trader positioning in CBOT futures.</p>
          <p className="mt-2 text-sm">{commitments.count} report(s) ingested · value parser not built yet</p>
        </Link>
      </section>
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Latest WASDE</h2>
        <ReportTable reports={wasde.reports} />
      </section>
      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">Latest Crop Progress</h2>
        <ReportTable reports={cropProgress.reports} />
      </section>
    </main>
  );
}
