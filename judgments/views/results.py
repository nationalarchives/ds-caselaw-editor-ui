from caselawclient.Client import MarklogicAPIError
from django.http import Http404
from django.views.generic import TemplateView

from judgments.utils.view_helpers import get_search_parameters, get_search_results


class ResultsView(TemplateView):
    template_engine = "jinja"
    template_name = "judgment/results.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            params = get_search_parameters(self.request.GET)
            results = get_search_results(params)
            search_context = results | {
                "page_title": "Search results",
                "query_string": f"query={params['query']}",
            }
        except MarklogicAPIError as e:
            msg = f"Search error, {e}"
            raise Http404(msg) from e  # TODO: This should be something else!

        search_context["documents"] = search_context["judgments"]
        context.update(search_context)

        return context
