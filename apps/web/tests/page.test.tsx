import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "../src/app/page";

describe("dog camera viewer", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      json: async () => ({
        cameraId: "dog-cam",
        state: "offline",
        message: "No heartbeat received",
        lastHeartbeatAt: null,
        publishedAt: null,
      }),
    }));
  });

  it("shows a useful offline state", async () => {
    render(<Home />);
    expect(await screen.findByText("No heartbeat received")).toBeTruthy();
    expect(screen.getByRole("button", {name: "Reconnect video"})).toBeTruthy();
  });
});
