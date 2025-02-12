from unittest.mock import Mock, patch

import pytest
from caselawclient.factories import IdentifierResolutionFactory, JudgmentFactory, PressSummaryFactory
from caselawclient.identifier_resolution import IdentifierResolutions
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from caselawclient.types import DocumentIdentifierSlug
from caselawclient.xquery_type_dicts import MarkLogicDocumentURIString
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from judgments.views.judgment_edit import (
    CannotUpdateNCNOfNonJudgment,
    NeutralCitationToUriError,
    SlugAlreadyUsedError,
    update_ncn_of_document,
    verify_slug_not_used,
)


class TestDocumentEdit(TestCase):
    def test_judgment_edit_view_redirects(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/ewca/civ/2004/63X/edit")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": "ewca/civ/2004/63X"},
        )

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    @patch("judgments.utils.aws.boto3")
    def test_edit_judgment_no_ncn_change(self, mock_boto, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )

        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")

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

        api_client.set_document_name.assert_called_with(
            "/edittest/4321/123",
            "New Name",
        )
        api_client.set_document_court_and_jurisdiction.assert_called_with(
            "/edittest/4321/123",
            "Court of Testing",
        )
        api_client.set_judgment_date.assert_called_with(
            "/edittest/4321/123",
            "2023-01-02",
        )

    @patch("judgments.views.judgment_edit.update_ncn_of_document")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    @patch("judgments.utils.aws.boto3")
    def test_edit_judgment_ncn_change(self, mock_boto, mock_judgment, api_client, mock_update_ncn_of_document):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")

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
        mock_update_ncn_of_document.assert_called_once_with(judgment, "[2023] EWCC 456")

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_date_error(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")

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


class TestUpdateNCNOfDocument(TestCase):
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.verify_slug_not_used")
    @patch("judgments.views.judgment_edit.update_document_uri")
    def test_update_ncn_of_document_where_change_is_valid(
        self,
        mock_update_document_uri,
        mock_verify_slug_not_used,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers = Mock()

        update_ncn_of_document(document, "[2025] EWCC 456")

        mock_verify_slug_not_used.assert_called_once_with("ewcc/2025/456")

        document.identifiers.delete_type.assert_called_once_with(NeutralCitationNumber)
        document.identifiers.add.assert_called_once()
        document.save_identifiers.assert_called_once()
        api_client.set_judgment_citation.assert_called_once_with("uksc/4321/123", "[2025] EWCC 456")
        mock_update_document_uri.assert_called_once_with("uksc/4321/123", "ewcc/2025/456")

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.verify_slug_not_used")
    @patch("judgments.views.judgment_edit.update_document_uri")
    def test_update_ncn_of_document_rejects_non_judgment(
        self,
        mock_update_document_uri,
        mock_verify_slug_not_used,
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

        mock_verify_slug_not_used.assert_not_called()
        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()
        mock_update_document_uri.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.verify_slug_not_used")
    @patch("judgments.views.judgment_edit.update_document_uri")
    def test_update_ncn_of_document_rejects_malformed_ncn(
        self,
        mock_update_document_uri,
        mock_verify_slug_not_used,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(NeutralCitationToUriError):
            update_ncn_of_document(document, "TEST-123")

        mock_verify_slug_not_used.assert_not_called()
        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()
        mock_update_document_uri.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.verify_slug_not_used")
    @patch("judgments.views.judgment_edit.update_document_uri")
    def test_update_ncn_of_document_rejects_plausible_but_invalid_ncn(
        self,
        mock_update_document_uri,
        mock_verify_slug_not_used,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(NeutralCitationToUriError):
            update_ncn_of_document(document, "[2023] UKSC 123 (Fam)")

        mock_verify_slug_not_used.assert_not_called()
        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()
        mock_update_document_uri.assert_not_called()


@patch("judgments.views.judgment_edit.api_client")
def test_verify_slug_with_resolutions(api_client):
    api_client.resolve_from_identifier_slug.return_value = IdentifierResolutions(
        [
            IdentifierResolutionFactory.build(
                document_uri=MarkLogicDocumentURIString("/uksc/2024/999.xml"),
                identifier_slug=DocumentURIString("slug"),
            ),
            IdentifierResolutionFactory.build(
                document_uri=MarkLogicDocumentURIString("/uksc/1701/999.xml"),
                identifier_slug=DocumentURIString("slug"),
            ),
        ],
    )

    # but it's not OK if it exists in the list of slugs
    with pytest.raises(SlugAlreadyUsedError):
        verify_slug_not_used(DocumentIdentifierSlug("uksc/1701/999"))

    api_client.resolve_from_identifier_slug.assert_called_with("uksc/1701/999")


@patch("judgments.views.judgment_edit.api_client")
def test_verify_slug_with_no_resolutions(api_client):
    api_client.resolve_from_identifier_slug.return_value = IdentifierResolutions([])
    verify_slug_not_used(DocumentIdentifierSlug("uksc/1701/999"))
    api_client.resolve_from_identifier_slug.assert_called_with("uksc/1701/999")
