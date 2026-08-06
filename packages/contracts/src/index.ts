import { z } from "zod";

export const cameraStatusSchema = z.object({
  cameraId: z.string(),
  state: z.enum(["starting", "streaming", "error", "offline"]),
  message: z.string().nullable().optional(),
  lastHeartbeatAt: z.iso.datetime().nullable(),
  publishedAt: z.iso.datetime().nullable(),
});

export const streamInfoSchema = z.object({
  name: z.string(),
  whepUrl: z.url(),
});

export type CameraStatus = z.infer<typeof cameraStatusSchema>;
export type StreamInfo = z.infer<typeof streamInfoSchema>;
