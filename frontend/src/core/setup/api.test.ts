import { afterEach, describe, expect, it, vi } from "vitest";

import {
  saveSetupModels,
  testImageProvider,
} from "./api";

const fetchWithTimeoutMock = vi.fn();

vi.mock("@/core/api/fetch", () => ({
  fetchWithTimeout: (...args: unknown[]) => fetchWithTimeoutMock(...args),
}));

vi.mock("@/core/config", () => ({
  getBackendBaseURL: () => "",
}));

describe("setup api", () => {
  afterEach(() => {
    fetchWithTimeoutMock.mockReset();
  });

  it("surfaces backend detail when save fails", async () => {
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Active image provider requires a model." }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      saveSetupModels({
        models: [],
        tool_keys: [],
        image_generation: null,
      }),
    ).rejects.toThrow("Active image provider requires a model.");
  });

  it("sends the expected payload for image provider tests", async () => {
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(JSON.stringify({ success: true, message: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await testImageProvider({
      provider: "openai-compatible",
      model: "gpt-image-1",
      api_key: "sk-test",
      base_url: "https://images.example.com/v1",
    });

    expect(fetchWithTimeoutMock).toHaveBeenCalledWith(
      "/api/setup/test-image-provider",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "openai-compatible",
          model: "gpt-image-1",
          api_key: "sk-test",
          base_url: "https://images.example.com/v1",
        }),
        timeoutMs: 190_000,
        timeoutErrorMessage: "Current image model validation timed out after about 3 minutes. Please retry later.",
      }),
    );
  });

  it("surfaces backend detail when image provider test fails", async () => {
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "OpenAI-compatible image provider returned a non-JSON response." }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      testImageProvider({
        provider: "openai-compatible",
        model: "gpt-image-1",
        api_key: "sk-test",
        base_url: "https://images.example.com/v1",
      }),
    ).rejects.toThrow("OpenAI-compatible image provider returned a non-JSON response.");
  });

  it("shows a specific fallback when the reverse proxy returns 504", async () => {
    fetchWithTimeoutMock.mockResolvedValue(
      new Response("<html>gateway timeout</html>", {
        status: 504,
        headers: { "Content-Type": "text/html" },
      }),
    );

    await expect(
      testImageProvider({
        provider: "google-ai-studio",
        model: "gemini-3-pro-image-preview",
        api_key: "google-key",
        base_url: null,
      }),
    ).rejects.toThrow("Image model validation timed out in the gateway before the backend replied.");
  });
});
