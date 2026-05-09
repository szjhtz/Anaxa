import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PromptInput, PromptInputTextarea } from "./prompt-input";

const renderPromptInput = (onSubmit: Parameters<typeof PromptInput>[0]["onSubmit"]) => {
  render(
    <PromptInput onSubmit={onSubmit}>
      <PromptInputTextarea placeholder="Message" />
      <button type="submit">Send</button>
    </PromptInput>,
  );

  return screen.getByPlaceholderText("Message") as HTMLTextAreaElement;
};

describe("PromptInputTextarea", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("submits on Enter when the user is not composing text", async () => {
    const onSubmit = vi.fn();
    const textarea = renderPromptInput(onSubmit);

    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter", code: "Enter" });

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls.at(0)?.[0]).toMatchObject({ text: "hello" });
  });

  it("does not submit when Enter confirms a just-finished IME composition", async () => {
    vi.useFakeTimers();
    const onSubmit = vi.fn();
    const textarea = renderPromptInput(onSubmit);

    fireEvent.change(textarea, { target: { value: "nihao" } });
    fireEvent.compositionStart(textarea);
    fireEvent.compositionEnd(textarea);
    const wasNotCanceled = fireEvent.keyDown(textarea, {
      key: "Enter",
      code: "Enter",
    });

    expect(onSubmit).not.toHaveBeenCalled();
    expect(wasNotCanceled).toBe(false);

    act(() => {
      vi.advanceTimersByTime(151);
    });
    fireEvent.keyDown(textarea, { key: "Enter", code: "Enter" });
    await act(async () => {
      await Promise.resolve();
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("does not submit IME Enter events reported with keyCode 229", () => {
    const onSubmit = vi.fn();
    const textarea = renderPromptInput(onSubmit);

    fireEvent.change(textarea, { target: { value: "abc" } });
    fireEvent.keyDown(textarea, {
      key: "Enter",
      code: "Enter",
      keyCode: 229,
      which: 229,
    });

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
