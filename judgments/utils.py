import xml.etree.ElementTree as ET
from datetime import datetime


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
