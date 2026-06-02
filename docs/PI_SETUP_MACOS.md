# Raspberry Pi 4 Model B — Setup Guide for macOS

> **Who is this for?** macOS users connecting a Raspberry Pi 4 Model B to run the RasperifyScanner backend for the first time — from unboxing to a fully working service.

---

## Critical: Know Which Machine You Are Typing On

Every command is labelled:

- **[PI]** — run inside an SSH session on the Pi, or directly on the Pi with a keyboard
- **[MAC]** — run in a Terminal on your Mac

**Never run a [PI] command on your Mac.** Tools like `raspi-config`, `rpicam-hello`, `vcgencmd`, `hostnamectl`, `apt`, and `systemctl` are Raspberry Pi OS / Linux tools. They do not exist on macOS and will print `command not found`.

If you are unsure which machine your terminal is connected to:

```bash
hostname
# "raspberrypi" (or your chosen name) → you are on the Pi
# anything else → you are on your Mac
```

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [macOS Prerequisites](#2-macos-prerequisites)
3. [Flash Raspberry Pi OS](#3-flash-raspberry-pi-os)
4. [First Boot — Get Initial Access](#4-first-boot--get-initial-access)
5. [System Configuration on the Pi](#5-system-configuration-on-the-pi)
6. [Attach and Enable the CSI Camera](#6-attach-and-enable-the-csi-camera)
7. [USB-C OTG Gadget Mode — Install rpi-usb-gadget](#7-usb-c-otg-gadget-mode--install-rpi-usb-gadget)
8. [Configure macOS Networking for USB-C](#8-configure-macos-networking-for-usb-c)
9. [Verify the Connection](#9-verify-the-connection)
10. [Deploy the RasperifyScanner Backend](#10-deploy-the-rasperify-scanner-backend)
11. [Run as a System Service — Auto-Start on Boot](#11-run-as-a-system-service--auto-start-on-boot)
12. [Diagnostics and Troubleshooting](#12-diagnostics-and-troubleshooting)

---

## 1. Hardware Requirements

| Item | Notes |
|---|---|
| Raspberry Pi 4 Model B (1 GB RAM minimum, 4 GB recommended) | Any RAM variant works; 4 GB gives comfortable headroom for the AI pipeline |
| MicroSD card ≥ 16 GB, Class 10 / A1 speed rating | Slower cards cause noticeable lag at boot and during pip installs |
| Raspberry Pi Camera Module v2 or v3 | Connected via the CSI ribbon cable |
| USB-C cable — **data-capable** | Many USB-C cables carry power only. Use one rated for data (USB 2.0+). Most Android phone charging cables work. Power-only cables are physically identical — if the gadget interface never appears on your Mac, swap the cable before troubleshooting anything else. |
| Mac with a USB-C or USB-A port | USB-C preferred; use a USB-A to USB-C adapter if your Mac only has USB-A |
| MicroSD card reader | To flash the OS from your Mac |
| USB-C power supply, 5V / 3A minimum | When not powering via USB-C OTG. A 65 W laptop charger with USB-C works. |
| (Optional) HDMI micro-to-full adapter + monitor | Only needed for the HDMI+keyboard first-boot option |
| (Optional) USB keyboard | Only needed for the HDMI+keyboard first-boot option |

---

## 2. macOS Prerequisites

Install these tools on your Mac **before starting**.

---

### Homebrew (Mac package manager)

Homebrew is required to install all other Mac tools.

**[MAC]** Check if already installed:

```bash
brew --version
# "Homebrew 4.x.x" → already installed, skip the next command
# "command not found: brew" → install it now
```

**[MAC]** Install Homebrew if not present:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. At the end the installer prints two commands to add Homebrew to your PATH — run both before continuing. They look like:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
# Expected: Homebrew 4.x.x
```

---

### nmap (network scanner — needed to find the Pi's IP during first boot)

`nmap` is not installed on macOS by default.

**[MAC]**

```bash
# Check if already installed
nmap --version
# "Nmap 7.x" → already installed, skip brew install
# "command not found: nmap" → install it now

brew install nmap
```

> **Why does `nmap -sn 192.168.1.0/24` return nothing?**
> Your network may not use the `192.168.1.x` subnet. Find your Mac's actual IP first:
>
> ```bash
> ipconfig getifaddr en0   # WiFi adapter
> ipconfig getifaddr en1   # Ethernet adapter (if plugged in)
> ```
>
> Example: if your Mac's IP is `192.168.0.105`, scan `192.168.0.0/24`.
> If it is `10.0.1.50`, scan `10.0.1.0/24`.

---

### Raspberry Pi Imager

**[MAC]**

```bash
brew install --cask raspberry-pi-imager
```

Or download from https://www.raspberrypi.com/software/

---

## 3. Flash Raspberry Pi OS

> **[MAC]** All steps in this section run on your Mac.

1. Insert the MicroSD card into your Mac via a card reader.
2. Open **Raspberry Pi Imager**.
3. Click **Choose OS** → **Raspberry Pi OS (64-bit)**.
   - Choose **Raspberry Pi OS Lite (64-bit)** for a minimal headless server (recommended — no desktop, smaller, faster boot).
   - Choose the full version only if you need a GUI on the Pi.
4. Click **Choose Storage** → select your MicroSD card. Verify the size matches your card.
5. Click the **gear icon (⚙)** (bottom-right) to open **Advanced Options** — configure all of these **before** writing:

   | Setting | What to set | Why |
   |---|---|---|
   | Set hostname | `raspberrypi` | Lets you find it as `raspberrypi.local` |
   | Enable SSH | Checked — **Use password authentication** | Required to connect without a monitor |
   | Username | `pi` | Used in all `ssh pi@...` commands |
   | Password | A password you will remember | Entered every time you SSH in |
   | Configure wireless LAN | Your WiFi name + password | Required for headless WiFi first boot. Leave blank if using Ethernet or HDMI/keyboard. |
   | Wireless LAN country | Your 2-letter country code (`TR`, `US`, `GB`, `DE` …) | Required for WiFi to function correctly |
   | Set locale | Your timezone and keyboard layout | Prevents clock drift |

6. Click **Save** → **Write**. Wait 3–8 minutes for write + verification.
7. Eject the MicroSD card safely.

> **Shortcut — enable USB gadget mode directly in Imager 2.0+:**
> In Advanced Options → Interfaces & Features → enable **"USB Gadget mode"**.
> This pre-configures everything in Section 7 so you can skip the manual `apt install` steps.

---

## 4. First Boot — Get Initial Access

> **Goal:** Reach the Pi's shell so you can install the USB gadget software (Section 7). You cannot use USB-C OTG until that software is installed, so you need another way in first.

Insert the MicroSD card into the Pi's card slot (underside of the board). Pick **one** option.

---

### Option A: HDMI + Keyboard (no network needed)

1. Connect a monitor to the Pi's **micro-HDMI port** — labelled "HDMI0", the one closest to the USB-C power port.
2. Connect a USB keyboard to any USB-A port.
3. Connect a USB-C power supply. The Pi boots automatically (no power button).
4. Wait ~30 seconds. A login prompt appears.
5. Log in: username `pi`, password from Imager.
6. You now have a Pi shell. Continue to [Section 5](#5-system-configuration-on-the-pi).

---

### Option B: Headless via WiFi

**Prerequisite:** WiFi credentials must have been entered in Imager Advanced Options (Section 3).

1. Connect USB-C power. The Pi boots and joins your WiFi.
2. Wait ~60 seconds, then find the Pi's IP from your Mac:

**[MAC]**

```bash
# Method 1: mDNS (try first — usually works)
ping raspberrypi.local

# Method 2: nmap — find your subnet first
ipconfig getifaddr en0        # your Mac's WiFi IP
nmap -sn 192.168.x.0/24 | grep -B2 -i "raspberry"
# Replace 192.168.x.0/24 with your actual subnet

# Method 3: ARP table
arp -a
# Raspberry Pi MAC addresses start with b8:27:eb, dc:a6:32, or e4:5f:01

# Method 4: Router admin page
# http://192.168.1.1  →  Connected Devices / DHCP Leases  →  look for "raspberrypi"
```

3. SSH into the Pi:

```bash
ssh pi@raspberrypi.local
# or
ssh pi@<ip-address-you-found>
```

4. First-time connection shows a fingerprint warning — type `yes` and press Enter. Enter your password.

---

### Option C: Headless via Ethernet

1. Plug an Ethernet cable between the Pi and your router (not directly to your Mac — direct requires manual static IPs on both sides).
2. Connect USB-C power.
3. Wait ~60 seconds. Find the IP using the same methods as Option B.
4. SSH: `ssh pi@<ip>`

---

## 5. System Configuration on the Pi

> **[PI]** Every command below runs on the Pi via SSH.
> `hostnamectl`, `apt`, `raspi-config`, and `systemctl` are Linux-only tools — they will fail on macOS.

### Update all packages

```bash
# [PI]
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

Wait ~30 seconds, then reconnect via SSH.

---

### Set hostname (only if you skipped it in Imager)

```bash
# [PI] — run this on the Pi, not on your Mac
sudo hostnamectl set-hostname raspberrypi
```

> `hostnamectl` does not exist on macOS. If you see `command not found: hostnamectl`, you ran it on your Mac — SSH into the Pi first.

---

### Install required system packages

```bash
# [PI]
sudo apt install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  python3-picamera2 \
  rpicam-apps \
  python3-psutil \
  git \
  curl
```

### Verify Python

```bash
# [PI]
python3.11 --version
# Expected: Python 3.11.x
```

---

## 6. Attach and Enable the CSI Camera

### Physical wiring

> **Power off the Pi before touching the ribbon cable.**

```bash
# [PI]
sudo shutdown -h now
```

Wait until the green activity LED stops flashing, then unplug the USB-C power cable.

**Connect the ribbon cable:**

1. Find the **CSI camera port** — the narrow black connector between the two HDMI ports and the USB-A ports, labelled "CAMERA".
2. Lift the brown plastic locking tab straight up (~2 mm). It does not detach.
3. Slide in the ribbon cable: the **blue strip faces toward the USB-A ports**, metal contacts face the HDMI side.
4. Press the brown locking tab firmly flat.
5. Connect the other end to the camera module the same way: lift tab, blue strip toward the lens, press tab down.
6. Reconnect USB-C power. Reconnect via SSH after ~30 seconds.

### Enable the camera interface

On Raspberry Pi OS Bookworm, the camera is auto-detected via `camera_auto_detect=1` in `/boot/firmware/config.txt` — no `raspi-config` step is needed.

```bash
# [PI] Confirm the line is present (it is by default after a fresh flash):
grep camera_auto_detect /boot/firmware/config.txt
# Expected: camera_auto_detect=1
```

### Verify the camera

```bash
# [PI]
rpicam-hello --list-cameras
# Expected: lists at least one camera (e.g. ov5647)

rpicam-hello --timeout 5000

rpicam-jpeg -o /tmp/test.jpg && echo "Camera OK"

python3 -c "
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
print('Camera service OK')
cam.stop()
"
```

**If no camera is listed:** Power off, reseat both ribbon cable ends (press locking tabs firmly closed), power on.

---

## 7. USB-C OTG Gadget Mode — Install rpi-usb-gadget

> This section uses the **official Raspberry Pi USB gadget package** from
> https://github.com/raspberrypi/rpi-usb-gadget

**[PI]** — run inside your SSH session.

### Install the package

```bash
# [PI]
sudo apt update
sudo apt install rpi-usb-gadget

# Enable gadget mode
sudo rpi-usb-gadget on

# Plug the USB-C data cable into your Mac before rebooting
sudo reboot
```

> **What `rpi-usb-gadget on` does automatically:**
> - Adds `dtoverlay=dwc2,dr_mode=peripheral` to `/boot/firmware/config.txt`
> - Adds `modules-load=dwc2,g_ether` to `/boot/firmware/cmdline.txt`
> - Creates two NetworkManager profiles on `usb0`
> - Enables the `rpi-usb-gadget-ics.service` auto-switcher
>
> You do NOT need to edit `config.txt` or `cmdline.txt` manually.

### Check gadget status

```bash
# [PI]
sudo rpi-usb-gadget status
```

---

### How the auto-switching works

The Pi runs two network profiles on the USB interface (`usb0`) and automatically switches between them:

| Mode | When it activates | Pi IP | Your Mac IP |
|---|---|---|---|
| **CLIENT mode** | macOS Internet Sharing is enabled | `192.168.2.x` (assigned by Mac) | `192.168.2.1` |
| **SHARED mode** | No ICS detected | `10.12.194.1` (fixed) | `10.12.194.2`–`10.12.194.14` (DHCP from Pi) |

**In SHARED mode (no ICS), the Pi is always reachable at `10.12.194.1`:**

```bash
ssh pi@10.12.194.1
curl http://10.12.194.1:8000/api/v1/health
```

**In CLIENT mode (with ICS), use mDNS:**

```bash
ssh pi@raspberrypi.local
curl http://raspberrypi.local:8000/api/v1/health
```

> **VPN warning:** Disable any VPN on your Mac before connecting. VPNs intercept the local routing table and block the USB gadget link.

---

## 8. Configure macOS Networking for USB-C

macOS recognises the Pi as a **CDC-ECM** USB Ethernet adapter — no driver needed.

After the Pi finishes booting with the USB-C cable plugged in, a new network interface appears automatically:

1. Open **System Settings → Network**.
2. Look for a new interface named `RNDIS/ECM Gadget`, `USB 10/100 LAN`, or `USB Ethernet`.
3. If you see it: **no further configuration is required for SHARED mode**. The Pi's DHCP server assigns your Mac an IP in `10.12.194.x` automatically.
4. Verify from your Mac:

```bash
# [MAC]
ifconfig | grep -A4 "10.12.194"
# Expected: inet 10.12.194.2 (or similar)

ping 10.12.194.1
# Expected: replies from the Pi
```

---

### Optional: Enable Internet Connection Sharing (CLIENT mode)

Enabling ICS lets the Pi access the internet through your Mac's WiFi. This is optional — the Pi works without internet access once deployed.

**macOS Ventura / Sonoma:**

1. **System Settings → General → Sharing → Internet Sharing**

**macOS Monterey and older:**

1. **System Preferences → Sharing → Internet Sharing**

In both cases:

2. Share connection from: **Wi-Fi**
3. To computers using: check the USB gadget interface (`RNDIS/ECM Gadget` or `USB Ethernet`)
4. Turn **Internet Sharing** on.

macOS assigns itself `192.168.2.1` on the gadget interface and hands the Pi a `192.168.2.x` IP. The Pi's auto-switcher detects this and switches to CLIENT mode within ~10 seconds.

```bash
# [MAC] After enabling ICS, verify
ping raspberrypi.local
ssh pi@raspberrypi.local
```

---

## 9. Verify the Connection

From your Mac, confirm you can reach the Pi:

| Mode | Pi IP | SSH command |
|---|---|---|
| SHARED (no ICS) | `10.12.194.1` | `ssh pi@10.12.194.1` |
| CLIENT (macOS ICS) | `192.168.2.x` | `ssh pi@raspberrypi.local` |

**[PI]** — from inside the SSH session, verify the USB interface:

```bash
ip addr show usb0
# Look for: state UP
# Look for: inet <ip>/xx

# Check which mode the switcher chose
sudo systemctl status rpi-usb-gadget-ics
```

---

## 10. Deploy the RasperifyScanner Backend

> **[PI]** All commands run on the Pi via SSH.

### Clone the repository

```bash
# [PI]
cd ~
git clone https://github.com/<your-username>/RasperifyScanner.git
cd RasperifyScanner/backend
```

### Create a virtual environment

```bash
# [PI]
python3.11 -m venv .venv
source .venv/bin/activate
# Prompt changes to (.venv) — virtual environment is active
```

### Install Python dependencies

```bash
# [PI]
pip install --upgrade pip
pip install -r requirements.txt
# Takes 5–15 minutes on Pi hardware
```

### Configure environment variables

```bash
# [PI]
cp .env.example .env
nano .env
```

| Variable | Value | Notes |
|---|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key | https://aistudio.google.com/ → Get API Key |
| `OPENAI_API_KEY` | Your OpenAI API key | Optional — Gemini fallback |
| `SECRET_KEY` | Random 32-char hex string | Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `CAMERA_MOCK` | `false` | Set `true` only for Mac development without a camera |

Save in nano: `Ctrl+X` → `Y` → `Enter`.

### Test-run

```bash
# [PI]
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

From your Mac, verify:

```bash
# [MAC] SHARED mode
curl http://10.12.194.1:8000/api/v1/health | python3 -m json.tool

# [MAC] CLIENT mode
curl http://raspberrypi.local:8000/api/v1/health | python3 -m json.tool
```

Expected response:

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

Interactive API docs: `http://10.12.194.1:8000/docs` (or `http://raspberrypi.local:8000/docs` in CLIENT mode).

Press `Ctrl+C` to stop the test run before continuing.

---

## 11. Run as a System Service — Auto-Start on Boot

**[PI]**

```bash
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
# Expected: Active: active (running)
```

**Service management:**

```bash
# [PI] Live logs
sudo journalctl -u rasperify -f

# [PI] Stop
sudo systemctl stop rasperify

# [PI] Update and restart
cd ~/RasperifyScanner && git pull
sudo systemctl restart rasperify
```

---

## 12. Diagnostics and Troubleshooting

### USB-C interface not appearing on Mac

```bash
# [MAC] Is the Pi detected as a USB device?
system_profiler SPUSBDataType | grep -A8 -i "raspberry\|rndis\|linux\|gadget"

# Does a USB Ethernet interface appear?
networksetup -listallhardwareports

# Does the Pi have an IP on the USB link?
ifconfig | grep -A4 "10.12.194"
```

**Most common causes in order:**
1. Power-only USB-C cable — swap the cable first
2. `rpi-usb-gadget on` was not run, or the Pi was not rebooted after
3. VPN active on your Mac — disable it

---

### Check gadget mode status on the Pi

```bash
# [PI]
sudo rpi-usb-gadget status

ip addr show usb0

sudo systemctl status rpi-usb-gadget-ics
sudo journalctl -u rpi-usb-gadget-ics -n 30 --no-pager
```

---

### Finding the Pi's IP without nmap

```bash
# [MAC] ARP table (works on same subnet)
arp -a
# Pi MAC prefixes: b8:27:eb  dc:a6:32  e4:5f:01

# Any OS: check router admin page
# Usually http://192.168.1.1 → Connected Devices / DHCP Leases → find "raspberrypi"
```

---

### `command not found` errors

| Command that failed | Fix |
|---|---|
| `hostnamectl` | SSH into the Pi first — this is a Pi-only command |
| `raspi-config` | SSH into the Pi first — this is a Pi-only command |
| `apt` / `apt-get` | SSH into the Pi first — this is a Pi-only command |
| `rpicam-hello` | SSH into the Pi first — this is a Pi-only command |
| `vcgencmd` | SSH into the Pi first — this is a Pi-only command |
| `nmap` | Run `brew install nmap` on your Mac |
| `brew` | Install Homebrew — see [Section 2](#2-macos-prerequisites) |

---

### Camera not detected

```bash
# [PI]
rpicam-hello --list-cameras
# Expected: lists at least one camera

rpicam-hello --timeout 3000
```

**Fixes:**
- Power off, reseat both ribbon cable ends, press tabs firmly, power on.
- Confirm `/boot/firmware/config.txt` contains `camera_auto_detect=1` (present by default on Bookworm).
- Do NOT use `raspi-config` → Interface Options → Camera — that option was removed on Bookworm.

---

### Backend service not starting

```bash
# [PI]
sudo journalctl -u rasperify -n 50 --no-pager
```

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'picamera2'` | `sudo apt install python3-picamera2` |
| `Address already in use` — port 8000 | `sudo fuser -k 8000/tcp` then `sudo systemctl restart rasperify` |
| `GEMINI_API_KEY not set` | Edit `~/RasperifyScanner/backend/.env` |
| `Permission denied: /dev/video0` | `sudo usermod -aG video pi` then reconnect SSH |

---

## Quick Reference

### Connection IP addresses

| Mode | Pi IP | SSH |
|---|---|---|
| USB-C SHARED (no ICS) | `10.12.194.1` | `ssh pi@10.12.194.1` |
| USB-C CLIENT (macOS ICS) | `192.168.2.x` | `ssh pi@raspberrypi.local` |
| Ethernet (DHCP) | run `ip addr show eth0` on Pi | `ssh pi@<eth0-ip>` |
| WiFi (DHCP) | run `hostname -I` on Pi | `ssh pi@raspberrypi.local` |

### Backend URLs

| Mode | Health check | API docs |
|---|---|---|
| USB-C SHARED | `http://10.12.194.1:8000/api/v1/health` | `http://10.12.194.1:8000/docs` |
| USB-C CLIENT / WiFi / Ethernet | `http://raspberrypi.local:8000/api/v1/health` | `http://raspberrypi.local:8000/docs` |

Full API reference: [API_REFERENCE.md](API_REFERENCE.md)
