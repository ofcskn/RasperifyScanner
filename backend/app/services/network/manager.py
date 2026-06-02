"""NetworkAdapterManager — Information Expert + Pure Fabrication (GRASP).

Probes all three adapters in priority order and exposes the first active one.
FastAPI binds to 0.0.0.0, so all adapters are served simultaneously — this manager
is used for health reporting and documentation, not for binding.
"""
from app.services.network.base import NetworkAdapter, AdapterInfo
from app.services.network.usb import USBCableAdapter
from app.services.network.wifi import WiFiAdapter
from app.services.network.ethernet import EthernetAdapter


class NetworkAdapterManager:
    def __init__(self) -> None:
        # Priority: USB-C first (direct cable to Mac), then Ethernet, then WiFi
        self._adapters: list[NetworkAdapter] = [
            USBCableAdapter(),
            EthernetAdapter(),
            WiFiAdapter(),
        ]

    def probe_all(self) -> list[AdapterInfo]:
        return [a.probe() for a in self._adapters]

    def active_adapter(self) -> AdapterInfo | None:
        for info in self.probe_all():
            if info.up and info.ip:
                return info
        return None


network_manager = NetworkAdapterManager()
