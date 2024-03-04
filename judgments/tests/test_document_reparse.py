from unittest.mock import patch

import lxml.html
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import DocumentFactory
from waffle.testutils import override_flag


class TestDocumentReparse(TestCase):
    def setUp(self):
        self.user = User.objects.get_or_create(username="user")[0]
        self.admin = User.objects.create_superuser(
            "myuser",
            "myemail@test.com",
            "password",
        )

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

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.view_helpers.get_linked_document_uri")
    def test_document_reparse_button_disabled(
        self,
        mock_linked_document,
        mock_document,
    ):
        """If the flag is set and the user is allowed, they can see the reparse
        button but it is disabled if it can't be reparsed"""
        uri = "test/4321/123"
        document = DocumentFactory.build(uri=uri, name="Enrichment Test")
        mock_document.return_value = document
        document.can_reparse.return_value = False
        self.client.force_login(self.admin)
        with override_flag("reparse", active=True):
            response = self.client.get("/test/4321/123")
        root = lxml.html.fromstring(response.content)
        tag = root.xpath("//input[@name='reparse']")
        assert tag  # the button appears
        assert tag[0].attrib.get("disabled") == "disabled"  # but is disabled

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.view_helpers.get_linked_document_uri")
    def test_document_reparse_button_enabled(self, mock_linked_document, mock_document):
        """If the flag is set and the user is allowed, they can see the reparse
        button and it is enabled if it can be reparsed"""
        uri = "test/4321/123"
        document = DocumentFactory.build(uri=uri, name="Enrichment Test")
        mock_document.return_value = document
        document.can_reparse.return_value = True
        self.client.force_login(self.admin)
        with override_flag("reparse", active=True):
            response = self.client.get("/test/4321/123")
        root = lxml.html.fromstring(response.content)
        tag = root.xpath("//input[@name='reparse']")
        assert tag  # the button appears
        assert tag[0].attrib.get("disabled") is None  # and is enabled
