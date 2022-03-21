import math
import re

import caselawclient.xml_tools as xml_tools
from caselawclient.Client import (
    RESULTS_PER_PAGE,
    MarklogicAPIError,
    MarklogicResourceNotFoundError,
    api_client,
)
from caselawclient.xml_tools import JudgmentMissingMetadataError
from django.http import Http404, HttpResponse
from django.template import loader
from django.utils.translation import gettext
from lxml import etree
from requests_toolbelt.multipart import decoder

from judgments.models import Judgment, SearchResult, SearchResults


def detail(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    context = {"judgment_uri": judgment_uri}
    try:
        results = api_client.eval_xslt(judgment_uri, show_unpublished=True)
        xml_results = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)

        multipart_data = decoder.MultipartDecoder.from_response(results)
        judgment = multipart_data.parts[0].text
        model = Judgment.create_from_string(xml_results)
        context["judgment"] = judgment
        context["page_title"] = model.metadata_name
    except MarklogicResourceNotFoundError:
        raise Http404("Judgment was not found")
    template = loader.get_template("judgment/detail.html")
    return HttpResponse(template.render({"context": context}, request))


def edit(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri")
    context = {"judgment_uri": judgment_uri}
    try:
        judgment_xml = api_client.get_judgment_xml(judgment_uri)
        context["published"] = api_client.get_published(judgment_uri)
        context["sensitive"] = api_client.get_sensitive(judgment_uri)
        context["supplemental"] = api_client.get_supplemental(judgment_uri)
        xml = etree.XML(bytes(judgment_xml, encoding="utf8"))
        name = xml_tools.get_metadata_name_value(xml)
        context["metadata_name"] = name
        context["page_title"] = name
    except MarklogicResourceNotFoundError:
        raise Http404("Judgment was not found")
    except JudgmentMissingMetadataError:
        context[
            "error"
        ] = "The Judgment is missing correct metadata structure and cannot be edited"
    template = loader.get_template("judgment/edit.html")
    return HttpResponse(template.render({"context": context}, request))


def update(request):
    judgment_uri = request.POST["judgment_uri"]
    published = bool(request.POST.get("published", False))
    sensitive = bool(request.POST.get("sensitive", False))
    supplemental = bool(request.POST.get("supplemental", False))

    context = {"judgment_uri": judgment_uri}
    try:
        api_client.set_published(judgment_uri, published)
        api_client.set_sensitive(judgment_uri, sensitive)
        api_client.set_supplemental(judgment_uri, supplemental)

        judgment_xml = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)
        xml = etree.XML(bytes(judgment_xml, encoding="utf8"))
        name = xml_tools.get_metadata_name_element(xml)
        new_name = request.POST["metadata_name"]
        name.set("value", new_name)
        api_client.save_judgment_xml(judgment_uri, xml)
        context["published"] = published
        context["metadata_name"] = xml_tools.get_metadata_name_value(xml)
        context["success"] = "Judgment successfully updated"
        context["page_title"] = new_name
    except MarklogicAPIError:
        context["error"] = "There was an error saving the Judgment"
    except JudgmentMissingMetadataError:
        context[
            "error"
        ] = "The Judgment is missing correct metadata structure and cannot be edited"
    template = loader.get_template("judgment/edit.html")
    return HttpResponse(template.render({"context": context}, request))


def index(request):
    context = {}
    try:
        model = perform_advanced_search(order="-date")
        search_results = [
            SearchResult.create_from_node(result) for result in model.results
        ]
        context["recent_judgments"] = search_results

    except MarklogicResourceNotFoundError:
        raise Http404(
            "Search results not found"
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
    except MarklogicAPIError:
        raise Http404("Search error")  # TODO: This should be something else!
    template = loader.get_template("judgment/results.html")
    return HttpResponse(template.render({"context": context}, request))


def paginator(current_page, total):
    size_per_page = RESULTS_PER_PAGE
    number_of_pages = math.ceil(int(total) / size_per_page)
    next_pages = list(range(current_page + 1, min(current_page + 10, number_of_pages)))

    return {
        "current_page": current_page,
        "has_next_page": current_page < number_of_pages,
        "next_page": current_page + 1,
        "has_prev_page": current_page > 1,
        "prev_page": current_page - 1,
        "next_pages": next_pages,
        "number_of_pages": number_of_pages,
    }


def trim_leading_slash(uri):
    return re.sub("^/|/$", "", uri)


def perform_advanced_search(
    query=None,
    court=None,
    judge=None,
    party=None,
    order=None,
    date_from=None,
    date_to=None,
    page=1,
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
    )
    multipart_data = decoder.MultipartDecoder.from_response(response)
    return SearchResults.create_from_string(multipart_data.parts[0].text)
