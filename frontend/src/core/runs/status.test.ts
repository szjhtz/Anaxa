import { describe, expect, it } from "vitest";

import { isActiveRunStale, isRunActive, resolveThreadRun } from "./status";

const baseRun = {
  run_id: "run-1",
  thread_id: "thread-1",
  status: "running",
  metadata: {},
  kwargs: {},
  multitask_strategy: "reject",
  created_at: "2026-05-09T00:00:00Z",
  updated_at: "2026-05-09T00:01:00Z",
};

describe("run status helpers", () => {
  it("resolves the current run when present and otherwise falls back to latest", () => {
    const runs = [
      { ...baseRun, run_id: "latest" },
      { ...baseRun, run_id: "current" },
    ];

    expect(resolveThreadRun(runs, "current")?.run_id).toBe("current");
    expect(resolveThreadRun(runs, "missing")?.run_id).toBe("latest");
    expect(resolveThreadRun(runs)?.run_id).toBe("latest");
  });

  it("treats old pending or running records as stale instead of active", () => {
    const now = Date.parse("2026-05-09T00:45:00Z");

    expect(isActiveRunStale(baseRun, { now })).toBe(true);
    expect(isRunActive(baseRun, { now })).toBe(false);
  });

  it("keeps recent pending or running records active", () => {
    const now = Date.parse("2026-05-09T00:10:00Z");

    expect(isActiveRunStale(baseRun, { now })).toBe(false);
    expect(isRunActive(baseRun, { now })).toBe(true);
  });

  it("does not mark terminal runs as active or stale", () => {
    const run = { ...baseRun, status: "success" };
    const now = Date.parse("2026-05-09T00:45:00Z");

    expect(isActiveRunStale(run, { now })).toBe(false);
    expect(isRunActive(run, { now })).toBe(false);
  });
});
