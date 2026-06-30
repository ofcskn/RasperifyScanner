# RasperifyScanner

Privacy-first environment scanner running on a Raspberry Pi 4 Model B. It captures
frames from the CSI camera and analyzes them in **two stages** — both running
**fully on the device by default**, with nothing sent to the cloud:

1. **Stage 1 — on-device detection (fast, every frame).** A small YOLO neural
   network draws bounding boxes around people and objects, and a tracker keeps a
   running count of how many people are *in frame now* and how many *unique*
   people have been seen.
2. **Stage 2 — local scene analysis (slower, on an interval).** A local Ollama
   vision model writes a structured description of the scene (and flags anomalies)
   as JSON.

Cloud providers (Google Gemini, OpenAI) are still supported but are **disabled by
default** — turn them on only if you opt in (`allow_cloud: true`).

```
  CSI Camera ──► CameraService ──► Pipeline ──────────────► SQLite DB
                      │                 │
                      │          ┌──────┴───────┐
                      │     Stage 1: YOLO   Stage 2: Ollama
                      │     (detection)     (scene JSON)
                      │          │               │
               FastAPI :8000     └──► Events ────┘
                      │
          ┌───────────┼───────────┐
       USB-C OTG   Ethernet    WiFi
        (usb0)     (eth0)    (wlan0)
                      │
              Mac / Mobile App
          Expo React Native frontend
        (live boxes • counts • events)
```

### New terms, in one line each

