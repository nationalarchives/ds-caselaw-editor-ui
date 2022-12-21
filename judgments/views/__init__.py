import json
import math
import re
from typing import Optional, Union

import environ
from caselawclient.Client import (
    RESULTS_PER_PAGE,
    MarklogicAPIError,
    MarklogicResourceNotFoundError,
    api_client,
)
from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.template import loader
from django.utils.translation import gettext
from requests_toolbelt.multipart import decoder

from judgments.models import SearchResult, SearchResults
from judgments.utils import (
    VERSION_REGEX,
    create_s3_client,
    delete_documents,
    generate_docx_url,
    generate_pdf_url,
    get_judgment_root,
    uri_for_s3,
)

from .edit_judgment import EditJudgmentView  # noqa

env = environ.Env()
akn_namespace = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
uk_namespace = {"uk": "https://caselaw.nationalarchives.gov.uk/akn"}


def detail(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    version_uri = params.get("version_uri", None)
    context = {"judgment_uri": judgment_uri, "is_failure": False}

    try:
        judgment_xml = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)
        judgment_root = get_judgment_root(judgment_xml)
        context["is_editable"] = True
        if "failures" in judgment_uri:
            context["is_failure"] = True

        if "error" in judgment_root:
            context["is_editable"] = False
            judgment = judgment_xml
            metadata_name = judgment_uri
        else:
            results = api_client.eval_xslt(
                judgment_uri, version_uri, show_unpublished=True
            )
            metadata_name = api_client.get_judgment_name(judgment_uri)

            multipart_data = decoder.MultipartDecoder.from_response(results)
            judgment = multipart_data.parts[0].text
        context["judgment"] = judgment
        context["page_title"] = metadata_name
        context["docx_url"] = generate_docx_url(uri_for_s3(judgment_uri))
        context["pdf_url"] = generate_pdf_url(uri_for_s3(judgment_uri))

        if version_uri:
            try:
                version = re.search(VERSION_REGEX, version_uri).group(1)
            except AttributeError:
                version = None
            context["version"] = version
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")
    template = loader.get_template("judgment/detail.html")
    return HttpResponse(template.render({"context": context}, request))


def detail_xml(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    try:
        judgment_xml = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    response = HttpResponse(judgment_xml, content_type="application/xml")
    response["Content-Disposition"] = f"attachment; filename={judgment_uri}.xml"
    return response


def delete(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    context = {
        "judgment_uri": judgment_uri,
        "page_title": gettext("judgment.delete_a_judgment"),
    }
    try:
        api_client.delete_judgment(judgment_uri)

        delete_documents(judgment_uri)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    template = loader.get_template("judgment/deleted.html")

    messages.success(request, "Judgment deleted.")
    return HttpResponse(template.render({"context": context}, request))


def hold_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    # we probably shouldn't hold if the judgment isn't assigned but we won't check
    hold = request.POST["hold"]
    if hold not in ["false", "true"]:
        raise RuntimeError("Hold value must be '0' or '1'")
    api_client.set_property(judgment_uri, "editor-hold", hold)
    target_uri = request.META.get("HTTP_REFERER") or "/"
    if hold == "true":
        word = "held"
    else:
        word = "released"
    messages.success(request, f"Judgment {word}.")
    return redirect(target_uri)


def assign_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    api_client.set_property(judgment_uri, "assigned-to", request.user.username)
    target_uri = request.META.get("HTTP_REFERER") or "/"
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponse(
            json.dumps({"assigned_to": request.user.username}),
            content_type="application/json",
        )
    else:
        messages.success(request, "Judgment assigned to you.")
        return redirect(target_uri)


def prioritise_judgment_button(request):
    """Editors can let other editors know that some judgments are more important than others."""

    def parse_priority(priority: Union[str, int]) -> Optional[str]:
        # note: use 09 if using numbers less than 10.
        priorities = {"low": "10", "medium": "20", "high": "30"}
        priority_string = priority.lower().strip()
        return priorities.get(priority_string)

    judgment_uri = request.POST["judgment_uri"]
    priority = parse_priority(request.POST["priority"])
    if priority:
        api_client.set_property(judgment_uri, "editor-priority", priority)
        target_uri = request.META.get("HTTP_REFERER") or "/"

        messages.success(request, "Judgment priority set.")
        return redirect(target_uri)

    return HttpResponseBadRequest("Priority string not recognised")


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
