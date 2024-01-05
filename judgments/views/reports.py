from django.views.generic import TemplateView

from judgments.utils import api_client


class Index(TemplateView):
    template_name = "reports/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Reports"

        return context


class AwaitingEnrichment(TemplateView):
    template_name = "reports/awaiting_enrichment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        target_enrichment_version = 6

        context["page_title"] = "Documents awaiting enrichment"
        context["target_enrichment_version"] = target_enrichment_version
        context["documents"] = api_client.get_pending_enrichment_for_version(
            target_enrichment_version,
        )[1:]

        return context
