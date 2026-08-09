import Hls from "hls.js";
import type { WhepSession } from "./whep";

export async function connectHls(
  url: string,
  video: HTMLVideoElement,
  onState: (state: string) => void,
): Promise<WhepSession> {
  if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = url;
    await video.play();
    onState("Live (secure HLS)");
    return {
      close: async () => {
        video.pause();
        video.removeAttribute("src");
        video.load();
      },
    };
  }

  if (!Hls.isSupported()) {
    throw new Error("This browser does not support HLS playback");
  }

  const hls = new Hls({
    lowLatencyMode: true,
    liveSyncDurationCount: 3,
    maxLiveSyncPlaybackRate: 1.5,
  });

  await new Promise<void>((resolve, reject) => {
    hls.once(Hls.Events.MANIFEST_PARSED, () => resolve());
    hls.once(Hls.Events.ERROR, (_event, data) => {
      if (data.fatal) reject(new Error(`HLS playback failed: ${data.details}`));
    });
    hls.loadSource(url);
    hls.attachMedia(video);
  });

  await video.play();
  onState("Live (secure HLS)");
  return {
    close: async () => {
      hls.destroy();
      video.removeAttribute("src");
      video.load();
    },
  };
}
