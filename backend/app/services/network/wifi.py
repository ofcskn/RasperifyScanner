"""WiFiAdapter — wlan0 interface."""
from app.services.network.base import NetworkAdapter, AdapterInfo
from app.services.network.usb import _probe_interface


class WiFiAdapter(NetworkAdapter):
    @property
    def name(self) -> str:
        return "wifi"

    @property
    def interface(self) -> str:
        return "wlan0"

    def probe(self) -> AdapterInfo:
        return _probe_interface(self.name, self.interface)
