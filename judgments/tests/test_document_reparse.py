from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from factories import make_editor


class TestDocumentReparse(TestCase):
    def setUp(self):
        self.user = make_editor("user")

    @patch("judgments.views.document_reparse.get_document_by_uri_or_404")
    def test_document_reparse_flow(self, mock_document):
        """Posting to the end point doesn't error and calls the right thing"""
        document = Mock()
        document.uri = "test/4321/123"
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
