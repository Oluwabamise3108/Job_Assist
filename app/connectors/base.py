from abc import ABC, abstractmethod

from app.sources.base import DiscoveredJob


class JobSourceConnector(ABC):
    """
    Base interface for external source connectors.

    Connectors are provider-integration components.

    They produce the same canonical DiscoveredJob objects
    consumed by the source/discovery layer.
    """

    source_name: str = "unknown"

    @abstractmethod
    def search(
        self,
        *,
        request,
    ) -> list[DiscoveredJob]:
        """
        Search the external provider using a JobSearchRequest-like
        request object.
        """
        raise NotImplementedError


__all__ = [
    "JobSourceConnector",
]