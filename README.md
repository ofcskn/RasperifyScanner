# RasperifyScanner

AI-powered environment scanner running on Raspberry Pi 4 Model B. Captures frames via the CSI camera module and analyzes them with Google Gemini Vision (primary) or OpenAI GPT-4o (fallback).

```
  CSI Camera ──► CameraService ──► Pipeline ──► DB
                      │
               FastAPI :8000
                      │
          ┌───────────┼───────────┐
       USB-C OTG   Ethernet    WiFi
        (usb0)     (eth0)    (wlan0)
                      │
              Mac / Mobile App
          Expo React Native frontend
```

---

## Quick Start

### Docker (recommended)

```bash
git clone <repo> ~/RasperifyScanner
cd ~/RasperifyScanner
cp backend/.env.example backend/.env   # set GEMINI_API_KEY, SECRET_KEY
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

> On first run the frontend image installs all npm packages inside the container. The source directory is mounted as a volume so code changes reflect without rebuilding.

---

### Manual Setup (alternative)

#### Backend — on the Pi

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set GEMINI_API_KEY, SECRET_KEY
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

> On Mac, `camera_connected` is always `true` (mock) and all adapters show `up: false` — `usb0`/`eth0`/`wlan0` are Linux interface names that don't exist on macOS. Expected during development.

#### Frontend

```bash
cd frontend && npm i && npx expo start
```

Point the app at `http://<pi-ip>:8000` (or `http://localhost:8000` for local mock dev).

### Tests

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```

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
  "active_adapter": "usb",
  "adapters": [
    {"name": "usb",      "interface": "usb0",  "up": true,  "ip": "10.12.194.1"},
    {"name": "ethernet", "interface": "eth0",  "up": false, "ip": null},
    {"name": "wifi",     "interface": "wlan0", "up": false, "ip": null}
  ],
  "cpu_percent": 12.4,
  "memory_percent": 38.1,
  "uptime_seconds": 3600.0
}
```

| Field | Meaning |
|---|---|
| `active_adapter: null` | No adapter is up — USB-C gadget not installed yet, or no cable |
| `camera_connected: false` | Ribbon cable not seated or `camera_auto_detect=1` missing from config.txt |
| `cpu_percent: null` | `psutil` not installed — run `sudo apt install python3-psutil` |

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

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/PI_SETUP.md](docs/PI_SETUP.md) | Full first-time setup: OS flash, camera wiring, USB-C OTG, Mac/Win/Linux networking, systemd service |
| [docs/PI_SETUP_MACOS.md](docs/PI_SETUP_MACOS.md) | macOS-specific setup guide |
| [docs/PI_SETUP_WINDOWS.md](docs/PI_SETUP_WINDOWS.md) | Windows-specific setup guide |
| [docs/PI_SETUP_LINUX.md](docs/PI_SETUP_LINUX.md) | Linux-specific setup guide |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | All API endpoints and WebSocket protocol |
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | GRASP architecture and data flow |
