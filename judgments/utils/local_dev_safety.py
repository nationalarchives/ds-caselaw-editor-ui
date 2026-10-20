"""Guards for destructive local-only developer commands."""

# ruff: noqa: TRY003, EM101, EM102, TC002

from __future__ import annotations

from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper

LOCAL_MARKLOGIC_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "marklogic",
    },
)

LOCAL_DATABASE_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",
    },
)

FORBIDDEN_MARKLOGIC_HOST_MARKERS = (
    "amazonaws.com",
    "elb.",
    "nationalarchives.gov.uk",
)


class LocalDevSafetyError(Exception):
    """Raised when a local-only operation would touch a non-local service."""


def host_without_port(host: str | None) -> str:
    if not host:
        return ""
    return host.split(":")[0].strip().lower()


def assert_local_marklogic_host(host: str | None, *, use_https: bool) -> None:
    if use_https:
        raise LocalDevSafetyError(
            "MARKLOGIC_USE_HTTPS is enabled. Refusing to reload fixtures outside plain local MarkLogic.",
        )

    normalized = host_without_port(host)
    if not normalized:
        raise LocalDevSafetyError("MARKLOGIC_HOST is not set.")

    lowered_host = (host or "").lower()
    for marker in FORBIDDEN_MARKLOGIC_HOST_MARKERS:
        if marker in lowered_host:
            raise LocalDevSafetyError(
                f'MARKLOGIC_HOST "{host}" looks like a remote environment. Refusing to reload fixtures.',
            )

    if normalized not in LOCAL_MARKLOGIC_HOSTS:
        raise LocalDevSafetyError(
            f'MARKLOGIC_HOST "{host}" is not an allowed local host ({", ".join(sorted(LOCAL_MARKLOGIC_HOSTS))}). '
            "Refusing to reload fixtures.",
        )


def assert_local_database(database: BaseDatabaseWrapper) -> None:
    if "sqlite" in database.settings_dict["ENGINE"]:
        return

    host = host_without_port(database.settings_dict.get("HOST"))
    if host not in LOCAL_DATABASE_HOSTS:
        raise LocalDevSafetyError(
            f'Database host "{database.settings_dict.get("HOST")}" is not an allowed local host '
            f"({', '.join(sorted(LOCAL_DATABASE_HOSTS))}). Refusing to flush the database.",
        )


def assert_local_marklogic_settings() -> None:
    assert_local_marklogic_host(settings.MARKLOGIC_HOST, use_https=settings.MARKLOGIC_USE_HTTPS)
