"""Document list filters and search parameter helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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

COURTS_BY_PARAM = {
    court.canonical_param: court
    for court in list(all_courts.get_listable_courts()) + list(all_courts.get_listable_tribunals())
    if court.canonical_param
}


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
    def from_query_params(cls, params, *, default_publication_status: str | None = None) -> DocumentListFilters:
        """Parse request GET params into filters.

        When the request has no publication_status, ``default_publication_status``
        is used — home defaults to unpublished, results to all.
        """
        raw_status = params.get("publication_status")
        if raw_status in PUBLICATION_STATUSES:
            publication_status = raw_status
        elif default_publication_status:
            publication_status = default_publication_status
        else:
            publication_status = PUBLICATION_STATUS_ALL

        query = params.get("query") or None
        if query is not None:
            query = query.strip() or None

        order = params.get("order") or None
        if order not in ORDER_VALUES:
            order = DEFAULT_ORDER

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

    def context_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "search_filter": self.search_filter,
            "page": self.page,
            "order": self.order,
            "publication_status": self.publication_status,
            "total_count_postfix": self.total_count_postfix(),
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
