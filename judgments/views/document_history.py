import ds_caselaw_utils as caselawutils
from django.views.generic.base import TemplateView

from judgments.utils import editors_dict, set_document_type_and_link
from judgments.utils.link_generators import build_jira_create_link
from judgments.utils.view_helpers import get_document_by_uri_or_404


class DocumentHistoryView(TemplateView):
    template_name = "judgment/history.html"

    def get_context_data(self, **kwargs):
        document_uri = kwargs["document_uri"]

        document = get_document_by_uri_or_404(document_uri)

        context = {"document_uri": document_uri}

        context["document"] = document

        # TODO: Remove this once we fully deprecate 'judgment' contexts
        context["judgment"] = document

        context["page_title"] = document.name
        context["courts"] = caselawutils.courts.get_all()

        context.update({"editors": editors_dict()})

        context["jira_create_link"] = build_jira_create_link(
            document=document, request=self.request
        )

        context = set_document_type_and_link(context, document_uri)

        return context
