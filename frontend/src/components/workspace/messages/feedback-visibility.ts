export function shouldShowRunFeedback(options: {
  messageType: string;
  isLoading?: boolean;
  runId?: string | null;
}) {
  return (
    options.messageType !== "human" &&
    !options.isLoading &&
    typeof options.runId === "string" &&
    options.runId.length > 0
  );
}
