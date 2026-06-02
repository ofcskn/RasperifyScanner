"""NetworkAdapter — Abstract base (Protected Variations + Polymorphism, GRASP)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AdapterInfo:
    name: str
    interface: str
    up: bool
    ip: str | None


class NetworkAdapter(ABC):
    """Protected Variations: shields the rest of the system from adapter-specific details."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def interface(self) -> str: ...

    @abstractmethod
    def probe(self) -> AdapterInfo: ...
