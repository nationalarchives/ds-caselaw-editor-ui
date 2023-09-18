from typing import Any

import ds_caselaw_utils as caselawutils
from caselawclient.client_helpers.search_helpers import search_and_parse_response
from caselawclient.errors import DocumentNotFoundError
from caselawclient.models.documents import Document, DocumentURIString
from caselawclient.search_parameters import SearchParameters
from django.http import Http404
from django.views.generic import TemplateView

from judgments.utils import api_client, editors_dict, get_linked_document_uri
from judgments.utils.link_generators import build_jira_create_link
from judgments.utils.paginator import paginator

ALLOWED_ORDERS = ["date", "-date"]


def get_search_parameters(
    params, default_page=1, default_order="-date", only_unpublished=False
):
    query = params.get("query")
    page = int(params.get("page", default_page))
    order = (
        params.get("order") if params.get("order") in ALLOWED_ORDERS else default_order
    )
    return {
        "query": query,
        "page": page,
        "order": order,
        "only_unpublished": only_unpublished,
    }


def get_search_results(parameters: dict[str, Any]) -> dict[str, Any]:
    search_parameters = SearchParameters(
        query=parameters["query"],
        order=parameters["order"],
        only_unpublished=parameters["only_unpublished"],
        show_unpublished=True,
        page=parameters["page"],
    )
    search_response = search_and_parse_response(api_client, search_parameters)
    return {
        "query": parameters,
        "total": search_response.total,
        "judgments": search_response.results,
        "order": parameters["order"],
        "paginator": paginator(parameters["page"], search_response.total),
    }


def get_document_by_uri_or_404(uri: str) -> Document:
    try:
        return api_client.get_document_by_uri(DocumentURIString(uri))
    except DocumentNotFoundError:
        raise Http404(f"Document not found at {uri}")


class DocumentView(TemplateView):
    def get_context_data(self, **kwargs):
        document_uri = kwargs["document_uri"]
        document = get_document_by_uri_or_404(document_uri)
        context = super().get_context_data(**kwargs)
        context["document_uri"] = document_uri

        context["document"] = document

        # TODO: Remove this once we fully deprecate 'judgment' contexts
        context["judgment"] = document

        context["page_title"] = document.name
        context["courts"] = caselawutils.courts.get_all()

        context["editors"] = editors_dict()

        context["jira_create_link"] = build_jira_create_link(
            document=document, request=self.request
        )

        context["linked_document_uri"] = get_linked_document_uri(document)
        context["document_type"] = document.document_noun.replace(" ", "_")

        return context
