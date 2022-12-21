from caselawclient.Client import (
    MarklogicAPIError

)
from django.http import Http404, HttpResponse
from django.template import loader
from django.utils.translation import gettext

from judgments.models import SearchResult

from judgments.utils import perform_advanced_search, paginator

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