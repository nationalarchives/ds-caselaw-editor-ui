from django.views.generic import TemplateView


class TemplateViewWithContext(TemplateView):
    page_title = None

    def get_context_data(self, **kwargs):
        return {
            "context": {
                "page_title": self.page_title or None,
            },
        }


class CheckView(TemplateViewWithContext):
    template_engine = "jinja"
    template_name = "pages/check.jinja"
