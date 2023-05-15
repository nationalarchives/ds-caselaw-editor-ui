from urllib.parse import quote, urlencode

import ds_caselaw_utils as caselawutils
from caselawclient.Client import MarklogicAPIError, api_client
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext
from django.views.generic import View

from judgments.utils import (
    MoveJudgmentError,
    NeutralCitationToUriError,
    editors_dict,
    update_judgment_uri,
)
from judgments.utils.aws import invalidate_caches
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


def build_email_link_with_content(address, subject, body=None):
    params = {"subject": "Find Case Law – {subject}".format(subject=subject)}

    if body:
        params["body"] = body

    return "mailto:{address}?{params}".format(
        address=address, params=urlencode(params, quote_via=quote)
    )


def build_confirmation_email_link(request, judgment):
    subject_string = "Notification of publication [TDR ref: {reference}]".format(
        reference=judgment.consignment_reference
    )

    email_context = {
        "judgment_name": judgment.name,
        "reference": judgment.consignment_reference,
        "public_judgment_url": judgment.public_uri,
        "user_signature": request.user.get_full_name() or "XXXXXX",
    }

    body_string = loader.render_to_string(
        "emails/confirmation_to_submitter.txt", email_context
    )

    return build_email_link_with_content(
        judgment.source_email, subject_string, body_string
    )


class EditJudgmentView(View):
    def build_raise_issue_email_link(self, context):
        subject_string = "Issue(s) found with {reference}".format(
            reference=context["judgment"].consignment_reference
        )

        return build_email_link_with_content(
            context["judgment"].source_email, subject_string
        )

    def build_jira_create_link(self, request, context):
        summary_string = "{name} / {ncn} / {tdr}".format(
            name=context["judgment"].name,
            ncn=context["judgment"].neutral_citation,
            tdr=context["judgment"].consignment_reference,
        )

        editor_html_url = request.build_absolute_uri(
            reverse("full-text-html", kwargs={"judgment_uri": context["judgment_uri"]})
        )

        description_string = "{editor_html_url}".format(
            editor_html_url="""{html_url}

{source_name_label}: {source_name}
{source_email_label}: {source_email}
{consignment_ref_label}: {consignment_ref}""".format(
                html_url=editor_html_url,
                source_name_label=gettext("judgments.submitter"),
                source_name=context["judgment"].source_name,
                source_email_label=gettext("judgments.submitteremail"),
                source_email=context["judgment"].source_email,
                consignment_ref_label=gettext("judgments.consignmentref"),
                consignment_ref=context["judgment"].consignment_reference,
            )
        )

        params = {
            "pid": "10090",
            "issuetype": "10320",
            "priority": "3",
            "summary": summary_string,
            "description": description_string,
        }
        return "https://{jira_instance}/secure/CreateIssueDetails!init.jspa?{params}".format(
            jira_instance=settings.JIRA_INSTANCE, params=urlencode(params)
        )

    def get(self, request, *args, **kwargs):
        judgment_uri = kwargs["judgment_uri"]
        judgment = get_judgment_by_uri_or_404(judgment_uri)

        context = {"judgment_uri": judgment_uri}

        context["judgment"] = judgment
        context["page_title"] = judgment.name
        context["view"] = "judgment_metadata"
        context["courts"] = caselawutils.courts.get_all()

        context.update({"editors": editors_dict()})

        context["email_raise_issue_link"] = self.build_raise_issue_email_link(context)
        context["email_confirmation_link"] = build_confirmation_email_link(
            request, judgment
        )
        context["jira_create_link"] = self.build_jira_create_link(request, context)

        template = loader.get_template("judgment/edit.html")
        return HttpResponse(template.render(context, request))

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        judgment = get_judgment_by_uri_or_404(judgment_uri)

        return_to = request.POST.get("return_to", None)

        # Default to not performing a subset update to maintain existing behaviour
        subset = False

        # But if we're going back to HTML or PDF views, this is a subset update
        if return_to in ("html", "pdf"):
            subset = True

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

            if not subset:
                sensitive = bool(request.POST.get("sensitive", False))
                supplemental = bool(request.POST.get("supplemental", False))
                anonymised = bool(request.POST.get("anonymised", False))

                api_client.set_sensitive(judgment_uri, sensitive)
                api_client.set_supplemental(judgment_uri, supplemental)
                api_client.set_anonymised(judgment_uri, anonymised)

                # Assignment
                # TODO consider validating assigned_to is a user?
                if new_assignment := request.POST.get("assigned_to", False):
                    api_client.set_property(judgment_uri, "assigned-to", new_assignment)

                published = bool(request.POST.get("published", False))

                if published and not judgment.is_published:
                    judgment.publish()
                elif not published and judgment.is_published:
                    judgment.unpublish()

            # If judgment_uri is a `failure` URI, amend it to match new neutral citation and redirect
            if "failures" in judgment_uri and new_citation is not None:
                new_judgment_uri = update_judgment_uri(judgment_uri, new_citation)
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
