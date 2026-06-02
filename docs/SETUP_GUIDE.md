# RasperifyScanner — Setup Guide

> All `[PI]` commands must run inside an SSH session on the Pi.
> `raspi-config`, `apt`, `libcamera-*`, `vcgencmd`, and `systemctl` are Pi OS tools — they do not exist on macOS or Windows.

---

## 1. System Dependencies

```bash
# [PI]
sudo apt update && sudo apt install -y \
  python3 python3-venv python3-dev \
  python3-picamera2 libcamera-apps \
  python3-psutil i2c-tools git curl
```

---

## 2. Camera (CSI)

On Raspberry Pi OS Bookworm, the camera is auto-detected — no `raspi-config` step needed.

```bash
# [PI] Verify config.txt has this line (present by default after a fresh flash):
grep camera_auto_detect /boot/firmware/config.txt
# Expected: camera_auto_detect=1

# Check detection:
vcgencmd get_camera
# Expected: supported=1 detected=1

# Test capture:
libcamera-jpeg -o /tmp/test.jpg && echo "Camera OK"

# Test from Python:
python3 -c "
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
print('Camera service OK')
cam.stop()
"
```

**If `detected=0`:** Power off the Pi, reseat both ends of the ribbon cable (brown locking tabs pressed firmly flat), power on. Do NOT use `raspi-config` → Interface Options → Camera — that option no longer exists on Bookworm.

**Diagnose with I2C** (to check if camera module is electrically present):

```bash
# [PI]
i2cdetect -y 0   # or -y 1
# IMX219 (v2 module) shows at address 0x10
# IMX708 (v3 module) shows at address 0x1a
# Empty grid = cable not seated or wrong bus
```

---

## 3. USB-C Gadget Mode

Uses the official `rpi-usb-gadget` package — handles all config.txt / cmdline.txt changes automatically.

```bash
# [PI] — plug USB-C data cable into Mac/PC before rebooting
sudo apt install rpi-usb-gadget
sudo rpi-usb-gadget on
sudo reboot
```

**Pi is reachable at `10.12.194.1`** (SHARED mode, no ICS required):

```bash
ssh pi@10.12.194.1
curl http://10.12.194.1:8000/api/v1/health
```

| Mode | Pi IP | When |
|---|---|---|
| SHARED | `10.12.194.1` (fixed) | No ICS on host |
| CLIENT (macOS ICS) | `192.168.2.x` | Internet Sharing enabled on Mac |
| CLIENT (Windows ICS) | `192.168.137.x` | ICS enabled on Windows |
| CLIENT (Linux ICS) | `10.42.0.x` | NetworkManager shared mode |

> Cable warning: power-only USB-C cables are physically identical to data cables. If the interface never appears, swap the cable first.

---

## 4. Backend Deployment

```bash
# [PI]
cd ~
git clone <repo> RasperifyScanner
cd RasperifyScanner/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env   # set GEMINI_API_KEY, SECRET_KEY, CAMERA_MOCK=false
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check from Mac:

```bash
curl http://10.12.194.1:8000/api/v1/health | python3 -m json.tool
```

---

## 5. Auto-Start on Boot (systemd)

```bash
# [PI]
sudo tee /etc/systemd/system/rasperify.service <<EOF
[Unit]
Description=RasperifyScanner Backend
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/RasperifyScanner/backend
ExecStart=/home/pi/RasperifyScanner/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable rasperify
sudo systemctl start rasperify
sudo systemctl status rasperify
```

Logs: `sudo journalctl -u rasperify -f`

---

## 6. WiFi / Ethernet

WiFi credentials must be set in **Raspberry Pi Imager** Advanced Options before flashing — it's the most reliable method.

To change credentials after boot:

```bash
# [PI]
sudo raspi-config
# System Options → Wireless LAN → enter SSID and password
```

Find the Pi's IP:

```bash
# [MAC/WIN/LINUX]
ping raspberrypi.local
nmap -sn 192.168.1.0/24 | grep -B2 -i raspberry
```

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `detected=0` from `vcgencmd get_camera` | Power off, reseat ribbon cable on both ends |
| `active_adapter: null` in health JSON | USB-C not configured — run Steps 3 above |
| `ModuleNotFoundError: picamera2` | `sudo apt install python3-picamera2` |
| `Address already in use` on port 8000 | `sudo fuser -k 8000/tcp` |
| USB Ethernet not appearing on Mac | Swap to a data-capable USB-C cable; disable VPN |
| `cpu_percent: null` in health JSON | `sudo apt install python3-psutil` |
