from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

from caselawclient.errors import MarklogicAPIError, MarklogicCheckoutConflictError
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.exceptions import DocumentMergeNotPossibleError
from caselawclient.models.documents.metadata.base import MultipleMetadata
from django.contrib import messages
from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from waffle import flag_is_active

from judgments.templatetags.navigation_tags import DOCUMENT_MERGE_FLAG
from judgments.utils.aws import invalidate_caches
from judgments.utils.document_list import SAVED_VIEW_ALL, InvalidDocumentListFilterError, get_saved_view_preset
from judgments.utils.permissions import editor_required
from judgments.utils.view_helpers import (
    DocumentView,
    get_document_by_uri_or_404,
    get_document_list_filters,
    get_search_results_from_filters,
)
from judgments.views.paginated_view import PaginatedView

SINGLE_VALUE_CHANGE = "The source value becomes current. The target value stays in the document history."
MULTIPLE_VALUE_CHANGE = "Both sets are kept. Values only on the source are added."
IDENTIFIER_REPLACEMENT = "The target identifier will be deprecated and the source identifier becomes current."
IDENTIFIER_ADDITION = "The source identifier will be added."
IDENTIFIER_ADDITIONS = "Identifiers only on the source are added. The target keeps its own."
PROPERTY_REPLACEMENT = "The source value replaces the target's."

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


def merge_review_url(source_uri: str, target_uri: str) -> str:
    path = reverse("merge-document-review", kwargs={"document_uri": source_uri})
    return f"{path}?{urlencode({'target': target_uri})}"


def merge_annotation_message(note: str, source_uri: str) -> str:
    cleaned_note = note.strip()
    if cleaned_note:
        return cleaned_note
    return f"Merged from {source_uri}"


def _require_merge_flag(request):
    if not flag_is_active(request, DOCUMENT_MERGE_FLAG):
        raise Http404


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
        changed = set(target_values) != set(source_values)
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
            changed = set(target_values) != set(source_values)
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


class MergeDocumentSearchView(DocumentView, PaginatedView):
    template_engine = "jinja"
    template_name = "judgment/merge.jinja"

    def setup(self, request, *args, **kwargs):
        _require_merge_flag(request)
        super().setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "merge_document"

        try:
            filters = get_document_list_filters(
                self.request.GET,
                base_saved_view=get_saved_view_preset(SAVED_VIEW_ALL),
            )
        except InvalidDocumentListFilterError as exc:
            raise BadRequest(str(exc)) from exc

        search_context = get_search_results_from_filters(filters)
        context.update(search_context)
        context["pagination_data"] = self.get_pagination_context(
            request=self.request,
            paginator=search_context["paginator"],
        )
        visible_documents = [
            result for result in search_context["documents"] if str(result.uri) != str(self.document.uri)
        ]
        hidden_on_this_page = len(search_context["documents"]) - len(visible_documents)
        context["total"] = max(search_context["total"] - hidden_on_this_page, 0)
        context["merge_results"] = [
            {
                "document": result,
                "select_url": merge_review_url(self.document.uri, result.uri),
            }
            for result in visible_documents
        ]
        return context


class MergeDocumentReviewView(DocumentView):
    template_engine = "jinja"
    template_name = "judgment/merge_review.jinja"

    def setup(self, request, *args, **kwargs):
        _require_merge_flag(request)
        super().setup(request, *args, **kwargs)
        target_uri = request.GET.get("target")
        if not target_uri:
            raise Http404
        self.target = get_document_by_uri_or_404(target_uri)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "merge_document"
        context["target"] = self.target
        context["target_title"] = self.target.metadata.title.value or "Untitled document"
        context["comparison_sections"] = build_merge_comparison(self.target, self.document)

        validation = self.document.merge.check_can_merge_into(self.target)
        context["can_merge"] = bool(validation.success)
        context["merge_failure_messages"] = [] if validation.success else list(validation.messages)
        return context


def merge(request):
    _require_merge_flag(request)
    return _merge_documents(request)


@editor_required
def _merge_documents(request):
    source_uri = request.POST.get("source_uri") or ""
    target_uri = request.POST.get("target_uri") or ""
    source = get_document_by_uri_or_404(source_uri)
    target = get_document_by_uri_or_404(target_uri)
    message = merge_annotation_message(request.POST.get("note") or "", source.uri)
    review_url = merge_review_url(source.uri, target.uri)

    try:
        # merge_into checks out both documents itself. Opening a session here would
        # merge the copy loaded before that checkout.
        source.merge_into(DocumentURIString(target.uri), message)
    except DocumentMergeNotPossibleError as exc:
        for message_text in exc.messages:
            messages.error(request, message_text)
        return HttpResponseRedirect(review_url)
    except MarklogicCheckoutConflictError:
        messages.error(request, "These documents cannot be merged while one of them is locked.")
        return HttpResponseRedirect(review_url)
    except MarklogicAPIError as exc:
        messages.error(request, f"There was an error merging the documents: {exc}")
        return HttpResponseRedirect(review_url)

    invalidate_caches(source.uri)
    invalidate_caches(target.uri)
    messages.success(request, f"{source.uri} was merged into {target.uri}.")
    return HttpResponseRedirect(reverse("full-text-html", kwargs={"document_uri": target.uri}))
