"use client";

import { useMemo, useState } from "react";

import { API_BASE, buildApiHeaders, getApiConfigError } from "@/lib/api";
import PrototypeBanner from "../_components/prototype-banner";

/**
 * Onboarding / farm-profile wizard prototype (Cycle 3).
 *
 * Multi-step wizard: farm location, crop mix + acres, storage,
 * cash-flow goals, risk tolerance. Purely client-side — it saves
 * nothing and calls no API while stepping through. On the final
 * step, a clearly-labelled "Preview" button optionally POSTs the
 * collected state to the existing POST /api/advisor/farm-profiles
 * shape so Adam can see what the payload would look like. The
 * preview is the only network call, and it is explicit.
 *
 * Note: in Cycle 1 the advisor router was built but not yet included
 * in the API's main.py, so the preview may return 404 until it is
 * wired in — the wizard reports that plainly instead of pretending
 * the profile was saved.
 */

const COMMODITIES = ["Corn", "Soybeans", "Wheat", "Canola", "Barley", "Oats"];

const RISK_OPTIONS = [
  { value: "conservative", label: "Conservative", blurb: "Lock in margins early; prefer certainty over upside." },
  { value: "moderate", label: "Moderate", blurb: "Sell in stages; balance price risk against storage cost." },
  { value: "aggressive", label: "Aggressive", blurb: "Hold for upside; comfortable with price swings." },
] as const;

type CropRow = {
  commodity: string;
  acres: string;
  expected_yield_bu_per_acre: string;
  cost_per_acre: string;
};

const EMPTY_CROP: CropRow = {
  commodity: "Corn",
  acres: "",
  expected_yield_bu_per_acre: "",
  cost_per_acre: "",
};

const STEPS = [
  { id: 1, title: "Farm location", hint: "Where the farm is — used to find nearby bids." },
  { id: 2, title: "Crop mix & acres", hint: "What you grow, how many acres, expected yield and cost." },
  { id: 3, title: "Storage", hint: "How much you can hold, and for how long." },
  { id: 4, title: "Cash-flow goals", hint: "What the farm needs the crop to pay for, and when." },
  { id: 5, title: "Risk tolerance", hint: "How you feel about price swings — this shapes sell / hold advice." },
  { id: 6, title: "Review", hint: "Check everything before you preview it. Nothing is saved yet." },
] as const;

