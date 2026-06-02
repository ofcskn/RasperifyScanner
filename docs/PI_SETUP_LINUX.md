# Raspberry Pi 4 Model B — Setup Guide for Linux

> **Who is this for?** Linux desktop/laptop users connecting a Raspberry Pi 4 Model B to run the RasperifyScanner backend for the first time — from unboxing to a fully working service.

---

## Critical: Know Which Machine You Are Typing On

Every command is labelled:

- **[PI]** — run inside an SSH session on the Pi, or directly on the Pi with a keyboard
- **[LINUX]** — run in a terminal on your Linux machine

**Never run a [PI] command on your Linux host.** Although both machines run Linux, tools like `raspi-config`, `libcamera-hello`, `vcgencmd`, and `rpi-usb-gadget` only exist on Raspberry Pi OS and will print `command not found` on a standard desktop distro.

If you are unsure which machine your terminal is connected to:

```bash
hostname
# "raspberrypi" (or your chosen name) → you are on the Pi
# anything else → you are on your Linux machine
```

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [Linux Prerequisites](#2-linux-prerequisites)
3. [Flash Raspberry Pi OS](#3-flash-raspberry-pi-os)
4. [First Boot — Get Initial Access](#4-first-boot--get-initial-access)
5. [System Configuration on the Pi](#5-system-configuration-on-the-pi)
6. [Attach and Enable the CSI Camera](#6-attach-and-enable-the-csi-camera)
7. [USB-C OTG Gadget Mode — Install rpi-usb-gadget](#7-usb-c-otg-gadget-mode--install-rpi-usb-gadget)
8. [Configure Linux Networking for USB-C](#8-configure-linux-networking-for-usb-c)
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
| USB-C cable — **data-capable** | Many USB-C cables carry power only. Use one rated for data (USB 2.0+). Most Android phone charging cables work. Power-only cables are physically identical — if the gadget interface never appears after boot, swap the cable before troubleshooting anything else. |
| Linux machine with a USB-C or USB-A port | Any major desktop distro (Ubuntu, Fedora, Arch, Debian, etc.) |
| MicroSD card reader | To flash the OS from your Linux machine |
| USB-C power supply, 5V / 3A minimum | When not powering via USB-C OTG. A 65 W laptop charger with USB-C works. |
| (Optional) HDMI micro-to-full adapter + monitor | Only needed for the HDMI+keyboard first-boot option |
| (Optional) USB keyboard | Only needed for the HDMI+keyboard first-boot option |

---

## 2. Linux Prerequisites

Install these tools on your Linux machine **before starting**.

---

### nmap

**[LINUX]**

```bash
# Debian/Ubuntu
sudo apt install nmap

# Fedora
sudo dnf install nmap

# Arch
sudo pacman -S nmap
```

Verify:

```bash
nmap --version
# Expected: Nmap 7.x
```

---

### Raspberry Pi Imager

**[LINUX]**

```bash
# Debian/Ubuntu/Raspberry Pi OS
sudo apt install rpi-imager

# Fedora
sudo dnf install rpi-imager

# Arch (AUR)
yay -S rpi-imager
```

Or download the AppImage from https://www.raspberrypi.com/software/

---

### Internet Connection Sharing (ICS) via NetworkManager

Linux uses NetworkManager's "shared" mode to give the Pi internet access through your machine's WiFi. No extra package is needed — NetworkManager is installed by default on all major desktop distros.

Verify NetworkManager is running:

```bash
# [LINUX]
systemctl is-active NetworkManager
# Expected: active
```

---

## 3. Flash Raspberry Pi OS

> **[LINUX]** All steps in this section run on your Linux machine.

1. Insert the MicroSD card into your machine via a card reader.
2. Open **Raspberry Pi Imager** (launch from your application menu or run `rpi-imager`).
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
7. Eject the MicroSD card safely:

```bash
# [LINUX]
sudo eject /dev/sdX   # replace sdX with your card reader device
```

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
2. Wait ~60 seconds, then find the Pi's IP from your Linux machine:

**[LINUX]**

```bash
# Method 1: mDNS (try first — usually works)
ping raspberrypi.local

# Method 2: nmap — find your subnet first
ip route | grep "src"          # shows your default subnet
nmap -sn 192.168.x.0/24 | grep -B2 -i "raspberry"
# Replace 192.168.x.0/24 with your actual subnet

# Method 3: ARP table
arp -n
# Raspberry Pi MAC addresses start with b8:27:eb, dc:a6:32, or e4:5f:01

# Method 4: Router admin page
# Usually http://192.168.1.1 → Connected Devices / DHCP Leases → find "raspberrypi"
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

1. Plug an Ethernet cable between the Pi and your router (not directly to your Linux machine — direct requires manual static IPs on both sides).
2. Connect USB-C power.
3. Wait ~60 seconds. Find the IP using the same methods as Option B.
4. SSH: `ssh pi@<ip>`

---

## 5. System Configuration on the Pi

> **[PI]** Every command below runs on the Pi via SSH.

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
# [PI] — run this inside the SSH session on the Pi
sudo hostnamectl set-hostname raspberrypi
```

> If you run `hostnamectl` outside the SSH session on your Linux host, it changes your Linux machine's hostname, not the Pi's. Always verify you are on the correct machine first.

---

### Install required system packages

```bash
# [PI]
sudo apt install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  python3-picamera2 \
  libcamera-apps \
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

```bash
# [PI]
sudo raspi-config
```

Navigate: **Interface Options → Camera → Yes → Finish → Reboot**

Reconnect via SSH after the reboot.

### Verify the camera

```bash
# [PI]
vcgencmd get_camera
# Expected: supported=1 detected=1, libcamera interfaces=1

libcamera-hello --timeout 5000

libcamera-jpeg -o /tmp/test.jpg && echo "Camera OK"

python3 -c "
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
print('Camera service OK')
cam.stop()
"
```

**If `detected=0`:** Power off, reseat both ribbon cable ends (press locking tabs firmly closed), power on.

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

# Plug the USB-C data cable into your Linux machine before rebooting
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

| Mode | When it activates | Pi IP | Your Linux machine IP |
|---|---|---|---|
| **CLIENT mode** | NetworkManager shared ICS is active on the gadget interface | `10.42.0.x` (assigned by Linux) | `10.42.0.1` |
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

> **VPN warning:** Disable any VPN on your Linux machine before connecting. VPNs intercept the local routing table and block the USB gadget link.

---

## 8. Configure Linux Networking for USB-C

Linux recognises the Pi as a **CDC-ECM** device — no driver needed.

After plugging in the USB-C cable and the Pi boots, a new interface appears automatically (usually `usb0` or `enx<mac-address>`).

**[LINUX]** Verify SHARED mode connectivity (no ICS needed):

```bash
ip addr
# Look for an interface named usb0 or enx<mac> with an IP in 10.12.194.x

ping 10.12.194.1
# Expected: replies from the Pi

ssh pi@10.12.194.1
```

---

### Optional: Enable Internet Connection Sharing via NetworkManager (CLIENT mode)

ICS lets the Pi use the internet through your machine's WiFi. This is optional — the Pi works without internet access once deployed.

```bash
# [LINUX] Step 1 — Find the gadget interface name (usb0 or enx...)
ip link show | grep -i "usb\|enx"
# Note the interface name (e.g. usb0 or enxb827eb123456)

# Step 2 — Create a shared connection on that interface (replace usb0 with your interface name)
nmcli con add type ethernet ifname usb0 con-name "pi-gadget-ics" \
  ipv4.method shared

# Step 3 — Bring it up
nmcli con up "pi-gadget-ics"
```

Your Linux machine is now assigned `10.42.0.1` on the gadget interface. The Pi's auto-switcher detects this gateway and switches to CLIENT mode, receiving a `10.42.0.x` IP.

```bash
# [LINUX] Verify after enabling ICS
ping raspberrypi.local
ssh pi@raspberrypi.local
```

To remove the ICS profile later:

```bash
# [LINUX]
nmcli con delete "pi-gadget-ics"
```

---

## 9. Verify the Connection

From your Linux machine, confirm you can reach the Pi:

| Mode | Pi IP | SSH command |
|---|---|---|
| SHARED (no ICS) | `10.12.194.1` | `ssh pi@10.12.194.1` |
| CLIENT (Linux ICS) | `10.42.0.x` | `ssh pi@raspberrypi.local` |

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

From your Linux machine, verify:

```bash
# [LINUX] SHARED mode
curl http://10.12.194.1:8000/api/v1/health | python3 -m json.tool

# [LINUX] CLIENT mode
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

### USB-C interface not appearing on Linux

```bash
# [LINUX] Is the Pi detected as a USB device?
lsusb | grep -i "raspberry\|rndis\|linux"

# Does a USB network interface appear?
ip link show

# Does the Pi have an IP on the USB link?
ip addr | grep "10.12.194"
```

**Most common causes in order:**
1. Power-only USB-C cable — swap the cable first
2. `rpi-usb-gadget on` was not run, or the Pi was not rebooted after
3. VPN active on your Linux machine — disable it

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
# [LINUX] ARP table (works on same subnet)
arp -n
# Pi MAC prefixes: b8:27:eb  dc:a6:32  e4:5f:01

# Any OS: check router admin page
# Usually http://192.168.1.1 → Connected Devices / DHCP Leases → find "raspberrypi"
```

---

### `command not found` errors

| Command that failed | Fix |
|---|---|
| `raspi-config` | SSH into the Pi first — this is a Pi-only command |
| `libcamera-hello` | SSH into the Pi first — this is a Pi-only command |
| `vcgencmd` | SSH into the Pi first — this is a Pi-only command |
| `rpi-usb-gadget` | SSH into the Pi first — this is a Pi-only command |
| `nmap` not found | Install: `sudo apt install nmap` (Debian/Ubuntu) |
| `rpi-imager` not found | Install: `sudo apt install rpi-imager` |

> **Caution:** Both your Linux machine and the Pi have `hostnamectl`, `apt`, and `systemctl`. Always verify which machine your terminal is connected to before running commands with these tools.

---

### Camera not detected

```bash
# [PI]
vcgencmd get_camera
# Must show: supported=1 detected=1

libcamera-hello --timeout 3000
```

**Fixes:**
- Power off, reseat both ribbon cable ends, press tabs firmly, power on.
- `sudo raspi-config` → Interface Options → Camera → Enable → Reboot.
- Confirm `/boot/firmware/config.txt` contains `camera_auto_detect=1`.

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
| USB-C CLIENT (Linux ICS) | `10.42.0.x` | `ssh pi@raspberrypi.local` |
| Ethernet (DHCP) | run `ip addr show eth0` on Pi | `ssh pi@<eth0-ip>` |
| WiFi (DHCP) | run `hostname -I` on Pi | `ssh pi@raspberrypi.local` |

### Backend URLs

| Mode | Health check | API docs |
|---|---|---|
| USB-C SHARED | `http://10.12.194.1:8000/api/v1/health` | `http://10.12.194.1:8000/docs` |
| USB-C CLIENT / WiFi / Ethernet | `http://raspberrypi.local:8000/api/v1/health` | `http://raspberrypi.local:8000/docs` |

Full API reference: [API_REFERENCE.md](API_REFERENCE.md)
