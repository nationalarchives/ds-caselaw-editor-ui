from unittest.mock import Mock, patch

import pytest
from caselawclient.factories import JudgmentFactory
from caselawclient.identifier_resolution import IdentifierResolution, IdentifierResolutions
from caselawclient.models.documents import DocumentURIString
from caselawclient.xquery_type_dicts import MarkLogicDocumentURIString
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from judgments.views.judgment_edit import StubAlreadyUsedError, verify_stub_not_used


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
    def test_edit_judgment(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )
        judgment.save_identifiers = Mock()  # type:ignore[method-assign]
        judgment.identifiers = Mock()
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
        api_client.set_judgment_citation.assert_called_with(
            "/edittest/4321/123",
            "[4321] UKSC 123",
        )
        api_client.set_document_court_and_jurisdiction.assert_called_with(
            "/edittest/4321/123",
            "Court of Testing",
        )
        api_client.set_judgment_date.assert_called_with(
            "/edittest/4321/123",
            "2023-01-02",
        )
        assert "NeutralCitationNumber" in str(judgment.identifiers.delete_type.call_args_list[0][0])
        assert "<Neutral Citation Number [4321] UKSC 123:" in str(judgment.identifiers.add.call_args_list[0][0])
        judgment.save_identifiers.assert_called_once_with()

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_date_error(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )
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


@patch("judgments.views.judgment_edit.api_client")
def test_verify_stub_not_used_no_values(api_client):
    api_client.resolve_from_identifer.return_value = []
    verify_stub_not_used("/uksc/2024/999", "[1701] UKSC 999")


@patch("judgments.views.judgment_edit.api_client")
def test_verify_stub_not_used_with_values(api_client):
    api_client.resolve_from_identifier.return_value = IdentifierResolutions(
        [
            IdentifierResolution(
                identifier_uuid="uuid",
                document_uri=MarkLogicDocumentURIString("uksc/2024/999"),
                identifier_slug=DocumentURIString("slug"),
                document_published=True,
            ),
            IdentifierResolution(
                identifier_uuid="uuid",
                document_uri=MarkLogicDocumentURIString("uksc/1701/999"),
                identifier_slug=DocumentURIString("slug"),
                document_published=True,
            ),
        ],
    )

    # If all Resolutions match either the old or new URI, that's fine
    verify_stub_not_used("uksc/2024/999", "[1701] UKSC 999")

    # but it's not OK if there's one left over which doesn't match
    with pytest.raises(StubAlreadyUsedError):
        verify_stub_not_used("uksc/2024/999", "[2024] UKSC 999")
    with pytest.raises(StubAlreadyUsedError):
        verify_stub_not_used("uksc/1701/999", "[1701] UKSC 999")
