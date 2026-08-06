# Raspberry Pi camera agent

Target: Raspberry Pi OS Bookworm and a USB V4L2 camera. The normal deployment
runs this agent as the `camera` service in the root Compose stack.

1. Confirm the device:
   ```sh
   sudo apt update
   sudo apt install -y v4l-utils
   v4l2-ctl --list-devices
   v4l2-ctl --device /dev/video0 --list-formats-ext
   ```
2. Set `CAMERA_DEVICE` and supported capture settings in the root `.env`, then
   run `bash deploy.sh`. Compose maps the selected device into the versioned
   camera container.

For a non-container systemd installation, copy this directory to
`/opt/phij-camera`, then install it:
   ```sh
   cd /opt/phij-camera
   python3 -m venv .venv
   .venv/bin/pip install .
   ```
Copy the root `.env.example` to `/etc/phij-camera.env`. Set
   `MEDIA_MTX_RTSP_URL` and `API_URL` to the server computer's LAN IP. Match
   `CAMERA_INPUT_FORMAT`, resolution, and FPS to values reported by `v4l2-ctl`.
Install `deploy/dog-camera.service` in `/etc/systemd/system/`, adjust `User`
   if needed, and run:
   ```sh
   sudo systemctl daemon-reload
   sudo systemctl enable --now dog-camera
   journalctl -u dog-camera -f
   ```

Allow outbound TCP from the Pi to ports 8554 and 4000 on the server. The agent
restarts FFmpeg with bounded backoff and continues streaming after transient
camera or network failures.