function num(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export default function OnboardingPrototypePage() {
  const headers = buildApiHeaders();
  const [step, setStep] = useState(1);
  const [farmName, setFarmName] = useState("");
  const [homeLocation, setHomeLocation] = useState("");
  const [crops, setCrops] = useState<CropRow[]>([{ ...EMPTY_CROP }]);
  const [storageCapacity, setStorageCapacity] = useState("");
  const [cashFlowTarget, setCashFlowTarget] = useState("");
  const [riskTolerance, setRiskTolerance] = useState<string>("moderate");
  const [previewStatus, setPreviewStatus] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [previewMessage, setPreviewMessage] = useState("");
  const [previewPayload, setPreviewPayload] = useState<Record<string, unknown> | null>(null);

  const totalAcres = useMemo(
    () => crops.reduce((sum, c) => sum + (num(c.acres) ?? 0), 0),
    [crops]
  );

  function updateCrop(index: number, field: keyof CropRow, value: string) {
    setCrops((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  }

  function buildPayload(): Record<string, unknown> {
    return {
      farm_name: farmName.trim() || "Example Farm (prototype)",
      crop_mix: crops
        .filter((c) => num(c.acres) != null && (num(c.acres) ?? 0) > 0)
        .map((c) => ({
          commodity: c.commodity,
          acres: num(c.acres),
          expected_yield_bu_per_acre: num(c.expected_yield_bu_per_acre) ?? 0,
          cost_per_acre: num(c.cost_per_acre) ?? 0,
        })),
      total_acres: totalAcres > 0 ? totalAcres : null,
      storage_capacity_bu: num(storageCapacity),
      cash_flow_target_usd: num(cashFlowTarget),
      risk_tolerance: riskTolerance,
      home_location: homeLocation.trim() || null,
    };
  }

  async function previewProfile() {
    const configError = getApiConfigError();
    if (configError) {
      setPreviewStatus("error");
      setPreviewMessage(`Cannot preview: ${configError}`);
      return;
    }
    const payload = buildPayload();
    setPreviewPayload(payload);
    setPreviewStatus("sending");
    setPreviewMessage("");
    try {
      const res = await fetch(`${API_BASE}/api/advisor/farm-profiles`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => "");
        throw new Error(
          `API returned ${res.status}${detail ? `: ${detail.slice(0, 200)}` : ""}. ` +
            "The advisor routes may not be wired into the API yet — nothing was saved."
        );
      }
      const created = await res.json();
      setPreviewStatus("done");
      setPreviewMessage(
        `Preview sent — the API accepted the profile${created?.id ? ` (id ${created.id})` : ""}. ` +
          "This was a preview only; the wizard itself still saves nothing on its own."
      );
    } catch (err) {
      setPreviewStatus("error");
      setPreviewMessage(String(err));
    }
  }

  function resetWizard() {
    setStep(1);
    setFarmName("");
    setHomeLocation("");
    setCrops([{ ...EMPTY_CROP }]);
    setStorageCapacity("");
    setCashFlowTarget("");
    setRiskTolerance("moderate");
    setPreviewStatus("idle");
    setPreviewMessage("");
    setPreviewPayload(null);
  }

  const stepMeta = STEPS[step - 1];
  const canContinue =
    step === 1 ? farmName.trim().length > 0 || homeLocation.trim().length > 0 : true;

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-6 sm:px-6">
      <PrototypeBanner
        title="Onboarding / farm-profile wizard prototype"
        blurb="Prototype — not production. This wizard saves nothing and calls no API while you step through it. Only the clearly-labelled preview button on the final step talks to the API — and only to show what the farm-profile payload would look like."
      />
      <p className="mt-6 text-xs uppercase tracking-[0.16em] text-black/50">GrainHub / Prototypes / Onboarding</p>
      <h1 className="mt-1 font-[family-name:var(--font-serif)] text-3xl leading-tight">
        Set up your farm profile
      </h1>
      <p className="mt-2 text-sm text-black/65">
        A few questions so the Advisor can give sell / hold help that fits
        your farm — not generic advice. Nothing here is saved until you
        choose to preview it.
      </p>

      {/* Stepper */}
      <ol className="mt-6 flex flex-wrap gap-2" aria-label="Onboarding steps">
        {STEPS.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              onClick={() => setStep(s.id)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                s.id === step
                  ? "border-black bg-black text-white"
                  : s.id < step
                    ? "border-black/30 bg-black/5 text-black/70"
                    : "border-black/15 text-black/50"
              }`}
            >
              {s.id}. {s.title}
            </button>
          </li>
        ))}
      </ol>

      <section className="mt-6 rounded-lg border border-black/10 bg-white/65 p-5 backdrop-blur">
        <h2 className="text-lg font-semibold">
          Step {stepMeta.id} of {STEPS.length}: {stepMeta.title}
        </h2>
        <p className="mt-1 text-sm text-black/55">{stepMeta.hint}</p>

        {step === 1 ? (
          <div className="mt-4 space-y-4">
            <div>
              <label htmlFor="ob-farm-name" className="text-sm font-medium">Farm name</label>
              <input
                id="ob-farm-name"
                type="text"
                value={farmName}
                onChange={(e) => setFarmName(e.target.value)}
                placeholder="e.g. Testville Acres"
                className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
              />
            </div>
            <div>
              <label htmlFor="ob-location" className="text-sm font-medium">Farm location</label>
              <input
                id="ob-location"
                type="text"
                value={homeLocation}
                onChange={(e) => setHomeLocation(e.target.value)}
                placeholder="e.g. Testville"
                autoComplete="off"
                className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
              />
              <p className="mt-1 text-xs text-black/50">
                Town or county — used to find bids near you. Synthetic locations only in this prototype.
              </p>
            </div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="mt-4 space-y-4">
            {crops.map((crop, i) => (
              <fieldset key={i} className="rounded-md border border-black/10 bg-white/70 p-3">
                <legend className="px-1 text-sm font-medium">Crop {i + 1}</legend>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor={`ob-crop-${i}`} className="text-xs text-black/60">Commodity</label>
                    <select
                      id={`ob-crop-${i}`}
                      value={crop.commodity}
                      onChange={(e) => updateCrop(i, "commodity", e.target.value)}
                      className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2 text-sm"
                    >
                      {COMMODITIES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor={`ob-acres-${i}`} className="text-xs text-black/60">Acres</label>
                    <input
                      id={`ob-acres-${i}`}
                      type="number"
                      min="0"
                      step="any"
                      value={crop.acres}
                      onChange={(e) => updateCrop(i, "acres", e.target.value)}
                      placeholder="e.g. 400"
                      className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor={`ob-yield-${i}`} className="text-xs text-black/60">Expected yield (bu/acre)</label>
                    <input
                      id={`ob-yield-${i}`}
                      type="number"
                      min="0"
                      step="any"
                      value={crop.expected_yield_bu_per_acre}
                      onChange={(e) => updateCrop(i, "expected_yield_bu_per_acre", e.target.value)}
                      placeholder="e.g. 180"
                      className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor={`ob-cost-${i}`} className="text-xs text-black/60">Cost ($/acre)</label>
                    <input
                      id={`ob-cost-${i}`}
                      type="number"
                      min="0"
                      step="any"
                      value={crop.cost_per_acre}
                      onChange={(e) => updateCrop(i, "cost_per_acre", e.target.value)}
                      placeholder="e.g. 650"
                      className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                {crops.length > 1 ? (
                  <button
                    type="button"
                    onClick={() => setCrops((prev) => prev.filter((_, j) => j !== i))}
                    className="mt-3 text-xs text-red-700 underline"
                  >
                    Remove this crop
                  </button>
                ) : null}
              </fieldset>
            ))}
            <button
              type="button"
              onClick={() => setCrops((prev) => [...prev, { ...EMPTY_CROP }])}
              className="rounded-md border border-black/20 bg-white/80 px-3 py-2 text-sm hover:border-black/40"
            >
              + Add another crop
            </button>
            <p className="text-sm text-black/60">
              Total acres so far: <strong>{totalAcres.toLocaleString()}</strong>
            </p>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="mt-4 space-y-4">
            <div>
              <label htmlFor="ob-storage" className="text-sm font-medium">On-farm storage capacity (bushels)</label>
              <input
                id="ob-storage"
                type="number"
                min="0"
                step="any"
                value={storageCapacity}
                onChange={(e) => setStorageCapacity(e.target.value)}
                placeholder="e.g. 50000"
                className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
              />
              <p className="mt-1 text-xs text-black/50">
                Leave blank if you have no on-farm storage — the Advisor will
                lean toward selling at harvest.
              </p>
            </div>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="mt-4 space-y-4">
            <div>
              <label htmlFor="ob-cashflow" className="text-sm font-medium">Cash-flow target (per year)</label>
              <input
                id="ob-cashflow"
                type="number"
                min="0"
                step="any"
                value={cashFlowTarget}
                onChange={(e) => setCashFlowTarget(e.target.value)}
                placeholder="e.g. 120000"
                className="mt-1 w-full rounded-md border border-black/20 bg-white px-3 py-2.5 text-base"
              />
              <p className="mt-1 text-xs text-black/50">
                What the farm needs the crop to cover — loan payments, rent,
                inputs, living costs. Currency follows your account settings;
                no currency is assumed here.
              </p>
            </div>
          </div>
        ) : null}

        {step === 5 ? (
          <fieldset className="mt-4 space-y-3">
            <legend className="sr-only">Risk tolerance</legend>
            {RISK_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 ${
                  riskTolerance === option.value ? "border-black bg-white" : "border-black/15 bg-white/60"
                }`}
              >
                <input
                  type="radio"
                  name="risk-tolerance"
                  value={option.value}
                  checked={riskTolerance === option.value}
                  onChange={() => setRiskTolerance(option.value)}
                  className="mt-1"
                />
                <span>
                  <span className="block font-medium">{option.label}</span>
                  <span className="block text-sm text-black/60">{option.blurb}</span>
                </span>
              </label>
            ))}
          </fieldset>
        ) : null}

        {step === 6 ? (
          <div className="mt-4 space-y-4">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4 border-b border-black/5 pb-2">
                <dt className="text-black/60">Farm</dt>
                <dd className="text-right font-medium">{farmName.trim() || "—"} · {homeLocation.trim() || "—"}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-black/5 pb-2">
                <dt className="text-black/60">Crops</dt>
                <dd className="text-right font-medium">
                  {crops.filter((c) => num(c.acres) != null).length === 0
                    ? "—"
                    : crops
                        .filter((c) => num(c.acres) != null)
                        .map((c) => `${c.commodity} — ${num(c.acres)?.toLocaleString()} ac`)
                        .join("; ")}
                </dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-black/5 pb-2">
                <dt className="text-black/60">Total acres</dt>
                <dd className="font-medium">{totalAcres > 0 ? totalAcres.toLocaleString() : "—"}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-black/5 pb-2">
                <dt className="text-black/60">Storage</dt>
                <dd className="font-medium">{num(storageCapacity) != null ? `${num(storageCapacity)?.toLocaleString()} bu` : "—"}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-black/5 pb-2">
                <dt className="text-black/60">Cash-flow target</dt>
                <dd className="font-medium">{num(cashFlowTarget) != null ? num(cashFlowTarget)?.toLocaleString() : "—"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-black/60">Risk tolerance</dt>
                <dd className="font-medium">{riskTolerance}</dd>
              </div>
            </dl>

            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-semibold">Nothing is saved yet.</p>
              <p className="mt-1">
                This prototype keeps everything in your browser. The button
                below is the only way anything leaves this page — it sends
                one preview request to POST /api/advisor/farm-profiles so you
                can see what the API would store.
              </p>
            </div>

            <button
              type="button"
              onClick={previewProfile}
              disabled={previewStatus === "sending"}
              className="w-full rounded-md bg-black px-4 py-3 text-base font-medium text-white disabled:opacity-50"
            >
              {previewStatus === "sending" ? "Sending preview…" : "Preview: send this profile to the API"}
            </button>

            {previewMessage ? (
              <p
                className={`rounded border px-4 py-3 text-sm ${
                  previewStatus === "done"
                    ? "border-green-300 bg-green-50 text-green-900"
                    : "border-red-300 bg-red-50 text-red-900"
                }`}
              >
                {previewMessage}
              </p>
            ) : null}

            {previewPayload ? (
              <details className="rounded-md border border-black/10 bg-white/70 p-3 text-xs">
                <summary className="cursor-pointer font-medium">Payload sent (for review)</summary>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(previewPayload, null, 2)}
                </pre>
              </details>
            ) : null}
          </div>
        ) : null}

        <div className="mt-6 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
            className="rounded-md border border-black/20 bg-white/80 px-4 py-2.5 text-sm disabled:opacity-40"
          >
            ← Back
          </button>
          {step < STEPS.length ? (
            <button
              type="button"
              onClick={() => setStep((s) => Math.min(STEPS.length, s + 1))}
              disabled={!canContinue}
              className="rounded-md bg-black px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40"
            >
              Continue →
            </button>
          ) : (
            <button
              type="button"
              onClick={resetWizard}
              className="rounded-md border border-black/20 bg-white/80 px-4 py-2.5 text-sm hover:border-black/40"
            >
              Start over
            </button>
          )}
        </div>
      </section>

      <p className="mt-6 text-xs text-black/45">
        Prototype note: risk tolerance is a lead magnet — the full Advisor
        (sell / hold signals, breakevens, cash-flow tools) is a paid silo in
        the draft pricing. See the pricing prototype.
      </p>
    </main>
  );
}
