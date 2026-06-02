# Raspberry Pi 4 Model B — Setup Guide for Windows

> **Who is this for?** Windows users connecting a Raspberry Pi 4 Model B to run the RasperifyScanner backend for the first time — from unboxing to a fully working service.

---

## Critical: Know Which Machine You Are Typing On

Every command is labelled:

- **[PI]** — run inside an SSH session on the Pi, or directly on the Pi with a keyboard
- **[WIN]** — run in Command Prompt or PowerShell on your Windows PC

**Never run a [PI] command on your PC.** Tools like `raspi-config`, `rpicam-hello`, `vcgencmd`, `hostnamectl`, `apt`, and `systemctl` are Raspberry Pi OS / Linux tools. They do not exist on Windows and will print `'...' is not recognized as an internal or external command`.

If you are unsure which machine your terminal is connected to:

```bash
hostname
# "raspberrypi" (or your chosen name) → you are on the Pi
# anything else → you are on your Windows PC
```

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [Windows Prerequisites](#2-windows-prerequisites)
3. [Flash Raspberry Pi OS](#3-flash-raspberry-pi-os)
4. [First Boot — Get Initial Access](#4-first-boot--get-initial-access)
5. [System Configuration on the Pi](#5-system-configuration-on-the-pi)
6. [Attach and Enable the CSI Camera](#6-attach-and-enable-the-csi-camera)
7. [USB-C OTG Gadget Mode — Install rpi-usb-gadget](#7-usb-c-otg-gadget-mode--install-rpi-usb-gadget)
8. [Configure Windows Networking for USB-C](#8-configure-windows-networking-for-usb-c)
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
| USB-C cable — **data-capable** | Many USB-C cables carry power only. Use one rated for data (USB 2.0+). Most Android phone charging cables work. Power-only cables are physically identical — if the gadget interface never appears in Device Manager, swap the cable before troubleshooting anything else. |
| Windows PC with a USB-C or USB-A port | Windows 10 version 1903+ or Windows 11 recommended |
| MicroSD card reader | To flash the OS from your PC |
| USB-C power supply, 5V / 3A minimum | When not powering via USB-C OTG. A 65 W laptop charger with USB-C works. |
| (Optional) HDMI micro-to-full adapter + monitor | Only needed for the HDMI+keyboard first-boot option |
| (Optional) USB keyboard | Only needed for the HDMI+keyboard first-boot option |

---

## 2. Windows Prerequisites

Install these tools on your Windows PC **before starting**.

---

### Raspberry Pi Imager

Download and install from https://www.raspberrypi.com/software/

Run the installer and follow the prompts. After installing, launch **Raspberry Pi Imager** from the Start menu to verify it opens.

---

### nmap (to find the Pi's IP during first boot)

Download and install the Windows installer (`.exe`) from https://nmap.org/download.html

After installing, open **Command Prompt** or **PowerShell** and verify:

```cmd
nmap --version
```

---

### RNDIS driver (required for USB-C gadget networking)

Windows does not natively recognise the Pi as a USB Ethernet device — it needs a driver.

Download `rpi-usb-gadget-driver-setup.exe` from:
https://github.com/raspberrypi/rpi-usb-gadget/releases/latest

> Do NOT install this yet — install it after the Pi is physically connected in Section 8. The installer requires the device to be present.

---

### OpenSSH client (built-in on Windows 10/11)

Windows 10 version 1809+ and Windows 11 include OpenSSH. Verify it is available:

```cmd
ssh -V
```

If `ssh` is not found, enable it via **Settings → Apps → Optional Features → Add a feature → OpenSSH Client**.

---

### Internet Connection Sharing (ICS) — no extra install needed

ICS is built into Windows. You will enable it on your Wi-Fi adapter in Section 8. This allows the Pi to reach the internet through your laptop's Wi-Fi while connected via USB-C.

---

## 3. Flash Raspberry Pi OS

> **[WIN]** All steps in this section run on your Windows PC.

1. Insert the MicroSD card into your PC via a card reader.
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
7. Eject the MicroSD card safely using the system tray icon.

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
2. Wait ~60 seconds, then find the Pi's IP. Open **Command Prompt** or **PowerShell**:

**[WIN]**

```cmd
ping raspberrypi.local

:: Or with nmap (after installing it from Section 2):
ipconfig
:: Note your IPv4 address under "Wi-Fi adapter" to find your subnet (e.g. 192.168.1.x)
nmap -sn 192.168.1.0/24
:: Look for a line mentioning "raspberry" or the Pi's MAC prefix (b8:27:eb, dc:a6:32, e4:5f:01)
```

3. SSH into the Pi:

```cmd
ssh pi@raspberrypi.local
:: or
ssh pi@<ip-address-you-found>
```

4. First-time connection shows a fingerprint warning — type `yes` and press Enter. Enter your password.

---

### Option C: Headless via Ethernet

1. Plug an Ethernet cable between the Pi and your router (not directly to your PC — direct requires manual static IPs on both sides).
2. Connect USB-C power.
3. Wait ~60 seconds. Find the IP using the same methods as Option B.
4. SSH: `ssh pi@<ip>`

---

## 5. System Configuration on the Pi

> **[PI]** Every command below runs on the Pi via SSH.
> `hostnamectl`, `apt`, `raspi-config`, and `systemctl` are Linux-only tools — they will not work on Windows.

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
# [PI] — run this on the Pi, not on your Windows PC
sudo hostnamectl set-hostname raspberrypi
```

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

# Plug the USB-C data cable into your PC before rebooting
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

| Mode | When it activates | Pi IP | Your PC IP |
|---|---|---|---|
| **CLIENT mode** | Windows ICS is enabled on the gadget NIC | `192.168.137.x` (assigned by Windows) | `192.168.137.1` |
| **SHARED mode** | No ICS detected | `10.12.194.1` (fixed) | `10.12.194.2`–`10.12.194.14` (DHCP from Pi) |

**In SHARED mode (no ICS), the Pi is always reachable at `10.12.194.1`:**

```cmd
ssh pi@10.12.194.1
curl http://10.12.194.1:8000/api/v1/health
```

**In CLIENT mode (with ICS), use mDNS:**

```cmd
ssh pi@raspberrypi.local
curl http://raspberrypi.local:8000/api/v1/health
```

> **VPN warning:** Disable any VPN on your PC before connecting. VPNs intercept the local routing table and block the USB gadget link.

---

## 8. Configure Windows Networking for USB-C

Windows requires a driver before the Pi is recognised. Follow these steps in order.

---

### Step 1 — Install the RNDIS driver

With the Pi's USB-C cable plugged into your PC:

1. Open **Device Manager** (`Win + X → Device Manager`).
2. Look for an unknown device — it may appear as `RNDIS` or `USB Ethernet/RNDIS Gadget` under "Other devices" with a yellow warning icon.
3. Run `rpi-usb-gadget-driver-setup.exe` (downloaded in Section 2).
4. Follow the installer. It adds the driver via `pnputil`.
5. After installation, Device Manager should show **"Raspberry Pi USB Remote NDIS Network Device"** under **Network Adapters**.

If the device still shows as unknown after installing the driver: unplug and replug the USB-C cable.

---

### Step 2 — Verify basic connectivity (SHARED mode, no ICS)

Without ICS, the Pi is in SHARED mode and assigns your PC an IP in `10.12.194.x`.

**[WIN]** Open Command Prompt or PowerShell:

```cmd
ping 10.12.194.1
:: Expected: replies from the Pi

ssh pi@10.12.194.1
```

---

### Step 3 — Enable Internet Connection Sharing (optional, CLIENT mode)

ICS lets the Pi use the internet through your PC's WiFi. This is optional — the Pi works without internet access once deployed.

1. Press `Win+R`, type `ncpa.cpl`, press Enter. This opens **Network Connections**.
2. Right-click your **Wi-Fi adapter** → **Properties**.
3. Go to the **Sharing** tab.
4. Check **"Allow other network users to connect through this computer's Internet connection"**.
5. In the dropdown **"Home networking connection"**, select **Raspberry Pi USB Remote NDIS Network Device**.
6. Click **OK**.

Windows assigns itself `192.168.137.1` on the gadget NIC. The Pi's auto-switcher detects this gateway and switches to CLIENT mode, receiving a `192.168.137.x` IP.

```cmd
:: [WIN] Verify after enabling ICS
ping raspberrypi.local
ssh pi@raspberrypi.local
```

---

### Troubleshooting Windows networking

| Symptom | Fix |
|---|---|
| "Unidentified adapter" / yellow warning in Device Manager | RNDIS driver not installed — run `rpi-usb-gadget-driver-setup.exe` |
| Pi shows `169.254.x.x` (APIPA address) | ICS is not active, or not bound to the gadget NIC — recheck Step 3 |
| Flapping between CLIENT/SHARED | Windows didn't bind ICS to the correct adapter — disable and re-enable ICS |
| Pi not showing in Device Manager at all | USB-C cable is power-only — swap to a data cable |
| SSH timeout via `raspberrypi.local` | Disable your VPN; or use `192.168.137.x` IP directly |

To manually push the Pi into CLIENT mode from the Pi side:

```bash
# [PI]
sudo nmcli con up 'USB Gadget (client)'
```

---

## 9. Verify the Connection

From your PC, confirm you can reach the Pi:

| Mode | Pi IP | SSH command |
|---|---|---|
| SHARED (no ICS) | `10.12.194.1` | `ssh pi@10.12.194.1` |
| CLIENT (Windows ICS) | `192.168.137.x` | `ssh pi@raspberrypi.local` |

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
| `CAMERA_MOCK` | `false` | Set `true` only for development without a camera |

Save in nano: `Ctrl+X` → `Y` → `Enter`.

### Test-run

```bash
# [PI]
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

From your PC, verify (open a new Command Prompt or PowerShell):

```cmd
:: [WIN] SHARED mode
curl http://10.12.194.1:8000/api/v1/health

:: [WIN] CLIENT mode
curl http://raspberrypi.local:8000/api/v1/health
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

Press `Ctrl+C` in the SSH session to stop the test run before continuing.

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

### USB-C interface not appearing in Device Manager

Open **Device Manager** (`Win+X → Device Manager`) and check under **Network Adapters** for **"Raspberry Pi USB Remote NDIS Network Device"**.

**Most common causes in order:**
1. Power-only USB-C cable — swap the cable first
2. `rpi-usb-gadget on` was not run, or the Pi was not rebooted after
3. RNDIS driver not installed — run `rpi-usb-gadget-driver-setup.exe`
4. VPN active on your PC — disable it

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

```cmd
:: [WIN] ARP table (works on same subnet)
arp -a
:: Pi MAC prefixes: b8:27:eb  dc:a6:32  e4:5f:01

:: Any OS: check router admin page
:: Usually http://192.168.1.1 → Connected Devices / DHCP Leases → find "raspberrypi"
```

---

### `command not found` / `not recognized` errors

| Command that failed | Fix |
|---|---|
| `hostnamectl` | SSH into the Pi first — this is a Pi-only command |
| `raspi-config` | SSH into the Pi first — this is a Pi-only command |
| `apt` / `apt-get` | SSH into the Pi first — this is a Pi-only command |
| `rpicam-hello` | SSH into the Pi first — this is a Pi-only command |
| `vcgencmd` | SSH into the Pi first — this is a Pi-only command |
| `nmap` not found | Install from https://nmap.org/download.html |
| `ssh` not found | Enable OpenSSH via Settings → Apps → Optional Features |

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
| USB-C CLIENT (Windows ICS) | `192.168.137.x` | `ssh pi@raspberrypi.local` |
| Ethernet (DHCP) | run `ip addr show eth0` on Pi | `ssh pi@<eth0-ip>` |
| WiFi (DHCP) | run `hostname -I` on Pi | `ssh pi@raspberrypi.local` |

### Backend URLs

| Mode | Health check | API docs |
|---|---|---|
| USB-C SHARED | `http://10.12.194.1:8000/api/v1/health` | `http://10.12.194.1:8000/docs` |
| USB-C CLIENT / WiFi / Ethernet | `http://raspberrypi.local:8000/api/v1/health` | `http://raspberrypi.local:8000/docs` |

Full API reference: [API_REFERENCE.md](API_REFERENCE.md)
