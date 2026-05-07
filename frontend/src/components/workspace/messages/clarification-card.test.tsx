import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ClarificationCard } from "./clarification-card";

const setInputMock = vi.fn();

vi.mock("@/components/ai-elements/prompt-input", () => ({
  usePromptInputController: () => ({
    textInput: {
      setInput: setInputMock,
    },
  }),
}));

describe("ClarificationCard", () => {
  it("locks immediately after picking an option so repeated clicks do not submit twice", async () => {
    const onSubmit = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          setTimeout(resolve, 10);
        }),
    );

    render(
      <ClarificationCard
        payload={{
          question: "Choose one",
          options: ["Option A", "Option B"],
        }}
        fallbackContent=""
        onSubmit={onSubmit}
      />,
    );

    const optionA = screen.getByRole("button", { name: "Option A" });
    const optionB = screen.getByRole("button", { name: "Option B" });

    fireEvent.click(optionA);
    fireEvent.click(optionB);

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("Option A");
    expect(optionA).toBeDisabled();
    expect(optionB).toBeDisabled();

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
  });

  it("renders resolved answers as locked state on old clarification cards", () => {
    render(
      <ClarificationCard
        payload={{
          question: "Choose one",
          options: ["Option A", "Option B"],
        }}
        fallbackContent=""
        resolvedAnswer="Custom answer"
      />,
    );

    expect(screen.getByText("Custom answer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Option A" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Option B" })).toBeDisabled();
  });
});
