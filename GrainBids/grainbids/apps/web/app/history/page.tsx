import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

const COMMODITIES = ["Corn", "Soybeans", "Wheat", "Oats", "Barley", "Canola"];
const DEFAULT_COMMODITY = "Corn";
const DEFAULT_DAYS = 90;

// Six distinguishable line colours; a seventh location reuses the
// palette from the start and is still named in the legend.
const LINE_COLORS = ["#1d4ed8", "#b45309", "#15803d", "#be185d", "#6d28d9", "#0f766e"];
const MAX_CHART_SERIES = 6;

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

type SeasonalPoint = {
  week?: number | null;
  month?: number | null;
  average_cash_price_bu?: number | null;
  years?: number[] | null;
  yearly_averages?: Record<string, number> | null;
  observations?: number | null;
};

type SeasonalPayload = {
  points: SeasonalPoint[];
  years: number[];
  years_covered: number;
  years_requested: number;
  note?: string | null;
};

function historyFrom(payload: unknown): HistoryPoint[] {
  if (Array.isArray(payload)) return payload as HistoryPoint[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.points)) return obj.points as HistoryPoint[];
    if (Array.isArray(obj.history)) return obj.history as HistoryPoint[];
    if (Array.isArray(obj.rows)) return obj.rows as HistoryPoint[];
    if (Array.isArray(obj.items)) return obj.items as HistoryPoint[];
  }
  return [];
}

function seasonalFrom(payload: unknown): SeasonalPayload {
  const empty: SeasonalPayload = { points: [], years: [], years_covered: 0, years_requested: 5 };
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    const points = Array.isArray(obj.points) ? (obj.points as SeasonalPoint[]) : [];
    return {
      points,
      years: Array.isArray(obj.years) ? (obj.years as number[]) : [],
      years_covered: typeof obj.years_covered === "number" ? obj.years_covered : 0,
      years_requested: typeof obj.years_requested === "number" ? obj.years_requested : 5,
      note: typeof obj.note === "string" ? obj.note : null,
    };
  }
  return empty;
}

