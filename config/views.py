from django.utils.translation import gettext
from django.views.generic import TemplateView


class TemplateViewWithContext(TemplateView):
    page_title = None

    def get_context_data(self, **kwargs):
        return {
            "context": {
                "page_title": gettext(self.page_title) if self.page_title else None,
            },
        }


class SourcesView(TemplateViewWithContext):
    template_name = "pages/sources.html"
    page_title = "judgmentsources.title"


class StructuredSearchView(TemplateViewWithContext):
    template_name = "pages/structured_search.html"
    page_title = "search.title"


class CheckView(TemplateViewWithContext):
    template_name = "pages/check.html"
