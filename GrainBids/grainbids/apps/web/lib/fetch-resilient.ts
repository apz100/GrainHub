/**
 * Resilient fetch helpers for talking to the GrainBids API.
 *
 * The production API runs on a free Render tier that sleeps when idle.
 * The first request after a nap can take ~50s while the instance wakes,
 * and a request issued mid-wake can fail at the network level even
 * though the API is healthy a few seconds later. Plain `fetch` calls
 * therefore need two things the raw API does not provide:
 *
 * 1. A timeout long enough to outlast a cold start (via AbortController),
 *    so a genuinely dead request eventually fails instead of hanging a
 *    panel on "Refreshing…" forever.
 * 2. Exactly one retry on network failure / timeout, so a request that
 *    raced the wake-up gets a second chance before the UI gives up.
 *
 * HTTP error responses (4xx/5xx) are NOT retried and are returned (or
 * thrown, for the JSON helper) exactly as the API sent them, so existing
 * callers keep their current status/detail handling.
 */

export type ApiFetchErrorKind = "timeout" | "network" | "http" | "aborted";

export class ApiFetchError extends Error {
  readonly kind: ApiFetchErrorKind;
  /** HTTP status, present only when kind === "http". */
  readonly status?: number;

  constructor(kind: ApiFetchErrorKind, message: string, status?: number) {
    super(message);
    this.name = "ApiFetchError";
    this.kind = kind;
    this.status = status;
  }
}

/** Long enough for a free-tier cold start (~50s) plus a real response. */
export const DEFAULT_API_TIMEOUT_MS = 75_000;

/** Delay before the single retry, giving a waking instance a moment. */
export const DEFAULT_RETRY_DELAY_MS = 1_500;

/** How long a fetch may run before the UI calls it "slow" (waking). */
export const SLOW_FETCH_THRESHOLD_MS = 3_000;

export type ResilientFetchInit = RequestInit & {
  /** Per-request timeout in ms. Defaults to DEFAULT_API_TIMEOUT_MS. */
  timeoutMs?: number;
  /** Extra attempts after the first on network failure/timeout. Default 1. Pass 0 for mutations (POST/PATCH/PUT/DELETE) that must not be replayed. */
  retries?: number;
  /** Delay between attempts in ms. Defaults to DEFAULT_RETRY_DELAY_MS. */
  retryDelayMs?: number;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isAbortError(err: unknown): boolean {
  return (
    err instanceof Error &&
    (err.name === "AbortError" || err.name === "TimeoutError")
  );
}

/**
 * fetch() with a timeout and one retry on network failure/timeout.
 *
 * Returns the Response for every HTTP status (including errors), like
 * fetch itself. Throws ApiFetchError only when no response could be
 * obtained at all: kind "timeout" after the timeout, "network" for
 * connection failures, "aborted" when the caller's own signal fired.
 */
export async function fetchResilient(
  input: RequestInfo | URL,
  init: ResilientFetchInit = {}
): Promise<Response> {
  const {
    timeoutMs = DEFAULT_API_TIMEOUT_MS,
    retries = 1,
    retryDelayMs = DEFAULT_RETRY_DELAY_MS,
    signal: callerSignal,
    ...fetchInit
  } = init;

  let lastError: ApiFetchError | null = null;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    if (attempt > 0) {
      await sleep(retryDelayMs);
    }

    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);

    const onCallerAbort = () => controller.abort();
    if (callerSignal) {
      if (callerSignal.aborted) {
        clearTimeout(timer);
        throw new ApiFetchError("aborted", "Request was cancelled before it started.");
      }
      callerSignal.addEventListener("abort", onCallerAbort, { once: true });
    }

    try {
      return await fetch(input, { ...fetchInit, signal: controller.signal });
    } catch (err) {
      if (callerSignal?.aborted) {
        throw new ApiFetchError("aborted", "Request was cancelled.");
      }
      if (timedOut || isAbortError(err)) {
        lastError = new ApiFetchError(
          "timeout",
          "The API took too long to respond. It may still be waking up — please retry."
        );
      } else {
        lastError = new ApiFetchError(
          "network",
          "Could not reach the API. It may be waking up — please retry."
        );
      }
      // Fall through to the single retry, if any attempts remain.
    } finally {
      clearTimeout(timer);
      if (callerSignal) {
        callerSignal.removeEventListener("abort", onCallerAbort);
      }
    }
  }

  throw lastError ?? new ApiFetchError("network", "Could not reach the API. Please retry.");
}

/** Read a failed Response's body the way the dashboard always has. */
export async function readApiFailure(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail || body);
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}

/**
 * fetchResilient + JSON parsing. Throws ApiFetchError with kind "http"
 * (and the API's detail message) for non-2xx responses.
 */
export async function fetchJsonResilient<T = unknown>(
  input: RequestInfo | URL,
  init: ResilientFetchInit = {}
): Promise<T> {
  const res = await fetchResilient(input, init);
  if (!res.ok) {
    throw new ApiFetchError("http", await readApiFailure(res), res.status);
  }
  return (await res.json()) as T;
}

/** True when an unknown thrown value is one of our typed fetch errors. */
export function isApiFetchError(err: unknown): err is ApiFetchError {
  return err instanceof ApiFetchError;
}
