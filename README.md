# Phij Dog Camera

Low-latency, local-network dog video from a Raspberry Pi USB camera to a web
viewer. MediaMTX handles RTSP ingest and WebRTC/WHEP playback; FastAPI tracks
camera health; Next.js renders the viewer.

## Projects

- `apps/server`: FastAPI status and stream-discovery API
- `apps/web`: Next.js WebRTC viewer
- `services/camera`: containerized Raspberry Pi FFmpeg supervisor and heartbeat agent
- `packages/contracts`: Zod response contracts for TypeScript clients
- `infra/mediamtx`: media gateway configuration
- `apps/app`: reserved for a future Tauri 2 Android/desktop client

## Local development

Requirements: Node 24+, pnpm 11, Python 3.9+, FFmpeg, and Docker Compose.

```sh
cp .env.example .env
pnpm install
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e "apps/server[dev]" -e "services/camera[dev]"
docker compose up -d mediamtx
pnpm server:dev
pnpm --filter @phij/web dev
```

Open http://localhost:3000. API docs are at http://localhost:4000/docs and
MediaMTX metrics at http://localhost:9998/metrics.

## Hardware-free stream

Run the stack and synthetic publisher:

```sh
docker compose --profile test-stream up --build --scale camera=0
```

The test profile publishes a moving test image and sends camera heartbeats.
Use `docker compose logs -f mediamtx test-stream` to troubleshoot publishing.

## Raspberry Pi deployment

Pushes to `main` publish `web`, `server`, and `camera` images to GHCR for both
`linux/amd64` and `linux/arm64`. A manually dispatched workflow also publishes
the requested release tag and creates the matching Git tag.

On the Pi, keep `compose.yml`, `deploy.sh`, `infra/mediamtx/mediamtx.yml`, and
an `.env` file together. Configure:

```env
APP_VERSION=0.1.0
IMAGE_PREFIX=ghcr.io/liorbuch/phij
MEDIA_HOST=192.168.1.50
CAMERA_DEVICE=/dev/video0
```

Replace `MEDIA_HOST` with the Pi's LAN address. Publish the same version from
GitHub Actions, then deploy. `IMAGE_PREFIX` must match the lowercased GitHub
repository path; the default is correct for `liorbuch/Phij`.

```sh
bash deploy.sh
```

The script pulls these versioned images and starts them without building:

- `ghcr.io/liorbuch/phij-web`
- `ghcr.io/liorbuch/phij-server`
- `ghcr.io/liorbuch/phij-camera`

Make the GHCR packages public, or run `docker login ghcr.io` once on the Pi.
To deploy another release without editing the script, run
`APP_VERSION=0.2.0 bash deploy.sh`.

## Secure Cloudflare Tunnel

Remote HTTPS viewers use authenticated HLS through Cloudflare; LAN HTTP viewers
keep low-latency WebRTC. The camera, API, and HLS ports are not published to the
internet, and no router port forwarding is required.

1. Under Zero Trust **Settings → Authentication**, configure Google as a login
   method.
2. Under **Access → Applications**, add a self-hosted application for the exact
   future hostname, such as `dogcam.example.com`. Add one **Allow** policy
   restricted to the specific Google email addresses that may view the camera.
   Do not add a Bypass policy.
3. Create a remotely-managed Cloudflare Tunnel and copy its token into the Pi's
   private `.env`:
   ```env
   CLOUDFLARE_TUNNEL_TOKEN=your-long-tunnel-token
   ```
4. Add the protected public hostname to the tunnel. Set its service type to
   HTTP and its internal URL to `http://web:3000`.
5. Set a short Access session duration and create a Cloudflare cache rule that
   bypasses caching for the dog-camera hostname.
6. Publish a new application release and run `bash deploy.sh` on the Pi.

Test the domain in a private browser window before relying on it: Cloudflare
must show Google authentication before any page loads. Do not forward ports
8889 or 8189 on the router; those published ports are only for LAN WebRTC.
Treat `.env` as a secret and rotate the tunnel token immediately if it leaks.

## LAN setup

Set `MEDIA_HOST` to the Pi's LAN IP before starting Compose. The browser derives
API and WHEP hosts from the page URL, so one published image works on any LAN.
Allow TCP 3001 and 8889 plus UDP 8189 only on the trusted LAN. Open
`http://PI_LAN_IP:3001` from a computer or phone on the same network.

## Quality checks

```sh
pnpm check
docker compose config
```

## Beyond the LAN MVP

Before internet exposure, add authentication and authorization, TLS, camera
publish credentials, and a TURN server for NAT traversal. Recording and
playback can be enabled in MediaMTX. For many simultaneous viewers, benchmark
the media host and consider a dedicated WebRTC platform. The future Tauri app
can reuse the API contracts and WHEP flow, but mobile background behavior and
secure credential storage need platform-specific work.
