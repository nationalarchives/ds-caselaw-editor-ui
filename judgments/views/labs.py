import waffle
from django.views.generic import TemplateView


class Labs(TemplateView):
    template_name = "pages/labs.html"

    # "embedded_pdf_view": {
    #     "title": "Embedded PDF",
    #     "description": "View PDFs directly in the browser without needing to download them.",
    # },
    EXPERIMENTS: dict[str, dict] = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context = {
            "page_title": "Labs",
            "experiments": [],
        }

        for flag, data in self.EXPERIMENTS.items():
            data["flag"] = flag
            data["active"] = waffle.flag_is_active(self.request, flag)
            context["experiments"].append(data)

        return context
