import datetime
from datetime import date

from caselawclient.models.documents import Document
from caselawclient.models.documents.metadata.fields.field import MetadataDateValue, MetadataField
from caselawclient.models.documents.metadata.fields.source import MetadataSource

JUDGMENT_DATE_FORM_FORMAT = "%d %b %Y"


def parse_judgment_date_form_value(value: str) -> date:
    return datetime.datetime.strptime(value, JUDGMENT_DATE_FORM_FORMAT).date()


def save_judgment_date_from_preview_form(document: Document, form_value: str) -> None:
    """Persist a judgment date from the preview form when it differs from resolved metadata.

    Raises ValueError when the form value is not a valid judgment date.
    """
    submitted_date = parse_judgment_date_form_value(form_value)
    if add_editor_date_claim_if_changed(document, submitted_date):
        document.save_metadata_fields()


def add_editor_date_claim_if_changed(document: Document, submitted_date: date) -> bool:
    current_date = document.metadata["date"].value
    if current_date == submitted_date:
        return False

    document.metadata_fields.add(
        MetadataField(
            name="date",
            value=MetadataDateValue(submitted_date),
            source=MetadataSource.EDITOR,
        ),
    )
    return True
