from judgments.utils.view_helpers import get_search_parameters, get_search_results

from .paginated_view import PaginatedView


class HomeView(PaginatedView):
    template_engine = "jinja"
    template_name = "pages/home.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = get_search_parameters(self.request.GET, only_unpublished=True)
        search_context = get_search_results(query)
        search_context["documents"] = search_context["judgments"]
        context.update(search_context)

        paginator = search_context["paginator"]

        context["pagination_data"] = self.get_pagination_context(
            request=self.request,
            paginator=paginator,
        )

        return context
