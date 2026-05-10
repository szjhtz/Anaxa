import type { RunData } from "@/core/api/runs";

export const ACTIVE_RUN_STATUSES = new Set(["pending", "running"]);
export const STALE_ACTIVE_RUN_MS = 30 * 60 * 1000;

export function resolveThreadRun(
  runs: RunData[] | undefined,
  currentRunId?: string | null,
): RunData | undefined {
  if (!runs || runs.length === 0) return undefined;
  if (currentRunId) {
    return runs.find((run) => run.run_id === currentRunId) ?? runs[0];
  }
  return runs[0];
}

export function isRunActiveStatus(status?: string | null): boolean {
  return Boolean(status && ACTIVE_RUN_STATUSES.has(status));
}

export function isActiveRunStale(
  run: RunData | undefined,
  {
    now = Date.now(),
    staleAfterMs = STALE_ACTIVE_RUN_MS,
  }: {
    now?: number;
    staleAfterMs?: number;
  } = {},
): boolean {
  if (!run || !isRunActiveStatus(run.status)) return false;
  const timestamp = Date.parse(run.updated_at || run.created_at);
  if (Number.isNaN(timestamp)) return false;
  return now - timestamp > staleAfterMs;
}

export function isRunActive(
  run: RunData | undefined,
  options?: {
    now?: number;
    staleAfterMs?: number;
  },
): boolean {
  return isRunActiveStatus(run?.status) && !isActiveRunStale(run, options);
}
