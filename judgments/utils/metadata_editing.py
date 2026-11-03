from datetime import date

from caselawclient.models.documents import Document
from caselawclient.models.documents.metadata.fields.field import MetadataDateValue, MetadataField, MetadataStringValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource


def add_editor_title_claim_if_changed(document: Document, submitted_title: str) -> bool:
    cleaned_title = submitted_title.strip()
    if not cleaned_title:
        return False

    current_title = document.metadata.title.value
    if current_title == cleaned_title:
        return False

    document.metadata_fields.add(
        MetadataField(
            name="title",
            value=MetadataStringValue(cleaned_title),
            source=MetadataSource.EDITOR,
        ),
    )
    return True


def save_judgment_title_from_document_form(document: Document, form_value: str) -> None:
    if add_editor_title_claim_if_changed(document, form_value):
        document.save_metadata_fields()


def add_editor_date_claim_if_changed(document: Document, submitted_date: date) -> bool:
    current_date = document.metadata.date.value
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


def save_judgment_date_from_document_form(document: Document, submitted_date: date) -> None:
    if add_editor_date_claim_if_changed(document, submitted_date):
        document.save_metadata_fields()
