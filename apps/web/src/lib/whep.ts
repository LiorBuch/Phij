export type WhepSession = { close: () => Promise<void> };

function waitForIceGathering(peer: RTCPeerConnection): Promise<void> {
  if (peer.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const listener = () => {
      if (peer.iceGatheringState === "complete") {
        peer.removeEventListener("icegatheringstatechange", listener);
        resolve();
      }
    };
    peer.addEventListener("icegatheringstatechange", listener);
  });
}

export async function connectWhep(
  url: string,
  video: HTMLVideoElement,
  onState: (state: RTCPeerConnectionState) => void,
): Promise<WhepSession> {
  const peer = new RTCPeerConnection();
  peer.addTransceiver("video", { direction: "recvonly" });
  peer.ontrack = (event) => { video.srcObject = event.streams[0]; };
  peer.onconnectionstatechange = () => onState(peer.connectionState);
  await peer.setLocalDescription(await peer.createOffer());
  await waitForIceGathering(peer);

  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/sdp"},
    body: peer.localDescription?.sdp,
  });
  if (!response.ok) {
    peer.close();
    throw new Error(`Media server rejected playback (${response.status})`);
  }
  await peer.setRemoteDescription({type: "answer", sdp: await response.text()});
  const location = response.headers.get("Location");

  return {
    close: async () => {
      peer.close();
      video.srcObject = null;
      if (location) {
        await fetch(new URL(location, url), {method: "DELETE"}).catch(() => undefined);
      }
    },
  };
}
