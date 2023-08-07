import ds_caselaw_utils as caselawutils
from django.http import HttpResponse
from django.template import loader
from django.views.generic import View

from judgments.utils import editors_dict, set_document_type_and_link
from judgments.utils.link_generators import build_jira_create_link
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


class DocumentHistoryView(View):
    def get(self, request, *args, **kwargs):
        document_uri = kwargs["document_uri"]

        document = get_judgment_by_uri_or_404(document_uri)

        context = {"document_uri": document_uri}

        context["document"] = document

        # TODO: Remove this once we fully deprecate 'judgment' contexts
        context["judgment"] = document

        context["page_title"] = document.name
        context["courts"] = caselawutils.courts.get_all()

        context.update({"editors": editors_dict()})

        context["jira_create_link"] = build_jira_create_link(
            judgment=document, request=request
        )

        context = set_document_type_and_link(context, document_uri)

        template = loader.get_template("judgment/history.html")
        return HttpResponse(template.render(context, request))
