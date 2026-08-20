from typing import TYPE_CHECKING, Any, cast

import ds_caselaw_utils as caselawutils
from caselawclient.client_helpers.search_helpers import search_and_parse_response
from caselawclient.errors import DocumentNotFoundError
from caselawclient.models.documents import Document, DocumentURIString
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from caselawclient.search_parameters import SearchParameters
from django.http import Http404
from django.views.generic import TemplateView

from judgments.templatetags.document_utils import display_datetime
from judgments.utils import api_client, editors_dict, extract_version_number_from_filename, get_linked_document_uri
from judgments.utils.document_list import DocumentListFilters, court_filter_options
from judgments.utils.link_generators import build_jira_create_link
from judgments.utils.paginator import paginator

if TYPE_CHECKING:
    from caselawclient.models.documents.metadata.types.name import NameMetadata


def user_is_superuser(user):
    """
    return: True if the User is a superuser
    """
    return user.is_superuser if user else None


def user_is_editor(user):
    """
    return: True if the User is part of the "Editors" group
    """
    return user.groups.filter(name="Editors").exists() if user else None


def user_is_developer(user):
    """
    return: True if the User is part of the "Developers" group
    """
    return user.groups.filter(name="Developers").exists() if user else None


def get_document_list_filters(params, *, default_publication_status: str | None = None) -> DocumentListFilters:
    return DocumentListFilters.from_query_params(
        params,
        default_publication_status=default_publication_status,
    )


def _search_parameters_from_filters(
    filters: DocumentListFilters,
    *,
    neutral_citation: bool = False,
) -> SearchParameters:
    common: dict[str, Any] = {
        "order": filters.order,
        "only_unpublished": filters.only_unpublished,
        "show_unpublished": filters.show_unpublished,
        "page": filters.page,
    }
    if filters.court_param:
        common["court"] = filters.court_param
    if filters.date_from:
        common["date_from"] = filters.date_from
    if filters.date_to:
        common["date_to"] = filters.date_to

    if neutral_citation:
        return SearchParameters(neutral_citation=filters.query, **common)
    return SearchParameters(query=filters.query, **common)


def get_search_results_from_filters(filters: DocumentListFilters) -> dict[str, Any]:
    neutral_citation = filters.search_filter == "ncn"
    search_parameters = _search_parameters_from_filters(filters, neutral_citation=neutral_citation)
    search_response = search_and_parse_response(api_client, search_parameters)

    return {
        **filters.context_dict(),
        "total": search_response.total,
        "judgments": search_response.results,
        "documents": search_response.results,
        "paginator": paginator(filters.page, search_response.total),
        "court_options": court_filter_options(filters, search_response.facets),
    }


def get_document_by_uri_or_404(uri: str) -> Document:
    try:
        return api_client.get_document_by_uri(DocumentURIString(uri))
    except DocumentNotFoundError as e:
        msg = f"Document not found at {uri}"
        raise Http404(msg) from e


class DocumentViewMixin(TemplateView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        document_uri = self.kwargs["document_uri"]
        self.document = get_document_by_uri_or_404(document_uri)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["document"] = self.document
        context["document_uri"] = self.document.uri

        version_uri = self.request.GET.get("version_uri", None)

        if version_uri:
            context["current_version_number"] = extract_version_number_from_filename(version_uri)
            context["document_html"] = get_document_by_uri_or_404(version_uri).content_as_html()
        else:
            context["document_html"] = self.document.content_as_html()

        title = cast("NameMetadata | None", self.document.metadata.get("title"))
        context["page_title"] = title.value if title else "Untitled document"
        context["courts"] = caselawutils.courts.get_all(with_jurisdictions=True)

        context["editors"] = editors_dict()

        context["jira_create_link"] = build_jira_create_link(
            document=self.document,
            request=self.request,
        )

        context["linked_document_uri"] = get_linked_document_uri(self.document)
        context["document_type"] = self.document.document_noun.replace(" ", "_")

        context["preferred_ncn"] = self.document.identifiers.preferred(type=NeutralCitationNumber)

        if self.document.has_ever_been_published:
            if self.document.first_published_datetime_display:
                context["first_published_date"] = display_datetime(
                    self.document.first_published_datetime_display,
                )
            else:
                context["first_published_date"] = "Unknown"
        else:
            context["first_published_date"] = "—"

        return context


class DocumentView(DocumentViewMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: Remove this once we fully deprecate 'judgment' contexts
        context["judgment"] = context["document"]

        return context
