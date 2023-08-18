import re
from unittest.mock import patch

from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from judgments.tests.factories import JudgmentFactory


class TestDocumentToolbar(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    @patch("django.template.context_processors.get_token")
    def test_delete_button_when_failure(
        self, mock_get_token, document_type, document_exists, mock_judgment
    ):
        mock_get_token.return_value = "predicabletoken"
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="failures/TDR-ref",
            is_failure=True,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri})
        )

        decoded_response = response.content.decode("utf-8")
        delete_button_html = """
        <form action="/delete" method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="predicabletoken">
            <input type="hidden" name="judgment_uri" value="failures/TDR-ref" />
            <input type="submit"
            name="assign"
            class="button-secondary judgment-toolbar__delete"
            value="Delete" />
        </form>
        """
        self.assertIn(
            self.preprocess_html(delete_button_html),
            self.preprocess_html(decoded_response),
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    @patch("django.template.context_processors.get_token")
    def test_no_delete_button_when_not_failure(
        self, mock_get_token, document_type, document_exists, mock_judgment
    ):
        mock_get_token.return_value = "predicabletoken"
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="good-document",
            is_failure=False,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri})
        )

        decoded_response = response.content.decode("utf-8")
        delete_button_html = """
        <form action="/delete" method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="predicabletoken">
            <input type="hidden" name="judgment_uri" value="good-document" />
            <input type="submit"
            name="assign"
            class="button-secondary judgment-toolbar__delete"
            value="Delete" />
        </form>
        """
        self.assertNotIn(
            self.preprocess_html(delete_button_html),
            self.preprocess_html(decoded_response),
        )

    def preprocess_html(self, html):
        """Removes leading and trailing whitespace, tabs, and line breaks"""
        cleaned_html = re.sub(r"\s+", " ", html).strip()
        return cleaned_html