async function fetchHistory(commodity: string, days: number) {
  try {
    const params = new URLSearchParams({
      commodity,
      days: String(days),
    });
    const res = await fetch(`${API_BASE}/api/prices/history?${params}`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return [];
    return historyFrom(await res.json());
  } catch {
    return [];
  }
}

async function fetchSeasonal(commodity: string) {
  try {
    const params = new URLSearchParams({ commodity });
    const res = await fetch(`${API_BASE}/api/prices/seasonal?${params}`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return seasonalFrom(null);
    return seasonalFrom(await res.json());
  } catch {
    return seasonalFrom(null);
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(2);
}

function monthName(month: number | null | undefined): string {
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  if (month == null || month < 1 || month > 12) return "-";
  return names[month - 1];
}

// ---------------------------------------------------------------------------
// Minimal SVG line charts. Pure functions over the API data: no chart
// library, no invented points. A series is one location (history) or
// the ISO-week seasonal average (seasonal). Weeks / dates with no data
// simply have no point — nothing is interpolated.
// ---------------------------------------------------------------------------

type ChartPoint = { x: number; y: number; label: string };

function niceBounds(values: number[]): { min: number; max: number } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return { min: min - 1, max: max + 1 };
  const pad = (max - min) * 0.1;
  return { min: min - pad, max: max + pad };
}

function LineChart({
  series,
  xMin,
  xMax,
  xTicks,
  yLabel,
  ariaLabel,
}: {
  series: { name: string; color: string; points: ChartPoint[] }[];
  xMin: number;
  xMax: number;
  xTicks: { x: number; label: string }[];
  yLabel: string;
  ariaLabel: string;
}) {
  const width = 640;
  const height = 260;
  const padLeft = 52;
  const padRight = 12;
  const padTop = 12;
  const padBottom = 30;
  const allY = series.flatMap((s) => s.points.map((p) => p.y));
  if (allY.length === 0) return null;
  const { min, max } = niceBounds(allY);
  const xScale = (x: number) =>
    padLeft + ((x - xMin) / Math.max(1, xMax - xMin)) * (width - padLeft - padRight);
  const yScale = (y: number) =>
    padTop + (1 - (y - min) / (max - min)) * (height - padTop - padBottom);
  const mid = (min + max) / 2;
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="mt-4 w-full"
      role="img"
      aria-label={ariaLabel}
    >
      {[min, mid, max].map((value) => (
        <g key={value}>
          <line
            x1={padLeft}
            x2={width - padRight}
            y1={yScale(value)}
            y2={yScale(value)}
            stroke="#00000014"
            strokeWidth="1"
          />
          <text x={padLeft - 6} y={yScale(value) + 4} textAnchor="end" fontSize="11" fill="#0000008c">
            {value.toFixed(2)}
          </text>
        </g>
      ))}
      {xTicks.map((tick) => (
        <text
          key={`${tick.x}-${tick.label}`}
          x={xScale(tick.x)}
          y={height - 8}
          textAnchor="middle"
          fontSize="11"
          fill="#0000008c"
        >
          {tick.label}
        </text>
      ))}
      <text x={padLeft} y={padTop - 2} fontSize="11" fill="#0000008c">
        {yLabel}
      </text>
      {series.map((s) => (
        <g key={s.name}>
          <polyline
            points={s.points.map((p) => `${xScale(p.x).toFixed(1)},${yScale(p.y).toFixed(1)}`).join(" ")}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          {s.points.map((p) => (
            <circle key={p.label} cx={xScale(p.x)} cy={yScale(p.y)} r="3" fill={s.color}>
              <title>{`${s.name}: ${p.label}`}</title>
            </circle>
          ))}
        </g>
      ))}
    </svg>
  );
}

function historySeries(points: HistoryPoint[]): {
  series: { name: string; color: string; points: ChartPoint[] }[];
  hiddenCount: number;
  xMin: number;
  xMax: number;
  xTicks: { x: number; label: string }[];
} {
  // One series per location; one point per location per day (the latest
  // quote that day), so a day with several quotes does not zig-zag.
  const byLocation = new Map<string, Map<string, HistoryPoint>>();
  for (const point of points) {
    const date = point.date ?? point.quote_date?.slice(0, 10) ?? null;
    const price = point.cash_price_bu;
    if (!date || price == null || Number.isNaN(price)) continue;
    const name = point.location ?? point.company_name ?? "Unknown location";
    let days = byLocation.get(name);
    if (!days) {
      days = new Map();
      byLocation.set(name, days);
    }
    const existing = days.get(date);
    const quote = point.quote_date ?? point.captured_at ?? "";
    if (!existing || (quote && quote >= (existing.quote_date ?? existing.captured_at ?? ""))) {
      days.set(date, point);
    }
  }
  const ordered = [...byLocation.entries()].sort((a, b) => b[1].size - a[1].size);
  const shown = ordered.slice(0, MAX_CHART_SERIES);
  const series = shown.map(([name, days], idx) => {
    const sorted = [...days.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return {
      name,
      color: LINE_COLORS[idx % LINE_COLORS.length],
      points: sorted.map(([date, point]) => ({
        x: new Date(`${date}T12:00:00Z`).getTime(),
        y: point.cash_price_bu as number,
        label: `${date} — $${formatNumber(point.cash_price_bu)}/bu`,
      })),
    };
  });
  const allX = series.flatMap((s) => s.points.map((p) => p.x));
  const xMin = allX.length ? Math.min(...allX) : 0;
  const xMax = allX.length ? Math.max(...allX) : 1;
  const firstDate = allX.length ? new Date(Math.min(...allX)).toISOString().slice(0, 10) : "";
  const lastDate = allX.length ? new Date(Math.max(...allX)).toISOString().slice(0, 10) : "";
  return {
    series,
    hiddenCount: Math.max(0, ordered.length - shown.length),
    xMin,
    xMax,
    xTicks:
      allX.length === 0
        ? []
        : [
            { x: xMin, label: firstDate },
            { x: xMax, label: lastDate },
          ],
  };
}

function seasonalSeries(points: SeasonalPoint[]): {
  series: { name: string; color: string; points: ChartPoint[] }[];
} {
  const plotted = points
    .filter((p) => p.week != null && p.average_cash_price_bu != null)
    .sort((a, b) => (a.week as number) - (b.week as number));
  return {
    series: [
      {
        name: "Seasonal average",
        color: LINE_COLORS[0],
        points: plotted.map((p) => ({
          x: p.week as number,
          y: p.average_cash_price_bu as number,
          label: `Week ${p.week} — $${formatNumber(p.average_cash_price_bu)}/bu`,
        })),
      },
    ],
  };
}

const SEASONAL_X_TICKS = [
  { x: 1, label: "Jan" },
  { x: 14, label: "Apr" },
  { x: 27, label: "Jul" },
  { x: 40, label: "Oct" },
  { x: 52, label: "Dec" },
];

export default async function HistoryPage({
  searchParams,
}: {
  searchParams?: { commodity?: string; days?: string };
}) {
  const commodity = (searchParams?.commodity || DEFAULT_COMMODITY).trim() || DEFAULT_COMMODITY;
  const daysRaw = Number(searchParams?.days ?? DEFAULT_DAYS);
  const days = Number.isFinite(daysRaw) ? Math.min(1825, Math.max(1, Math.floor(daysRaw))) : DEFAULT_DAYS;
  const [history, seasonal] = await Promise.all([fetchHistory(commodity, days), fetchSeasonal(commodity)]);
  const historyChart = historySeries(history);
  const seasonalChart = seasonalSeries(seasonal.points);
  const seasonalEmpty = seasonalChart.series[0].points.length === 0;
  const historyEmpty = historyChart.series.length === 0;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / History</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Price History
      </h1>
      <p className="mt-2 text-sm text-black/65">
        Cash prices over time, and how each week of the year usually prices against its
        seasonal average. Averages are computed only from real ingested prices — a week
        with no history shows no average, never a guessed one.
      </p>

      <nav className="mt-6 flex flex-wrap gap-2" aria-label="Commodity">
        {COMMODITIES.map((grain) => (
          <Link
            key={grain}
            href={`/history?commodity=${encodeURIComponent(grain)}&days=${days}`}
            className={`rounded-full border px-3 py-1 text-sm ${
              grain.toLowerCase() === commodity.toLowerCase()
                ? "border-black/60 bg-black text-white"
                : "border-black/20 bg-white/80 hover:border-black/40"
            }`}
          >
            {grain}
          </Link>
        ))}
      </nav>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">
          Price history — {commodity} (last {days} days)
        </h2>
        {historyEmpty ? (
          <p className="mt-2 text-sm text-black/55">
            No price history available yet for {commodity}. History accumulates as ingestion
            runs — nothing is backfilled or estimated.
          </p>
        ) : (
          <>
            <LineChart
              series={historyChart.series}
              xMin={historyChart.xMin}
              xMax={historyChart.xMax}
              xTicks={historyChart.xTicks}
              yLabel="$/bu"
              ariaLabel={`Cash price per bushel over time for ${commodity}`}
            />
            <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-black/65">
              {historyChart.series.map((s) => (
                <li key={s.name}>
                  <span
                    className="mr-1 inline-block h-2.5 w-2.5 rounded-full align-middle"
                    style={{ backgroundColor: s.color }}
                  />
                  {s.name} ({s.points.length} days)
                </li>
              ))}
              {historyChart.hiddenCount > 0 && (
                <li>+{historyChart.hiddenCount} more location(s) in the table below</li>
              )}
            </ul>
            <p className="mt-2 text-xs text-black/50">
              One point per location per day (latest quote that day). Currency is not stored
              on normalized prices, so no currency is assumed.
            </p>
          </>
        )}
        {history.length === 0 ? null : (
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
        <h2 className="text-lg font-semibold">Seasonal averages — {commodity}</h2>
        {seasonalEmpty ? (
          <p className="mt-2 text-sm text-black/55">
            No seasonal averages yet for {commodity}. Averages need real ingested prices
            for a week of the year — until then the chart and table stay empty rather than
            showing a guessed average.
          </p>
        ) : (
          <>
            <LineChart
              series={seasonalChart.series}
              xMin={1}
              xMax={52}
              xTicks={SEASONAL_X_TICKS}
              yLabel="$/bu (seasonal avg)"
              ariaLabel={`Seasonal average cash price by ISO week for ${commodity}`}
            />
            <p className="mt-2 text-xs text-black/50">
              Average cash price by ISO week, averaged across the {seasonal.years_covered}{" "}
              year(s) actually present
              {seasonal.years.length > 0 ? ` (${seasonal.years.join(", ")})` : ""} — at most{" "}
              {seasonal.years_requested}. A year with many quotes does not outweigh a year
              with few; missing years are not invented or interpolated.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                    <th className="px-2 py-2">ISO week</th>
                    <th className="px-2 py-2">Month</th>
                    <th className="px-2 py-2 text-right">Seasonal average ($/bu)</th>
                    <th className="px-2 py-2 text-right">Years in avg</th>
                    <th className="px-2 py-2 text-right">Observations</th>
                  </tr>
                </thead>
                <tbody>
                  {seasonal.points.map((row, idx) => (
                    <tr key={`${row.week}-${idx}`} className="border-b border-black/5">
                      <td className="px-2 py-2">{row.week ?? "-"}</td>
                      <td className="px-2 py-2">{monthName(row.month)}</td>
                      <td className="px-2 py-2 text-right">{formatNumber(row.average_cash_price_bu)}</td>
                      <td className="px-2 py-2 text-right">
                        {row.years && row.years.length > 0 ? row.years.join(", ") : "-"}
                      </td>
                      <td className="px-2 py-2 text-right">{row.observations ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <Link href="/bids" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
          Back to market
        </Link>
      </section>
    </main>
  );
}
