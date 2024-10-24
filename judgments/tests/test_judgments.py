from datetime import date
from unittest.mock import patch
from urllib.parse import urlencode

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestJudgmentView(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_judgment_html_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="hvtest/4321/123",
            body=DocumentBodyFactory.build(
                name="Test v Tested",
                xml_string="<akomantoso>This is our test judgment.</akomantoso>",
            ),
        )
        judgment.body.document_date_as_date = date(1999, 10, 31)
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        assert reverse("full-text-html", kwargs={"document_uri": judgment.uri}) == "/hvtest/4321/123"

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert "This is our test judgment." in decoded_response
        assert "31 Oct 1999" in decoded_response
        assert response.status_code == 200

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_judgment_html_view_with_parser_failure(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="hvtest/4321/123",
            body=DocumentBodyFactory.build(xml_string="<error>Error log</error>"),
        )

        assert judgment.body.failed_to_parse

        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        decoded_response = response.content.decode("utf-8")
        assert "This document has failed to parse" in decoded_response

        assert "&lt;error&gt;Error log&lt;/error&gt;" in decoded_response
        assert "<error>Error log</error>" not in decoded_response

        assert response.status_code == 200

    def test_judgment_html_view_redirect(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/detail?judgment_uri=ewca/civ/2004/63X")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": "ewca/civ/2004/63X"},
        )

    def test_judgment_html_view_redirect_with_version(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get(
            "/detail?judgment_uri=ewca/civ/2004/63X&version_uri=ewca/civ/2004/63X_xml_versions/1-376",
        )
        assert response.status_code == 302
        assert response["Location"] == (
            reverse("full-text-html", kwargs={"document_uri": "ewca/civ/2004/63X"})
            + "?"
            + urlencode(
                {
                    "version_uri": "ewca/civ/2004/63X_xml_versions/1-376",
                },
            )
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_judgment_pdf_view_no_pdf_response(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        mock_judgment.return_value.name = "JUDGMENT v JUDGEMENT"
        mock_judgment.return_value.pdf_url = ""
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/test/1234/pdf")
        decoded_response = response.content.decode("utf-8")
        assert "Document &quot;JUDGMENT v JUDGEMENT&quot; does not have a PDF." in decoded_response
        assert response.status_code == 404

    def test_judgment_xml_view_redirect(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/xml?judgment_uri=ewca/civ/2004/63X")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-xml",
            kwargs={"document_uri": "ewca/civ/2004/63X"},
        )
