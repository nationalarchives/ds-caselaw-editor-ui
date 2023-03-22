import waffle
from django.views.generic import TemplateView


class Labs(TemplateView):
    template_name = "pages/labs.html"

    EXPERIMENTS: dict[str, dict] = {
        "embedded_pdf_view": {
            "title": "Embedded PDF",
            "description": "View PDFs directly in the browser without needing to download them.",
        },
        "publish_flow": {
            "title": "Revamped Publish Workflow",
            "description": "A new workflow for publishing judgments.",
        },
    }

    def get_context_data(self, **kwargs):
        context = super(Labs, self).get_context_data(**kwargs)

        context["context"] = {"page_title": "Labs"}

        context["experiments"] = []

        for flag, data in self.EXPERIMENTS.items():
            data["flag"] = flag
            data["active"] = waffle.flag_is_active(self.request, flag)
            context["experiments"].append(data)

        return context
