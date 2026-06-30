from caselawclient.Client import MarklogicAPIError
from django.http import Http404

from judgments.utils.view_helpers import get_search_parameters, get_search_results

from .paginated_view import PaginatedView


class ResultsView(PaginatedView):
    template_engine = "jinja"
    template_name = "judgment/results.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            params = get_search_parameters(self.request.GET)
            results = get_search_results(params)

        except MarklogicAPIError as e:
            msg = f"Search error, {e}"
            raise Http404(msg) from e  # TODO: This should be something else!

        else:
            context["documents"] = results["judgments"]

            context.update(results)
            context.update(
                {
                    "page_title": "Search results",
                    "query_string": f"query={params['query']}",
                },
            )

            paginator = results["paginator"]

            context["pagination_data"] = self.get_pagination_context(
                request=self.request,
                paginator=paginator,
            )

            return context
