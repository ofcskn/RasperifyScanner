"""USBCableAdapter — Pi 4B connected to Mac via USB-C in OTG gadget mode (usb0 interface)."""
import socket
import subprocess

from app.services.network.base import NetworkAdapter, AdapterInfo


class USBCableAdapter(NetworkAdapter):
    @property
    def name(self) -> str:
        return "usb"

    @property
    def interface(self) -> str:
        return "usb0"

    def probe(self) -> AdapterInfo:
        return _probe_interface(self.name, self.interface)


def _probe_interface(name: str, iface: str) -> AdapterInfo:
    try:
        result = subprocess.run(
            ["ip", "addr", "show", iface],
            capture_output=True, text=True, timeout=2,
        )
        up = "UP" in result.stdout and "state UP" in result.stdout
        ip: str | None = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet ") and "scope global" in line:
                ip = line.split()[1].split("/")[0]
                break
        return AdapterInfo(name=name, interface=iface, up=up, ip=ip)
    except Exception:
        return AdapterInfo(name=name, interface=iface, up=False, ip=None)
