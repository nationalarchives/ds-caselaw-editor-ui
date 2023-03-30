from caselawclient.Client import MarklogicResourceNotFoundError
from django.http import Http404, HttpResponse
from django.template import loader

from judgments.utils.view_helpers import get_search_parameters, get_search_results


def index(request):
    try:
        query = get_search_parameters(request.GET, only_unpublished=True)
        context = get_search_results(query)
    except MarklogicResourceNotFoundError as e:
        raise Http404(
            f"Search results not found, {e}"
        )  # TODO: This should be something else!
    template = loader.get_template("pages/home.html")
    return HttpResponse(template.render(context, request))
