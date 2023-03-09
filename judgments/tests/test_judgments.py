from unittest.mock import patch
from urllib.parse import urlencode

from caselawclient.Client import MarklogicResourceNotFoundError
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import JudgmentFactory


class TestJudgmentEdit(TestCase):
    @patch("judgments.views.edit_judgment.Judgment")
    def test_judgment_edit_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="edtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        assert (
            reverse("edit-judgment", kwargs={"judgment_uri": judgment.uri})
            == "/edtest/4321/123/edit"
        )

        response = self.client.get(
            reverse("edit-judgment", kwargs={"judgment_uri": judgment.uri})
        )

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200

    @patch("judgments.views.edit_judgment.invalidate_caches")
    @patch("judgments.views.edit_judgment.api_client")
    @patch("judgments.views.edit_judgment.Judgment")
    def test_judgment_publish_flow(
        self, mock_judgment, mock_api_client, mock_invalidate_caches
    ):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Publication Test",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("edit-judgment", kwargs={"judgment_uri": judgment.uri}),
            data={
                "judgment_uri": judgment.uri,
                "metadata_name": judgment.name,
                "neutral_citation": judgment.neutral_citation,
                "court": judgment.court,
                "judgment_date": judgment.judgment_date_as_string,
                "assigned_to": judgment.assigned_to,
                "published": "on",
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "edit-judgment", kwargs={"judgment_uri": judgment.uri}
        )
        mock_judgment.return_value.publish.assert_called_once()
        mock_judgment.return_value.unpublish.assert_not_called()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.views.edit_judgment.invalidate_caches")
    @patch("judgments.views.edit_judgment.api_client")
    @patch("judgments.views.edit_judgment.Judgment")
    def test_judgment_unpublish_flow(
        self, mock_judgment, mock_api_client, mock_invalidate_caches
    ):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Publication Test",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("edit-judgment", kwargs={"judgment_uri": judgment.uri}),
            data={
                "judgment_uri": judgment.uri,
                "metadata_name": judgment.name,
                "neutral_citation": judgment.neutral_citation,
                "court": judgment.court,
                "judgment_date": judgment.judgment_date_as_string,
                "assigned_to": judgment.assigned_to,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "edit-judgment", kwargs={"judgment_uri": judgment.uri}
        )
        mock_judgment.return_value.unpublish.assert_called_once()
        mock_judgment.return_value.publish.assert_not_called()
        mock_invalidate_caches.assert_called_once()


class TestJudgmentView(TestCase):
    @patch("judgments.views.full_text.Judgment")
    def test_judgment_html_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="hvtest/4321/123",
            name="Test v Tested",
            html="<h1>Test Judgment</h1>",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        assert (
            reverse("full-text-html", kwargs={"judgment_uri": judgment.uri})
            == "/hvtest/4321/123"
        )

        response = self.client.get(
            reverse("full-text-html", kwargs={"judgment_uri": judgment.uri})
        )

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        self.assertIn("<h1>Test Judgment</h1>", decoded_response)
        assert response.status_code == 200

    @patch("judgments.views.full_text.Judgment")
    def test_judgment_html_view_with_failure(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="hvtest/4321/123",
            html="<h1>Test Judgment</h1>",
            is_failure=True,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"judgment_uri": judgment.uri})
        )

        decoded_response = response.content.decode("utf-8")
        self.assertIn("&lt;h1&gt;Test Judgment&lt;/h1&gt;", decoded_response)
        assert response.status_code == 200

    @patch(
        "judgments.models.judgments.MarklogicApiClient.get_judgment_citation",
        side_effect=MarklogicResourceNotFoundError(),
    )
    def test_judgment_html_view_not_found_response(self, mock_api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/ewca/civ/2004/63X")
        decoded_response = response.content.decode("utf-8")
        self.assertIn("Judgment was not found", decoded_response)
        self.assertEqual(response.status_code, 404)

    def test_judgment_html_view_redirect(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/detail?judgment_uri=ewca/civ/2004/63X")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html", kwargs={"judgment_uri": "ewca/civ/2004/63X"}
        )

    def test_judgment_html_view_redirect_with_version(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get(
            "/detail?judgment_uri=ewca/civ/2004/63X&version_uri=ewca/civ/2004/63X_xml_versions/1-376"
        )
        assert response.status_code == 302
        assert response["Location"] == (
            reverse("full-text-html", kwargs={"judgment_uri": "ewca/civ/2004/63X"})
            + "?"
            + urlencode(
                {
                    "version_uri": "ewca/civ/2004/63X_xml_versions/1-376",
                }
            )
        )

    @patch(
        "judgments.models.judgments.MarklogicApiClient.get_judgment_citation",
        side_effect=MarklogicResourceNotFoundError(),
    )
    def test_judgment_pdf_view_not_found_response(self, mock_api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/test/1234/pdf")
        decoded_response = response.content.decode("utf-8")
        self.assertIn("Judgment was not found", decoded_response)
        self.assertEqual(response.status_code, 404)

    @patch(
        "judgments.views.full_text.Judgment",
    )
    def test_judgment_pdf_view_no_pdf_response(self, mock_judgment):
        mock_judgment.return_value.name = "JUDGMENT v JUDGEMENT"
        mock_judgment.return_value.pdf_url = ""
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/test/1234/pdf")
        decoded_response = response.content.decode("utf-8")
        self.assertIn(
            "Judgment &quot;JUDGMENT v JUDGEMENT&quot; does not have a PDF.",
            decoded_response,
        )
        self.assertEqual(response.status_code, 404)

    @patch(
        "judgments.models.judgments.MarklogicApiClient.get_judgment_citation",
        side_effect=MarklogicResourceNotFoundError(),
    )
    def test_judgment_xml_view_not_found_response(self, mock_api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/ewca/civ/2004/63X/xml")
        decoded_response = response.content.decode("utf-8")
        self.assertIn("Judgment was not found", decoded_response)
        self.assertEqual(response.status_code, 404)

    def test_judgment_xml_view_redirect(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/xml?judgment_uri=ewca/civ/2004/63X")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-xml", kwargs={"judgment_uri": "ewca/civ/2004/63X"}
        )
