# Raspberry Pi camera agent

Target: Raspberry Pi OS Bookworm and a LAN RTSP camera. The normal deployment
runs this agent as the `camera` service in the root Compose stack. FFmpeg reads
the camera stream and republishes it to MediaMTX for WebRTC playback.

1. Inspect the camera stream:
   ```sh
   ffprobe -v error -rtsp_transport tcp \
     -show_entries stream=codec_type,codec_name \
     -of compact "rtsp://user:password@camera-ip:8554/ch2"
   ```
2. Set `CAMERA_RTSP_URL` in the root `.env`, then run `bash deploy.sh`. Keep
   credentials in `.env`; never commit them.

For the lowest latency, configure the camera to emit H.264 and leave
`CAMERA_VIDEO_CODEC=copy`. If the stream is H.265, select an H.264 camera
profile or set `CAMERA_VIDEO_CODEC=libx264` to transcode it. Source audio is
encoded as mono Opus for WebRTC compatibility; set `CAMERA_AUDIO_CODEC=none`
to disable it.

For a non-container systemd installation, copy this directory to
`/opt/phij-camera`, then install it:
   ```sh
   cd /opt/phij-camera
   python3 -m venv .venv
   .venv/bin/pip install .
   ```
Copy the root `.env.example` to `/etc/phij-camera.env`. Set
   `CAMERA_RTSP_URL`, `MEDIA_MTX_RTSP_URL`, and `API_URL` for your network.
Install `deploy/dog-camera.service` in `/etc/systemd/system/`, adjust `User`
   if needed, and run:
   ```sh
   sudo systemctl daemon-reload
   sudo systemctl enable --now dog-camera
   journalctl -u dog-camera -f
   ```

Allow the Pi to reach the camera's RTSP port and the server's ports 8554 and
4000, and allow it to query the MediaMTX API on port 9997. The agent restarts
FFmpeg with bounded backoff after camera or network failures. It also restarts
a stuck FFmpeg process when the MediaMTX path remains unavailable after the
configured startup grace period.
