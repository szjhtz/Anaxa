import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PromptInputProvider } from "@/components/ai-elements/prompt-input";
import { I18nProvider } from "@/core/i18n/context";

import { InputBox } from "./input-box";
import { ThreadContext } from "./messages/context";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/core/models/hooks", () => ({
  useModels: () => ({
    models: [
      {
        name: "safe-model",
        display_name: "Safe Model",
        model: "safe-model",
        supports_thinking: false,
      },
    ],
  }),
}));

function wrapper({ children }: PropsWithChildren) {
  const client = new QueryClient();
  return (
    <QueryClientProvider client={client}>
      <I18nProvider initialLocale="zh-CN">
        <ThreadContext.Provider
          value={{
            isMock: true,
            thread: {
              messages: [],
              values: { title: "", messages: [], artifacts: [] },
            } as never,
          }}
        >
          <PromptInputProvider>{children}</PromptInputProvider>
        </ThreadContext.Provider>
      </I18nProvider>
    </QueryClientProvider>
  );
}

describe("InputBox synthetic experiment mode", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    vi.stubGlobal(
      "ResizeObserver",
      vi.fn().mockImplementation(() => ({
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      })),
    );
  });

  it("replaces new-chat shortcut suggestions with one synthetic experiment toggle", () => {
    const onContextChange = vi.fn();

    render(
      <InputBox
        context={{
          mode: "flash",
          model_name: "safe-model",
          reasoning_effort: undefined,
          synthetic_data_mode: false,
        }}
        threadId="thread-1"
        isNewThread
        onContextChange={onContextChange}
      />,
      { wrapper },
    );

    expect(screen.getByText(/模拟实验模式|Simulation mode/)).toBeInTheDocument();
    expect(
      screen.getByText(/允许模拟个人实验数据|Allow simulated personal experiment data/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/写作|Write/)).not.toBeInTheDocument();
    expect(screen.queryByText(/研究|Research/)).not.toBeInTheDocument();
    expect(screen.queryByText(/收集|Collect/)).not.toBeInTheDocument();
    expect(screen.queryByText(/学习|Learn/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("switch", { name: /模拟实验模式|Simulation mode/ }));

    expect(onContextChange).toHaveBeenCalledWith(
      expect.objectContaining({ synthetic_data_mode: true }),
    );
  });
});
