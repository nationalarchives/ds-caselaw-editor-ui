from caselawclient.types import MarkLogicDocumentURIString
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView

from judgments.utils import api_client
from judgments.utils.view_helpers import user_is_developer

MISSING_FCLID_REPORT_LIMIT = 200


class DeveloperRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not user_is_developer(request.user):
            msg = "Only developers can access tools"
            raise PermissionDenied(msg)
        return super().dispatch(request, *args, **kwargs)


class ToolsIndex(DeveloperRequiredMixin, TemplateView):
    template_engine = "jinja"
    template_name = "tools/index.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Tools"
        return context


class MissingFclid(DeveloperRequiredMixin, TemplateView):
    template_engine = "jinja"
    template_name = "tools/missing_fclid.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Published documents missing FCLID"
        context["report_limit"] = MISSING_FCLID_REPORT_LIMIT

        marklogic_uris = api_client.get_missing_fclid(maximum_records=MISSING_FCLID_REPORT_LIMIT)
        context["documents"] = [
            {
                "marklogic_uri": marklogic_uri,
                "document_uri": MarkLogicDocumentURIString(marklogic_uri).as_document_uri(),
            }
            for marklogic_uri in marklogic_uris
        ]
        context["document_count"] = len(context["documents"])
        context["results_capped"] = context["document_count"] >= MISSING_FCLID_REPORT_LIMIT

        return context
