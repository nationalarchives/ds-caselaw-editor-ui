from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestDocumentEnrich(TestCase):
    def setUp(self):
        self.user = User.objects.get_or_create(username="user")[0]

    @patch("judgments.views.enrich.get_document_by_uri_or_404")
    def test_document_enrich_flow(self, mock_document):
        document = Mock()
        document.uri = "a uri"
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
