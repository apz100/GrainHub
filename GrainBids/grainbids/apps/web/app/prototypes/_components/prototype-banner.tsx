import Link from "next/link";

/**
 * Shared banner for every prototype page in app/prototypes/.
 *
 * Prototypes are UI explorations, not production pages: no invented
 * prices, no real company branding, no featured elevator anywhere.
 */
export default function PrototypeBanner({ title, blurb }: { title: string; blurb?: string }) {
  return (
    <div className="rounded-lg border border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <p className="font-semibold">Prototype — not production</p>
      <p className="mt-1">
        {blurb ??
          "This is a design prototype. Nothing here is final, no prices are invented, and no real company is featured."}{" "}
        <Link href="/prototypes" className="underline hover:text-amber-700">
          All prototypes
        </Link>
      </p>
      <p className="mt-1 text-xs text-amber-800/80">{title}</p>
    </div>
  );
}
