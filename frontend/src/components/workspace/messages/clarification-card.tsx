"use client";

import { useEffect, useState } from "react";

import { usePromptInputController } from "@/components/ai-elements/prompt-input";
import { Button } from "@/components/ui/button";

export function ClarificationCard({
  payload,
  fallbackContent,
  onSubmit,
  resolvedAnswer,
  isLoading = false,
}: {
  payload:
    | {
        question?: string;
        clarification_type?: string;
        context?: string;
        options?: string[];
        allow_custom_input?: boolean;
      }
    | null;
  fallbackContent: string;
  onSubmit?: (text: string) => Promise<void>;
  resolvedAnswer?: string | null;
  isLoading?: boolean;
}) {
  const { textInput } = usePromptInputController();
  const [pendingChoice, setPendingChoice] = useState<string | null>(null);
  const [isSubmittingChoice, setIsSubmittingChoice] = useState(false);

  const options = payload?.options ?? [];
  const question = payload?.question ?? fallbackContent;
  const context = payload?.context;
  const allowCustomInput = payload?.allow_custom_input !== false;

  useEffect(() => {
    if (resolvedAnswer) {
      setPendingChoice(null);
      setIsSubmittingChoice(false);
    }
  }, [resolvedAnswer]);

  const selectedAnswer = resolvedAnswer ?? pendingChoice;
  const isLocked = Boolean(selectedAnswer) || isSubmittingChoice || isLoading;
  const hasCustomSelection =
    Boolean(selectedAnswer) && !options.includes(selectedAnswer ?? "");

  const handlePick = async (choice: string) => {
    if (isLocked) {
      return;
    }
    setPendingChoice(choice);
    setIsSubmittingChoice(true);
    try {
      await onSubmit?.(choice);
    } catch {
      setPendingChoice(null);
      setIsSubmittingChoice(false);
    }
  };

  const handleCustom = () => {
    if (isLocked) {
      return;
    }
    textInput.setInput("");
    requestAnimationFrame(() => {
      document
        .querySelector<HTMLTextAreaElement>("textarea[name='message']")
        ?.focus();
    });
  };

  return (
    <div className="min-w-0 max-w-full overflow-hidden rounded-2xl border bg-background p-4">
      {context && (
        <div className="text-muted-foreground mb-2 text-sm">{context}</div>
      )}
      <div className="mb-3 text-sm font-medium">{question}</div>

      {hasCustomSelection && selectedAnswer && (
        <div className="bg-muted mb-3 rounded-xl px-3 py-2 text-sm break-words">
          {selectedAnswer}
        </div>
      )}

      <div className="w-full min-w-0 space-y-2">
        {options.length > 0 && (
          <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
            {options.map((option) => {
              const isSelected = selectedAnswer === option;
              return (
                <Button
                  key={option}
                  variant={isSelected ? "default" : "secondary"}
                  className="h-auto w-full max-w-full justify-start whitespace-normal break-words px-4 py-3 text-left leading-5"
                  disabled={isLocked}
                  onClick={() => void handlePick(option)}
                >
                  {option}
                </Button>
              );
            })}
          </div>
        )}

        {allowCustomInput && (
          <Button
            variant="outline"
            className="h-auto max-w-full whitespace-normal break-words"
            disabled={isLocked}
            onClick={handleCustom}
          >
            type something
          </Button>
        )}
      </div>
    </div>
  );
}
