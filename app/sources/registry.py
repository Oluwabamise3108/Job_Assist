"""Central registry for configured job sources."""

from typing import Any

from app.sources.linkedin import LinkedInSource
from app.sources.remoteok import RemoteOKSource
from app.sources.weworkremotely import (
    WeWorkRemotelySource,
)


SOURCE_FACTORIES = {
    "linkedin": LinkedInSource,
    "remoteok": RemoteOKSource,
    "weworkremotely": WeWorkRemotelySource,
}


def create_source(
    name: str,
) -> Any:

    normalized_name = (
        str(name)
        .strip()
        .lower()
    )

    factory = SOURCE_FACTORIES.get(
        normalized_name
    )

    if factory is None:
        raise ValueError(
            f"Unknown job source: {name}"
        )

    return factory()


def create_sources(
    enabled_sources: list[str] | None = None,
) -> list[Any]:

    names = (
        list(SOURCE_FACTORIES.keys())
        if enabled_sources is None
        else enabled_sources
    )

    return [
        create_source(name)
        for name in names
    ]


def registered_sources() -> list[str]:

    return list(
        SOURCE_FACTORIES.keys()
    )


__all__ = [
    "SOURCE_FACTORIES",
    "create_source",
    "create_sources",
    "registered_sources",
]