import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/core/i18n/context";
import type { PlanState } from "@/core/threads/types";

import { PlanApprovalCard } from "./plan-approval-card";

const mocks = vi.hoisted(() => ({
  updateState: vi.fn(),
}));

vi.mock("@/core/api", () => ({
  getAPIClient: vi.fn(() => ({
    threads: {
      updateState: (...args: unknown[]) => mocks.updateState(...args),
    },
  })),
}));

function wrapper({ children }: PropsWithChildren) {
  return <I18nProvider initialLocale="zh-CN">{children}</I18nProvider>;
}

const awaitingPlan: PlanState = {
  summary: "先完成证据地图，再生成论文交付物",
  phases: ["确认研究问题", "设计实验与消融", "生成成稿"],
  deliverables: ["experiment_contract.json", "manuscript.tex"],
  open_questions: ["是否需要中文摘要？"],
  acceptance_criteria: ["所有结论都有证据来源"],
  risk_points: ["公开 benchmark 可能需要登录"],
  status: "awaiting_approval",
  revision_count: 1,
  updated_at: "2026-05-09T00:00:10Z",
  revisions: [
    {
      revision_number: 1,
      source: "agent",
      note: "Initial plan",
      status: "awaiting_approval",
      updated_at: "2026-05-09T00:00:10Z",
    },
  ],
};

describe("PlanApprovalCard", () => {
  beforeEach(() => {
    document.cookie = "locale=zh-CN; path=/; max-age=31536000";
  });

  afterEach(() => {
    mocks.updateState.mockReset();
    document.body.innerHTML = "";
    document.cookie = "locale=; max-age=0; path=/";
  });

  it("shows the current plan in the main conversation and approves it", async () => {
    mocks.updateState.mockResolvedValue(undefined);
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <PlanApprovalCard
        plan={awaitingPlan}
        threadId="thread-1"
        onSubmit={onSubmit}
      />,
      { wrapper },
    );

    expect(screen.getByText("待确认计划")).toBeInTheDocument();
    expect(screen.getByText("先完成证据地图，再生成论文交付物")).toBeInTheDocument();
    expect(screen.getByText("确认研究问题")).toBeInTheDocument();
    expect(screen.getByText("experiment_contract.json")).toBeInTheDocument();
    expect(screen.getByText("是否需要中文摘要？")).toBeInTheDocument();
    expect(screen.getByText(/也可以直接回复/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /批准并执行/ }));

    await waitFor(() => {
      expect(mocks.updateState).toHaveBeenCalledWith(
        "thread-1",
        expect.objectContaining({
          values: {
            plan: expect.objectContaining({
              status: "approved",
              revision_count: 2,
            }),
          },
        }),
      );
    });
    expect(onSubmit).toHaveBeenCalledWith("我批准当前计划，请按计划执行。");
    expect(screen.queryByRole("button", { name: /批准并执行/ })).not.toBeInTheDocument();
  });

  it("does not show approval actions after the plan is approved", () => {
    render(
      <PlanApprovalCard
        plan={{ ...awaitingPlan, status: "approved" }}
        threadId="thread-1"
      />,
      { wrapper },
    );

    expect(screen.getByText("先完成证据地图，再生成论文交付物")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /批准并执行/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /修改计划/ })).not.toBeInTheDocument();
  });

  it("focuses the message input when revising the plan", async () => {
    render(
      <>
        <textarea name="message" />
        <PlanApprovalCard plan={awaitingPlan} threadId="thread-1" />
      </>,
      { wrapper },
    );

    fireEvent.click(screen.getByRole("button", { name: /修改计划/ }));

    await waitFor(() => {
      expect(document.querySelector("textarea[name='message']")).toHaveFocus();
    });
  });
});
