from dataclasses import dataclass, replace
from datetime import date
from urllib.parse import urlencode

from caselawclient.client_helpers.search_helpers import search_and_parse_response
from caselawclient.models.documents.metadata.base import MultipleMetadata
from django.urls import reverse

from judgments.utils import api_client
from judgments.utils.document_list import DocumentListFilters
from judgments.utils.view_helpers import (
    _search_parameters_from_filters,
    get_search_results_from_filters,
)

SINGLE_VALUE_CHANGE = "The source value becomes current. The target value stays in the document history."
MULTIPLE_VALUE_CHANGE = "Both sets are kept. Values only on the source are added."
IDENTIFIER_REPLACEMENT = "The target identifier will be deprecated and the source identifier becomes current."
IDENTIFIER_ADDITION = "The source identifier will be added."
IDENTIFIER_ADDITIONS = "Identifiers only on the source are added. The target keeps its own."
PROPERTY_REPLACEMENT = "The source value replaces the target's."


def merge_review_url(source_uri: str, target_uri: str) -> str:
    path = reverse("merge-document-review", kwargs={"document_uri": source_uri})
    return f"{path}?{urlencode({'target': target_uri})}"


def merge_annotation_message(note: str, source_uri: str) -> str:
    cleaned_note = note.strip()
    if cleaned_note:
        return cleaned_note
    return f"Merged from {source_uri}"


INGEST_PROPERTIES = (
    ("Submitter organisation", "source-organisation", None),
    ("Submitter name", "source-name", "source_name"),
    ("Submitter email", "source-email", "source_email"),
    ("TDR reference", "transfer-consignment-reference", "consignment_reference"),
    ("TDR received", "transfer-received-at", None),
)


@dataclass(frozen=True)
class MergeComparisonRow:
    label: str
    target_values: list[str]
    source_values: list[str]
    changed: bool
    detail: str


@dataclass(frozen=True)
class MergeComparisonSection:
    title: str
    rows: list[MergeComparisonRow]


def format_metadata_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%-d %b %Y")

    name = getattr(value, "name", None)
    if isinstance(name, str):
        parent = getattr(value, "parent", None)
        if parent:
            return f"{name} ({parent})"
        return name

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _display_values(metadata_item) -> list[str]:
    if metadata_item is None:
        return []

    if isinstance(metadata_item, MultipleMetadata):
        raw_values = metadata_item.values
    else:
        raw_value = metadata_item.value
        raw_values = [] if raw_value in (None, "") else [raw_value]

    displayed = []
    for raw_value in raw_values:
        text = format_metadata_value(raw_value)
        if text:
            displayed.append(text)
    return displayed


def _metadata_row(target_item, source_item) -> MergeComparisonRow:
    item = target_item or source_item
    target_values = _display_values(target_item)
    source_values = _display_values(source_item)
    if isinstance(item, MultipleMetadata):
        changed = bool(set(source_values) - set(target_values))
        detail = MULTIPLE_VALUE_CHANGE if changed else ""
    else:
        changed = target_values != source_values
        detail = SINGLE_VALUE_CHANGE if changed else ""

    return MergeComparisonRow(
        label=item.title,
        target_values=target_values,
        source_values=source_values,
        changed=changed,
        detail=detail,
    )


def _metadata_rows(target, source) -> list[MergeComparisonRow]:
    source_items = {item.key: item for item in source.metadata}
    seen = {item.key for item in target.metadata}
    paired = [_metadata_row(item, source_items.get(item.key)) for item in target.metadata]
    extras = [_metadata_row(None, item) for item in source.metadata if item.key not in seen]
    return paired + extras


def _current_identifiers(document) -> dict[str, dict]:
    grouped: dict[str, dict] = {}
    for identifier in document.identifiers.values():
        if identifier.deprecated:
            continue
        group = grouped.setdefault(
            identifier.schema.name,
            {"allow_multiple": identifier.schema.allow_multiple, "values": []},
        )
        group["allow_multiple"] = identifier.schema.allow_multiple
        group["values"].append(str(identifier.value))
    return grouped


