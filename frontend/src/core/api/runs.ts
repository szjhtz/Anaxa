import { getBackendBaseURL } from "@/core/config";

import { fetchWithTimeout } from "./fetch";

export type RunData = {
  run_id: string;
  thread_id: string;
  assistant_id?: string | null;
  status: string;
  metadata: Record<string, unknown>;
  kwargs: Record<string, unknown>;
  multitask_strategy: string;
  created_at: string;
  updated_at: string;
};

export async function registerThreadRun(
  threadId: string,
  runId: string,
  options?: {
    assistantId?: string;
    context?: Record<string, unknown>;
  },
): Promise<RunData> {
  const response = await fetchWithTimeout(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/runs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: runId,
        assistant_id: options?.assistantId,
        context: options?.context,
      }),
    },
  );
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(error.detail ?? "Failed to register run.");
  }
  return response.json() as Promise<RunData>;
}

export async function completeThreadRun(
  threadId: string,
  runId: string,
  status: "success" | "interrupted" | "error" = "success",
): Promise<RunData> {
  const response = await fetchWithTimeout(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/runs/${encodeURIComponent(runId)}/complete`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(error.detail ?? "Failed to complete run.");
  }
  return response.json() as Promise<RunData>;
}
