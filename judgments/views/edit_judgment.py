from urllib.parse import quote, urlencode

from caselawclient.Client import MarklogicAPIError, api_client
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext
from django.views.generic import View
from requests_toolbelt.multipart import decoder

from judgments.models import Judgment
from judgments.utils import (
    MoveJudgmentError,
    NeutralCitationToUriError,
    render_versions,
    update_judgment_uri,
    users_dict,
)
from judgments.utils.aws import (
    generate_docx_url,
    generate_pdf_url,
    invalidate_caches,
    notify_changed,
    publish_documents,
    unpublish_documents,
    uri_for_s3,
)


class EditJudgmentView(View):
    def get_metadata(self, uri: str) -> dict:
        meta = dict()

        meta["sensitive"] = api_client.get_sensitive(uri)
        meta["supplemental"] = api_client.get_supplemental(uri)
        meta["anonymised"] = api_client.get_anonymised(uri)
        meta["page_title"] = api_client.get_judgment_name(uri)
        meta["judgment_date"] = api_client.get_judgment_work_date(uri)
        meta["docx_url"] = generate_docx_url(uri_for_s3(uri))
        meta["pdf_url"] = generate_pdf_url(uri_for_s3(uri))
        meta["previous_versions"] = self.get_versions(uri)
        meta["consignment_reference"] = api_client.get_property(
            uri, "transfer-consignment-reference"
        )
        meta["source_name"] = api_client.get_property(uri, "source-name")
        meta["source_email"] = api_client.get_property(uri, "source-email")
        meta["assigned_to"] = api_client.get_property(uri, "assigned-to")
        meta["is_editable"] = True
        return meta

    def get_versions(self, uri: str):
        versions_response = api_client.list_judgment_versions(uri)
        try:
            decoded_versions = decoder.MultipartDecoder.from_response(versions_response)
            return render_versions(decoded_versions.parts)
        except AttributeError:
            return []

    def build_email_link_with_content(self, address, subject, body=None):
        params = {"subject": "Find Case Law – {subject}".format(subject=subject)}

        if body:
            params["body"] = body

        return "mailto:{address}?{params}".format(
            address=address, params=urlencode(params, quote_via=quote)
        )

    def build_raise_issue_email_link(self, context):
        subject_string = "Issue(s) found with {reference}".format(
            reference=context["consignment_reference"]
        )

        return self.build_email_link_with_content(
            context["source_email"], subject_string
        )

    def build_confirmation_email_link(self, request, context):
        subject_string = "Notification of publication [TDR ref: {reference}]".format(
            reference=context["consignment_reference"]
        )

        email_context = {
            "judgment_name": context["judgment"].name,
            "reference": context["consignment_reference"],
            "public_judgment_url": "https://caselaw.nationalarchives.gov.uk/{uri}".format(
                uri=context["judgment_uri"]
            ),
            "user_signature": request.user.get_full_name() or "XXXXXX",
        }

        body_string = loader.render_to_string(
            "emails/confirmation_to_submitter.txt", email_context
        )

        return self.build_email_link_with_content(
            context["source_email"], subject_string, body_string
        )

    def build_jira_create_link(self, request, context):
        summary_string = "{name} / {ncn} / {tdr}".format(
            name=context["judgment"].name,
            ncn=context["judgment"].neutral_citation,
            tdr=context["consignment_reference"],
        )

        editor_details_url = request.build_absolute_uri(
            "{base_url}?{params}".format(
                base_url=reverse("detail"),
                params=urlencode(
                    {
                        "judgment_uri": context["judgment_uri"],
                    }
                ),
            )
        )

        description_string = "{editor_details_url}".format(
            editor_details_url="""{details_url}

{source_name_label}: {source_name}
{source_email_label}: {source_email}
{consignment_ref_label}: {consignment_ref}""".format(
                details_url=editor_details_url,
                source_name_label=gettext("judgments.submitter"),
                source_name=context["source_name"],
                source_email_label=gettext("judgments.submitteremail"),
                source_email=context["source_email"],
                consignment_ref_label=gettext("judgments.consignmentref"),
                consignment_ref=context["consignment_reference"],
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

    def render(self, request, context):
        template = loader.get_template("judgment/edit.html")
        return HttpResponse(template.render({"context": context}, request))

    def get(self, request, *args, **kwargs):
        params = request.GET
        judgment_uri = params.get("judgment_uri")
        context = {"judgment_uri": judgment_uri}
        context.update(self.get_metadata(judgment_uri))

        context["judgment"] = Judgment.objects.get_by_uri(judgment_uri)

        context.update({"users": users_dict()})

        context["email_raise_issue_link"] = self.build_raise_issue_email_link(context)
        context["email_confirmation_link"] = self.build_confirmation_email_link(
            request, context
        )
        context["jira_create_link"] = self.build_jira_create_link(request, context)

        return self.render(request, context)

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        published = bool(request.POST.get("published", False))
        sensitive = bool(request.POST.get("sensitive", False))
        supplemental = bool(request.POST.get("supplemental", False))
        anonymised = bool(request.POST.get("anonymised", False))

        context = {"judgment_uri": judgment_uri}
        try:
            api_client.set_published(judgment_uri, published)
            api_client.set_sensitive(judgment_uri, sensitive)
            api_client.set_supplemental(judgment_uri, supplemental)
            api_client.set_anonymised(judgment_uri, anonymised)

            if published:
                publish_documents(uri_for_s3(judgment_uri))
            else:
                unpublish_documents(uri_for_s3(judgment_uri))

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

            # Assignment
            # TODO consider validating assigned_to is a user?
            if new_assignment := request.POST["assigned_to"]:
                api_client.set_property(judgment_uri, "assigned-to", new_assignment)

            # If judgment_uri is a `failure` URI, amend it to match new neutral citation and redirect
            if "failures" in judgment_uri and new_citation is not None:
                new_judgment_uri = update_judgment_uri(judgment_uri, new_citation)
                return redirect(reverse("edit") + f"?judgment_uri={new_judgment_uri}")

            if published:
                notify_status = "published"
            else:
                notify_status = "not published"
            notify_changed(
                uri=judgment_uri,
                status=notify_status,
                enrich=published,  # placeholder for now, should perhaps be "has this become published"
            )

            context["success"] = "Judgment successfully updated"

        except (MoveJudgmentError, NeutralCitationToUriError) as e:
            context[
                "error"
            ] = f"There was an error updating the Judgment's neutral citation: {e}"

        except MarklogicAPIError as e:
            context["error"] = f"There was an error saving the Judgment: {e}"

        context.update(self.get_metadata(judgment_uri))
        invalidate_caches(judgment_uri)

        context.update({"users": users_dict()})

        return self.render(request, context)
