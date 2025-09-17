from typing import Any

import ds_caselaw_utils as caselawutils
import environ
from caselawclient.client_helpers.search_helpers import search_and_parse_response
from caselawclient.errors import DocumentNotFoundError
from caselawclient.models.documents import Document, DocumentURIString
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from caselawclient.search_parameters import SearchParameters
from django.http import Http404
from django.views.generic import TemplateView

from judgments.utils import api_client, editors_dict, extract_version_number_from_filename, get_linked_document_uri
from judgments.utils.link_generators import build_jira_create_link
from judgments.utils.paginator import paginator

env = environ.Env()
RESULTS_ORDER = "-date"


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


def get_search_parameters(
    params,
    default_page=1,
    only_unpublished=False,
):
    query = params.get("query")
    search_filter = params.get("search_filter")
    page = int(params.get("page", default_page))
    return {
        "query": query,
        "search_filter": search_filter,
        "page": page,
        "order": RESULTS_ORDER,
        "only_unpublished": only_unpublished,
    }


def get_default_search_results(parameters: dict[str, Any]) -> dict[str, Any]:
    search_parameters = SearchParameters(
        query=parameters["query"],
        order=RESULTS_ORDER,
        only_unpublished=parameters["only_unpublished"],
        show_unpublished=True,
        page=parameters["page"],
    )

    search_response = search_and_parse_response(api_client, search_parameters)

    return {
        "query": parameters["query"],
        "search_filter": parameters["search_filter"],
        "total": search_response.total,
        "judgments": search_response.results,
        "order": RESULTS_ORDER,
        "paginator": paginator(parameters["page"], search_response.total),
    }


def get_ncn_results(parameters: dict[str, Any]) -> dict[str, Any]:
    search_parameters = SearchParameters(
        neutral_citation=parameters["query"],
        order=RESULTS_ORDER,
        only_unpublished=parameters["only_unpublished"],
        show_unpublished=True,
        page=parameters["page"],
    )

    search_response = search_and_parse_response(api_client, search_parameters)

    return {
        "query": parameters["query"],
        "search_filter": parameters["search_filter"],
        "total": search_response.total,
        "judgments": search_response.results,
        "order": RESULTS_ORDER,
        "paginator": paginator(parameters["page"], search_response.total),
    }


def get_search_results(parameters: dict[str, Any]) -> dict[str, Any]:
    search_filter = parameters["search_filter"]

    match search_filter:
        case "ncn":
            return get_ncn_results(parameters)

        case _:
            return get_default_search_results(parameters)


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

        context["page_title"] = self.document.body.name
        context["courts"] = caselawutils.courts.get_all(with_jurisdictions=True)

        context["editors"] = editors_dict()

        context["jira_create_link"] = build_jira_create_link(
            document=self.document,
            request=self.request,
        )

        context["linked_document_uri"] = get_linked_document_uri(self.document)
        context["document_type"] = self.document.document_noun.replace(" ", "_")

        context["preferred_ncn"] = self.document.identifiers.preferred(type=NeutralCitationNumber)

        return context


class DocumentView(DocumentViewMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: Remove this once we fully deprecate 'judgment' contexts
        context["judgment"] = context["document"]

        return context
