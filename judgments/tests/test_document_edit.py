from unittest.mock import patch

import lxml.html
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
            "full-text-html",
            kwargs={"document_uri": "ewca/civ/2004/63X"},
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
            },
        )

        api_client.set_document_name.assert_called_with(
            "/edittest/4321/123",
            "New Name",
        )
        api_client.set_judgment_citation.assert_called_with(
            "/edittest/4321/123",
            "[4321] TEST 123",
        )
        api_client.set_document_court_and_jurisdiction.assert_called_with(
            "/edittest/4321/123",
            "Court of Testing",
        )
        api_client.set_judgment_date.assert_called_with(
            "/edittest/4321/123",
            "2023-01-02",
        )

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

        messages = list(get_messages(response.wsgi_request))
        assert "Could not parse the date" in messages[0].message


class TestDocumentBadURIWarning(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.view_helpers.get_linked_document_uri")
    def test_bad_ncn_has_banner(self, linked_document_uri, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="uksc/1234/123",
            neutral_citation="[1234] UKSC 321",
            best_human_identifier="[1234] UKSC 321",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            "/uksc/1234/123",
        )

        root = lxml.html.fromstring(response.content)
        message = lxml.html.tostring(root.xpath("//div[@class='page-notification--warning']")[0])
        assert b'This document is at uksc/1234/123 but has an NCN of <a href="/uksc/1234/321">' in message
        assert b'<input type="hidden" name="judgment_uri" value="uksc/1234/123">' in message

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.update_document_uri")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_update_uri_called(self, mock_judgment, update_document_uri, api_client):
        judgment = JudgmentFactory.build(
            uri="uksc/4321/123",
            name="Test v Tested",
            neutral_citation="[1234] UKSC 321",
            best_human_identifier="[1234] UKSC 321",
        )
        judgment.document_noun = "judgment"

        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        self.client.post(
            "/uksc/4321/123/edit",
            {
                "move_document": "yes",
                "judgment_uri": "uksc/4321/123",
            },
        )

        update_document_uri.assert_called_with("uksc/4321/123", "[1234] UKSC 321")

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.update_document_uri")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_update_uri_not_called_for_press_summary(self, mock_judgment, update_document_uri, api_client):
        judgment = JudgmentFactory.build(
            uri="uksc/4321/123",
            name="Test v Tested",
            neutral_citation="[1234] UKSC 321",
            best_human_identifier="[1234] UKSC 321",
        )
        judgment.document_noun = "press-summary"

        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            "/uksc/4321/123/edit",
            {
                "move_document": "yes",
                "judgment_uri": "uksc/4321/123",
            },
        )

        update_document_uri.assert_not_called()
        messages = list(get_messages(response.wsgi_request))
        assert "Unable to move non-judgments at this time" in messages[0].message
