"""EthernetAdapter — eth0 interface."""
from app.services.network.base import NetworkAdapter, AdapterInfo
from app.services.network.usb import _probe_interface


class EthernetAdapter(NetworkAdapter):
    @property
    def name(self) -> str:
        return "ethernet"

    @property
    def interface(self) -> str:
        return "eth0"

    def probe(self) -> AdapterInfo:
        return _probe_interface(self.name, self.interface)
