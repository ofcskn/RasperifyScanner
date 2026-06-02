# RasperifyScanner — Setup Guide

## 1. Raspberry Pi 4 Model B — Initial Configuration

### Enable Camera (CSI)
```bash
sudo raspi-config
# Interface Options → Camera → Enable → Reboot
sudo reboot
```

### Install system dependencies
```bash
sudo apt update && sudo apt install -y \
  python3.11 python3.11-venv python3.11-dev \
  python3-picamera2 libcamera-apps
```

### Verify camera
```bash
# Test live preview for 5 seconds
libcamera-hello --timeout 5000

# Test still capture
libcamera-jpeg -o /tmp/test.jpg && echo "Camera OK"

# Test from Python (should print picamera2 version)
python3 -c "from picamera2 import Picamera2; cam = Picamera2(); cam.start(); print('Camera service OK'); cam.stop()"
```

If `libcamera-hello` fails, check:
- Ribbon cable is seated firmly in both the Pi CSI port and the camera module
- `dtoverlay=dwc2` is not accidentally replacing the camera overlay in `/boot/firmware/config.txt`
- Run `vcgencmd get_camera` — should show `supported=1 detected=1`

---

## 2. USB-C OTG Gadget Mode (Pi connected to Mac via USB-C)

This lets the Pi appear as a USB Ethernet device on the Mac.

### On the Pi

Edit `/boot/firmware/config.txt` and add at the end:
```
dtoverlay=dwc2
```

Edit `/boot/firmware/cmdline.txt` — add after `rootwait`:
```
modules-load=dwc2,g_ether
```

Assign a static IP to `usb0` — create `/etc/network/interfaces.d/usb0`:
```
auto usb0
iface usb0 inet static
    address 192.168.7.2
    netmask 255.255.255.0
```

Reboot the Pi, then plug the USB-C cable into the Mac.

### On the Mac

1. System Settings → Network
2. Find the new `RNDIS/ECM Gadget` or `USB 10/100 LAN` interface
3. Set to Manual: IP `192.168.7.1`, Subnet `255.255.255.0`
4. Test: `ping 192.168.7.2`

---

## 3. WiFi Adapter

The Pi connects to your LAN via `wlan0`. Find its IP with `hostname -I`.

---

## 4. Ethernet Adapter

Plug an Ethernet cable. The Pi gets a DHCP address on `eth0`. Find it with `hostname -I`.

---

## 5. Backend Deployment on Pi

```bash
git clone <repo> ~/RasperifyScanner
cd ~/RasperifyScanner/backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set GEMINI_API_KEY, OPENAI_API_KEY, SECRET_KEY
uvicorn main:app --host 0.0.0.0 --port 8000
```

Access at:
- USB-C: `http://192.168.7.2:8000/docs`
- WiFi/Ethernet: `http://<pi-ip>:8000/docs`
