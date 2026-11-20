import Link from "next/link";
import PrototypeBanner from "../_components/prototype-banner";

/**
 * Pricing page prototype (Cycle 3).
 *
 * Four-silo draft pricing built ONLY from the public benchmarks in
 * docs/plans/grainhub-super-plan.md — Farmbucks, GrainFox, Bushel and
 * GrainStats. These are benchmark-based draft prices, not final:
 * final pricing is Adam's decision. No invented prices, no real
 * company branding, no featured elevator anywhere.
 */

type Tier = {
  silo: string;
  name: string;
  price: string;
  priceNote: string;
  benchmark: string;
  features: string[];
  cta: string;
  featured?: boolean;
};

const TIERS: Tier[] = [
  {
    silo: "Price Finder",
    name: "Price Finder",
    price: "$0",
    priceNote: "Free — best bids for everyone",
    benchmark: "Benchmark: Farmbucks free public best-bid page; GrainFox Basic $0.",
    features: [
      "Free public best-bid page by commodity and delivery month",
      "Search by location, grain, radius and delivery month",
      "Top bids per month, sorted by price",
      "Watchlists and saved searches",
    ],
    cta: "Start free",
  },
  {
    silo: "Price Finder Pro",
    name: "Price Finder Pro",
    price: "$120 CAD / year",
    priceNote: "or $20 CAD / month",
    benchmark: "Benchmark: Farmbucks $120 CAD/yr or $20 CAD/mo, 30-day trial; newsletter add-on $14.99 CAD/mo.",
    features: [
      "Everything in free Price Finder",
      "Price alerts (email now, SMS next)",
      "Best-bid history",
      "Daily newsletter add-on (draft: benchmark $14.99 CAD/mo)",
    ],
    cta: "Try free for 30 days",
    featured: true,
  },
  {
    silo: "Research",
    name: "Research",
    price: "$50 / month",
    priceNote: "Alerts tier · Pro tier $100 / month",
    benchmark: "Benchmark: GrainStats Alerts $50/mo, Pro $100/mo (real-time alerts, daily newsletter, ad-free).",
    features: [
      "Every USDA report, made simple: WASDE, Crop Progress, Export Sales and more",
      "Charts, maps and sortable tables with week-on-week change and 5-year average",
      "Source, delay and vintage on every number",
      "Pro: real-time alerts, daily newsletter, ad-free",
    ],
    cta: "See Research",
  },
  {
    silo: "Advisor",
    name: "Advisor",
    price: "$1,500 CAD / year",
    priceNote: "Smart tier $3,000 CAD / year",
    benchmark: "Benchmark: GrainFox Market Intelligence $1,500 CAD/yr, Smart $3,000 CAD/yr, Smart Plan+ per acre with a human advisor; AI assistant $19.99 / 100 questions.",
    features: [
      "Farm profile, risk profile and breakevens",
      "Personalised sell / hold signals and a sales plan",
      "Scenario, cash-flow and ROI tools",
      "Smart: AI assistant question packs (draft: benchmark $19.99 / 100 questions)",
      "Smart Plan+: per-acre pricing with a human advisor",
    ],
    cta: "Build my farm profile",
  },
  {
    silo: "Elevator Ops",
    name: "Elevator Ops",
    price: "$75 – $599 / year",
    priceNote: "Farmer plans · agribusiness pricing on request",
    benchmark: "Benchmark: Bushel farmer plans $75–$599/yr; agribusiness pricing demo-only. Grain Discovery demo-only.",
    features: [
      "White-label grower portal under your elevator's brand",
      "Live bids and firm offers with timestamped acceptance",
      "Contracts, scale tickets, settlements, eSign and payments",
      "CRM and origination analytics",
    ],
    cta: "Talk to us",
  },
];

export default function PricingPrototypePage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <PrototypeBanner
        title="Pricing page prototype"
        blurb="Prototype — not production. Benchmark-based draft pricing, not final: every figure below comes from a named public benchmark in the GrainBids super plan. Final pricing is Adam's decision."
      />
      <p className="mt-6 text-xs uppercase tracking-[0.16em] text-black/50">GrainBids / Prototypes / Pricing</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Pricing — draft
      </h1>
      <p className="mt-2 max-w-2xl text-sm text-black/65">
        One platform, four silos. The free best-bid page stays free for
        everyone; each silo adds depth for the people who need it. Prices
        below are drafts anchored to what Farmbucks, GrainFox, Bushel and
        GrainStats charge today — they are not GrainBids&apos;s final prices.
      </p>

      <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {TIERS.map((tier) => (
          <article
            key={tier.name}
            className={`flex flex-col rounded-lg border p-5 backdrop-blur ${
              tier.featured
                ? "border-black bg-white/80 shadow-sm"
                : "border-black/10 bg-white/65"
            }`}
          >
            {tier.featured ? (
              <p className="mb-2 inline-block w-fit rounded-full bg-black px-2.5 py-1 text-xs font-medium text-white">
                Most popular draft
              </p>
            ) : null}
            <p className="text-xs uppercase tracking-[0.16em] text-black/50">{tier.silo}</p>
            <h2 className="mt-1 text-xl font-semibold">{tier.name}</h2>
            <p className="mt-3 text-2xl font-semibold">{tier.price}</p>
            <p className="text-sm text-black/55">{tier.priceNote}</p>
            <ul className="mt-4 flex-1 space-y-2 text-sm text-black/75">
              {tier.features.map((feature) => (
                <li key={feature} className="flex gap-2">
                  <span aria-hidden="true">✓</span>
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 border-t border-black/10 pt-3 text-xs text-black/50">
              {tier.benchmark}
            </p>
            <span className="mt-4 inline-flex justify-center rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm font-medium">
              {tier.cta} (prototype — no signup)
            </span>
          </article>
        ))}

        <article className="flex flex-col justify-between rounded-lg border border-dashed border-black/20 bg-transparent p-5">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-black/50">All silos</p>
            <h2 className="mt-1 text-xl font-semibold">Bundle — draft</h2>
            <p className="mt-3 text-sm text-black/65">
              Price Finder Pro + Research Pro + Advisor, one subscription.
              No benchmark exists for a four-silo bundle yet — this tier is
              deliberately left unpriced until Adam decides.
            </p>
          </div>
          <p className="mt-4 text-xs text-black/50">
            Draft only. Final pricing is Adam&apos;s decision.
          </p>
        </article>
      </div>

      <section className="mt-8 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">How these drafts were set</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-black/65">
          <li>Price Finder Pro — Farmbucks: $120 CAD/yr or $20 CAD/mo, 30-day trial.</li>
          <li>Research — GrainStats: Alerts $50/mo, Pro $100/mo (real-time alerts, daily newsletter, ad-free).</li>
          <li>Advisor — GrainFox: Basic $0, Market Intelligence $1,500 CAD/yr, Smart $3,000 CAD/yr, Smart Plan+ per acre with a human advisor, AI assistant $19.99 / 100 questions.</li>
          <li>Elevator Ops — Bushel: farmer plans $75–$599/yr; agribusiness pricing demo-only. Grain Discovery: demo-only, no published pricing.</li>
        </ul>
        <p className="mt-3 text-sm text-black/55">
          Benchmarks were checked 2026-11-18 and are recorded in the GrainBids
          super plan. They will move — re-check before launch. Nothing on this
          page charges anyone anything.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/prototypes/price-finder" className="rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
            Try the Price Finder prototype
          </Link>
          <Link href="/prototypes/onboarding" className="rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40">
            Try the onboarding prototype
          </Link>
        </div>
      </section>
    </main>
  );
}
