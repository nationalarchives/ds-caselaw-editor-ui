from datetime import date
from unittest.mock import patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents.metadata.fields.field import MetadataDateValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from django.test import TestCase

from judgments.utils.metadata_editing import add_editor_date_claim_if_changed, parse_judgment_date_form_value


class TestMetadataEditing(TestCase):
    def test_parse_judgment_date_form_value(self):
        assert parse_judgment_date_form_value("2 Jan 2023") == date(2023, 1, 2)

    def test_add_editor_date_claim_if_changed_adds_claim(self):
        judgment = JudgmentFactory.build(
            body=DocumentBodyFactory.build(document_date_as_string="2024-02-03"),
        )

        changed = add_editor_date_claim_if_changed(judgment, date(2023, 1, 2))

        assert changed is True
        date_claims = judgment.metadata_fields.by_name("date")
        assert len(date_claims) == 1
        assert date_claims[0].value == MetadataDateValue(date(2023, 1, 2))
        assert date_claims[0].source is MetadataSource.EDITOR

    def test_add_editor_date_claim_if_changed_skips_when_unchanged(self):
        judgment = JudgmentFactory.build(
            body=DocumentBodyFactory.build(document_date_as_string="2023-01-02"),
        )

        with patch.object(judgment.metadata_fields, "add") as mock_add:
            changed = add_editor_date_claim_if_changed(judgment, date(2023, 1, 2))

        assert changed is False
        mock_add.assert_not_called()
