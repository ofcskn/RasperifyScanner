# Raspberry Pi 4 Model B — Complete Setup Guide

> **Who is this for?** Any developer connecting a Raspberry Pi 4 Model B to run the RasperifyScanner backend for the first time — from unboxing to a fully working service.

---

## Critical: Know Which Machine You Are Typing On

Every command in this guide is labelled with one of two tags:

- **[MAC]** — run this in a Terminal window on your Mac
- **[PI]** — run this inside an SSH session connected to the Pi, or directly on the Pi with a keyboard attached

**Never run a [PI] command on your Mac.** Tools like `raspi-config`, `libcamera-hello`, `vcgencmd`, `hostnamectl`, `apt`, and `systemctl` are Linux/Raspberry Pi OS tools. They do not exist on macOS and will produce `command not found`.

If you are unsure which machine your terminal is connected to, run:

```bash
hostname
# If it says "raspberrypi" (or whatever you named it) → you are on the Pi
# If it says your Mac's name → you are on the Mac
```

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [Mac Prerequisites](#2-mac-prerequisites)
3. [Flash Raspberry Pi OS](#3-flash-raspberry-pi-os)
4. [First Boot — Get Initial Access](#4-first-boot--get-initial-access)
5. [System Configuration on the Pi](#5-system-configuration-on-the-pi)
6. [Attach and Enable the CSI Camera](#6-attach-and-enable-the-csi-camera)
7. [USB-C OTG Gadget Mode — Permanent Mac ↔ Pi Link](#7-usb-c-otg-gadget-mode--permanent-mac--pi-link)
8. [Configure Mac Networking for USB-C](#8-configure-mac-networking-for-usb-c)
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
| USB-C cable — **data-capable** | Many USB-C cables carry power only. Use one rated for data (USB 2.0 or higher). Most Android phone charging cables work. Power-only cables are physically identical — if the connection never appears on your Mac, the cable is the first thing to swap. |
| Mac with a USB-C port | For USB-C OTG networking — the direct, no-router connection method |
| MicroSD card reader | To flash the OS from your Mac |
| USB-C power supply, 5V / 3A | Powers the Pi. A 65W laptop charger with USB-C works. |
| (Optional) HDMI micro-to-full adapter + monitor | Needed only if you choose the HDMI+keyboard first-boot option |
| (Optional) USB keyboard | Needed only if you choose the HDMI+keyboard first-boot option |

---

## 2. Mac Prerequisites

Install these tools on your Mac **before starting**. They are required by later steps.

### Homebrew (Mac package manager)

Homebrew is required to install the other tools. If you already have it, skip this.

**[MAC]** Check if Homebrew is installed:

```bash
brew --version
# If this prints a version number (e.g. "Homebrew 4.x.x"), Homebrew is installed — skip the install step below
# If this prints "command not found: brew", install it now
```

**[MAC]** Install Homebrew (if not installed):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen prompts. At the end, the installer will print two commands to run to add Homebrew to your PATH — run them before continuing. They look like:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify it works:

```bash
brew --version
# Expected: Homebrew 4.x.x
```

---

### nmap (network scanner — used to find the Pi's IP)

`nmap` is used to scan your local network and find the Pi's IP address during first boot. It is not installed on macOS by default.

**[MAC]**

```bash
# Check if already installed
nmap --version
# If this prints "Nmap 7.x", nmap is installed — skip the install step below
# If this prints "command not found: nmap", install it now

brew install nmap
```

> **Why does `nmap -sn 192.168.1.0/24` return nothing?**
> Your network may use a different subnet than `192.168.1.x`. First find your Mac's actual IP to determine the correct subnet:
>
> ```bash
> # [MAC] Find your Mac's IP on the current network
> ipconfig getifaddr en0   # WiFi
> ipconfig getifaddr en1   # Ethernet (if connected)
> ```
>
> If your Mac's IP is `192.168.0.105`, your subnet is `192.168.0.0/24`.
> If it is `10.0.1.50`, your subnet is `10.0.1.0/24`.
> Use that subnet in the nmap command, not `192.168.1.0/24`.

---

### Raspberry Pi Imager

Used to flash the OS onto the MicroSD card.

**[MAC]**

```bash
brew install --cask raspberry-pi-imager
```

Or download directly from https://www.raspberrypi.com/software/ — click "Download for macOS".

---

## 3. Flash Raspberry Pi OS

> **[MAC]** All steps in this section are performed on your Mac.

1. Insert the MicroSD card into your Mac using a card reader.
2. Open **Raspberry Pi Imager** (installed in Section 2).
3. Click **Choose OS** → select **Raspberry Pi OS (64-bit)**.
   - Choose **Raspberry Pi OS Lite (64-bit)** if you want a minimal headless server (recommended — no desktop, smaller image, faster boot).
   - Choose the full desktop version only if you need a GUI.
4. Click **Choose Storage** → select your MicroSD card. Double-check the size matches your card — do not accidentally select an external drive.
5. Click the **gear icon (⚙)** in the bottom-right corner to open **Advanced Options**. Configure all of these before writing:

   | Setting | What to set | Why |
   |---|---|---|
   | Set hostname | `raspberrypi` | Lets you find it with `raspberrypi.local` instead of scanning for its IP |
   | Enable SSH | Check it. Choose **Use password authentication** | Required to connect remotely — without this you need a monitor and keyboard forever |
   | Username | `pi` | This is the username you will use in all `ssh pi@...` commands |
   | Password | A password you will remember | You type this every time you SSH in |
   | Configure wireless LAN | Enter your WiFi name and password | Required for headless WiFi first-boot (Option B below). Leave blank if using Ethernet or HDMI/keyboard. |
   | Wireless LAN country | Your 2-letter country code (e.g. `TR`, `US`, `GB`, `DE`) | Required for WiFi to work legally and correctly |
   | Set locale settings | Your timezone and keyboard layout | Prevents clock drift and keyboard mis-mapping |

6. Click **Save**, then **Write**.
7. Wait for the write and verification to finish — usually 3–8 minutes depending on your card speed.
8. Eject the MicroSD card from your Mac safely (drag to Trash or right-click → Eject).

---

## 4. First Boot — Get Initial Access

> **Goal:** Reach the Pi with a shell so you can run Section 5 setup commands on it.
>
> USB-C OTG (the permanent connection method) cannot be set up until you have already SSHed into the Pi at least once. Pick one of the three options below to get that first access.

Insert the MicroSD card into the Pi's card slot (underside of the board).

---

### Option A: HDMI + Keyboard (no network needed, simplest)

1. Connect a monitor to the Pi's **micro-HDMI port** — this is the port labelled "HDMI0", closest to the USB-C power port (not the one furthest away).
2. Connect a USB keyboard to any of the Pi's USB-A ports.
3. Connect a USB-C power supply. The Pi powers on and boots automatically — there is no power button.
4. Wait ~30 seconds for the boot to complete. A login prompt appears on the monitor.
5. Log in:
   - Username: `pi`
   - Password: the password you set in Imager
6. You now have a shell on the Pi. Continue to [Section 5](#5-system-configuration-on-the-pi).

---

### Option B: Headless via WiFi (no monitor needed)

**Prerequisite:** You must have filled in the WiFi name and password in Imager's Advanced Options in Section 3. If you did not, use Option A or C instead.

1. Connect the USB-C power supply to the Pi. It boots automatically.
2. Wait ~60 seconds for the Pi to fully boot and connect to WiFi.
3. On your Mac, find the Pi's IP address:

**[MAC]**

```bash
# Method 1: mDNS (works on most home networks — try this first)
ping raspberrypi.local
# If you get replies like "64 bytes from raspberrypi.local (192.168.x.y)" → use that IP
# Press Ctrl+C to stop

# Method 2: nmap scan (requires nmap from Section 2)
# First find your Mac's IP to know your subnet:
ipconfig getifaddr en0
# Example output: 192.168.1.105  →  your subnet is 192.168.1.0/24

# Then scan that subnet:
nmap -sn 192.168.1.0/24 | grep -B2 -i "raspberry"
# Replace 192.168.1.0/24 with your actual subnet

# Method 3: Check your router's admin page
# Open http://192.168.1.1 (or your router's IP) in a browser
# Look for "Connected devices" or "DHCP clients" — find "raspberrypi"

# Method 4: ARP table (works if Mac and Pi are on the same subnet)
arp -a | grep -v incomplete
# Look for a line that appeared recently — the Pi's MAC address starts with b8:27:eb or dc:a6:32 or e4:5f:01
```

4. SSH into the Pi:

**[MAC]**

```bash
ssh pi@raspberrypi.local
# or, if mDNS didn't work:
ssh pi@192.168.1.xxx   # replace with the IP you found above
```

5. The first time you SSH to a new Pi you will see:

```
The authenticity of host 'raspberrypi.local' can't be established.
ED25519 key fingerprint is SHA256:xxxx...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Type `yes` and press Enter. Enter your password when prompted.

6. You now have a shell on the Pi. Continue to [Section 5](#5-system-configuration-on-the-pi).

---

### Option C: Headless via Ethernet Cable

1. Plug an Ethernet cable between the Pi and your router (not directly to your Mac — direct Mac-to-Pi Ethernet requires manual static IP configuration on both ends).
2. Connect the USB-C power supply. The Pi boots and gets a DHCP IP from your router.
3. Wait ~60 seconds, then find the Pi's IP using the same methods as Option B (mDNS, nmap, or router admin page).
4. SSH in: `ssh pi@<ip-address>`

---

## 5. System Configuration on the Pi

> **[PI]** Every command in this section must be run on the Pi — either via SSH or directly on the Pi with a keyboard attached.
>
> `hostnamectl`, `apt`, `raspi-config`, and `systemctl` are Linux commands. They do not exist on macOS. If you accidentally run them on your Mac, they will print `command not found` — nothing is broken, just switch to the Pi terminal.

### Update all packages

```bash
# [PI]
sudo apt update && sudo apt full-upgrade -y
```

This downloads and installs all available updates. It may take 2–10 minutes on first run. When it finishes, reboot:

```bash
# [PI]
sudo reboot
```

Wait ~30 seconds, then reconnect via SSH.

---

### Set the hostname (only if you skipped it in Imager)

> Skip this if you already set the hostname to `raspberrypi` in Imager's Advanced Options.

```bash
# [PI] — run this ON THE PI, not on your Mac
sudo hostnamectl set-hostname raspberrypi
```

`hostnamectl` is a Linux systemd tool. It does not exist on macOS — this is the cause of `command not found: hostnamectl` if you ran it in a Mac terminal. Always verify which machine your terminal is on before running commands.

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

These packages are only available through `apt` on Raspberry Pi OS. Do not run `apt` on your Mac.

### Verify Python

```bash
# [PI]
python3.11 --version
# Expected: Python 3.11.x
```

---

## 6. Attach and Enable the CSI Camera

### Physical wiring

> **Power off the Pi completely before touching the ribbon cable.** Connecting or disconnecting the camera while powered can damage the camera module.

**[PI]** Shut down cleanly:

```bash
sudo shutdown -h now
```

Wait until the green activity LED on the Pi stops flashing. Then unplug the USB-C power cable.

**Connect the ribbon cable:**

1. Find the **CSI camera port** on the Pi. It is the narrow black connector located between the two HDMI ports and the USB-A ports. It has a small label "CAMERA" printed on the board.
2. Gently lift the brown plastic locking tab straight up — it rises about 2 mm. It does not detach.
3. Slide in the ribbon cable. The **blue strip** on the cable must face toward the USB-A ports. The metal contacts (silver lines) must face away from you toward the HDMI side.
4. Hold the cable in place and press the brown locking tab back down firmly until it clicks flat.
5. Connect the other end of the ribbon cable to the camera module the same way: lift tab, insert cable with blue strip toward the lens, press tab down.
6. Reconnect the USB-C power cable. The Pi boots automatically.

Reconnect via SSH after ~30 seconds.

---

### Enable the camera interface

**[PI]**

```bash
sudo raspi-config
```

Navigate with arrow keys:

```
Interface Options → Camera → Yes → Finish → Reboot
```

Reconnect via SSH after the reboot.

---

### Verify the camera

**[PI]**

```bash
# Check hardware detection
vcgencmd get_camera
# Expected: supported=1 detected=1, libcamera interfaces=1

# Run a 5-second live preview (exits cleanly — no display needed over SSH)
libcamera-hello --timeout 5000

# Capture a test image
libcamera-jpeg -o /tmp/test.jpg && echo "Camera OK"

# Verify from Python
python3 -c "
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
print('Camera service OK')
cam.stop()
"
```

**If `vcgencmd get_camera` shows `detected=0`:**
- Power off, open both ribbon cable connectors, reseat the cable, and lock firmly.
- The most common cause is the brown tab not being fully pressed down at one end.

---

## 7. USB-C OTG Gadget Mode — Permanent Mac ↔ Pi Link

> **What this does:** Configures the Pi to appear as a USB Ethernet adapter when plugged into your Mac. After this one-time setup, the USB-C cable both powers the Pi and provides a direct network link — no router, no WiFi, no DHCP server needed.
>
> **Cable:** Must be a data-capable USB-C cable. Power-only cables are physically identical but carry no data. If the Mac interface never appears after completing all steps, swap the cable before troubleshooting anything else.

> **[PI]** All commands in this section run on the Pi via your existing SSH session.

---

### Step 1 — Add the USB OTG overlay to the boot config

```bash
# [PI]
echo "dtoverlay=dwc2" | sudo tee -a /boot/firmware/config.txt
```

Verify it was added:

```bash
# [PI]
tail -5 /boot/firmware/config.txt
# The last line must read exactly: dtoverlay=dwc2
```

> **Do not edit `/boot/firmware/config.txt` by mounting the SD card on your Mac** and opening it in TextEdit or VS Code. Mac text editors can add Windows-style line endings (CRLF) that corrupt the file. Always edit it via SSH on the Pi.

---

### Step 2 — Enable the gadget Ethernet kernel module

`/boot/firmware/cmdline.txt` is a single-line file. If a newline is added to it, the Pi will fail to boot and enter emergency mode. Use the `sed` command below — it appends to the existing line safely.

```bash
# [PI]
# First check what is already in the file
cat /boot/firmware/cmdline.txt
# Expected: one long line ending with "rootwait"

# Append the module load instruction to that same line
sudo sed -i 's/$/ modules-load=dwc2,g_ether/' /boot/firmware/cmdline.txt

# Verify: must still be ONE line, ending with g_ether
cat /boot/firmware/cmdline.txt
# Expected end: ... rootwait modules-load=dwc2,g_ether
```

> If `modules-load=dwc2,g_ether` already appears in the file from a previous attempt, do not run the `sed` command again — it would duplicate the entry.

---

### Step 3 — Assign a static IP to the USB network interface

```bash
# [PI]
sudo tee /etc/network/interfaces.d/usb0 <<EOF
auto usb0
iface usb0 inet static
    address 192.168.7.2
    netmask 255.255.255.0
EOF

# Verify the file
cat /etc/network/interfaces.d/usb0
```

---

### Step 4 — Reboot the Pi with the USB-C cable connected to your Mac

Plug the USB-C data cable into your Mac **before** issuing the reboot command. This ensures the USB gadget device registers on the Mac during the Pi's boot sequence.

```bash
# [PI]
sudo reboot
```

Wait ~45 seconds for the Pi to fully boot.

---

## 8. Configure Mac Networking for USB-C

> **[MAC]** All steps in this section are performed on your Mac.

After the Pi reboots, a new network interface appears on your Mac. You need to assign a static IP to it.

### Assign a static IP on the Mac

1. Open **System Settings** → **Network** (or **System Preferences → Network** on older macOS).
2. In the left sidebar, look for a new interface named one of:
   - `RNDIS/ECM Gadget`
   - `USB 10/100 LAN`
   - `USB Ethernet`
   
   If you do not see it: the cable is power-only, or the Pi did not fully boot, or Steps 1–2 of Section 7 were not applied correctly. See [Section 12](#12-diagnostics-and-troubleshooting).

3. Click on the interface → click **Details...** (macOS Ventura/Sonoma) or the gear icon (older macOS).
4. Go to the **TCP/IP** tab.
5. Change **Configure IPv4** from `Using DHCP` to **Manually**.
6. Set:
   - **IP Address:** `192.168.7.1`
   - **Subnet Mask:** `255.255.255.0`
   - **Router:** *(leave completely blank)*
7. Click **OK**, then **Apply**.

### Verify the Mac interface is configured

**[MAC]**

```bash
ifconfig | grep -A4 "192.168.7"
# Expected output: inet 192.168.7.1 netmask 0xffffff00 broadcast 192.168.7.255
```

---

## 9. Verify the Connection

**[MAC]**

```bash
# Step 1: Can you reach the Pi by IP?
ping 192.168.7.2
# Expected: 64 bytes from 192.168.7.2: icmp_seq=0 ttl=64 time=0.5 ms
# Press Ctrl+C to stop

# Step 2: Can you SSH into the Pi over USB-C?
ssh pi@192.168.7.2
# Enter password → you are now on the Pi
```

**[PI]** — from inside the SSH session, confirm the USB interface is up:

```bash
ip addr show usb0
# Look for: state UP
# Look for: inet 192.168.7.2/24
```

---

### What to do if `ping 192.168.7.2` fails

Work through these checks in order:

| Check | Command | Expected |
|---|---|---|
| Is the Pi visible as a USB device at all? | `[MAC] system_profiler SPUSBDataType \| grep -A8 -i "raspberry\|rndis\|gadget"` | Lines mentioning "RNDIS" or "Linux" or "Gadget" |
| Did a new network interface appear? | `[MAC] networksetup -listallhardwareports` | A line mentioning USB or Gadget |
| Is the Mac IP set correctly? | `[MAC] ifconfig \| grep "192.168.7"` | `inet 192.168.7.1` |
| Is `dtoverlay=dwc2` in the Pi's boot config? | `[PI] grep dwc2 /boot/firmware/config.txt` | `dtoverlay=dwc2` |
| Is the module load in cmdline.txt? | `[PI] grep dwc2 /boot/firmware/cmdline.txt` | `modules-load=dwc2,g_ether` |
| Is the Pi USB interface up? | `[PI] ip addr show usb0` | `state UP` and `inet 192.168.7.2` |

**Most common causes in order:**
1. Power-only USB-C cable — swap the cable first before anything else
2. `dtoverlay=dwc2` not saved correctly in config.txt
3. `modules-load=dwc2,g_ether` not saved correctly in cmdline.txt (or was accidentally duplicated)
4. Mac-side IP is not set to `192.168.7.1` manually (still on DHCP)

**If the Pi boots to emergency/maintenance mode** (`cmdline.txt` got corrupted with a newline):
Reflash the MicroSD card following Section 3 and redo Sections 4–7.

---

## 10. Deploy the RasperifyScanner Backend

> **[PI]** All commands in this section run on the Pi. SSH in via `ssh pi@192.168.7.2`.

### Clone the repository

```bash
# [PI]
cd ~
git clone https://github.com/<your-username>/RasperifyScanner.git
cd RasperifyScanner/backend
```

Replace `<your-username>` with your actual GitHub username.

### Create a Python virtual environment

```bash
# [PI]
python3.11 -m venv .venv
source .venv/bin/activate
```

Your prompt will change to show `(.venv)` — this means the virtual environment is active.

### Install Python dependencies

```bash
# [PI] (virtual environment must be active)
pip install --upgrade pip
pip install -r requirements.txt
```

This may take 5–15 minutes on a Pi. `picamera2` is included; on the Pi it uses the system-installed library.

### Configure environment variables

```bash
# [PI]
cp .env.example .env
nano .env
```

Edit the following values:

| Variable | What to set | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key | https://aistudio.google.com/ → Get API Key |
| `OPENAI_API_KEY` | Your OpenAI API key | Optional — used as fallback if Gemini fails |
| `SECRET_KEY` | A random 32-character hex string | Generate one: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `CAMERA_MOCK` | `false` | Set `true` only when running on Mac in development mode |

Save and exit nano: press `Ctrl+X`, then `Y`, then `Enter`.

### Test-run the backend

```bash
# [PI]
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open a second terminal on your Mac and verify:

```bash
# [MAC]
curl http://192.168.7.2:8000/api/v1/health | python3 -m json.tool
```

Expected response:

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

Interactive API docs are available at: `http://192.168.7.2:8000/docs`

Press `Ctrl+C` in the Pi terminal to stop the test run before continuing to Section 11.

---

## 11. Run as a System Service — Auto-Start on Boot

This configures the backend to start automatically whenever the Pi is powered on — no manual SSH or uvicorn command needed.

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

# Check the service started cleanly
sudo systemctl status rasperify
```

You should see `Active: active (running)`.

**Useful service management commands:**

```bash
# [PI] View live logs (Ctrl+C to stop)
sudo journalctl -u rasperify -f

# [PI] Stop the service
sudo systemctl stop rasperify

# [PI] Restart after pulling a code update
cd ~/RasperifyScanner && git pull
sudo systemctl restart rasperify
```

---

## 12. Diagnostics and Troubleshooting

### USB-C interface not appearing on Mac

```bash
# [MAC] Is the Pi detected as a USB device at all?
system_profiler SPUSBDataType | grep -A8 -i "raspberry\|rndis\|linux\|gadget"

# [MAC] Does a USB Ethernet interface appear in the network list?
networksetup -listallhardwareports
# Look for a Hardware Port line mentioning USB or Gadget

# [MAC] Is the Mac IP set correctly?
ifconfig | grep -A4 "192.168.7"
# Must show: inet 192.168.7.1

# [PI] Are both boot files correct?
grep dwc2 /boot/firmware/config.txt
grep dwc2 /boot/firmware/cmdline.txt
```

---

### Finding Pi's IP without nmap

If `nmap` is not installed and `raspberrypi.local` does not resolve:

```bash
# [MAC] Check the ARP table after the Pi connects to the same network
arp -a
# Raspberry Pi MAC addresses start with: b8:27:eb  or  dc:a6:32  or  e4:5f:01

# [MAC] Check your router admin page
# Usually at http://192.168.1.1 or http://192.168.0.1
# Look for "Connected devices" or "DHCP leases" — find "raspberrypi"

# [MAC] Find your own Mac IP to know the subnet
ipconfig getifaddr en0    # WiFi
ipconfig getifaddr en1    # Ethernet
# Then scan: nmap -sn <your-subnet>.0/24
```

---

### `command not found` errors on Mac

| Command that failed | Why | Fix |
|---|---|---|
| `hostnamectl` | Linux-only command — must run on the Pi | SSH into the Pi first, then run it |
| `raspi-config` | Raspberry Pi OS tool — does not exist on macOS | SSH into the Pi |
| `apt` | Debian/Ubuntu package manager — does not exist on macOS | SSH into the Pi |
| `libcamera-hello` | Raspberry Pi camera tool | SSH into the Pi |
| `vcgencmd` | Raspberry Pi firmware tool | SSH into the Pi |
| `nmap` | Not installed on Mac by default | `brew install nmap` |
| `brew` | Homebrew not installed | See [Section 2](#2-mac-prerequisites) |

---

### Camera not detected

```bash
# [PI]
vcgencmd get_camera
# Must show: supported=1 detected=1

libcamera-hello --timeout 3000
```

**If `detected=0`:**
- Power off the Pi, reseat both ends of the ribbon cable, press locking tabs firmly closed, power on.
- Run `sudo raspi-config` → Interface Options → Camera → Enable → Reboot.
- Check `/boot/firmware/config.txt` contains `camera_auto_detect=1` (the default — do not remove it).

---

### Backend service not starting

```bash
# [PI]
sudo journalctl -u rasperify -n 50 --no-pager
```

| Error message | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'picamera2'` | `sudo apt install python3-picamera2` |
| `Address already in use` — port 8000 | `sudo fuser -k 8000/tcp` then `sudo systemctl restart rasperify` |
| `GEMINI_API_KEY not set` | Edit `~/RasperifyScanner/backend/.env` and add the key |
| `Permission denied: /dev/video0` | `sudo usermod -aG video pi` then log out and back in |

---

### SSH connection refused

```bash
# [PI] Check SSH service (requires keyboard/monitor if you can't SSH at all)
sudo systemctl status ssh

# If inactive:
sudo systemctl enable ssh
sudo systemctl start ssh
```

---

## Quick Reference

### IP addresses

| Connection method | Pi IP | Mac IP | SSH command |
|---|---|---|---|
| USB-C OTG | `192.168.7.2` | `192.168.7.1` | `ssh pi@192.168.7.2` |
| Ethernet (DHCP) | run `ip addr show eth0` on Pi | your Mac's LAN IP | `ssh pi@<eth0-ip>` |
| WiFi (DHCP) | run `hostname -I` on Pi | your Mac's WiFi IP | `ssh pi@raspberrypi.local` |

### Backend URLs

| What | URL |
|---|---|
| Health check | `http://192.168.7.2:8000/api/v1/health` |
| Interactive API docs | `http://192.168.7.2:8000/docs` |
| Full API reference | [API_REFERENCE.md](API_REFERENCE.md) |
