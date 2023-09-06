from urllib.parse import quote, urlencode

from caselawclient.models.documents import Document
from django.conf import settings
from django.http import HttpRequest
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext


def build_email_link_with_content(
    address: str,
    subject: str,
    body: str | None = None,
) -> str:
    """Given a destination address, subject, and (optionally) body for an email build a mailto link for it."""
    params = {"subject": f"Find Case Law - {subject}"}

    if body:
        params["body"] = body

    return f"mailto:{address}?{urlencode(params, quote_via=quote)}"


def build_confirmation_email_link(
    document: Document,
    signature: str | None = None,
) -> str:
    subject_string = "Notification of publication [TDR ref: {reference}]".format(
        reference=document.consignment_reference,
    )

    email_context = {
        "judgment_name": document.name,
        "reference": document.consignment_reference,
        "public_judgment_url": document.public_uri,
        "submitter": document.source_name,
        "user_signature": signature or "XXXXXX",
    }

    body_string = loader.render_to_string(
        "emails/confirmation_to_submitter.txt",
        email_context,
    )

    return build_email_link_with_content(
        document.source_email,
        subject_string,
        body_string,
    )


def build_raise_issue_email_link(
    document: Document,
    signature: str | None = None,
) -> str:
    subject_string = f"Issue(s) found with {document.consignment_reference}"
    email_context = {
        "judgment_name": document.name,
        "reference": document.consignment_reference,
        "public_judgment_url": document.public_uri,
        "user_signature": signature,
        "submitter": document.source_name or "XXXXXX",
    }

    body_string = loader.render_to_string(
        "emails/raise_issue_with_submitter.txt",
        email_context,
    )

    return build_email_link_with_content(
        document.source_email,
        subject_string,
        body_string,
    )


def build_jira_create_link(document: Document, request: HttpRequest) -> str:
    summary_string = "{name} / {ncn} / {tdr}".format(
        name=document.name,
        ncn=document.best_human_identifier,
        tdr=document.consignment_reference,
    )

    editor_html_url = request.build_absolute_uri(
        reverse("full-text-html", kwargs={"document_uri": document.uri}),
    )

    description_string = "{editor_html_url}".format(
        editor_html_url="""{html_url}

{source_name_label}: {source_name}
{source_email_label}: {source_email}
{consignment_ref_label}: {consignment_ref}""".format(
            html_url=editor_html_url,
            source_name_label=gettext("judgments.submitter"),
            source_name=document.source_name,
            source_email_label=gettext("judgments.submitteremail"),
            source_email=document.source_email,
            consignment_ref_label=gettext("judgments.consignmentref"),
            consignment_ref=document.consignment_reference,
        ),
    )

    params = {
        "pid": "10090",
        "issuetype": "10320",
        "priority": "3",
        "summary": summary_string,
        "description": description_string,
    }
    return (
        "https://{jira_instance}/secure/CreateIssueDetails!init.jspa?{params}".format(
            jira_instance=settings.JIRA_INSTANCE,
            params=urlencode(params),
        )
    )
