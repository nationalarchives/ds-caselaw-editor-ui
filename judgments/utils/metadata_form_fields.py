from enum import StrEnum


class MetadataFormFieldKind(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    DATE = "date"


METADATA_KEY_TO_FORM_FIELD_KIND: dict[str, MetadataFormFieldKind] = {
    "date": MetadataFormFieldKind.DATE,
    "title": MetadataFormFieldKind.TEXTAREA,
}


def form_field_kind_for_metadata_key(key: str) -> MetadataFormFieldKind:
    return METADATA_KEY_TO_FORM_FIELD_KIND.get(key, MetadataFormFieldKind.TEXT)


def new_claim_post_name_prefix(metadata_key: str) -> str:
    return f"new_claim__{metadata_key}"
