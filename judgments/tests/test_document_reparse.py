from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import DocumentFactory


class TestDocumentReparse(TestCase):
    def setUp(self):
        self.user = User.objects.get_or_create(username="user")[0]

    @patch("judgments.views.document_reparse.get_document_by_uri_or_404")
    def test_document_reparse_flow(self, mock_document):
        """Posting to the end point doesn't error and calls the right thing"""
        document = DocumentFactory.build(uri="test/4321/123", name="Enrichment Test")
        mock_document.return_value = document

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("reparse"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": document.uri},
        )
        mock_document.return_value.reparse.assert_called_once()
