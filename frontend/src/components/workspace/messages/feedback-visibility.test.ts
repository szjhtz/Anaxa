import { describe, expect, it } from "vitest";

import { shouldShowRunFeedback } from "./feedback-visibility";

describe("shouldShowRunFeedback", () => {
  it("shows controls for non-human messages with a runId once loading is complete", () => {
    expect(
      shouldShowRunFeedback({
        messageType: "ai",
        isLoading: false,
        runId: "run-1",
      }),
    ).toBe(true);
  });

  it("hides controls when runId is missing", () => {
    expect(
      shouldShowRunFeedback({
        messageType: "ai",
        isLoading: false,
        runId: null,
      }),
    ).toBe(false);
  });

  it("hides controls while the message is still streaming", () => {
    expect(
      shouldShowRunFeedback({
        messageType: "ai",
        isLoading: true,
        runId: "run-1",
      }),
    ).toBe(false);
  });
});
