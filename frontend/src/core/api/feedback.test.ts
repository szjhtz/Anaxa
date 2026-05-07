import { afterEach, describe, expect, it, vi } from "vitest";

import {
  deleteRunFeedback,
  getRunFeedback,
  putRunFeedback,
} from "./feedback";

const fetchMock = vi.fn();

vi.stubGlobal("fetch", fetchMock);

describe("feedback api", () => {
  afterEach(() => {
    fetchMock.mockReset();
  });

  it("requests the current run feedback", async () => {
    fetchMock.mockResolvedValue(
      new Response("null", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await getRunFeedback("thread-1", "run-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/thread-1/runs/run-1/feedback",
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it("sends the expected PUT payload", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          feedback_id: "fb-1",
          thread_id: "thread-1",
          run_id: "run-1",
          rating: 1,
          created_at: "now",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await putRunFeedback("thread-1", "run-1", 1);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/thread-1/runs/run-1/feedback",
      expect.objectContaining({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating: 1 }),
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it("deletes feedback for a run", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await deleteRunFeedback("thread-1", "run-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/threads/thread-1/runs/run-1/feedback",
      expect.objectContaining({
        method: "DELETE",
        signal: expect.any(AbortSignal),
      }),
    );
  });
});
