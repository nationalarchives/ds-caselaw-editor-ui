from unittest.mock import patch

from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import JudgmentFactory


class TestAssociatedDocuments(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_associated_documents_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="associateddocumentstest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        associated_documents_uri = reverse("associated-documents", kwargs={"document_uri": judgment.uri})

        assert associated_documents_uri == "/associateddocumentstest/4321/123/associated-documents"

        response = self.client.get(associated_documents_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Associated documents for" in decoded_response
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200
