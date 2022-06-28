import xml.etree.ElementTree as ET
from datetime import datetime

import ds_caselaw_utils as caselawutils
from caselawclient.Client import MarklogicAPIError, api_client


class MoveJudgmentError(Exception):
    pass


class NeutralCitationToUriError(Exception):
    pass


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
    new_uri = caselawutils.neutral_url(new_citation)
    if new_uri is None:
        raise NeutralCitationToUriError(
            f"Unable to form new URI for {old_uri} from neutral citation: {new_citation}"
        )

    existing_judgment = api_client.get_judgment_xml(new_uri, show_unpublished=True)
    if existing_judgment != "":
        raise MoveJudgmentError(
            f"The URI {new_uri} generated from {new_citation} already exists, you cannot move this judgment to a"
            f" pre-existing Neutral Citation Number."
        )

    try:
        api_client.copy_judgment(old_uri, new_uri)
        set_metadata(old_uri, new_uri)
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
    for (key, value) in [
        ("source-organisation", source_organisation),
        ("source-name", source_name),
        ("source-email", source_email),
        ("transfer-consignment_reference", transfer_consignment_reference),
        ("transfer-received-at", transfer_received_at),
    ]:
        if value is not None:
            api_client.set_property(new_uri, key, value)
