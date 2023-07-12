import ds_caselaw_utils as caselawutils
from caselawclient.Client import MarklogicAPIError, api_client
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.views.generic import View

from judgments.utils import (
    MoveJudgmentError,
    NeutralCitationToUriError,
    editors_dict,
    update_document_uri,
)
from judgments.utils.aws import invalidate_caches
from judgments.utils.link_generators import (
    build_confirmation_email_link,
    build_jira_create_link,
    build_raise_issue_email_link,
)
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


class EditJudgmentView(View):
    def get(self, request, *args, **kwargs):
        judgment_uri = kwargs["judgment_uri"]
        judgment = get_judgment_by_uri_or_404(judgment_uri)

        context = {"judgment_uri": judgment_uri}

        context["judgment"] = judgment
        context["page_title"] = judgment.name
        context["view"] = "judgment_metadata"
        context["courts"] = caselawutils.courts.get_all()

        context.update({"editors": editors_dict()})

        context["email_raise_issue_link"] = build_raise_issue_email_link(
            judgment=judgment, signature=request.user.get_full_name()
        )
        context["email_confirmation_link"] = build_confirmation_email_link(
            judgment=judgment, signature=request.user.get_full_name()
        )
        context["jira_create_link"] = build_jira_create_link(
            judgment=judgment, request=request
        )

        template = loader.get_template("judgment/edit.html")
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        judgment = get_judgment_by_uri_or_404(judgment_uri)

        return_to = request.POST.get("return_to", None)

        try:
            # Set name
            new_name = request.POST["metadata_name"]
            api_client.set_judgment_name(judgment_uri, new_name)

            # Set neutral citation
            new_citation = request.POST["neutral_citation"]
            api_client.set_judgment_citation(judgment_uri, new_citation)

            # Set court
            new_court = request.POST["court"]
            api_client.set_judgment_court(judgment_uri, new_court)

            # Date
            new_date = request.POST["judgment_date"]
            api_client.set_judgment_date(judgment_uri, new_date)

            # Editor assignment
            if new_assignment := request.POST.get("assigned_to", False):
                api_client.set_property(judgment_uri, "assigned-to", new_assignment)

            # If judgment_uri is a `failure` URI, amend it to match new neutral citation and redirect
            if "failures" in judgment_uri and new_citation is not None:
                new_judgment_uri = update_document_uri(judgment_uri, new_citation)
                return redirect(
                    reverse("edit-judgment", kwargs={"judgment_uri": new_judgment_uri})
                )

            messages.success(request, "Judgment successfully updated")

        except (MoveJudgmentError, NeutralCitationToUriError) as e:
            messages.error(
                request,
                f"There was an error updating the Judgment's neutral citation: {e}",
            )

        except MarklogicAPIError as e:
            messages.error(request, f"There was an error saving the Judgment: {e}")

        invalidate_caches(judgment.uri)

        if return_to == "html":
            return_path = reverse(
                "full-text-html", kwargs={"judgment_uri": judgment.uri}
            )
        elif return_to == "pdf":
            return_path = reverse(
                "full-text-pdf", kwargs={"judgment_uri": judgment.uri}
            )
        else:
            return_path = reverse(
                "edit-judgment", kwargs={"judgment_uri": judgment.uri}
            )

        return HttpResponseRedirect(return_path)


def edit_view_redirect(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    return HttpResponseRedirect(
        reverse("edit-judgment", kwargs={"judgment_uri": judgment_uri})
    )
