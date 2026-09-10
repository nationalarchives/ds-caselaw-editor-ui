"""Document list filters and search parameter helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from ds_caselaw_utils import courts as all_courts

ORDER_VALUES = frozenset(
    {
        "relevance",
        "-date",
        "date",
        "-transformation",
        "transformation",
        "-updated",
        "updated",
    },
)

PUBLICATION_STATUS_UNPUBLISHED = "unpublished"
PUBLICATION_STATUS_PUBLISHED = "published"
PUBLICATION_STATUS_ALL = "all"
PUBLICATION_STATUSES = frozenset(
    {
        PUBLICATION_STATUS_ALL,
        PUBLICATION_STATUS_UNPUBLISHED,
        PUBLICATION_STATUS_PUBLISHED,
    },
)

DEFAULT_ORDER = "-date"

PRESET_UNPUBLISHED = "unpublished"
PRESET_PUBLISHED = "published"
PRESET_ALL = "all"

COURTS_BY_PARAM = {
    court.canonical_param: court
    for court in list(all_courts.get_listable_courts()) + list(all_courts.get_listable_tribunals())
    if court.canonical_param
}


@dataclass(frozen=True)
class SystemPreset:
    """Named system view: a stable id over publication status + order defaults."""

    id: str
    label: str
    publication_status: str
    order: str = DEFAULT_ORDER

    def as_query_params(self) -> dict[str, str]:
        return {
            "publication_status": self.publication_status,
            "order": self.order,
        }

    def query_string(self) -> str:
        return urlencode(self.as_query_params())


SYSTEM_PRESETS: tuple[SystemPreset, ...] = (
    SystemPreset(
        id=PRESET_UNPUBLISHED,
        label="Unpublished documents",
        publication_status=PUBLICATION_STATUS_UNPUBLISHED,
    ),
    SystemPreset(
        id=PRESET_PUBLISHED,
        label="Published documents",
        publication_status=PUBLICATION_STATUS_PUBLISHED,
    ),
    SystemPreset(
        id=PRESET_ALL,
        label="All documents",
        publication_status=PUBLICATION_STATUS_ALL,
    ),
)

SYSTEM_PRESETS_BY_ID = {preset.id: preset for preset in SYSTEM_PRESETS}


def get_system_preset(preset_id: str) -> SystemPreset:
    try:
        return SYSTEM_PRESETS_BY_ID[preset_id]
    except KeyError as exc:
        msg = f"Unknown system preset: {preset_id}"
        raise KeyError(msg) from exc


@dataclass
class DocumentListFilters:
    query: str | None = None
    search_filter: str | None = None
    page: int = 1
    order: str = DEFAULT_ORDER
    publication_status: str = PUBLICATION_STATUS_UNPUBLISHED
    courts: list[str] = field(default_factory=list)
    from_year: int | None = None
    to_year: int | None = None

    @classmethod
    def from_query_params(
        cls,
        params,
        *,
        default_preset: SystemPreset | None = None,
    ) -> DocumentListFilters:
        """Parse request GET params into filters.

        When the request has no publication_status (or an invalid one), defaults
        come from ``default_preset``, falling back to the unpublished preset.
        Missing/invalid order falls back to that preset's order.
        """
        if default_preset is None:
            default_preset = get_system_preset(PRESET_UNPUBLISHED)

        raw_status = params.get("publication_status")
        publication_status = raw_status if raw_status in PUBLICATION_STATUSES else default_preset.publication_status

        query = params.get("query") or None
        if query is not None:
            query = query.strip() or None

        order = params.get("order") or None
        if order not in ORDER_VALUES:
            order = default_preset.order

        courts = params.getlist("court") if hasattr(params, "getlist") else []
        courts = [c for c in courts if c in COURTS_BY_PARAM]

        from_year = _parse_year(params.get("from_year"))
        to_year = _parse_year(params.get("to_year"))
        if from_year is not None and to_year is not None and from_year > to_year:
            from_year, to_year = to_year, from_year

        try:
            page = max(1, int(params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1

        return cls(
            query=query,
            search_filter=params.get("search_filter") or None,
            page=page,
            order=order,
            publication_status=publication_status,
            courts=courts,
            from_year=from_year,
            to_year=to_year,
        )

    @property
    def only_unpublished(self) -> bool:
        return self.publication_status == PUBLICATION_STATUS_UNPUBLISHED

    @property
    def show_unpublished(self) -> bool:
        # Published-only currently requires show_unpublished=False — the only
        # available lever without an only_published API flag.
        return self.publication_status != PUBLICATION_STATUS_PUBLISHED

    @property
    def date_from(self) -> str | None:
        if self.from_year is None:
            return None
        return f"{self.from_year:04d}-01-01"

    @property
    def date_to(self) -> str | None:
        if self.to_year is None:
            return None
        return f"{self.to_year:04d}-12-31"

    @property
    def court_param(self) -> str | None:
        if not self.courts:
            return None
        return ",".join(self.courts)

    def total_count_postfix(self) -> str:
        if self.publication_status == PUBLICATION_STATUS_UNPUBLISHED:
            return "unpublished documents"
        if self.publication_status == PUBLICATION_STATUS_PUBLISHED:
            return "published documents"
        return "documents"

    def matching_preset(self) -> SystemPreset | None:
        """Return the system preset that exactly matches the current filters.

        A preset is only active when publication status and order match and there
        are no search/court/year refinements (page alone does not clear it).
        """
        for preset in SYSTEM_PRESETS:
            if (
                self.publication_status == preset.publication_status
                and self.order == preset.order
                and not self.query
                and not self.courts
                and self.from_year is None
                and self.to_year is None
            ):
                return preset
        return None

    def context_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "search_filter": self.search_filter,
            "page": self.page,
            "order": self.order,
            "publication_status": self.publication_status,
            "total_count_postfix": self.total_count_postfix(),
            "active_preset": self.matching_preset(),
        }


def _parse_year(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    if year < 1000 or year > 9999:
        return None
    return year
