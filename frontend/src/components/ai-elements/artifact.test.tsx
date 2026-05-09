import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ArtifactAction } from "./artifact";

describe("ArtifactAction", () => {
  it("renders asChild tooltip actions without adding an extra slotted child", () => {
    expect(() =>
      render(
        <ArtifactAction asChild tooltip="Open in new window">
          <a href="#artifact" aria-label="Open in new window">
            Open
          </a>
        </ArtifactAction>,
      ),
    ).not.toThrow();

    expect(
      screen.getByRole("link", { name: "Open in new window" }),
    ).toHaveAttribute("href", "#artifact");
  });

  it("keeps the generated accessible label for regular button actions", () => {
    render(
      <ArtifactAction tooltip="Close">
        <span aria-hidden="true">X</span>
      </ArtifactAction>,
    );

    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });
});
