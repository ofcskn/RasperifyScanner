# Raspberry Pi 4 Model B — Complete Setup Guide

> **Who is this for?** Any developer connecting a Raspberry Pi 4 Model B to run the RasperifyScanner backend for the first time — from unboxing to a fully working service.

---

## Critical: Know Which Machine You Are Typing On

Every command is labelled:

- **[PI]** — run inside an SSH session on the Pi, or directly on the Pi with a keyboard
- **[MAC]** — run in a Terminal on your Mac
- **[WIN]** — run on a Windows PC
- **[LINUX]** — run on a Linux desktop/laptop

**Never run a [PI] command on your host machine.** Tools like `raspi-config`, `rpicam-hello`, `vcgencmd`, `hostnamectl`, `apt`, and `systemctl` are Raspberry Pi OS / Linux tools. They do not exist on macOS or Windows and will print `command not found`.

If you are unsure which machine your terminal is connected to:

```bash
hostname
# "raspberrypi" (or your chosen name) → you are on the Pi
# anything else → you are on your host machine
```

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [Host Machine Prerequisites](#2-host-machine-prerequisites)
   - [macOS](#macos)
   - [Windows](#windows)
   - [Linux](#linux)
3. [Flash Raspberry Pi OS](#3-flash-raspberry-pi-os)
4. [First Boot — Get Initial Access](#4-first-boot--get-initial-access)
5. [System Configuration on the Pi](#5-system-configuration-on-the-pi)
6. [Attach and Enable the CSI Camera](#6-attach-and-enable-the-csi-camera)
7. [USB-C OTG Gadget Mode — Install rpi-usb-gadget](#7-usb-c-otg-gadget-mode--install-rpi-usb-gadget)
8. [Configure Host Networking for USB-C](#8-configure-host-networking-for-usb-c)
   - [macOS](#macos-1)
   - [Windows](#windows-1)
   - [Linux](#linux-1)
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
| USB-C cable — **data-capable** | Many USB-C cables carry power only. Use one rated for data (USB 2.0+). Most Android phone charging cables work. Power-only cables are physically identical — if the gadget interface never appears on your host, swap the cable before troubleshooting anything else. |
| Host machine with a USB-C or USB-A port | macOS, Windows, or Linux all supported |
| MicroSD card reader | To flash the OS from your host machine |
| USB-C power supply, 5V / 3A minimum | When not powering via USB-C OTG. A 65 W laptop charger with USB-C works. |
| (Optional) HDMI micro-to-full adapter + monitor | Only needed for the HDMI+keyboard first-boot option |
| (Optional) USB keyboard | Only needed for the HDMI+keyboard first-boot option |

---

## 2. Host Machine Prerequisites

Install these tools on your host machine **before starting**. They are required by later steps.

---

### macOS

#### Homebrew (Mac package manager)

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

#### nmap (network scanner — needed to find the Pi's IP during first boot)

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

#### Raspberry Pi Imager

**[MAC]**

```bash
brew install --cask raspberry-pi-imager
```

Or download from https://www.raspberrypi.com/software/

---

### Windows

#### Raspberry Pi Imager

Download and install from https://www.raspberrypi.com/software/

#### nmap (to find the Pi's IP during first boot)

Download and install from https://nmap.org/download.html — choose the Windows installer (`.exe`).

After installing, open **Command Prompt** or **PowerShell** and verify:

```cmd
nmap --version
```

#### RNDIS driver (required for USB-C gadget networking on Windows)

Windows does not natively recognize the Pi as a USB Ethernet device — it needs a driver.

Download `rpi-usb-gadget-driver-setup.exe` from:
https://github.com/raspberrypi/rpi-usb-gadget/releases/latest

> Do NOT install this yet — install it after the Pi is physically connected in Section 8. The installer requires the device to be present.

#### Internet Connection Sharing (ICS) — no extra install needed

ICS is built into Windows. You will enable it on your Wi-Fi adapter in Section 8. This allows the Pi to reach the internet through your laptop's Wi-Fi while connected via USB-C.

---

### Linux

#### nmap

**[LINUX]**

```bash
# Debian/Ubuntu
sudo apt install nmap

# Fedora
sudo dnf install nmap

# Arch
sudo pacman -S nmap
```

#### Raspberry Pi Imager

**[LINUX]**

```bash
# Debian/Ubuntu/Raspberry Pi OS
sudo apt install rpi-imager

# Or download the AppImage from https://www.raspberrypi.com/software/
```

#### Internet Connection Sharing (ICS) via NetworkManager

Linux uses NetworkManager's "shared" mode. No extra install needed if NetworkManager is running (it is on all major desktop distros).

---

## 3. Flash Raspberry Pi OS

> **[MAC/WIN/LINUX]** All steps in this section are on your host machine.

1. Insert the MicroSD card into your machine via a card reader.
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

> **Alternatively, enable USB gadget mode directly in Imager 2.0+:**
> In Advanced Options → Interfaces & Features → enable **"USB Gadget mode"**.
> This pre-configures everything in Section 7 so you can skip the manual `apt install` steps.
> The CLI equivalent: `rpi-imager-cli --usb-gadget`

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
2. Wait ~60 seconds, then find the Pi's IP on your host machine:

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

**[WIN]** Open Command Prompt or PowerShell:

```cmd
ping raspberrypi.local

:: Or with nmap (after installing it from Section 2):
ipconfig
:: Note your IPv4 address under "Wi-Fi adapter" to find your subnet
nmap -sn 192.168.x.0/24
:: Look for a line mentioning "raspberry" or the Pi's MAC prefix
```

**[LINUX]**

```bash
ping raspberrypi.local

# Or with nmap:
ip route | grep "src"          # shows your default subnet
nmap -sn 192.168.x.0/24 | grep -B2 -i "raspberry"
```

3. SSH into the Pi from any host OS:

```bash
ssh pi@raspberrypi.local
# or
ssh pi@<ip-address-you-found>
```

4. First-time connection shows a fingerprint warning — type `yes` and press Enter. Enter your password.

---

### Option C: Headless via Ethernet

1. Plug an Ethernet cable between the Pi and your router (not directly to your host — direct requires manual static IPs on both sides).
2. Connect USB-C power.
3. Wait ~60 seconds. Find the IP using the same methods as Option B.
4. SSH: `ssh pi@<ip>`

---

## 5. System Configuration on the Pi

> **[PI]** Every command below runs on the Pi via SSH.
> `hostnamectl`, `apt`, `raspi-config`, `systemctl` are Linux-only tools — they will fail on macOS/Windows.

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
# [PI] — this is a Linux command, run it on the Pi only
sudo hostnamectl set-hostname raspberrypi
```

> `hostnamectl` does not exist on macOS or Windows. The `command not found: hostnamectl` error you may have seen earlier means it was accidentally run on the host machine, not the Pi.

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
>
> It replaces the manual `config.txt` / `cmdline.txt` editing used in older guides. The package handles all of that automatically and adds auto-switching between two networking modes.

**[PI]** — run inside your SSH session.

### Install the package

```bash
# [PI]
sudo apt update
sudo apt install rpi-usb-gadget

# Enable gadget mode
sudo rpi-usb-gadget on

# Reboot — plug the USB-C cable into your host before rebooting
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

### How the auto-switching works (important — read this)

The Pi runs two network profiles on the USB interface (`usb0`) and automatically switches between them:

| Mode | When it activates | Pi IP | Host IP |
|---|---|---|---|
| **CLIENT mode** | Host has Internet Connection Sharing (ICS) enabled | Assigned by host DHCP (e.g. `192.168.137.x` on Windows, `192.168.2.x` on macOS, `10.42.0.x` on Linux) | Windows: `192.168.137.1` / macOS: `192.168.2.1` / Linux: `10.42.0.1` |
| **SHARED mode** | No ICS detected on host | `10.12.194.1` (fixed) | `10.12.194.2`–`10.12.194.14` (DHCP from Pi) |

**The switcher checks every ~4 seconds** by probing for a known ICS gateway via ARP. If ICS is active on your host, the Pi becomes a client and gets internet through the host. If ICS is off, the Pi becomes the DHCP server and gives the host an IP in the `10.12.194.x` range.

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

> **VPN warning:** Disable any VPN on your host before connecting. VPNs intercept the local routing table and block the USB gadget link.

---

## 8. Configure Host Networking for USB-C

Plug the USB-C data cable into your host machine, then follow the section for your OS.

---

### macOS

macOS recognises the Pi as a **CDC-ECM** USB Ethernet adapter — no driver needed.

After the Pi finishes booting, a new network interface appears in System Settings:

1. Open **System Settings → Network**.
2. Look for a new interface named `RNDIS/ECM Gadget`, `USB 10/100 LAN`, or `USB Ethernet`.
3. If you see it: **no further configuration is required for SHARED mode**. The Pi's DHCP server assigns your Mac an IP in `10.12.194.x` automatically.
4. Verify:

```bash
# [MAC]
ifconfig | grep -A4 "10.12.194"
# Expected: inet 10.12.194.2 (or similar)

ping 10.12.194.1
# Expected: replies from the Pi
```

#### Optional: Enable Internet Connection Sharing (CLIENT mode)

Enabling ICS lets the Pi access the internet through your Mac's WiFi.

1. **System Settings → General → Sharing → Internet Sharing** (macOS Ventura/Sonoma)
   or **System Preferences → Sharing → Internet Sharing** (older macOS).
2. Share connection from: **Wi-Fi**
3. To computers using: check the USB gadget interface (`RNDIS/ECM Gadget` or `USB Ethernet`)
4. Turn **Internet Sharing** on.

macOS assigns itself `192.168.2.1` on the gadget interface and hands the Pi a `192.168.2.x` IP via DHCP. The Pi's auto-switcher detects this and switches to CLIENT mode within ~10 seconds.

```bash
# [MAC] After enabling ICS, verify
ping raspberrypi.local
ssh pi@raspberrypi.local
```

---

### Windows

Windows requires a driver before the Pi is recognised. Follow these steps in order.

#### Step 1 — Install the RNDIS driver

1. With the Pi's USB-C cable plugged into your PC, open **Device Manager** (`Win + X → Device Manager`).
2. Look for an unknown device — it may appear as `RNDIS` or `USB Ethernet/RNDIS Gadget` under "Other devices" with a yellow warning icon.
3. Run `rpi-usb-gadget-driver-setup.exe` (downloaded in Section 2).
4. Follow the installer. It adds the driver via `pnputil`.
5. After installation, Device Manager should show **"Raspberry Pi USB Remote NDIS Network Device"** under Network Adapters.

If the device still shows as unknown after installing the driver: unplug and replug the USB-C cable.

#### Step 2 — Verify basic connectivity (SHARED mode, no ICS)

Without ICS, the Pi is in SHARED mode and assigns your PC an IP in `10.12.194.x`.

**[WIN]** Open Command Prompt or PowerShell:

```cmd
ping 10.12.194.1
:: Expected: replies from the Pi

ssh pi@10.12.194.1
```

#### Step 3 — Enable Internet Connection Sharing (optional, CLIENT mode)

ICS lets the Pi use the internet through your PC's WiFi.

1. Open **Control Panel → Network and Internet → Network Connections** (or press `Win+R`, type `ncpa.cpl`, Enter).
2. Right-click your **Wi-Fi adapter** → **Properties**.
3. Go to the **Sharing** tab.
4. Check **"Allow other network users to connect through this computer's Internet connection"**.
5. In the dropdown "Home networking connection", select **Raspberry Pi USB Remote NDIS Network Device**.
6. Click **OK**.

Windows assigns itself `192.168.137.1` on the gadget NIC. The Pi's auto-switcher detects this gateway and switches to CLIENT mode, receiving a `192.168.137.x` IP.

```cmd
:: [WIN] Verify after enabling ICS
ping raspberrypi.local
ssh pi@raspberrypi.local
```

#### Troubleshooting Windows

| Symptom | Fix |
|---|---|
| "Unidentified adapter" / yellow warning in Device Manager | RNDIS driver not installed — run `rpi-usb-gadget-driver-setup.exe` |
| Pi shows `169.254.x.x` (APIPA address) | ICS is not active, or not bound to the gadget NIC — recheck Step 3 |
| Flapping between CLIENT/SHARED | Windows didn't bind ICS to the correct adapter — disable and re-enable ICS |
| Pi not showing in Device Manager at all | USB-C cable is power-only — swap to a data cable |
| SSH timeout via `raspberrypi.local` | Disable your VPN; or use IP `192.168.137.x` directly |

To manually push the Pi into CLIENT mode from the Pi side:

```bash
# [PI]
sudo nmcli con up 'USB Gadget (client)'
```

---

### Linux

Linux recognises the Pi as a **CDC-ECM** device — no driver needed.

After plugging in the USB-C cable and the Pi boots, a new interface appears (usually `usb0` or `enx...`).

**[LINUX]** Verify:

```bash
ip addr
# Look for an interface named usb0 or enx<mac> with an IP in 10.12.194.x

ping 10.12.194.1
ssh pi@10.12.194.1
```

#### Enable Internet Connection Sharing via NetworkManager (optional, CLIENT mode)

```bash
# [LINUX] Find the gadget interface name (usb0 or enx...)
ip link show | grep -i "usb\|enx"

# Enable shared/ICS mode on it (replace usb0 with your interface name)
nmcli con add type ethernet ifname usb0 con-name "pi-gadget-ics" \
  ipv4.method shared

nmcli con up "pi-gadget-ics"
```

This assigns your Linux machine `10.42.0.1` on the gadget interface and gives the Pi a `10.42.0.x` IP via DHCP. The Pi's auto-switcher detects the `10.42.0.1` gateway and switches to CLIENT mode.

```bash
# [LINUX] Verify after enabling ICS
ping raspberrypi.local
ssh pi@raspberrypi.local
```

---

## 9. Verify the Connection

From your host machine, confirm you can reach the Pi. Use the correct IP for your mode:

| Mode | Pi IP | SSH command |
|---|---|---|
| SHARED (no ICS) | `10.12.194.1` | `ssh pi@10.12.194.1` |
| CLIENT — Windows ICS | `192.168.137.x` (check via `raspberrypi.local`) | `ssh pi@raspberrypi.local` |
| CLIENT — macOS ICS | `192.168.2.x` | `ssh pi@raspberrypi.local` |
| CLIENT — Linux ICS | `10.42.0.x` | `ssh pi@raspberrypi.local` |

**[PI]** — from inside the SSH session, verify the USB interface:

```bash
ip addr show usb0
# Look for: state UP
# Look for: inet <ip>/xx

# Check which mode the switcher chose
sudo systemctl status rpi-usb-gadget-ics
```

**[ANY HOST]** Verify the backend (after Section 10):

```bash
# SHARED mode
curl http://10.12.194.1:8000/api/v1/health

# CLIENT mode
curl http://raspberrypi.local:8000/api/v1/health
```

---

## 10. Deploy the RasperifyScanner Backend

> **[PI]** All commands run on the Pi via SSH.

### Clone the repository

```bash
cd ~
git clone https://github.com/<your-username>/RasperifyScanner.git
cd RasperifyScanner/backend
```

### Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
# Prompt changes to (.venv) — virtual environment is active
```

### Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
# Takes 5–15 minutes on Pi hardware
```

### Configure environment variables

```bash
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
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

From your host, verify:

```bash
# SHARED mode
curl http://10.12.194.1:8000/api/v1/health | python3 -m json.tool
```

Expected:

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

### USB-C interface not appearing on host

**[MAC]**

```bash
# Is the Pi detected as a USB device?
system_profiler SPUSBDataType | grep -A8 -i "raspberry\|rndis\|linux\|gadget"

# Does a USB Ethernet interface appear?
networksetup -listallhardwareports

# Does the Pi have an IP on the USB link?
ifconfig | grep -A4 "10.12.194"
```

**[WIN]** Open Device Manager (`Win+X → Device Manager`) and check under "Network Adapters" for "Raspberry Pi USB Remote NDIS Network Device".

**[LINUX]**

```bash
lsusb | grep -i "raspberry\|rndis\|linux"
ip link show
```

**Most common causes in order:**
1. Power-only USB-C cable — swap the cable first
2. `rpi-usb-gadget on` was not run, or the Pi was not rebooted after
3. Windows: RNDIS driver not installed
4. VPN active on the host — disable it

---

### Check gadget mode status on the Pi

```bash
# [PI]
sudo rpi-usb-gadget status

# Check if the USB interface is up
ip addr show usb0

# Check the auto-switcher service
sudo systemctl status rpi-usb-gadget-ics
sudo journalctl -u rpi-usb-gadget-ics -n 30 --no-pager
```

---

### Finding Pi's IP without nmap

```bash
# [MAC] ARP table (works on same subnet)
arp -a
# Pi MAC prefixes: b8:27:eb  dc:a6:32  e4:5f:01

# [WIN]
arp -a

# [LINUX]
arp -n

# Any OS: check router admin page
# Usually http://192.168.1.1 → Connected Devices / DHCP Leases → find "raspberrypi"
```

---

### `command not found` errors

| Command that failed | Correct machine | Fix |
|---|---|---|
| `hostnamectl` | [PI] only | SSH into the Pi first |
| `raspi-config` | [PI] only | SSH into the Pi first |
| `apt` / `apt-get` | [PI] only | SSH into the Pi first |
| `rpicam-hello` | [PI] only | SSH into the Pi first |
| `vcgencmd` | [PI] only | SSH into the Pi first |
| `rpi-usb-gadget` | [PI] only | SSH into the Pi first |
| `nmap` | [MAC] not pre-installed | `brew install nmap` |
| `brew` | [MAC] not installed | See [Section 2 → macOS](#macos) |

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
| USB-C CLIENT — Windows ICS | assigned by Windows (`192.168.137.x`) | `ssh pi@raspberrypi.local` |
| USB-C CLIENT — macOS ICS | assigned by Mac (`192.168.2.x`) | `ssh pi@raspberrypi.local` |
| USB-C CLIENT — Linux ICS | assigned by Linux (`10.42.0.x`) | `ssh pi@raspberrypi.local` |
| Ethernet (DHCP) | run `ip addr show eth0` on Pi | `ssh pi@<eth0-ip>` |
| WiFi (DHCP) | run `hostname -I` on Pi | `ssh pi@raspberrypi.local` |

### Backend URLs

| Mode | Health check | API docs |
|---|---|---|
| USB-C SHARED | `http://10.12.194.1:8000/api/v1/health` | `http://10.12.194.1:8000/docs` |
| USB-C CLIENT / WiFi / Ethernet | `http://raspberrypi.local:8000/api/v1/health` | `http://raspberrypi.local:8000/docs` |

Full API reference: [API_REFERENCE.md](API_REFERENCE.md)
