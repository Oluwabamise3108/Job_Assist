from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DiscoveredJob:
    """
    Canonical normalized job representation returned by
    every discovery source.
    """

    source: str
    source_job_id: Optional[str]

    title: str
    company: str

    location: Optional[str]

    url: str
    description: str

    is_remote: bool


class JobSource(ABC):
    """
    Canonical interface for discovery sources.

    Every source adapter must:

        1. expose a stable `name`
        2. implement `search()`
        3. return list[DiscoveredJob]

    The discovery engine depends on this contract rather than
    knowing anything about individual providers.
    """

    name: str

    @abstractmethod
    def search(
        self,
        *,
        keywords: list[str],
        remote_only: bool = True,
    ) -> list[DiscoveredJob]:
        """
        Search the source and return normalized jobs.
        """
        raise NotImplementedError


__all__ = [
    "DiscoveredJob",
    "JobSource",
]