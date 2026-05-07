import { describe, expect, it } from "vitest";

import { hasTaskPatchChanges } from "./context";

describe("hasTaskPatchChanges", () => {
  it("returns true when there is no previous task", () => {
    expect(
      hasTaskPatchChanges(undefined, {
        id: "task-1",
        status: "in_progress" as const,
      }),
    ).toBe(true);
  });

  it("returns false when patch does not change any field", () => {
    const previous = {
      id: "task-1",
      status: "in_progress" as const,
      subagent_type: "general-purpose",
      description: "desc",
      prompt: "prompt",
    };

    expect(
      hasTaskPatchChanges(previous, {
        id: "task-1",
        status: "in_progress" as const,
      }),
    ).toBe(false);
  });

  it("returns true when patch changes an existing field", () => {
    const previous = {
      id: "task-1",
      status: "in_progress" as const,
      subagent_type: "general-purpose",
      description: "desc",
      prompt: "prompt",
    };

    expect(
      hasTaskPatchChanges(previous, {
        id: "task-1",
        status: "completed" as const,
        result: "done",
      }),
    ).toBe(true);
  });
});
