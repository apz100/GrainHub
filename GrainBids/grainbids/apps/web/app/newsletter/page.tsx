import Link from "next/link";
import { API_BASE, buildApiHeaders } from "@/lib/api";

const headers = buildApiHeaders();

type NewsletterSection = {
  kind?: string | null;
  title?: string | null;
  heading?: string | null;
  body?: string | null;
  text?: string | null;
  note?: string | null;
  empty?: boolean | null;
  empty_reason?: string | null;
  items?: Array<Record<string, unknown>> | null;
  commodities?: Record<string, Array<Record<string, unknown>>> | null;
  reports?: Array<Record<string, unknown>> | null;
};

type NewsletterDraft = {
  subject?: string | null;
  title?: string | null;
  issue_key?: string | null;
  generated_at?: string | null;
  date?: string | null;
  report_date?: string | null;
  region?: string | null;
  intro?: string | null;
  body?: string | null;
  text?: string | null;
  sections?: NewsletterSection[] | null;
  top_bids?: Array<Record<string, unknown>> | null;
  research?: Array<Record<string, unknown>> | null;
};

async function fetchDraft(): Promise<NewsletterDraft | null> {
  try {
    const res = await fetch(`${API_BASE}/api/newsletter/daily-draft`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) return null;
    const payload = await res.json();
    if (payload && typeof payload === "object") return payload as NewsletterDraft;
    return null;
  } catch {
    return null;
  }
}

function formatPrice(value: unknown): string {
  return typeof value === "number" && !Number.isNaN(value) ? `$${value.toFixed(2)}/bu` : "";
}

function bidLine(item: Record<string, unknown>): string {
  const label =
    typeof item.label === "string"
      ? item.label
      : typeof item.title === "string"
        ? item.title
        : "";
  const commodity =
    typeof item.commodity === "string"
      ? item.commodity
      : typeof item.commodity_name === "string"
        ? item.commodity_name
        : "";
  const location = typeof item.location === "string" ? item.location : "";
  const price = formatPrice(item.cash_price_bu);
  const basis =
    typeof item.basis === "number" && !Number.isNaN(item.basis)
      ? `basis ${item.basis > 0 ? "+" : ""}${item.basis.toFixed(2)}`
      : "";
  return [label, commodity, location, price, basis].filter(Boolean).join(" — ");
}

function reportLine(item: Record<string, unknown>): string {
  const report =
    typeof item.report === "string"
      ? item.report
      : typeof item.report_type === "string"
        ? item.report_type
        : typeof item.title === "string"
          ? item.title
          : "";
  const date =
    typeof item.report_date === "string"
      ? item.report_date
      : typeof item.release_at === "string"
        ? item.release_at
        : "";
  const commodity = typeof item.commodity === "string" ? item.commodity : "";
  return [report, commodity, date].filter(Boolean).join(" — ");
}

function SectionBody({ section }: { section: NewsletterSection }) {
  if (section.empty) {
    return (
      <p className="mt-1 text-sm text-black/55">
        {section.empty_reason ?? "Nothing to include in this section today."}
      </p>
    );
  }
  const items = section.items ?? [];
  const reports = section.reports ?? [];
  const commodities = section.commodities ?? {};
  const commodityNames = Object.keys(commodities);
  if (section.body) return <p className="mt-1 text-sm whitespace-pre-line">{section.body}</p>;
  if (section.text) return <p className="mt-1 text-sm whitespace-pre-line">{section.text}</p>;
  return (
    <div className="mt-1 space-y-1 text-sm">
      {items.map((item, idx) => (
        <p key={`item-${idx}`}>{bidLine(item) || "—"}</p>
      ))}
      {commodityNames.map((name) => (
        <div key={name}>
          <p className="font-medium">{name}</p>
          {(commodities[name] ?? []).map((item, idx) => (
            <p key={`${name}-${idx}`} className="pl-3">
              {bidLine(item) || "—"}
            </p>
          ))}
        </div>
      ))}
      {reports.map((item, idx) => (
        <p key={`report-${idx}`}>{reportLine(item) || "—"}</p>
      ))}
      {items.length === 0 && reports.length === 0 && commodityNames.length === 0 ? (
        <p className="text-black/55">No content in this section.</p>
      ) : null}
      {section.note ? <p className="text-xs text-black/55">{section.note}</p> : null}
    </div>
  );
}

export default async function NewsletterPage() {
  const draft = await fetchDraft();
  const sections = draft?.sections ?? [];
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <p className="text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / Newsletter</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Daily Newsletter — Preview
      </h1>
      <p className="mt-2 text-sm text-black/65">
        A preview of today&apos;s daily market newsletter, generated from real ingested
        bids and research. The preview shows exactly what subscribers would receive —
        if a section has no data, it is left out rather than filled in.
      </p>

      {!draft ? (
        <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
          <h2 className="text-lg font-semibold">No draft yet</h2>
          <p className="mt-2 text-sm text-black/55">
            Today&apos;s newsletter draft has not been generated yet. The draft is built
            from the latest ingested bids and research — once the daily generator runs,
            the preview appears here. Nothing is shown until a real draft exists.
          </p>
          <Link href="/bids" className="mt-4 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
            View the market dashboard
          </Link>
        </section>
      ) : (
        <article className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
          <h2 className="text-lg font-semibold">{draft.subject ?? draft.title ?? "Daily Grain Newsletter"}</h2>
          <p className="mt-1 text-sm text-black/55">
            {draft.generated_at ? `Generated ${draft.generated_at}` : ""}
            {draft.issue_key ? ` · Issue ${draft.issue_key}` : ""}
            {draft.date ?? draft.report_date ? ` · ${draft.date ?? draft.report_date}` : ""}
            {draft.region ? ` · ${draft.region}` : ""}
          </p>
          {draft.intro ? <p className="mt-4 text-sm whitespace-pre-line">{draft.intro}</p> : null}
          {draft.body ? <p className="mt-4 text-sm whitespace-pre-line">{draft.body}</p> : null}
          {sections.length === 0 && !draft.body && !draft.intro && !draft.text ? (
            <p className="mt-4 text-sm text-black/55">
              This draft has no sections — the generator found no bids or research to
              include today.
            </p>
          ) : (
            sections.map((section, idx) => (
              <section key={section.title ?? section.heading ?? `section-${idx}`} className="mt-6">
                <h3 className="text-base font-semibold">{section.title ?? section.heading ?? "Section"}</h3>
                <SectionBody section={section} />
              </section>
            ))
          )}
          {draft.text ? (
            <details className="mt-6">
              <summary className="cursor-pointer text-sm font-medium">Full plain-text version</summary>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-md border border-black/10 bg-white p-3 text-sm">
                {draft.text}
              </pre>
            </details>
          ) : null}
          <Link href="/research" className="mt-6 inline-flex rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
            Research
          </Link>
        </article>
      )}
    </main>
  );
}
