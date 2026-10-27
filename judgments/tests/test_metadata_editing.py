from unittest.mock import patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents.metadata.fields.field import MetadataStringValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from django.test import TestCase

from judgments.tests.helpers.metadata_claims import judgment_with_title_claim
from judgments.utils.metadata_editing import add_editor_title_claim_if_changed


class TestMetadataEditing(TestCase):
    def test_add_editor_title_claim_if_changed_adds_claim(self):
        judgment = JudgmentFactory.build(
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )

        changed = add_editor_title_claim_if_changed(judgment, "  New Name  ")

        assert changed is True
        title_claims = judgment.metadata_fields.by_name("title")
        assert len(title_claims) == 1
        assert title_claims[0].value == MetadataStringValue("New Name")
        assert title_claims[0].source is MetadataSource.EDITOR

    def test_add_editor_title_claim_if_changed_skips_when_unchanged(self):
        judgment = JudgmentFactory.build(
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )

        with patch.object(judgment.metadata_fields, "add") as mock_add:
            changed = add_editor_title_claim_if_changed(judgment, "Test v Tested")

        assert changed is False
        mock_add.assert_not_called()

    def test_add_editor_title_claim_if_changed_strips_whitespace_before_compare(self):
        judgment = JudgmentFactory.build(
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )

        with patch.object(judgment.metadata_fields, "add") as mock_add:
            changed = add_editor_title_claim_if_changed(judgment, "  Test v Tested  ")

        assert changed is False
        mock_add.assert_not_called()

    def test_add_editor_title_claim_if_changed_ignores_whitespace_only_submission(self):
        judgment = JudgmentFactory.build(
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )

        with patch.object(judgment.metadata_fields, "add") as mock_add:
            changed = add_editor_title_claim_if_changed(judgment, "   ")

        assert changed is False
        mock_add.assert_not_called()

    def test_add_editor_title_claim_if_changed_skips_when_structured_title_unchanged(self):
        judgment = judgment_with_title_claim(
            body_name="Body title from XML",
            title_claim="Resolved structured title",
            source=MetadataSource.DOCUMENT,
        )

        assert judgment.metadata.title.value == "Resolved structured title"
        assert judgment.body.name == "Body title from XML"

        with patch.object(judgment.metadata_fields, "add") as mock_add:
            changed = add_editor_title_claim_if_changed(judgment, "  Resolved structured title  ")

        assert changed is False
        mock_add.assert_not_called()

    def test_add_editor_title_claim_if_changed_appends_claim_without_removing_existing(self):
        judgment = judgment_with_title_claim(
            body_name="Body title from XML",
            title_claim="Resolved structured title",
            source=MetadataSource.DOCUMENT,
        )

        changed = add_editor_title_claim_if_changed(judgment, "Editor updated title")

        assert changed is True
        title_claims = judgment.metadata_fields.by_name("title")
        assert len(title_claims) == 2
        assert title_claims[0].value == MetadataStringValue("Resolved structured title")
        assert title_claims[0].source is MetadataSource.DOCUMENT
        assert title_claims[1].value == MetadataStringValue("Editor updated title")
        assert title_claims[1].source is MetadataSource.EDITOR
