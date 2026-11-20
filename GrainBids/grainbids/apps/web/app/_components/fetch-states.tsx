"use client";

import { useEffect, useState } from "react";

import { SLOW_FETCH_THRESHOLD_MS } from "@/lib/fetch-resilient";

/**
 * Shared loading / waking / error UI for panels that talk to the API.
 *
 * The API sleeps on a free tier, so loads have three honest states:
 * fast (nothing extra shown), slow (the API is probably waking — say
 * so, with a time expectation), and failed (a clear error with a retry
 * button). No panel should sit on an indefinite "Refreshing…".
 */

/** Returns true once `loading` has been continuously true past the threshold. */
export function useSlowLoad(
  loading: boolean,
  thresholdMs: number = SLOW_FETCH_THRESHOLD_MS
): boolean {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!loading) {
      setSlow(false);
      return;
    }
    const timer = setTimeout(() => setSlow(true), thresholdMs);
    return () => clearTimeout(timer);
  }, [loading, thresholdMs]);

  return slow;
}

/** Amber notice shown when a fetch is taking long enough to mean a cold start. */
export function WakingApiNotice({ className = "" }: { className?: string }) {
  return (
    <div
      role="status"
      className={`rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 ${className}`}
    >
      <span className="font-medium">Waking the API</span> — free tier, first load can take
      up to a minute. Hang tight; this page will update on its own.
    </div>
  );
}

/** Error notice with a retry button, for a fetch that ultimately failed. */
export function FetchErrorNotice({
  message,
  onRetry,
  className = "",
}: {
  message: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 ${className}`}
    >
      <p className="min-w-0 flex-1">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-800 hover:border-red-400"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}

/** Pulsing placeholder rows for a table body while data loads. */
export function SkeletonTableRows({
  columns,
  rows = 5,
}: {
  columns: number;
  rows?: number;
}) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <tr key={`skeleton-${rowIdx}`} aria-hidden="true" className="border-b border-black/5">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <td key={colIdx} className="px-3 py-3">
              <span className="block h-3 animate-pulse rounded bg-black/10" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

/** Pulsing placeholder cards while a card grid loads. */
export function SkeletonCards({ count = 3 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={`skeleton-card-${idx}`}
          aria-hidden="true"
          className="rounded-md border border-black/10 bg-white p-3"
        >
          <span className="block h-4 w-2/3 animate-pulse rounded bg-black/10" />
          <span className="mt-3 block h-3 w-full animate-pulse rounded bg-black/10" />
          <span className="mt-2 block h-3 w-5/6 animate-pulse rounded bg-black/10" />
        </div>
      ))}
    </>
  );
}
