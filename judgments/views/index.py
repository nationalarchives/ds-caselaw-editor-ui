from judgments.utils import perform_advanced_search, paginator
from judgments.models import SearchResult
from caselawclient.Client import MarklogicResourceNotFoundError
from django.http import Http404, HttpResponse
from django.template import loader

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