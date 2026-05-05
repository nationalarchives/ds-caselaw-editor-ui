from django.views.generic import TemplateView

from judgments.utils.view_helpers import get_search_parameters, get_search_results


class HomeView(TemplateView):
    template_engine = "jinja"
    template_name = "pages/home.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = get_search_parameters(self.request.GET, only_unpublished=True)
        search_context = get_search_results(query)
        search_context["documents"] = search_context["judgments"]
        context.update(search_context)

        return context
