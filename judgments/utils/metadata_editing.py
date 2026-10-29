from caselawclient.models.documents import Document
from caselawclient.models.documents.metadata.fields.field import MetadataField, MetadataStringValue
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
