import ds_caselaw_utils as caselawutils
from django.http import HttpResponse
from django.template import loader
from django.views.generic import View

from judgments.utils import editors_dict, set_document_type_and_link
from judgments.utils.link_generators import build_jira_create_link
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


class JudgmentHistoryView(View):
    def get(self, request, *args, **kwargs):
        judgment_uri = kwargs["judgment_uri"]

        judgment = get_judgment_by_uri_or_404(judgment_uri)

        context = {"judgment_uri": judgment_uri}

        context["judgment"] = judgment
        context["page_title"] = judgment.name
        context["view"] = "judgment_metadata"
        context["courts"] = caselawutils.courts.get_all()

        context.update({"editors": editors_dict()})

        context["jira_create_link"] = build_jira_create_link(
            judgment=judgment, request=request
        )

        context = set_document_type_and_link(context, judgment_uri)

        template = loader.get_template("judgment/history.html")
        return HttpResponse(template.render(context, request))
