from unittest.mock import patch

from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import JudgmentFactory


class TestDocumentHistory(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_history_view(self, document_type, document_exists, mock_document):
        document_type.return_value = Judgment
        document_exists.return_value = None

        document = JudgmentFactory.build(
            uri="edtest/4321/123",
            name="Test v Tested",
        )
        mock_document.return_value = document

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        assert (
            reverse("document-history", kwargs={"document_uri": document.uri})
            == "/edtest/4321/123/history"
        )

        response = self.client.get(
            reverse("document-history", kwargs={"document_uri": document.uri}),
        )

        assert response.status_code == 200

        decoded_response = response.content.decode("utf-8")
        dt = document.versions_as_documents[0].get_latest_manifestation_datetime

        assert "Version 1" in decoded_response
        assert dt.strftime("%d %b %Y") in decoded_response
        assert dt.strftime("%H:%M") in decoded_response
        assert "Submission" in decoded_response
