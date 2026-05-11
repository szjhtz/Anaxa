import { describe, expect, it } from "vitest";

import type { AgentThread } from "./types";
import { cleanThreadTitle, titleOfThread, titleOfThreadState } from "./utils";

function makeThread(title: string, firstUserMessage?: string): AgentThread {
  return {
    thread_id: "thread-1",
    created_at: "2026-05-10T00:00:00.000Z",
    updated_at: "2026-05-10T00:00:00.000Z",
    state_updated_at: "2026-05-10T00:00:00.000Z",
    metadata: {},
    status: "idle",
    interrupts: {},
    values: {
      title,
      artifacts: [],
      messages: firstUserMessage
        ? [
            {
              id: "msg-1",
              type: "human",
              content: firstUserMessage,
            },
          ]
        : [],
    },
  } as AgentThread;
}

describe("thread title utilities", () => {
  it("strips model thinking blocks from generated titles", () => {
    expect(
      cleanThreadTitle(
        "<think>The user asks for a title.</think>\nVCFM Literature Review",
      ),
    ).toBe("VCFM Literature Review");
  });

  it("rejects prompt echo titles and falls back to the first user message", () => {
    const thread = makeThread(
      '<think> The user: "Generate a concise title (max 6 words) fo',
      "GNN和MLP在Virtual Cell Foundation Model中的局限与突破方向",
    );

    expect(titleOfThread(thread)).toBe(
      "GNN和MLP在Virtual Cell Foundation Model中的局限与突破方向",
    );
  });

  it("rejects generic conversation summary labels and falls back to the first user message", () => {
    const thread = makeThread(
      "Here is a summary of the conversation to date:",
      "论文文件生成与 LaTeX 编译排错",
    );

    expect(cleanThreadTitle("Here is a summary of the conversation to date:")).toBe("");
    expect(cleanThreadTitle("Conversation Summary")).toBe("");
    expect(cleanThreadTitle("Summary of this conversation")).toBe("");
    expect(titleOfThread(thread)).toBe("论文文件生成与 LaTeX 编译排错");
  });

  it("keeps normal titles and removes common labels", () => {
    expect(cleanThreadTitle("Title: Claim-Level Evidence Audit")).toBe(
      "Claim-Level Evidence Audit",
    );
    expect(cleanThreadTitle("论文文件生成与 LaTeX 编译排错")).toBe(
      "论文文件生成与 LaTeX 编译排错",
    );
  });

  it("cleans active thread state titles for header and notifications", () => {
    expect(
      titleOfThreadState({
        title:
          "<think>The title prompt was echoed.</think>\nQuality Audit Repair Loop",
        messages: [],
      }),
    ).toBe("Quality Audit Repair Loop");
  });
});