| Term | What it means here |
|---|---|
| **YOLO** | "You Only Look Once" — a fast neural network that finds objects in an image in a single pass. We use the tiny `yolov8n` ("n" = nano) variant so it runs on the Pi's CPU. |
| **ONNX / ONNX Runtime** | A portable model file format (`.onnx`) and the engine that runs it. Lets us run YOLO without a heavyweight ML framework. |
| **COCO labels** | The 80 object names YOLO can recognize (person, car, chair, …). Class 0 is `person`. |
| **Bounding box** | The rectangle drawn around a detected object, stored as `[x1, y1, x2, y2]` normalized to 0–1 of the frame. |
| **Confidence** | How sure the model is about a detection (0–1). Detections below `detection_conf_threshold` are discarded. |
| **NMS (Non-Max Suppression)** | Removes duplicate boxes for the same object, keeping the most confident one. Controlled by `detection_iou_threshold`. |
| **IoU (Intersection over Union)** | How much two boxes overlap (0 = none, 1 = identical). Used both for NMS and for the tracker. |
| **Tracker** | Follows the same object across frames and gives it a stable **track ID**, so a moving person isn't counted as a new person each frame. |
| **Ollama** | A local LLM runtime ([ollama.com](https://ollama.com)) that runs vision models like `moondream` on-device over a simple HTTP API. |
| **Event** | A saved operational log entry (e.g. "live person count crossed the alert threshold") shown live in the app's Events tab. |

See [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) for how the detection,
tracking, counting, and analysis algorithms actually work.

---

## Quick Start

### Docker (recommended)

```bash
git clone <repo> ~/RasperifyScanner
cd ~/RasperifyScanner
cp backend/.env.example backend/.env   # set SECRET_KEY (API keys only needed if allow_cloud=true)
docker compose up
```

| Service | URL |
|---|---|
| Backend API | `http://<pi-ip>:8000` |
| Frontend (Expo web) | `http://<pi-ip>:8081` |

First run builds the images — this takes a few minutes on the Pi. Subsequent starts are fast.

```bash
docker compose up --build   # rebuild after dependency changes
docker compose down         # stop and remove containers
```

> **Stage 2 needs Ollama.** The compose stack does **not** run Ollama for you —
> it runs on the host and the containers reach it at `http://localhost:11434`
> (both containers use `network_mode: host`). Install Ollama on the Pi and pull
> the model: `ollama pull moondream`. The backend logs a clear warning at startup
> if Ollama is unreachable, and Stage 1 detection keeps working without it.
>
> The one-command helper sets all of this up: see
> [docs/LOCAL_AI_SETUP.md](docs/LOCAL_AI_SETUP.md) → `python scripts/setup_local.py`.

---

### Manual Setup (alternative)

#### Backend — on the Pi

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # includes onnxruntime, numpy, opencv-headless
python scripts/setup_local.py            # fetches the YOLO model + starts/pulls Ollama
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Backend — on Mac (mock camera)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # CAMERA_MOCK=true
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> On Mac, `camera_connected` is `true` only after the camera is started (mock
> mode), and all network adapters show `up: false` — `usb0`/`eth0`/`wlan0` are
> Linux interface names that don't exist on macOS. Expected during development.

#### Frontend

```bash
cd frontend && npm i && npx expo start
```

Point the app at the backend:

```bash
EXPO_PUBLIC_API_URL=http://<pi-ip>:8000/api/v1 \
EXPO_PUBLIC_WS_URL=ws://<pi-ip>:8000/ws/analysis-stream npx expo start
```

### Tests

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
python scripts/verify_pipeline.py    # end-to-end: detection, counting, Ollama, failure recovery
```

`verify_pipeline.py` **skips** (rather than fails) any check whose dependency is
missing — e.g. if Ollama isn't running it tells you why and moves on.

---

## Connecting to the Pi

> **First time?** Follow [docs/PI_SETUP.md](docs/PI_SETUP.md) — covers OS flashing, camera wiring, USB-C OTG setup, and systemd service. The sections below are a quick reference for developers who have already completed setup.

### USB-C (recommended)

Uses `rpi-usb-gadget` — the Pi appears as a USB Ethernet adapter. No router or WiFi needed.

**One-time Pi setup:**

```bash
sudo apt install rpi-usb-gadget
sudo rpi-usb-gadget on
sudo reboot   # plug USB-C into Mac before rebooting
```

**Pi IP (SHARED mode, no ICS):** `10.12.194.1`

```bash
ssh pi@10.12.194.1
curl http://10.12.194.1:8000/api/v1/health
```

**With Internet Connection Sharing enabled on Mac** (CLIENT mode), use `raspberrypi.local` instead.

| Mode | Pi IP | Activates when |
|---|---|---|
| SHARED | `10.12.194.1` (fixed) | No ICS on host |
| CLIENT | assigned by host DHCP | ICS enabled on Mac/Win/Linux |

If the USB Ethernet interface never appears on your Mac: swap the cable (power-only cables are physically identical to data cables).

### Ethernet

```bash
ssh pi@raspberrypi.local
curl http://raspberrypi.local:8000/api/v1/health
```

### WiFi

Same as Ethernet — Pi joins your LAN via `wlan0`. Set credentials in Raspberry Pi Imager before flashing.

---

## Health Check

```bash
curl http://10.12.194.1:8000/api/v1/health | python3 -m json.tool
```

```json
{
  "status": "ok",
  "camera_connected": true,
  "camera_source": "picamera2",
  "active_adapter": "usb",
  "adapters": [
    {"name": "usb",      "interface": "usb0",  "up": true,  "ip": "10.12.194.1"},
    {"name": "ethernet", "interface": "eth0",  "up": false, "ip": null},
    {"name": "wifi",     "interface": "wlan0", "up": false, "ip": null}
  ],
  "detector": {"backend": "onnx-yolo", "available": true, "enabled": true},
  "ollama":   {"enabled": true, "reachable": true, "model": "moondream",
               "model_present": true, "host": "http://localhost:11434"},
  "cpu_percent": 12.4,
  "memory_percent": 38.1,
  "uptime_seconds": 3600.0
}
```

| Field | Meaning |
|---|---|
| `detector.available: false` | `onnxruntime`/`numpy` not installed, or `models/yolo.onnx` missing — run `scripts/setup_local.py` |
| `ollama.reachable: false` | Ollama isn't running — `ollama serve` (Stage 2 is skipped, Stage 1 still works) |
| `ollama.model_present: false` | model not pulled — `ollama pull moondream` |
| `active_adapter: null` | No adapter is up — USB-C gadget not installed yet, or no cable |
| `camera_connected: false` | Camera not started, ribbon cable not seated, or `camera_auto_detect=1` missing from config.txt |
| `cpu_percent: null` | `psutil` not installed — run `sudo apt install python3-psutil` |

---

## Configuration

All settings live in [`config/scanner.yml`](config/scanner.yml). Precedence is
**environment variables / `.env` → `scanner.yml` → code defaults**. Most values can
be changed live from the app's **Settings** screen (which calls `PATCH /api/v1/config`)
with no restart.

The knobs you'll reach for most:

| Key | Default | Meaning |
|---|---|---|
| `camera_source` | `picamera2` | `picamera2`, `usb:/dev/video0`, or `rtsp://host:554/stream` |
| `detection_enabled` | `true` | Turn Stage-1 detection on/off |
| `detection_conf_threshold` | `0.35` | Minimum confidence to keep a detection (0–1) |
| `detection_iou_threshold` | `0.45` | NMS overlap threshold for de-duplicating boxes (0–1) |
| `detection_target_labels` | `[]` | `[]` = all 80 COCO classes; e.g. `["person"]` for people only |
| `counting_min_hits` | `3` | Frames a track must persist before it counts as a unique person |
| `counting_person_alert_threshold` | `0` | `>0` raises an **event** when the live count exceeds it |
| `ollama_model` | `moondream` | Local vision model for Stage 2 (e.g. `llava`) |
| `analysis_default_interval_seconds` | `30` | Seconds between scheduled Stage-2 analyses |
| `allow_cloud` | `false` | `false` = fully local; `true` enables Gemini/OpenAI if keys are set |
| `store_frames` | `true` | Persist frame thumbnails alongside each analysis |

Full list and tuning advice: [docs/LOCAL_AI_SETUP.md](docs/LOCAL_AI_SETUP.md).

---

## Camera Setup

On modern Raspberry Pi OS (Bookworm), the camera is enabled automatically via `camera_auto_detect=1` in `/boot/firmware/config.txt` — no `raspi-config` step needed.

```bash
# Verify config (should already be present after a fresh flash):
grep camera_auto_detect /boot/firmware/config.txt
# Expected: camera_auto_detect=1

# Check detection:
rpicam-hello --list-cameras
# Expected: lists at least one camera

# Test capture:
rpicam-jpeg -o /tmp/test.jpg && echo "Camera OK"
```

If `detected=0`: power off the Pi, reseat both ends of the ribbon cable (brown locking tabs must be pressed firmly flat), power on.

> **Live camera, not stills.** The camera service streams with libcamera's
> *video* configuration (continuous frames) rather than a still configuration —
> this is what fixed the earlier "No Signal" stalls. It also requests the
> `BGR888` pixel format, which (due to a libcamera byte-order quirk) yields the
> RGB array PIL expects; the wrong format swaps red/blue and makes YOLO
> misclassify people as cats or dogs.

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | **Architecture + algorithms**: GRASP roles, the two-stage data flow, and how detection / tracking / counting / analysis work |
| [docs/LOCAL_AI_SETUP.md](docs/LOCAL_AI_SETUP.md) | Local AI setup, full config reference, performance & troubleshooting |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | All REST endpoints (incl. `/config`, `/events`) and the WebSocket protocol |
| [docs/PI_SETUP.md](docs/PI_SETUP.md) | Full first-time setup: OS flash, camera wiring, USB-C OTG, Mac/Win/Linux networking, systemd service |
| [docs/PI_SETUP_MACOS.md](docs/PI_SETUP_MACOS.md) | macOS-specific setup guide |
| [docs/PI_SETUP_WINDOWS.md](docs/PI_SETUP_WINDOWS.md) | Windows-specific setup guide |
| [docs/PI_SETUP_LINUX.md](docs/PI_SETUP_LINUX.md) | Linux-specific setup guide |
</content>
