"use client";

import { cameraStatusSchema, streamInfoSchema, type CameraStatus } from "@phij/contracts";
import { useCallback, useEffect, useRef, useState } from "react";
import { connectHls } from "@/lib/hls";
import { connectWhep, type WhepSession } from "@/lib/whep";

function localServiceUrl(configured: string | undefined, port: number, path = "") {
  if (configured && !configured.includes("localhost")) return configured;
  const hostname = window.location.hostname;
  return `${window.location.protocol}//${hostname}:${port}${path}`;
}

export default function Home() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const sessionRef = useRef<WhepSession | null>(null);
  const [camera, setCamera] = useState<CameraStatus | null>(null);
  const [player, setPlayer] = useState("Waiting for camera");
  const [attempt, setAttempt] = useState(0);
  const [muted, setMuted] = useState(true);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const response = await fetch("/api/cameras/dog-cam", {cache: "no-store"});
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
        const secureRemote = window.location.protocol === "https:";
        let session: WhepSession;
        if (secureRemote) {
          session = await connectHls(
            `${window.location.origin}/dog-cam/index.m3u8`,
            videoRef.current!,
            (state) => { if (!cancelled) setPlayer(state); },
          );
        } else {
          const fallbackWhep = localServiceUrl(
            process.env.NEXT_PUBLIC_WHEP_URL,
            8889,
            "/dog-cam/whep",
          );
          const response = await fetch("/api/stream", {cache: "no-store"});
          const stream = response.ok ? streamInfoSchema.parse(await response.json()) : null;
          const configuredUrl = stream?.whepUrl;
          const whepUrl = configuredUrl?.includes("localhost")
            ? fallbackWhep
            : configuredUrl ?? fallbackWhep;
          session = await connectWhep(whepUrl, videoRef.current!, (state) => {
            if (!cancelled) setPlayer(state === "connected" ? "Live (LAN WebRTC)" : state);
          });
        }
        if (cancelled) await session.close(); else sessionRef.current = session;
      } catch (error) {
        if (!cancelled) setPlayer(error instanceof Error ? error.message : "Connection failed");
      }
    };
    void connect();
    return () => { cancelled = true; void sessionRef.current?.close(); sessionRef.current = null; };
  }, [camera?.state, attempt]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  const toggleSound = useCallback(() => {
    setMuted((current) => {
      const next = !current;
      if (videoRef.current) videoRef.current.muted = next;
      return next;
    });
  }, []);
  const isLive = camera?.state === "streaming";

  return (
    <main>
      <header><div><span className="eyebrow">PHIJ HOME</span><h1>Dog Cam</h1></div>
        <span className={`status ${isLive ? "online" : ""}`}>{isLive ? "Camera online" : camera?.state ?? "API unavailable"}</span>
      </header>
      <section className="viewer">
        <video ref={videoRef} autoPlay muted={muted} playsInline />
        {!isLive && <div className="empty"><strong>No live picture</strong><span>{camera?.message ?? "Checking the camera service…"}</span></div>}
        <div className="player-state">{player}</div>
      </section>
      <footer>
        <div><span>Last heartbeat</span><strong>{camera?.lastHeartbeatAt ? new Date(camera.lastHeartbeatAt).toLocaleString() : "Never"}</strong></div>
        <div className="actions">
          <button className="secondary" onClick={toggleSound} disabled={!isLive}>
            {muted ? "Enable sound" : "Mute sound"}
          </button>
          <button onClick={retry}>Reconnect video</button>
        </div>
      </footer>
    </main>
  );
}
