import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

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
  delay_label?: string | null;
};

function eventsFrom(payload: unknown): CalendarEvent[] {
  if (Array.isArray(payload)) return payload as CalendarEvent[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (Array.isArray(obj.events)) return obj.events as CalendarEvent[];
    if (Array.isArray(obj.upcoming)) return obj.upcoming as CalendarEvent[];
    if (Array.isArray(obj.calendar)) return obj.calendar as CalendarEvent[];
    if (Array.isArray(obj.rows)) return obj.rows as CalendarEvent[];
    if (Array.isArray(obj.items)) return obj.items as CalendarEvent[];
  }
  return [];
}

async function fetchCalendar() {
  try {
    const res = await fetch(`${API_BASE}/api/research/calendar`, { cache: "no-store", headers });
    if (!res.ok) return { events: [] as CalendarEvent[], source: null as string | null, schedule: null as string | null };
    const payload = await res.json();
    const obj = payload as Record<string, unknown>;
    return {
      events: eventsFrom(payload),
      source: typeof obj.source === "string" ? obj.source : null,
      schedule: typeof obj.schedule === "string" ? obj.schedule : null,
    };
  } catch {
    return { events: [] as CalendarEvent[], source: null as string | null, schedule: null as string | null };
  }
}

function eventDate(event: CalendarEvent): Date | null {
  const raw = event.release_at ?? event.scheduled_at ?? event.next_release ?? event.release_date ?? null;
  if (!raw) return null;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function countdownLabel(event: CalendarEvent): string {
  // Prefer the server-computed countdown when the API provides it.
  if (typeof event.days_until === "number") {
    if (event.is_today) return "Today";
    if (event.days_until < 0) {
      const past = -event.days_until;
      return `Released ${past} day${past === 1 ? "" : "s"} ago`;
    }
    if (event.days_until === 0) return "Today";
    if (event.days_until === 1) return "Tomorrow";
    return `in ${event.days_until} days`;
  }
  const date = eventDate(event);
  if (!date) return "No date scheduled";
  const now = Date.now();
  const diffMs = date.getTime() - now;
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

function eventName(event: CalendarEvent): string {
  return event.report ?? event.title ?? prettyReportType(event.report_type);
}

function prettyReportType(reportType: string | null | undefined): string {
  if (!reportType) return "Report";
  return reportType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default async function CalendarPage() {
  const { events, source, schedule } = await fetchCalendar();
  const sorted = [...events].sort((a, b) => {
    const da = eventDate(a)?.getTime();
    const db = eventDate(b)?.getTime();
    if (da == null && db == null) return 0;
    if (da == null) return 1;
    if (db == null) return -1;
    return da - db;
  });
  const upcoming = sorted.filter((e) => {
    if (typeof e.days_until === "number") return e.days_until >= 0;
    const d = eventDate(e);
    return d != null && d.getTime() >= Date.now();
  });
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / Research / Calendar</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Report Calendar
      </h1>
      <p className="mt-2 text-sm text-black/65">
        When the reports that move grain markets are released — WASDE, Crop Progress,
        Grain Stocks, Export Sales, Commitments of Traders — with a countdown to each
        release. Dates come from the USDA / CFTC release schedules, not from memory.
        {schedule ? ` ${schedule}.` : ""}
        {source ? ` Source: ${source}.` : ""}
      </p>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">
          Upcoming releases {upcoming.length > 0 ? `(${upcoming.length})` : ""}
        </h2>
        {sorted.length === 0 ? (
          <p className="mt-2 text-sm text-black/55">
            No release calendar data available yet. The calendar is populated from the
            official USDA and CFTC release schedules once the research calendar endpoint
            is wired up — no dates are shown until a real schedule provides them.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/10 text-xs uppercase tracking-wide text-black/50">
                  <th className="px-2 py-2">Report</th>
                  <th className="px-2 py-2">Release</th>
                  <th className="px-2 py-2">Countdown</th>
                  <th className="px-2 py-2">Frequency</th>
                  <th className="px-2 py-2">Publisher</th>
                  <th className="px-2 py-2">What it is</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((event, idx) => {
                  const date = eventDate(event);
                  return (
                    <tr key={event.id ?? `${event.report ?? event.report_type}-${event.release_at ?? idx}-${idx}`} className="border-b border-black/5">
                      <td className="px-2 py-2">
                        {event.source_url ? (
                          <a href={event.source_url} target="_blank" rel="noreferrer" className="underline hover:text-black">
                            {eventName(event)}
                          </a>
                        ) : (
                          eventName(event)
                        )}
                      </td>
                      <td className="px-2 py-2">
                        {date ? date.toLocaleString("en-CA", { timeZone: "America/Toronto" }) : "-"}
                        {event.release_time_et ? ` (${event.release_time_et})` : ""}
                      </td>
                      <td className="px-2 py-2 font-medium">{countdownLabel(event)}</td>
                      <td className="px-2 py-2">{event.frequency ?? event.cadence ?? "-"}</td>
                      <td className="px-2 py-2">{event.publisher ?? event.source ?? "-"}</td>
                      <td className="px-2 py-2">{event.description ?? event.delay_label ?? "-"}</td>
                    </tr>
                  );
                })}
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
