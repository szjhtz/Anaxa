import { describe, expect, it } from "vitest";

import { parseTaskToolResult } from "./result-parser";

describe("parseTaskToolResult", () => {
  it("parses completed result", () => {
    expect(parseTaskToolResult("Task Succeeded. Result: done")).toEqual({
      status: "completed",
      result: "done",
    });
  });

  it("parses failed result", () => {
    expect(parseTaskToolResult("Task failed. invalid input")).toEqual({
      status: "failed",
      error: "invalid input",
    });
  });

  it("parses timeout as failed", () => {
    expect(parseTaskToolResult("Task timed out after 120s")).toEqual({
      status: "failed",
      error: "Task timed out after 120s",
    });
  });

  it("falls back to in_progress", () => {
    expect(parseTaskToolResult("")).toEqual({ status: "in_progress" });
    expect(parseTaskToolResult("working...")).toEqual({
      status: "in_progress",
    });
  });
});
