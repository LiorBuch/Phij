"use client";

import { cameraStatusSchema, streamInfoSchema, type CameraStatus } from "@phij/contracts";
import { useCallback, useEffect, useRef, useState } from "react";
import { connectWhep, type WhepSession } from "@/lib/whep";

function serviceUrl(configured: string | undefined, port: number, path = "") {
  if (configured) return configured;
  const hostname = window.location.hostname;
  return `${window.location.protocol}//${hostname}:${port}${path}`;
}

export default function Home() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const sessionRef = useRef<WhepSession | null>(null);
  const [camera, setCamera] = useState<CameraStatus | null>(null);
  const [player, setPlayer] = useState("Waiting for camera");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const apiUrl = serviceUrl(process.env.NEXT_PUBLIC_API_URL, 4000);
        const response = await fetch(`${apiUrl}/api/cameras/dog-cam`, {cache: "no-store"});
        if (active) setCamera(cameraStatusSchema.parse(await response.json()));
      } catch {
        if (active) setCamera(null);
      }
    };
    void poll();
    const timer = window.setInterval(poll, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    if (camera?.state !== "streaming" || !videoRef.current) return;
    let cancelled = false;
    const connect = async () => {
      setPlayer("Connecting");
      try {
        const apiUrl = serviceUrl(process.env.NEXT_PUBLIC_API_URL, 4000);
        const fallbackWhep = serviceUrl(
          process.env.NEXT_PUBLIC_WHEP_URL,
          8889,
          "/dog-cam/whep",
        );
        const response = await fetch(`${apiUrl}/api/stream`, {cache: "no-store"});
        const stream = response.ok ? streamInfoSchema.parse(await response.json()) : null;
        const configuredUrl = stream?.whepUrl;
        const whepUrl = configuredUrl?.includes("localhost") ? fallbackWhep : configuredUrl ?? fallbackWhep;
        const session = await connectWhep(whepUrl, videoRef.current!, (state) => {
          if (!cancelled) setPlayer(state === "connected" ? "Live" : state);
        });
        if (cancelled) await session.close(); else sessionRef.current = session;
      } catch (error) {
        if (!cancelled) setPlayer(error instanceof Error ? error.message : "Connection failed");
      }
    };
    void connect();
    return () => { cancelled = true; void sessionRef.current?.close(); sessionRef.current = null; };
  }, [camera?.state, attempt]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  const isLive = camera?.state === "streaming";

  return (
    <main>
      <header><div><span className="eyebrow">PHIJ HOME</span><h1>Dog Cam</h1></div>
        <span className={`status ${isLive ? "online" : ""}`}>{isLive ? "Camera online" : camera?.state ?? "API unavailable"}</span>
      </header>
      <section className="viewer">
        <video ref={videoRef} autoPlay muted playsInline />
        {!isLive && <div className="empty"><strong>No live picture</strong><span>{camera?.message ?? "Checking the camera service…"}</span></div>}
        <div className="player-state">{player}</div>
      </section>
      <footer>
        <div><span>Last heartbeat</span><strong>{camera?.lastHeartbeatAt ? new Date(camera.lastHeartbeatAt).toLocaleString() : "Never"}</strong></div>
        <button onClick={retry}>Reconnect video</button>
      </footer>
    </main>
  );
}