def _identifier_rows(target, source) -> list[MergeComparisonRow]:
    target_groups = _current_identifiers(target)
    source_groups = _current_identifiers(source)
    schema_names = sorted(set(target_groups) | set(source_groups))
    if not schema_names:
        return [
            MergeComparisonRow(
                label="Identifiers",
                target_values=[],
                source_values=[],
                changed=False,
                detail="",
            ),
        ]

    rows = []
    for schema_name in schema_names:
        target_group = target_groups.get(schema_name, {"allow_multiple": False, "values": []})
        source_group = source_groups.get(schema_name, {"allow_multiple": False, "values": []})
        target_values = target_group["values"]
        source_values = source_group["values"]
        allow_multiple = target_group["allow_multiple"] or source_group["allow_multiple"]
        incoming = set(source_values) - set(target_values)

        if allow_multiple:
            changed = bool(incoming)
            detail = IDENTIFIER_ADDITIONS if changed else ""
        elif incoming and target_values:
            changed = True
            detail = IDENTIFIER_REPLACEMENT
        elif incoming:
            changed = True
            detail = IDENTIFIER_ADDITION
        else:
            changed = False
            detail = ""

        rows.append(
            MergeComparisonRow(
                label=schema_name,
                target_values=target_values,
                source_values=source_values,
                changed=changed,
                detail=detail,
            ),
        )
    return rows


def _ingest_property(document, attribute: str | None, property_name: str) -> str:
    if attribute:
        value = getattr(document, attribute, "") or ""
    else:
        value = document.api_client.get_property(document.uri, property_name) or ""
    return str(value).strip()


def _property_rows(target, source) -> list[MergeComparisonRow]:
    rows = []
    for label, property_name, attribute in INGEST_PROPERTIES:
        target_value = _ingest_property(target, attribute, property_name)
        source_value = _ingest_property(source, attribute, property_name)
        changed = bool(source_value) and source_value != target_value
        rows.append(
            MergeComparisonRow(
                label=label,
                target_values=[target_value] if target_value else [],
                source_values=[source_value] if source_value else [],
                changed=changed,
                detail=PROPERTY_REPLACEMENT if changed else "",
            ),
        )
    return rows


def build_merge_comparison(target, source) -> list[MergeComparisonSection]:
    return [
        MergeComparisonSection(title="Case metadata", rows=_metadata_rows(target, source)),
        MergeComparisonSection(title="Identifiers", rows=_identifier_rows(target, source)),
        MergeComparisonSection(title="Submitter and TDR", rows=_property_rows(target, source)),
    ]


def is_source_in_search_results(source_uri: str, filters: DocumentListFilters) -> bool:
    neutral_citation = filters.search_filter == "ncn"
    base_params = _search_parameters_from_filters(filters, neutral_citation=neutral_citation)
    probe_params = replace(
        base_params,
        specific_keyword=str(source_uri),
        page=1,
        page_size=1,
    )
    response = search_and_parse_response(api_client, probe_params)
    return any(str(result.uri) == str(source_uri) for result in response.results)


def merge_target_search_results(
    filters: DocumentListFilters,
    source_uri: str,
) -> tuple[dict, list, int]:
    """Search for merge targets, excluding the source document from the list.

    Editors pick another document to merge into; the source cannot be its own
    target. MarkLogic returns paginated search results and a total count. We
    remove the source from the current page when it appears there, and reduce
    the reported total by one when the source is part of the overall result set
    (including when it would only appear on another page).
    """
    search_context = get_search_results_from_filters(filters)
    visible_documents = [result for result in search_context["documents"] if str(result.uri) != str(source_uri)]
    source_on_page = len(visible_documents) != len(search_context["documents"])
    source_in_results = source_on_page or is_source_in_search_results(source_uri, filters)
    adjusted_total = max(search_context["total"] - (1 if source_in_results else 0), 0)
    return search_context, visible_documents, adjusted_total
