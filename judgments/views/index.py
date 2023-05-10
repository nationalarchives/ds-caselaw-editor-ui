from django.http import HttpResponse
from django.template import loader

from judgments.utils.view_helpers import get_search_parameters, get_search_results


def index(request):
    query = get_search_parameters(request.GET, only_unpublished=True)
    context = get_search_results(query)
    template = loader.get_template("pages/home.html")
    return HttpResponse(template.render(context, request))
