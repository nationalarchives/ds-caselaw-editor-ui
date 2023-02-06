import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse

import ds_caselaw_utils as caselawutils
from caselawclient.Client import (
    MarklogicAPIError,
    MarklogicResourceNotFoundError,
    api_client,
)
from django.contrib.auth.models import User

from .aws import copy_assets

VERSION_REGEX = r"(\d+)-(\d+|TDR)"
akn_namespace = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
uk_namespace = {"uk": "https://caselaw.nationalarchives.gov.uk/akn"}


class MoveJudgmentError(Exception):
    pass


class NeutralCitationToUriError(Exception):
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


def get_judgment_root(judgment_xml) -> str:
    try:
        parsed_xml = ET.XML(bytes(judgment_xml, encoding="utf-8"))
        return parsed_xml.tag
    except ET.ParseError:
        return "error"


def update_judgment_uri(old_uri, new_citation):
    new_uri = caselawutils.neutral_url(new_citation.strip())
    if new_uri is None:
        raise NeutralCitationToUriError(
            f"Unable to form new URI for {old_uri} from neutral citation: {new_citation}"
        )

    try:
        api_client.get_judgment_xml(new_uri, show_unpublished=True)
        raise MoveJudgmentError(
            f"The URI {new_uri} generated from {new_citation} already exists, you cannot move this judgment to a"
            f" pre-existing Neutral Citation Number."
        )
    except (MarklogicAPIError, MarklogicResourceNotFoundError):
        try:
            api_client.copy_judgment(old_uri, new_uri)
            set_metadata(old_uri, new_uri)
            copy_assets(old_uri, new_uri)
            api_client.set_judgment_this_uri(new_uri)
        except MarklogicAPIError as e:
            raise MoveJudgmentError(
                f"Failure when attempting to copy judgment from {old_uri} to {new_uri}: {e}"
            )

        try:
            api_client.delete_judgment(old_uri)
        except MarklogicAPIError as e:
            raise MoveJudgmentError(
                f"Failure when attempting to delete judgment from {old_uri}: {e}"
            )

        return new_uri


def set_metadata(old_uri, new_uri):
    source_organisation = api_client.get_property(old_uri, "source-organisation")
    source_name = api_client.get_property(old_uri, "source-name")
    source_email = api_client.get_property(old_uri, "source-email")
    transfer_consignment_reference = api_client.get_property(
        old_uri, "transfer-consignment-reference"
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


def render_versions(decoded_versions):
    versions = [
        {
            "uri": part.text.rstrip(".xml"),
            "version": extract_version(part.text),
        }
        for part in decoded_versions
    ]
    sorted_versions = sorted(versions, key=lambda d: -d["version"])
    return sorted_versions


def extract_version(version_string: str) -> int:
    try:
        return int(re.search(VERSION_REGEX, version_string).group(1))
    except AttributeError:
        return 0


def users_dict():
    users = User.objects.all()
    return [
        {
            "name": u.get_username(),
            "print_name": u.get_full_name() or u.get_username(),
        }
        for u in users
    ]
