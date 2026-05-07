import { expect, test } from "@playwright/test";

type MockMessage = {
  type: "human" | "ai";
  content: string;
  id: string;
};

function sseEvent(id: string, event: string, data: unknown): string {
  return `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

test("chat streaming, feedback toggle, and sidebar remain functional", async ({
  page,
}) => {
  const now = new Date("2026-05-07T12:00:00.000Z").toISOString();
  const state: {
    threadId: string;
    runId: string;
    title: string;
    messages: MockMessage[];
    feedback: null | {
      feedback_id: string;
      run_id: string;
      thread_id: string;
      rating: 1 | -1;
      created_at: string;
      updated_at?: string;
    };
  } = {
    threadId: "thread-smoke-1",
    runId: "run-smoke-1",
    title: "Smoke Thread",
    messages: [],
    feedback: null,
  };
  let streamRequestSeen = false;

  await page.route("**/api/langgraph/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith("/threads") && request.method() === "POST") {
      const payload = request.postDataJSON() as { thread_id?: string };
      state.threadId = payload.thread_id ?? state.threadId;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          thread_id: state.threadId,
          created_at: now,
          updated_at: now,
          metadata: {},
          status: "idle",
          values: { title: "", messages: [], artifacts: [] },
          interrupts: {},
        }),
      });
      return;
    }

    if (path.endsWith("/threads/search") && request.method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          state.messages.length === 0
            ? []
            : [
                {
                  thread_id: state.threadId,
                  created_at: now,
                  updated_at: now,
                  state_updated_at: now,
                  metadata: {},
                  status: "idle",
                  values: {
                    title: state.title,
                    messages: state.messages,
                    artifacts: [],
                  },
                  interrupts: {},
                },
              ],
        ),
      });
      return;
    }

    if (
      path.endsWith(`/threads/${state.threadId}/history`) &&
      request.method() === "POST"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            checkpoint: { checkpoint_id: "cp-smoke-1" },
            values: {
              title: state.title,
              messages: state.messages,
              artifacts: [],
            },
            metadata: {},
            created_at: now,
          },
        ]),
      });
      return;
    }

    if (
      path.endsWith(`/threads/${state.threadId}/state`) &&
      request.method() === "GET"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          checkpoint: { checkpoint_id: "cp-smoke-1" },
          values: {
            title: state.title,
            messages: state.messages,
            artifacts: [],
          },
          metadata: {},
        }),
      });
      return;
    }

    if (
      path.endsWith(`/threads/${state.threadId}/runs/stream`) &&
      request.method() === "POST"
    ) {
      streamRequestSeen = true;
      const payload = request.postDataJSON() as {
        input?: { messages?: Array<{ content?: string }> };
      };
      const prompt =
        payload.input?.messages?.[0]?.content ?? "Hello from smoke test";
      state.messages = [
        { type: "human", content: prompt, id: "msg-human-1" },
        {
          type: "ai",
          content: "Mock assistant response",
          id: "msg-ai-1",
        },
      ];
      const body = [
        sseEvent("1", "messages-tuple", {
          type: "ai",
          content: "Mock assistant response",
          id: "msg-ai-1",
        }),
        sseEvent("2", "values", {
          title: state.title,
          messages: state.messages,
          artifacts: [],
        }),
        sseEvent("3", "end", {
          usage: {
            input_tokens: 1,
            output_tokens: 1,
            total_tokens: 2,
          },
        }),
      ].join("");
      await route.fulfill({
        status: 200,
        headers: {
          "content-type": "text/event-stream; charset=utf-8",
          "Content-Location": `/threads/${state.threadId}/runs/${state.runId}`,
          "Cache-Control": "no-cache",
        },
        body,
      });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: `Unhandled mock request: ${path}` }),
    });
  });

  await page.route("**/api/threads/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (
      path.endsWith(`/api/threads/${state.threadId}/runs`) &&
      request.method() === "POST"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: state.runId,
          thread_id: state.threadId,
          assistant_id: "lead_agent",
          status: "running",
          metadata: {},
          kwargs: {},
          multitask_strategy: "reject",
          created_at: now,
          updated_at: now,
        }),
      });
      return;
    }

    if (
      path.endsWith(`/api/threads/${state.threadId}/runs/${state.runId}/complete`) &&
      request.method() === "POST"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: state.runId,
          thread_id: state.threadId,
          assistant_id: "lead_agent",
          status: "success",
          metadata: {},
          kwargs: {},
          multitask_strategy: "reject",
          created_at: now,
          updated_at: now,
        }),
      });
      return;
    }

    if (
      path.endsWith(`/api/threads/${state.threadId}/runs/${state.runId}/feedback`) &&
      request.method() === "GET"
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.feedback),
      });
      return;
    }

    if (
      path.endsWith(`/api/threads/${state.threadId}/runs/${state.runId}/feedback`) &&
      request.method() === "PUT"
    ) {
      const payload = request.postDataJSON() as { rating: 1 | -1 };
      state.feedback = {
        feedback_id: "feedback-smoke-1",
        run_id: state.runId,
        thread_id: state.threadId,
        rating: payload.rating,
        created_at: now,
        updated_at: now,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.feedback),
      });
      return;
    }

    if (
      path.endsWith(`/api/threads/${state.threadId}/runs/${state.runId}/feedback`) &&
      request.method() === "DELETE"
    ) {
      state.feedback = null;
      await route.fulfill({ status: 204, body: "" });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: `Unhandled backend request: ${path}` }),
    });
  });

  await page.route("**/api/models", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        models: [
          {
            id: "smoke-model",
            name: "smoke-model",
            model: "smoke-model",
            display_name: "Smoke Model",
          },
        ],
      }),
    });
  });

  await page.addInitScript(() => {
    window.sessionStorage.setItem("medrix_flow.setup-prompted", "1");
  });

  await page.goto("/workspace/chats/new");

  await expect(page.getByTestId("workspace-sidebar")).toBeVisible();

  const textarea = page.locator("textarea[name='message']");
  await textarea.fill("Smoke test prompt");
  await textarea.press("Enter");
  await expect.poll(() => streamRequestSeen).toBe(true);

  await expect(page.getByText("Mock assistant response")).toBeVisible();
  await expect(page.getByTestId("workspace-sidebar")).toContainText(
    "Smoke Thread",
  );

  const assistantMessage = page.getByTestId("assistant-message-with-feedback");
  await assistantMessage.hover();

  const thumbsUp = page.getByTestId("message-feedback-up");
  await expect(thumbsUp).toBeVisible();
  await thumbsUp.click();
  await expect(thumbsUp).toHaveAttribute("aria-pressed", "true");

  await thumbsUp.click();
  await expect(thumbsUp).toHaveAttribute("aria-pressed", "false");
});
