import { getBackendBaseURL } from "@/core/config";

import { fetchWithTimeout } from "./fetch";

export type FeedbackData = {
  feedback_id: string;
  run_id: string;
  thread_id: string;
  rating: 1 | -1;
  comment?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export async function getRunFeedback(
  threadId: string,
  runId: string,
): Promise<FeedbackData | null> {
  const response = await fetchWithTimeout(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/runs/${encodeURIComponent(runId)}/feedback`,
  );
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(error.detail ?? "Failed to load feedback.");
  }
  return response.json() as Promise<FeedbackData | null>;
}

export async function putRunFeedback(
  threadId: string,
  runId: string,
  rating: 1 | -1,
): Promise<FeedbackData> {
  const response = await fetchWithTimeout(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/runs/${encodeURIComponent(runId)}/feedback`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating }),
    },
  );
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(error.detail ?? "Failed to save feedback.");
  }
  return response.json() as Promise<FeedbackData>;
}

export async function deleteRunFeedback(
  threadId: string,
  runId: string,
): Promise<void> {
  const response = await fetchWithTimeout(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/runs/${encodeURIComponent(runId)}/feedback`,
    {
      method: "DELETE",
    },
  );
  if (!response.ok && response.status !== 404) {
    const error = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(error.detail ?? "Failed to delete feedback.");
  }
}
