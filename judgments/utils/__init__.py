from __future__ import annotations

import re
from datetime import datetime
from operator import itemgetter
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from caselawclient.Client import DEFAULT_USER_AGENT, MarklogicApiClient
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.press_summaries import PressSummary
from django.conf import settings
from django.contrib.auth.models import Group, User

api_client = MarklogicApiClient(
    host=settings.MARKLOGIC_HOST,
    username=settings.MARKLOGIC_USER,
    password=settings.MARKLOGIC_PASSWORD,
    use_https=settings.MARKLOGIC_USE_HTTPS,
    user_agent=f"ds-caselaw-editor/unknown {DEFAULT_USER_AGENT}",
)
if TYPE_CHECKING:
    from caselawclient.models.documents import Document

VERSION_REGEX = r"xml_versions/(\d{1,10})-(\d{1,10}|TDR)"
# Here we limit the number of digits in the version and document reference to 10 on purpose, see
# https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS for an explanation of why.

akn_namespace = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
uk_namespace = {"uk": "https://caselaw.nationalarchives.gov.uk/akn"}


class MoveJudgmentError(Exception):
    pass


def is_url_relative(url):
    return not bool(urlparse(url).netloc)


def ensure_local_referer_url(request, default="/"):
    """
    Make sure that we do not redirect the user to a website we do not control.
    In future we should explicitly specify a return URL in the POST data when clicking a button,
    rather than parsing the HTTP_REFERER header.
    """
    referer = request.META.get("HTTP_REFERER")
    if referer:
        parsed = urlparse(referer)
        is_url_local = parsed.netloc in ["", request.get_host()]
        if is_url_local:
            return referer
    return default


def format_date(date):
    if date == "" or date is None:
        return None

    time = datetime.strptime(date, "%Y-%m-%d")
    return time.strftime("%d-%m-%Y")


def set_metadata(old_uri, new_uri):
    source_organisation = api_client.get_property(old_uri, "source-organisation")
    source_name = api_client.get_property(old_uri, "source-name")
    source_email = api_client.get_property(old_uri, "source-email")
    transfer_consignment_reference = api_client.get_property(
        old_uri,
        "transfer-consignment-reference",
    )
    transfer_received_at = api_client.get_property(old_uri, "transfer-received-at")
    for key, value in [
        ("source-organisation", source_organisation),
        ("source-name", source_name),
        ("source-email", source_email),
        ("transfer-consignment-reference", transfer_consignment_reference),
        ("transfer-received-at", transfer_received_at),
    ]:
        if value is not None:
            api_client.set_property(new_uri, key, value)

    """
    `published` is a boolean property and set differently, technically
    these failures should be unpublished but copy the property just in case.
    """
    published = api_client.get_published(old_uri)
    api_client.set_boolean_property(new_uri, "published", bool(published))


def extract_version_number_from_filename(version_string: str) -> int:
    result = re.search(VERSION_REGEX, version_string)
    return int(result.group(1)) if result else 0


def editors_dict():
    if settings.EDITORS_GROUP_ID:
        editors_group = Group.objects.get(id=settings.EDITORS_GROUP_ID)
        editors = editors_group.user_set.filter(is_active=True)
    else:
        editors = User.objects.filter(is_active=True)

    return sorted(
        [
            {
                "name": editor.get_username(),
                "print_name": editor.get_full_name() or editor.get_username(),
            }
            for editor in editors
        ],
        key=itemgetter("print_name"),
    )


def get_linked_document_uri(document: Document) -> str | None:
    related_uri = _build_related_document_uri(document)
    return related_uri if api_client.document_exists(DocumentURIString(related_uri)) else None


def _build_related_document_uri(document: Document) -> str:
    press_summary_suffix = "/press-summary/1"
    if isinstance(document, PressSummary):
        return document.uri.removesuffix(press_summary_suffix)
    return document.uri + press_summary_suffix
