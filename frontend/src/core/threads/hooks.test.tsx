import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useThreadStream } from "./hooks";

const mocks = vi.hoisted(() => ({
  registerThreadRun: vi.fn(),
  completeThreadRun: vi.fn(),
  createRunEvent: vi.fn(),
  updateSubtask: vi.fn(),
  toastError: vi.fn(),
  submit: vi.fn(),
}));

let capturedOptions: Record<string, unknown> | null = null;

vi.mock("@langchain/langgraph-sdk/react", () => ({
  useStream: vi.fn((options) => {
    capturedOptions = options;
    return {
      messages: [],
      isLoading: false,
      isThreadLoading: false,
      values: { title: "", messages: [], artifacts: [] },
      stop: vi.fn(),
      submit: mocks.submit,
    };
  }),
}));

vi.mock("@/core/api", () => ({
  getAPIClient: vi.fn(() => ({
    threads: {
      getState: vi.fn(),
    },
  })),
}));

vi.mock("@/core/api/runs", () => ({
  registerThreadRun: (...args: unknown[]) => mocks.registerThreadRun(...args),
  completeThreadRun: (...args: unknown[]) => mocks.completeThreadRun(...args),
  createRunEvent: (...args: unknown[]) => mocks.createRunEvent(...args),
}));

vi.mock("@/core/i18n/hooks", () => ({
  useI18n: () => ({
    t: {
      setup: {
        noModelsConfigured: "No model",
        noModelsConfiguredHint: "Hint",
        openSettings: "Open settings",
      },
      uploads: { uploadingFiles: "Uploading files" },
      common: { thinking: "Thinking" },
    },
  }),
}));

vi.mock("@/core/tasks/context", () => ({
  useUpdateSubtask: () => mocks.updateSubtask,
}));

vi.mock("sonner", () => ({
  toast: {
    error: mocks.toastError,
  },
}));

vi.mock("@/core/settings/events", () => ({
  dispatchOpenSettings: vi.fn(),
}));

function wrapper({ children }: PropsWithChildren) {
  const client = new QueryClient();
  return (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe("useThreadStream", () => {
  afterEach(() => {
    capturedOptions = null;
    mocks.registerThreadRun.mockReset();
    mocks.completeThreadRun.mockReset();
    mocks.createRunEvent.mockReset();
    mocks.updateSubtask.mockReset();
    mocks.toastError.mockReset();
    mocks.submit.mockReset();
  });

  it("captures run_id from useStream metadata and sideband-registers it", async () => {
    mocks.registerThreadRun.mockResolvedValue(undefined);
    mocks.createRunEvent.mockResolvedValue(undefined);

    const { result } = renderHook(
      () =>
        useThreadStream({
          threadId: "thread-1",
          context: {
            mode: "flash",
            model_name: undefined,
            reasoning_effort: undefined,
          },
        }),
      { wrapper },
    );

    expect(capturedOptions).not.toBeNull();

    await act(async () => {
      (capturedOptions?.onCreated as (meta: { thread_id: string; run_id: string }) => void)({
        thread_id: "thread-1",
        run_id: "run-1",
      });
    });

    await waitFor(() => {
      expect(result.current[4]).toBe("run-1");
    });
    expect(mocks.registerThreadRun).toHaveBeenCalledWith("thread-1", "run-1", {
      assistantId: "lead_agent",
      context: {
        mode: "flash",
        model_name: undefined,
        reasoning_effort: undefined,
      },
    });
  });

  it("records tool-start events so workflow can reconstruct decisions", async () => {
    mocks.registerThreadRun.mockResolvedValue(undefined);
    mocks.createRunEvent.mockResolvedValue(undefined);

    renderHook(
      () =>
        useThreadStream({
          threadId: "thread-1",
          context: {
            mode: "flash",
            model_name: undefined,
            reasoning_effort: undefined,
          },
        }),
      { wrapper },
    );

    await act(async () => {
      (capturedOptions?.onCreated as (meta: { thread_id: string; run_id: string }) => void)({
        thread_id: "thread-1",
        run_id: "run-1",
      });
      (
        capturedOptions?.onLangChainEvent as (event: {
          event: string;
          name: string;
          run_id?: string;
          data?: unknown;
        }) => void
      )({
        event: "on_tool_start",
        name: "record_decision",
        run_id: "decision-call-1",
        data: {
          input: {
            title: "Choose benchmark discovery",
            decision_type: "tool_selection",
            rationale: "Need a benchmark map before experiments.",
            next_step: "Run dataset_benchmark_discovery.",
            status: "running",
          },
        },
      });
    });

    await waitFor(() => {
      expect(mocks.createRunEvent).toHaveBeenCalledWith(
        "thread-1",
        "run-1",
        expect.objectContaining({
          event_type: "ai_tool_calls",
          caller: "assistant",
          content: expect.objectContaining({
            tool_calls: [
              expect.objectContaining({
                name: "record_decision",
                id: "decision-call-1",
                args: expect.objectContaining({
                  title: "Choose benchmark discovery",
                }),
              }),
            ],
          }),
        }),
      );
    });
  });

  it("marks ordinary text requests as non-visual", async () => {
    mocks.submit.mockResolvedValue(undefined);

    const { result } = renderHook(
      () =>
        useThreadStream({
          threadId: "thread-1",
          context: {
            mode: "flash",
            model_name: undefined,
            reasoning_effort: undefined,
          },
        }),
      { wrapper },
    );

    await act(async () => {
      await result.current[1]("thread-1", {
        text: "帮我解释一下这个配置为什么报错",
        files: [],
      });
    });

    expect(mocks.submit).toHaveBeenCalledOnce();
    expect(mocks.submit.mock.calls[0]?.[1]?.context.visual_output_intent).toBe(false);
  });

  it("marks explicit visual requests as visual output intent", async () => {
    mocks.submit.mockResolvedValue(undefined);

    const { result } = renderHook(
      () =>
        useThreadStream({
          threadId: "thread-1",
          context: {
            mode: "flash",
            model_name: undefined,
            reasoning_effort: undefined,
          },
        }),
      { wrapper },
    );

    await act(async () => {
      await result.current[1]("thread-1", {
        text: "帮我画一个架构图",
        files: [],
      });
    });

    expect(mocks.submit).toHaveBeenCalledOnce();
    expect(mocks.submit.mock.calls[0]?.[1]?.context.visual_output_intent).toBe(true);
  });

  it("passes synthetic data mode through thread context", async () => {
    mocks.submit.mockResolvedValue(undefined);

    const { result } = renderHook(
      () =>
        useThreadStream({
          threadId: "thread-1",
          context: {
            mode: "flash",
            model_name: undefined,
            reasoning_effort: undefined,
            synthetic_data_mode: true,
          },
        }),
      { wrapper },
    );

    await act(async () => {
      await result.current[1]("thread-1", {
        text: "帮我完成一篇实验论文",
        files: [],
      });
    });

    expect(mocks.submit).toHaveBeenCalledOnce();
    expect(mocks.submit.mock.calls[0]?.[1]?.context.synthetic_data_mode).toBe(true);
  });
});
