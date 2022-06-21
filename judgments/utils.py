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

    try:
        api_client.copy_judgment(old_uri, new_uri)
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
