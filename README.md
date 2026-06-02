# RasperifyScanner

AI-powered environment scanner running on Raspberry Pi 4 Model B. Captures frames via the CSI camera module and analyzes them with Google Gemini Vision (primary) or OpenAI GPT-4o (fallback).

```
                     ┌─────────────────────────────────────┐
                     │      Raspberry Pi 4 Model B          │
                     │                                       │
  CSI Camera ───────►│  CameraService  ──►  Pipeline  ──►  DB │
                     │                         │             │
                     │    FastAPI (0.0.0.0:8000)│             │
                     └────────┬────────────────┘             │
                              │                              │
              ┌───────────────┼──────────────────┐          │
              │               │                  │          │
          USB-C OTG       Ethernet            WiFi          │
         (usb0)           (eth0)            (wlan0)         │
              │               │                  │          │
              └───────────────┼──────────────────┘          │
                              │                             │
              ┌───────────────┴──────────────────┐         │
              │         Mac / Mobile App           │         │
              │   Expo React Native (Dashboard,    │         │
              │   History, Settings screens)       │         │
              └────────────────────────────────────┘        │
```

---

## Quick Start

### 1. Backend — on the Pi (production)

SSH into the Pi first (see [Connecting to the Pi](#connecting-to-the-pi) below), then:

```bash
git clone <repo> ~/RasperifyScanner
cd ~/RasperifyScanner/backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set GEMINI_API_KEY, SECRET_KEY, etc.
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Backend — on Mac (development, mock camera)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # CAMERA_MOCK=true is auto-set when picamera2 is absent
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> When running on Mac, `camera_connected` is always `true` (mock mode — `picamera2` is absent on macOS) and all three Pi network adapters show `up: false` because `usb0`/`eth0`/`wlan0` are Linux interface names that do not exist on macOS. This is expected — run the backend on the Pi for real hardware readings.

### 3. Frontend

```bash
cd frontend
npm i
npx expo start
```

Point the app at `http://<pi-ip>:8000` (or `http://localhost:8000` for local mock dev).

### 4. Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### 5. Docker (ARM64, on Pi)

```bash
docker-compose up --build
```

---

## Connecting to the Pi

> **First time?** See the full step-by-step guide: [docs/PI_SETUP.md](docs/PI_SETUP.md) — covers flashing the OS, camera installation, USB-C OTG setup, and deploying the backend as a system service.
>
> The sections below are a quick reference for developers who have already completed the one-time setup.

The Pi runs the backend and must be reachable from your Mac. There are three ways to connect — pick one.

---

### Option A — USB-C Cable (recommended for desk use)

The Pi 4 USB-C port supports OTG gadget mode. When configured, the Pi appears as a USB Ethernet adapter on your Mac — no router, no WiFi, no DHCP needed.

> **Important:** The USB-C port on Pi 4 is power-only by default. OTG gadget mode must be explicitly enabled in the Pi's boot config (steps below). Also make sure you are using a **data-capable** USB-C cable — many USB-C cables are power-only and will not work.

**One-time setup on the Pi:**

**Step 1.** Add the USB OTG overlay to `/boot/firmware/config.txt`:

```bash
echo "dtoverlay=dwc2" | sudo tee -a /boot/firmware/config.txt
```

**Step 2.** Enable the gadget Ethernet driver in `/boot/firmware/cmdline.txt`.
This file is a single line — append to it without adding a newline:

```bash
sudo sed -i 's/$/ modules-load=dwc2,g_ether/' /boot/firmware/cmdline.txt
```

Verify the file still looks like one line:

```bash
cat /boot/firmware/cmdline.txt
# Should end with: ... rootwait modules-load=dwc2,g_ether
```

**Step 3.** Give the Pi a static IP on the `usb0` interface:

```bash
sudo tee /etc/network/interfaces.d/usb0 <<EOF
auto usb0
iface usb0 inet static
    address 192.168.7.2
    netmask 255.255.255.0
EOF
```

**Step 4.** Reboot the Pi with the USB-C cable already plugged into your Mac:

```bash
sudo reboot
```

**Step 5.** On your Mac: System Settings → Network → find the new interface named **RNDIS/ECM Gadget** or **USB 10/100 LAN**.
Set it to Manual:
- IP address: `192.168.7.1`
- Subnet mask: `255.255.255.0`
- Router: (leave blank)

**Step 6.** Verify:

```bash
ping 192.168.7.2                               # Pi should respond
ssh pi@192.168.7.2                             # SSH into Pi
curl http://192.168.7.2:8000/api/v1/health     # Pi API health check
```

**Diagnose USB-C from your Mac:**

```bash
# Did a USB Ethernet adapter appear?
ifconfig | grep -A4 "192.168.7"
networksetup -listallhardwareports | grep -i usb

# Is the Pi visible as a USB device at all?
system_profiler SPUSBDataType | grep -A8 -i "raspberry\|rndis\|linux\|gadget"
```

If no new network interface appears after plugging in:
1. Confirm `dtoverlay=dwc2` is the last line of `/boot/firmware/config.txt`
2. Confirm `/boot/firmware/cmdline.txt` has `modules-load=dwc2,g_ether` on the **same single line** as `rootwait`
3. Swap to a different USB-C cable (power-only cables will not work)
4. Try a different USB-C port on your Mac

**Diagnose from the Pi:**

```bash
ip addr show usb0
# Expected output: "state UP" with inet 192.168.7.2/24
# If "state DOWN" or interface missing: gadget mode is not active — recheck Steps 1 and 2
```

---

### Option B — Ethernet Cable

Plug an Ethernet cable between the Pi and your router (or directly into your Mac via a USB-C Ethernet adapter).

**Find the Pi's IP:**

```bash
# On Mac — scan your LAN (install nmap: brew install nmap)
nmap -sn 192.168.1.0/24 | grep -B2 -i "raspberry"

# Or check your router's DHCP table at http://192.168.1.1

# On the Pi directly:
hostname -I
ip addr show eth0
```

**Verify:**

```bash
ping <pi-eth0-ip>
curl http://<pi-eth0-ip>:8000/api/v1/health
```

**Diagnose Ethernet:**

```bash
# On the Pi — did eth0 get a DHCP address?
ip addr show eth0
# "state DOWN" means the cable is not detected — check physical connection

# No IP assigned? Request one manually:
sudo dhclient eth0
```

---

### Option C — WiFi

The Pi joins your WiFi network via `wlan0`. Best for wireless or mobile use.

**Configure WiFi on the Pi:**

```bash
sudo raspi-config
# System Options → Wireless LAN → enter SSID and password → Finish → Reboot
```

Or write the credentials directly:

```bash
sudo tee /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
country=TR
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YOUR_WIFI_NAME"
    psk="YOUR_WIFI_PASSWORD"
}
EOF
sudo systemctl restart wpa_supplicant
```

**Find the Pi's IP:**

```bash
# mDNS — works when avahi-daemon is installed on the Pi
ping raspberrypi.local

# Or scan the LAN:
nmap -sn 192.168.1.0/24 | grep -B2 -i "raspberry"

# On the Pi directly:
hostname -I
ip addr show wlan0
```

**Verify:**

```bash
ping <pi-wlan0-ip>
curl http://<pi-wlan0-ip>:8000/api/v1/health
```

**Diagnose WiFi:**

```bash
# On the Pi — check wlan0 state and signal:
ip addr show wlan0
iwconfig wlan0          # shows SSID and signal strength

# Not connected?
sudo wpa_cli status     # shows current connection state
sudo wpa_cli reconfigure  # re-reads wpa_supplicant.conf without rebooting
```

---

## Verifying the Pi is Running Correctly

Once connected via any method, the health endpoint shows the Pi's real hardware state:

```bash
curl http://<pi-ip>:8000/api/v1/health | python3 -m json.tool
```

Expected response when everything is working (example: connected via USB-C):

```json
{
  "status": "ok",
  "camera_connected": true,
  "active_adapter": "usb",
  "adapters": [
    {"name": "usb",      "interface": "usb0",  "up": true,  "ip": "192.168.7.2"},
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
| `camera_connected: true` | Pi CSI camera is physically attached and capturing frames |
| `active_adapter` | First adapter that is up with an IP — this is the address to use in the app |
| `cpu_percent` / `memory_percent` | Non-null only on real Pi hardware with `psutil` installed |
| All adapters `up: false` | Backend is running on Mac (mock mode) — normal during development |

---

## Pi Setup (first time only)

### Enable the CSI camera

```bash
sudo raspi-config
# Interface Options → Camera → Enable → Reboot
```

### Install system dependencies

```bash
sudo apt update && sudo apt install -y \
  python3.11 python3.11-venv python3.11-dev \
  python3-picamera2 libcamera-apps python3-psutil
```

### Verify the camera

```bash
libcamera-hello --timeout 3000
libcamera-jpeg -o /tmp/test.jpg && echo "Camera OK"
vcgencmd get_camera    # should show: supported=1 detected=1
```

If `vcgencmd get_camera` shows `detected=0`: the ribbon cable is not seated — press the brown locking tab in the CSI port down firmly on both the Pi and the camera module.

---

## Architecture

See [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) for the full GRASP-based design.

## API Reference

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) or visit `http://<pi-ip>:8000/docs` once the backend is running on the Pi.

## Pi Setup Guide

See [docs/PI_SETUP.md](docs/PI_SETUP.md) for the complete first-time setup guide: OS flashing, camera wiring, USB-C OTG gadget mode, Mac networking, backend deployment, and systemd service configuration.
