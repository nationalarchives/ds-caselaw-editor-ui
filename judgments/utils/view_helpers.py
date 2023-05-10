from caselawclient.errors import JudgmentNotFoundError
from django.http import Http404

from judgments.models import SearchResult
from judgments.utils import Judgment, get_judgment_by_uri
from judgments.utils.paginator import paginator
from judgments.utils.perform_advanced_search import perform_advanced_search

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


def get_search_results(query):
    model = perform_advanced_search(
        query=query["query"],
        order=query["order"],
        only_unpublished=query["only_unpublished"],
        page=query["page"],
    )
    search_results = [SearchResult.create_from_node(result) for result in model.results]
    return {
        "query": query,
        "total": model.total,
        "judgments": search_results,
        "order": query["order"],
        "paginator": paginator(query["page"], model.total),
    }


def get_judgment_by_uri_or_404(uri: str) -> Judgment:
    try:
        return get_judgment_by_uri(uri)
    except JudgmentNotFoundError:
        raise Http404(f"Judgment not found at {uri}")
