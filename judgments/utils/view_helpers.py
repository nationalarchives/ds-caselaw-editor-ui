from typing import Any

from caselawclient.client_helpers.search_helpers import (
    search_judgments_and_parse_response,
)
from caselawclient.errors import JudgmentNotFoundError
from caselawclient.search_parameters import SearchParameters
from django.http import Http404

from judgments.utils import Judgment, get_judgment_by_uri
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
    search_response = search_judgments_and_parse_response(search_parameters)
    return {
        "query": parameters,
        "total": search_response.total,
        "judgments": search_response.results,
        "order": parameters["order"],
        "paginator": paginator(parameters["page"], search_response.total),
    }


def get_judgment_by_uri_or_404(uri: str) -> Judgment:
    try:
        return get_judgment_by_uri(uri)
    except JudgmentNotFoundError:
        raise Http404(f"Judgment not found at {uri}")
