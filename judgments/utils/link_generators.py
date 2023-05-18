from typing import Optional
from urllib.parse import quote, urlencode

from caselawclient.models.judgments import Judgment
from django.conf import settings
from django.http import HttpRequest
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext


def build_email_link_with_content(
    address: str, subject: str, body: Optional[str] = None
) -> str:
    """Given a destination address, subject, and (optionally) body for an email build a mailto link for it."""
    params = {"subject": "Find Case Law – {subject}".format(subject=subject)}

    if body:
        params["body"] = body

    return "mailto:{address}?{params}".format(
        address=address, params=urlencode(params, quote_via=quote)
    )


def build_confirmation_email_link(
    judgment: Judgment, signature: Optional[str] = None
) -> str:
    subject_string = "Notification of publication [TDR ref: {reference}]".format(
        reference=judgment.consignment_reference
    )

    email_context = {
        "judgment_name": judgment.name,
        "reference": judgment.consignment_reference,
        "public_judgment_url": judgment.public_uri,
        "user_signature": signature or "XXXXXX",
    }

    body_string = loader.render_to_string(
        "emails/confirmation_to_submitter.txt", email_context
    )

    return build_email_link_with_content(
        judgment.source_email, subject_string, body_string
    )


def build_raise_issue_email_link(
    judgment: Judgment, signature: Optional[str] = None
) -> str:
    subject_string = "Issue(s) found with {reference}".format(
        reference=judgment.consignment_reference
    )

    return build_email_link_with_content(judgment.source_email, subject_string)


def build_jira_create_link(judgment: Judgment, request: HttpRequest) -> str:
    summary_string = "{name} / {ncn} / {tdr}".format(
        name=judgment.name,
        ncn=judgment.neutral_citation,
        tdr=judgment.consignment_reference,
    )

    editor_html_url = request.build_absolute_uri(
        reverse("full-text-html", kwargs={"judgment_uri": judgment.uri})
    )

    description_string = "{editor_html_url}".format(
        editor_html_url="""{html_url}

{source_name_label}: {source_name}
{source_email_label}: {source_email}
{consignment_ref_label}: {consignment_ref}""".format(
            html_url=editor_html_url,
            source_name_label=gettext("judgments.submitter"),
            source_name=judgment.source_name,
            source_email_label=gettext("judgments.submitteremail"),
            source_email=judgment.source_email,
            consignment_ref_label=gettext("judgments.consignmentref"),
            consignment_ref=judgment.consignment_reference,
        )
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
            jira_instance=settings.JIRA_INSTANCE, params=urlencode(params)
        )
    )
