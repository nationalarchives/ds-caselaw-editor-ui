from unittest.mock import Mock, patch

import pytest
from caselawclient.errors import MarklogicAPIError
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory, PressSummaryFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import MetadataStringValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.identifiers.neutral_citation import (
    NCNCannotConvertToValidURLSlugException,
    NCNDoesNotMatchExpectedPatternException,
    NeutralCitationNumber,
)
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from editing import editing_order, record, tracking_editing_session
from factories import make_editor

from judgments.tests.helpers.metadata_claims import judgment_with_title_claim
from judgments.views.judgment_edit import CannotUpdateNCNOfNonJudgment, update_ncn_of_document


class TestDocumentEdit(TestCase):
    def test_judgment_edit_view_redirects(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/ewca/civ/2004/63X/edit")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": "ewca/civ/2004/63X"},
        )

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    @patch("judgments.utils.aws.boto3")
    def test_edit_judgment_no_ncn_change(self, mock_boto, mock_judgment, api_client, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )

        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())
        User.objects.get_or_create(username="testuser2")

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "judgment_date": "2 Jan 2023",
                },
            )

        api_client.set_document_name.assert_not_called()

        title_claims = judgment.metadata_fields.by_name("title")
        assert title_claims[0].value == MetadataStringValue("New Name")
        assert title_claims[0].source is MetadataSource.EDITOR

        api_client.set_document_court_and_jurisdiction.assert_called_with(
            "/edittest/4321/123",
            "Court of Testing",
        )
        api_client.set_judgment_date.assert_called_with(
            "/edittest/4321/123",
            "2023-01-02",
        )

        assert order == [
            "editing_session",
            "save_metadata_fields",
            "set_court",
            "set_judgment_date",
            "editing_session_end",
        ]
        mock_invalidate_caches.assert_called_once_with(judgment.uri)

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_does_not_invalidate_cache_when_api_save_fails(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )

        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()

        def fail_to_save_metadata(*args, **kwargs):
            order.append("save_metadata_fields")
            message = "Failed to save"
            raise MarklogicAPIError(message)

        judgment.save_metadata_fields = fail_to_save_metadata  # type:ignore[method-assign]

        self.client.force_login(make_editor())

        with patch.object(judgment, "editing_session", tracking_editing_session(order)):
            response = self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "judgment_date": "2 Jan 2023",
                },
            )

        messages = list(get_messages(response.wsgi_request))

        assert "There was an error saving the Document" in messages[0].message
        assert order == ["editing_session", "save_metadata_fields"]
        mock_invalidate_caches.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    @patch("judgments.utils.aws.boto3")
    def test_edit_judgment_ncn_change(self, mock_boto, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_judgment_citation.side_effect = record(order, "set_judgment_citation")
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())
        User.objects.get_or_create(username="testuser2")

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_identifiers", side_effect=record(order, "save_identifiers")),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/uksc/4321/123/edit",
                {
                    "judgment_uri": "/uksc/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[2023] EWCC 456",
                    "court": "Court of Testing",
                    "judgment_date": "2 Jan 2023",
                },
            )
        api_client.set_judgment_citation.assert_called_once_with("uksc/4321/123", "[2023] EWCC 456")
        assert order == [
            "editing_session",
            "save_identifiers",
            "set_judgment_citation",
            "save_metadata_fields",
            "set_court",
            "set_judgment_date",
            "editing_session_end",
        ]

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_date_error(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")

        self.client.force_login(make_editor())
        User.objects.get_or_create(username="testuser2")

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            response = self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "judgment_date": "Kittens",
                },
            )

        messages = list(get_messages(response.wsgi_request))
        assert "Could not parse the date" in messages[0].message
        assert order == ["editing_session", "save_metadata_fields", "set_court", "editing_session_end"]
        api_client.set_judgment_date.assert_not_called()

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_skips_metadata_save_when_title_unchanged(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "Test v Tested",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "judgment_date": "2 Jan 2023",
                },
            )

        assert "save_metadata_fields" not in order
        assert judgment.metadata_fields.by_name("title") == []

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_skips_metadata_save_when_structured_title_unchanged(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = judgment_with_title_claim(
            body_name="Body title from XML",
            title_claim="Resolved structured title",
            source=MetadataSource.DOCUMENT,
            uri=DocumentURIString("edittest/4321/123"),
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "Resolved structured title",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "judgment_date": "2 Jan 2023",
                },
            )

        assert "save_metadata_fields" not in order
        assert len(judgment.metadata_fields.by_name("title")) == 1

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_appends_title_claim_when_structured_title_changes(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = judgment_with_title_claim(
            body_name="Body title from XML",
            title_claim="Resolved structured title",
            source=MetadataSource.DOCUMENT,
            uri=DocumentURIString("edittest/4321/123"),
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "Editor updated title",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "judgment_date": "2 Jan 2023",
                },
            )

        title_claims = judgment.metadata_fields.by_name("title")
        assert len(title_claims) == 2
        assert title_claims[0].value == MetadataStringValue("Resolved structured title")
        assert title_claims[1].value == MetadataStringValue("Editor updated title")
        assert title_claims[1].source is MetadataSource.EDITOR
        assert order == [
            "editing_session",
            "save_metadata_fields",
            "set_court",
            "set_judgment_date",
            "editing_session_end",
        ]


class TestUpdateNCNOfDocument(TestCase):
    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_where_change_is_valid(
        self,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers = Mock()

        update_ncn_of_document(document, "[2025] EWCC 456")

        document.identifiers.delete_type.assert_called_once_with(NeutralCitationNumber)
        document.identifiers.add.assert_called_once()
        document.save_identifiers.assert_called_once()
        api_client.set_judgment_citation.assert_called_once_with("uksc/4321/123", "[2025] EWCC 456")

    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_rejects_non_judgment(
        self,
        api_client,
    ):
        document = PressSummaryFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(CannotUpdateNCNOfNonJudgment):
            update_ncn_of_document(document, "[2025] EWCC 456")

        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_rejects_malformed_ncn(
        self,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(NCNDoesNotMatchExpectedPatternException):
            update_ncn_of_document(document, "TEST-123")

        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_rejects_plausible_but_invalid_ncn(
        self,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(NCNCannotConvertToValidURLSlugException):
            update_ncn_of_document(document, "[2023] UKSC 123 (Fam)")

        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()
