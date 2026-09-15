"""Document list filters, presets, and court facet helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from ds_caselaw_utils import courts as all_courts

ORDER_CHOICES: list[tuple[str, str]] = [
    ("relevance", "Most relevant"),
    ("-date", "Newest"),
    ("date", "Oldest"),
    ("-transformation", "Recently modified"),
    ("transformation", "Least recently modified"),
    ("-updated", "Recently updated"),
    ("updated", "Least recently updated"),
]
ORDER_VALUES = {value for value, _label in ORDER_CHOICES}

PUBLICATION_STATUS_UNPUBLISHED = "unpublished"
PUBLICATION_STATUS_PUBLISHED = "published"
PUBLICATION_STATUS_ALL = "all"
PUBLICATION_STATUS_CHOICES: list[tuple[str, str]] = [
    (PUBLICATION_STATUS_ALL, "All"),
    (PUBLICATION_STATUS_UNPUBLISHED, "Unpublished"),
    (PUBLICATION_STATUS_PUBLISHED, "Published"),
]
PUBLICATION_STATUSES = frozenset(
    {
        PUBLICATION_STATUS_ALL,
        PUBLICATION_STATUS_UNPUBLISHED,
        PUBLICATION_STATUS_PUBLISHED,
    },
)

DEFAULT_ORDER = "-date"

SAVED_VIEW_UNPUBLISHED = "unpublished"
SAVED_VIEW_PUBLISHED = "published"
SAVED_VIEW_ALL = "all"


class InvalidDocumentListFilterError(ValueError):
    """Raised when a filter query param is present but not an allowed value."""


@dataclass(frozen=True)
class SavedViewPreset:
    """Named saved view: a stable id over publication status + order defaults."""

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


SAVED_VIEW_PRESETS: tuple[SavedViewPreset, ...] = (
    SavedViewPreset(
        id=SAVED_VIEW_UNPUBLISHED,
        label="Unpublished documents",
        publication_status=PUBLICATION_STATUS_UNPUBLISHED,
    ),
    SavedViewPreset(
        id=SAVED_VIEW_PUBLISHED,
        label="Published documents",
        publication_status=PUBLICATION_STATUS_PUBLISHED,
    ),
    SavedViewPreset(
        id=SAVED_VIEW_ALL,
        label="All documents",
        publication_status=PUBLICATION_STATUS_ALL,
    ),
)

SAVED_VIEW_PRESETS_BY_ID = {preset.id: preset for preset in SAVED_VIEW_PRESETS}


def get_saved_view_preset(preset_id: str) -> SavedViewPreset:
    try:
        return SAVED_VIEW_PRESETS_BY_ID[preset_id]
    except KeyError as exc:
        msg = f"Unknown saved view preset: {preset_id}"
        raise KeyError(msg) from exc


def _listable_courts() -> list[Any]:
    return [
        court
        for court in list(all_courts.get_listable_courts()) + list(all_courts.get_listable_tribunals())
        if court.canonical_param
    ]


ALL_COURT_CODES = {str(court.code) for court in all_courts.get_all()}
COURTS_BY_CODE = {str(court.code): court for court in all_courts.get_all()}
COURTS_BY_PARAM = {court.canonical_param: court for court in _listable_courts()}


@dataclass
class CourtFilterOption:
    value: str
    label: str
    count: str | None = None
    checked: bool = False


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
        base_saved_view: SavedViewPreset,
    ) -> DocumentListFilters:
        """Parse request GET params into filters stacked on ``base_saved_view``.

        When publication_status or order are omitted, they come from the base
        saved view. If either param is present but not an allowed value, raise
        ``InvalidDocumentListFilterError``.
        """
        raw_status = params.get("publication_status")
        if raw_status in (None, ""):
            publication_status = base_saved_view.publication_status
        elif raw_status in PUBLICATION_STATUSES:
            publication_status = raw_status
        else:
            msg = f"Invalid publication_status: {raw_status}"
            raise InvalidDocumentListFilterError(msg)

        query = params.get("query") or None
        if query is not None:
            query = query.strip() or None

        raw_order = params.get("order")
        if raw_order in (None, ""):
            order = base_saved_view.order
        elif raw_order in ORDER_VALUES:
            order = raw_order
        else:
            msg = f"Invalid order: {raw_order}"
            raise InvalidDocumentListFilterError(msg)

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

    @property
    def uses_court_facets(self) -> bool:
        return bool(self.query)

    def total_count_postfix(self) -> str:
        if self.publication_status == PUBLICATION_STATUS_UNPUBLISHED:
            return "unpublished documents"
        if self.publication_status == PUBLICATION_STATUS_PUBLISHED:
            return "published documents"
        return "documents"

    def matching_saved_view(self) -> SavedViewPreset | None:
        """Return the saved view preset that exactly matches the current filters.

        A saved view is only active when publication status and order match and there
        are no search/court/year refinements (page alone does not clear it).
        """
        for preset in SAVED_VIEW_PRESETS:
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

    def clear_filters_query_string(self) -> str:
        """Drop court/year refinements; keep publication status, order, and search."""
        params: list[tuple[str, str]] = [
            ("publication_status", self.publication_status),
            ("order", self.order),
        ]
        if self.query:
            params.append(("query", self.query))
        if self.search_filter:
            params.append(("search_filter", self.search_filter))
        return urlencode(params)

    def clear_search_query_string(self) -> str:
        """Drop query/search_filter/page; keep sidebar filter parameters."""
        params: list[tuple[str, str]] = [
            ("publication_status", self.publication_status),
            ("order", self.order),
        ]
        params.extend(("court", court) for court in self.courts)
        if self.from_year is not None:
            params.append(("from_year", str(self.from_year)))
        if self.to_year is not None:
            params.append(("to_year", str(self.to_year)))
        return urlencode(params)

    def as_hidden_fields(self) -> list[tuple[str, str]]:
        """Fields to preserve when submitting the other form (search vs filters)."""
        fields: list[tuple[str, str]] = [
            ("publication_status", self.publication_status),
            ("order", self.order),
        ]
        fields.extend(("court", court) for court in self.courts)
        if self.from_year is not None:
            fields.append(("from_year", str(self.from_year)))
        if self.to_year is not None:
            fields.append(("to_year", str(self.to_year)))
        if self.query:
            fields.append(("query", self.query))
        if self.search_filter:
            fields.append(("search_filter", self.search_filter))
        return fields

    def context_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "search_filter": self.search_filter,
            "page": self.page,
            "order": self.order,
            "publication_status": self.publication_status,
            "selected_courts": self.courts,
            "from_year": self.from_year,
            "to_year": self.to_year,
            "order_choices": ORDER_CHOICES,
            "publication_status_choices": PUBLICATION_STATUS_CHOICES,
            "saved_view_presets": SAVED_VIEW_PRESETS,
            "active_saved_view": self.matching_saved_view(),
            "uses_court_facets": self.uses_court_facets,
            "total_count_postfix": self.total_count_postfix(),
            "clear_filters_query_string": self.clear_filters_query_string(),
            "clear_search_query_string": self.clear_search_query_string(),
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


def _sort_options_by_count(options: list[CourtFilterOption]) -> list[CourtFilterOption]:
    return sorted(
        options,
        key=lambda option: int(option.count) if option.count and option.count.isdigit() else -1,
        reverse=True,
    )


def catalogue_court_options(selected: list[str]) -> list[CourtFilterOption]:
    selected_set = set(selected)
    return [
        CourtFilterOption(
            value=court.canonical_param,
            label=court.name,
            checked=court.canonical_param in selected_set,
        )
        for court in _listable_courts()
    ]


def process_court_facets(
    facets: dict[str, str],
    selected: list[str],
) -> list[CourtFilterOption]:
    """Split flattened SearchResponse.facets into court options with counts."""
    selected_set = set(selected)
    options: list[CourtFilterOption] = []
    seen_params: set[str] = set()

    for facet_key, count in facets.items():
        if facet_key not in ALL_COURT_CODES:
            continue
        court = COURTS_BY_CODE.get(facet_key)
        if court is None or not court.canonical_param:
            continue
        if court.canonical_param not in COURTS_BY_PARAM:
            continue
        seen_params.add(court.canonical_param)
        options.append(
            CourtFilterOption(
                value=court.canonical_param,
                label=court.name,
                count=count,
                checked=court.canonical_param in selected_set,
            ),
        )

    options = _sort_options_by_count(options)

    # Keep currently selected courts visible even if missing from top facets.
    for param in selected:
        if param in seen_params:
            continue
        court = COURTS_BY_PARAM.get(param)
        if court is None:
            continue
        options.insert(
            0,
            CourtFilterOption(
                value=court.canonical_param,
                label=court.name,
                count=None,
                checked=True,
            ),
        )

    return options


def court_filter_options(
    filters: DocumentListFilters,
    facets: dict[str, str] | None,
) -> list[CourtFilterOption]:
    if filters.uses_court_facets and facets is not None:
        return process_court_facets(facets, filters.courts)
    return catalogue_court_options(filters.courts)
