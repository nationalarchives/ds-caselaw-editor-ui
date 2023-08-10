from unittest.mock import patch

from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import JudgmentFactory


class TestDocumentDelete(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_delete_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        document = JudgmentFactory.build(
            uri="deltest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = document

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        delete_uri = reverse("delete-document", kwargs={"document_uri": document.uri})

        assert delete_uri == "/deltest/4321/123/delete"

        response = self.client.get(delete_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Delete this", decoded_response)
        assert response.status_code == 200

    @patch("judgments.views.document_delete.invalidate_caches")
    @patch("judgments.views.document_delete.get_document_by_uri_or_404")
    def test_document_delete_flow_if_safe(self, mock_document, mock_invalidate_caches):
        document = JudgmentFactory.build(
            uri="deltest/4321/123",
            name="Hold Test",
            is_published=False,
        )
        mock_document.return_value = document
        mock_document.return_value.safe_to_delete = True

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("delete"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse("home")
        mock_document.return_value.delete.assert_called_once()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.views.document_delete.invalidate_caches")
    @patch("judgments.views.document_delete.get_document_by_uri_or_404")
    def test_document_delete_flow_if_not_safe(
        self, mock_document, mock_invalidate_caches
    ):
        document = JudgmentFactory.build(
            uri="deltest/4321/123",
            name="Hold Test",
            is_published=True,
        )
        mock_document.return_value = document
        mock_document.return_value.safe_to_delete = False

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("delete"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 403
        mock_document.return_value.delete.assert_not_called()
        mock_invalidate_caches.assert_not_called()
