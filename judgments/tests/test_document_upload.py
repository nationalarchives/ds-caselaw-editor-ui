from unittest.mock import patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase


class TestUploadView(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists", return_value=None)
    @patch("judgments.utils.api_client.get_document_type_from_uri", return_value=Judgment)
    def test_judgment_upload_view(self, doc_type, exists, mock_doc):
        uri = "d-a1b2c3"
        document = JudgmentFactory.build(
            uri=DocumentURIString(uri),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_doc.return_value = document
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/d-a1b2c3/upload")
        mock_doc.assert_called_once_with("d-a1b2c3")
        decoded_response = response.content.decode("utf-8")
        assert "Upload a document against:" in decoded_response
        assert "Test v Tested" in decoded_response
        assert "It will be uploaded to d-a1b2c3/d-a1b2c3.pdf" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.upload.get_document_by_uri_or_404")
    @patch("judgments.views.upload.upload_asset_to_private_bucket")
    def test_judgment_upload_post(self, mock_upload, mock_doc):
        document = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_doc.return_value = document
        pdf = SimpleUploadedFile("file.pdf", b"%PDF-1.7", content_type="application/pdf")
        superuser = User.objects.create_superuser(username="clark")
        self.client.force_login(superuser)

        _response = self.client.post("/upload", {"file": pdf, "judgment_uri": "d-a1b2c3"})
        mock_doc.assert_called_once_with("d-a1b2c3")
        mock_upload.assert_called_once_with(body=b"%PDF-1.7", s3_key="d-a1b2c3/d-a1b2c3.pdf")

    @patch("judgments.views.upload.get_document_by_uri_or_404")
    @patch("judgments.views.upload.upload_asset_to_private_bucket")
    def test_judgment_upload_not_pdf(self, mock_upload, mock_doc):
        document = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_doc.return_value = document
        # if the document does not have the magic PDF bytes
        not_pdf = SimpleUploadedFile("file.pdf", b"not-a-pdf", content_type="application/pdf")
        superuser = User.objects.create_superuser(username="clark")
        self.client.force_login(superuser)

        response = self.client.post("/upload", {"file": not_pdf, "judgment_uri": "d-a1b2c3"})
        # user is redirected back to the upload page
        assert response.url == "/d-a1b2c3/upload"
        mock_doc.assert_called_once_with("d-a1b2c3")
        # and file is not uploaded
        mock_upload.assert_not_called()
