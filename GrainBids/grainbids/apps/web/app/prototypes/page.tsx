import Link from "next/link";
import PrototypeBanner from "./_components/prototype-banner";

const PROTOTYPES = [
  {
    href: "/prototypes/price-finder",
    title: "Mobile-first Price Finder",
    description:
      "Phone-width search by location, grain, radius and delivery month, wired to the real /api/best-bids and /api/market-search endpoints.",
  },
  {
    href: "/prototypes/onboarding",
    title: "Onboarding / Farm-Profile Wizard",
    description:
      "Multi-step wizard (location, crop mix + acres, storage, cash-flow goals, risk tolerance). Saves nothing; an optional preview button posts to /api/advisor/farm-profiles.",
  },
  {
    href: "/prototypes/pricing",
    title: "Pricing Page",
    description:
      "Four-silo draft pricing built from the public benchmarks in the GrainHub super plan (Farmbucks, GrainFox, Bushel, GrainStats). Draft only — final pricing is Adam's decision.",
  },
];

export default function PrototypesIndexPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <PrototypeBanner
        title="Prototypes index"
        blurb="Design prototypes for the four GrainHub silos. Nothing here is production, no prices are invented, and no real company is featured."
      />
      <p className="mt-6 text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / Prototypes</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-4xl leading-tight">
        Prototypes
      </h1>
      <p className="mt-2 max-w-2xl text-sm text-black/65">
        Early UI explorations for the Price Finder, Advisor onboarding, and
        pricing. Each page carries a prototype banner and shows real API data
        when the API is reachable — otherwise an honest empty state (or, in
        the price finder, clearly-labelled example rows).
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PROTOTYPES.map((proto) => (
          <Link
            key={proto.href}
            href={proto.href}
            className="rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur transition hover:border-black/30"
          >
            <h2 className="text-lg font-semibold">{proto.title}</h2>
            <p className="mt-2 text-sm text-black/65">{proto.description}</p>
            <span className="mt-4 inline-block text-sm font-medium underline">Open prototype →</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
