"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { API_BASE, buildApiHeaders, getApiConfigError } from "@/lib/api";

type ContractRow = {
  id: string;
  grower_name: string;
  commodity: string;
  quantity_bushels: number;
  delivery_start: string | null;
  delivery_end: string | null;
  price_per_bushel: number | null;
  status: string;
  esign_status: string | null;
};

type ScaleTicketRow = {
  id: string;
  ticket_number: string;
  ticket_date: string | null;
  commodity: string;
  bushels: number;
  moisture_percent: number | null;
  grade: string | null;
};

type CrmNoteRow = {
  id: string;
  grower_name: string;
  author: string | null;
  note: string;
  follow_up_date: string | null;
};

/**
 * White-label grower portal scaffold (Elevator Ops silo v1).
 *
 * The elevator name / logo are placeholders driven by the org: there is no
 * org-branding endpoint yet, so the header shows "Your Elevator" until
 * white-label branding is configured per org. No grower data is invented —
 * every section renders an empty state until the API returns real rows.
 * When the API is unreachable, the page says so plainly ("demo data —
 * connect API") instead of showing fake numbers.
 */
export default function GrowerPortalPage() {
  const headers = buildApiHeaders();
  const [contracts, setContracts] = useState<ContractRow[]>([]);
  const [tickets, setTickets] = useState<ScaleTicketRow[]>([]);
  const [notes, setNotes] = useState<CrmNoteRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiConnected, setApiConnected] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const configError = getApiConfigError();
    if (configError) {
      setError(configError);
      setLoading(false);
      return;
    }
    async function load() {
      try {
        const [contractsRes, ticketsRes, notesRes] = await Promise.all([
          fetch(`${API_BASE}/api/elevator-ops/contracts?limit=25`, { cache: "no-store", headers }),
          fetch(`${API_BASE}/api/elevator-ops/scale-tickets?limit=25`, { cache: "no-store", headers }),
          fetch(`${API_BASE}/api/elevator-ops/crm-notes?limit=25`, { cache: "no-store", headers }),
        ]);
        if (!contractsRes.ok || !ticketsRes.ok || !notesRes.ok) {
          throw new Error("Elevator Ops API returned an error");
        }
        const [contractsJson, ticketsJson, notesJson] = await Promise.all([
          contractsRes.json(),
          ticketsRes.json(),
          notesRes.json(),
        ]);
        setContracts(contractsJson.rows || []);
        setTickets(ticketsJson.rows || []);
        setNotes(notesJson.rows || []);
        setApiConnected(true);
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="mx-auto w-full max-w-7xl px-6 py-10">
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-black/50">Grower Portal</p>
        <h1 className="font-[family-name:var(--font-serif)] text-4xl leading-tight">
          Your Elevator
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-black/70">
          White-label grower portal. The elevator name and logo shown here are
          placeholders — branding is driven by your organization once it is
          configured.
        </p>
        {!apiConnected && !loading ? (
          <p className="mt-4 rounded border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Demo data — connect API: the Elevator Ops API could not be reached
            {error ? ` (${error})` : ""}. Sections below show empty states
            until real data is available. No grower data shown is real.
          </p>
        ) : null}
      </header>

      <nav className="mb-8 flex flex-wrap gap-3 text-sm">
        <Link href="#contracts" className="rounded-full border border-black/15 px-4 py-2 hover:bg-black/5">
          Contracts
        </Link>
        <Link href="#scale-tickets" className="rounded-full border border-black/15 px-4 py-2 hover:bg-black/5">
          Scale Tickets
        </Link>
        <Link href="#crm-notes" className="rounded-full border border-black/15 px-4 py-2 hover:bg-black/5">
          Notes
        </Link>
        <Link href="/bids" className="rounded-full border border-black/15 px-4 py-2 hover:bg-black/5">
          Cash Bids
        </Link>
      </nav>

      {loading ? (
        <p className="text-sm text-black/60">Loading your portal…</p>
      ) : (
        <div className="space-y-10">
          <section id="contracts">
            <h2 className="mb-3 font-[family-name:var(--font-serif)] text-2xl">Contracts</h2>
            {contracts.length === 0 ? (
              <p className="rounded border border-black/10 bg-white/70 px-4 py-6 text-sm text-black/60">
                No contracts yet. Contracts created by your elevator will appear here.
              </p>
            ) : (
              <ul className="divide-y divide-black/10 rounded border border-black/10 bg-white/70">
                {contracts.map((row) => (
                  <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                    <span>
                      {row.commodity} — {row.quantity_bushels.toLocaleString()} bu
                      {row.delivery_start ? ` · ${row.delivery_start}` : ""}
                      {row.delivery_end ? ` to ${row.delivery_end}` : ""}
                    </span>
                    <span className="text-black/60">
                      {row.status}
                      {row.esign_status === "pending_signature" ? " · awaiting signature" : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section id="scale-tickets">
            <h2 className="mb-3 font-[family-name:var(--font-serif)] text-2xl">Scale Tickets</h2>
            {tickets.length === 0 ? (
              <p className="rounded border border-black/10 bg-white/70 px-4 py-6 text-sm text-black/60">
                No scale tickets yet. Tickets from deliveries will appear here.
              </p>
            ) : (
              <ul className="divide-y divide-black/10 rounded border border-black/10 bg-white/70">
                {tickets.map((row) => (
                  <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                    <span>
                      Ticket {row.ticket_number} · {row.commodity} — {row.bushels.toLocaleString()} bu
                    </span>
                    <span className="text-black/60">
                      {row.ticket_date || ""}
                      {row.moisture_percent !== null ? ` · ${row.moisture_percent}% moisture` : ""}
                      {row.grade ? ` · ${row.grade}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section id="crm-notes">
            <h2 className="mb-3 font-[family-name:var(--font-serif)] text-2xl">Notes</h2>
            {notes.length === 0 ? (
              <p className="rounded border border-black/10 bg-white/70 px-4 py-6 text-sm text-black/60">
                No notes yet.
              </p>
            ) : (
              <ul className="divide-y divide-black/10 rounded border border-black/10 bg-white/70">
                {notes.map((row) => (
                  <li key={row.id} className="px-4 py-3 text-sm">
                    <p className="text-black/60">
                      {row.grower_name}
                      {row.author ? ` · ${row.author}` : ""}
                      {row.follow_up_date ? ` · follow up ${row.follow_up_date}` : ""}
                    </p>
                    <p className="mt-1">{row.note}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
