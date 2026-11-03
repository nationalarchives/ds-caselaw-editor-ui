from django.test import SimpleTestCase

from judgments.utils.metadata_form_fields import (
    MetadataFormFieldKind,
    form_field_kind_for_metadata_key,
    new_claim_post_name_prefix,
)


class TestMetadataFormFields(SimpleTestCase):
    def test_form_field_kind_for_known_keys(self):
        assert form_field_kind_for_metadata_key("date") is MetadataFormFieldKind.DATE
        assert form_field_kind_for_metadata_key("title") is MetadataFormFieldKind.TEXTAREA

    def test_form_field_kind_defaults_to_text(self):
        assert form_field_kind_for_metadata_key("court") is MetadataFormFieldKind.TEXT

    def test_new_claim_post_name_prefix(self):
        assert new_claim_post_name_prefix("date") == "new_claim__date"
