from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from factories import JudgmentFactory


class TestDocumentEdit(TestCase):
    def test_judgment_edit_view_redirects(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/ewca/civ/2004/63X/edit")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html", kwargs={"document_uri": "ewca/civ/2004/63X"}
        )

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri="edittest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")

        self.client.post(
            "/pubtest/4321/123/edit",
            {
                "judgment_uri": "/edittest/4321/123",
                "metadata_name": "New Name",
                "neutral_citation": "[4321] TEST 123",
                "court": "Court of Testing",
                "judgment_date": "2 Jan 2023",
                "assigned_to": "testuser2",
            },
        )

        api_client.set_document_name.assert_called_with(
            "/edittest/4321/123", "New Name"
        )
        api_client.set_judgment_citation.assert_called_with(
            "/edittest/4321/123", "[4321] TEST 123"
        )
        api_client.set_document_court.assert_called_with(
            "/edittest/4321/123", "Court of Testing"
        )
        api_client.set_judgment_date.assert_called_with(
            "/edittest/4321/123", "2023-01-02"
        )
        api_client.set_property.assert_called_with(
            "/edittest/4321/123", "assigned-to", "testuser2"
        )

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_without_assignment(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri="edittest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")

        self.client.post(
            "/pubtest/4321/123/edit",
            {
                "judgment_uri": "/edittest/4321/123",
                "metadata_name": "New Name",
                "neutral_citation": "[4321] TEST 123",
                "court": "Court of Testing",
                "judgment_date": "02 Jan 2023",
            },
        )

        api_client.set_property.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_date_error(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri="edittest/4321/123",
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
                "neutral_citation": "[4321] TEST 123",
                "court": "Court of Testing",
                "judgment_date": "Kittens",
            },
        )

        messages = [msg for msg in get_messages(response.wsgi_request)]
        assert "Could not parse the date" in messages[0].message
