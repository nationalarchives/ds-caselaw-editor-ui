import math

import environ
from caselawclient.Client import (
    RESULTS_PER_PAGE,
    MarklogicAPIError,
    MarklogicResourceNotFoundError,
    api_client,
)
from django.http import Http404, HttpResponse
from django.template import loader
from django.utils.translation import gettext
from requests_toolbelt.multipart import decoder

from judgments.models import SearchResult, SearchResults
from judgments.utils import create_s3_client

from .button_handlers import (  # noqa
    assign_judgment_button,
    hold_judgment_button,
    prioritise_judgment_button,
)
from .delete import delete  # noqa
from .detail import detail  # noqa
from .detail_xml import detail_xml  # noqa
from .edit_judgment import EditJudgmentView  # noqa

env = environ.Env()
akn_namespace = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
uk_namespace = {"uk": "https://caselaw.nationalarchives.gov.uk/akn"}


def index(request):
    context = {}
    try:
        params = request.GET
        page = params.get("page") if params.get("page") else "1"
        order = (
            params.get("order") if params.get("order") in ["date", "-date"] else "-date"
        )
        model = perform_advanced_search(order=order, only_unpublished=True, page=page)
        search_results = [
            SearchResult.create_from_node(result) for result in model.results
        ]

        context["recent_judgments"] = list(filter(None, search_results))
        context["count_judgments"] = model.total
        context["paginator"] = paginator(int(page), model.total)
        context["order"] = order

    except MarklogicResourceNotFoundError as e:
        raise Http404(
            f"Search results not found, {e}"
        )  # TODO: This should be something else!
    template = loader.get_template("pages/home.html")
    return HttpResponse(template.render({"context": context}, request))


def results(request):
    context = {"page_title": gettext("results.search.title")}

    try:
        params = request.GET
        query = params.get("query")
        page = params.get("page") if params.get("page") else "1"

        if query:
            model = perform_advanced_search(query=query, page=page)

            context["search_results"] = [
                SearchResult.create_from_node(result) for result in model.results
            ]
            context["total"] = model.total
            context["paginator"] = paginator(int(page), model.total)
            context["query_string"] = f"query={query}"
        else:
            model = perform_advanced_search(order="-date", page=page)
            search_results = [
                SearchResult.create_from_node(result) for result in model.results
            ]
            context["recent_judgments"] = search_results

            context["total"] = model.total
            context["search_results"] = search_results
            context["paginator"] = paginator(int(page), model.total)
    except MarklogicAPIError as e:
        raise Http404(f"Search error, {e}")  # TODO: This should be something else!
    template = loader.get_template("judgment/results.html")
    return HttpResponse(template.render({"context": context}, request))


def get_parser_log(uri: str) -> str:
    s3 = create_s3_client()
    private_bucket = env("PRIVATE_ASSET_BUCKET", None)
    # Locally, we may not have an S3 bucket set up; continue as best we can.
    if not private_bucket:
        return ""

    try:
        parser_log = s3.get_object(Bucket=private_bucket, Key=f"{uri}/parser.log")
        return parser_log["Body"].read().decode("utf-8")
    except KeyError:
        return ""


def paginator(current_page, total):
    size_per_page = RESULTS_PER_PAGE
    number_of_pages = math.ceil(int(total) / size_per_page)
    next_pages = list(
        range(current_page + 1, min(current_page + 10, number_of_pages) + 1)
    )

    return {
        "current_page": current_page,
        "has_next_page": current_page < number_of_pages,
        "next_page": current_page + 1,
        "has_prev_page": current_page > 1,
        "prev_page": current_page - 1,
        "next_pages": next_pages,
        "number_of_pages": number_of_pages,
    }


def perform_advanced_search(
    query=None,
    court=None,
    judge=None,
    party=None,
    order=None,
    date_from=None,
    date_to=None,
    page=1,
    only_unpublished=False,
):
    response = api_client.advanced_search(
        q=query,
        court=court,
        judge=judge,
        party=party,
        page=page,
        order=order,
        date_from=date_from,
        date_to=date_to,
        show_unpublished=True,
        only_unpublished=only_unpublished,
    )
    multipart_data = decoder.MultipartDecoder.from_response(response)
    return SearchResults.create_from_string(multipart_data.parts[0].text)
