import { describe, expect, it } from "vitest";
import { cameraStatusSchema, streamInfoSchema } from "../src";

describe("API contracts", () => {
  it("validates camera and stream responses", () => {
    expect(cameraStatusSchema.parse({
      cameraId: "dog-cam", state: "offline", lastHeartbeatAt: null, publishedAt: null,
    }).state).toBe("offline");
    expect(streamInfoSchema.parse({
      name: "dog-cam", whepUrl: "http://localhost:8889/dog-cam/whep",
    }).name).toBe("dog-cam");
  });
});
