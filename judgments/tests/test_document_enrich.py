from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse


class TestDocumentEnrich(TestCase):
    def setUp(self):
        self.user = User.objects.get_or_create(username="user")[0]

    @patch("judgments.views.enrich.get_document_by_uri_or_404")
    def test_document_enrich_failure(self, mock_document):
        document = Mock()
        document.uri = "a uri"
        document.enrich.return_value = False
        mock_document.return_value = document

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("enrich"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": document.uri},
        )
        mock_document.return_value.enrich.assert_called_once()

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert str(messages[0]) == f"Enrichment request failed for {document.body.name}."

    @patch("judgments.views.enrich.get_document_by_uri_or_404")
    def test_document_enrich_success(self, mock_document):
        document = Mock()
        document.uri = "a uri"
        document.enrich.return_value = True
        mock_document.return_value = document

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("enrich"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": document.uri},
        )
        mock_document.return_value.enrich.assert_called_once()

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert str(messages[0]) == f"Enrichment requested for {document.body.name}."
