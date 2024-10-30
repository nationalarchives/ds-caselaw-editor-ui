from caselawclient.Client import MarklogicAPIError
from django.http import Http404, HttpResponse
from django.template import loader

from judgments.utils.view_helpers import get_search_parameters, get_search_results


def results(request):
    try:
        query = get_search_parameters(request.GET)
        results = get_search_results(query)
        context = results | {
            "page_title": "Search results",
            "query_string": f"query={query['query']}",
        }
    except MarklogicAPIError as e:
        msg = f"Search error, {e}"
        raise Http404(msg) from e  # TODO: This should be something else!
    template = loader.get_template("judgment/results.html")
    return HttpResponse(template.render(context, request))
