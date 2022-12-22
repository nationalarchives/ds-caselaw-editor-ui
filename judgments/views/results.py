from caselawclient.Client import MarklogicAPIError
from django.http import Http404, HttpResponse
from django.template import loader
from django.utils.translation import gettext

from judgments.utils.view_helpers import get_search_parameters, get_search_results


def results(request):
    try:
        query = get_search_parameters(request.GET)
        results = get_search_results(query)
        context = results | {
            "page_title": gettext("results.search.title"),
            "query_string": f"query={query['query']}",
        }
    except MarklogicAPIError as e:
        raise Http404(f"Search error, {e}")  # TODO: This should be something else!
    template = loader.get_template("judgment/results.html")
    return HttpResponse(template.render({"context": context}, request))
