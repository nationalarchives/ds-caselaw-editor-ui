from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode

from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from django.conf import settings
from django.template import loader
from django.urls import reverse

if TYPE_CHECKING:
    from caselawclient.models.documents import Document
    from django.http import HttpRequest


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
    subject_string = f"Notification of publication [TDR ref: {document.consignment_reference}]"

    email_context = {
        "judgment_name": document.body.name,
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
        "judgment_name": document.body.name,
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
    summary_string = f"{document.body.name} / {document.consignment_reference}"

    editor_html_url = request.build_absolute_uri(
        reverse("full-text-html", kwargs={"document_uri": document.uri}),
    )

    description_string = "{editor_html_url}".format(
        editor_html_url="""{html_url}

NCN: {preferred_ncn}

{source_name_label}: {source_name}
{source_email_label}: {source_email}
{consignment_ref_label}: {consignment_ref}""".format(
            html_url=editor_html_url,
            preferred_ncn=document.identifiers.preferred(type=NeutralCitationNumber),
            source_name_label="Submitter",
            source_name=document.source_name,
            source_email_label="Contact email",
            source_email=document.source_email,
            consignment_ref_label="TDR ref",
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
    return f"https://{settings.JIRA_INSTANCE}/secure/CreateIssueDetails!init.jspa?{urlencode(params)}"
