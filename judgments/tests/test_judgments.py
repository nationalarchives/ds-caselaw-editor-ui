from unittest.mock import patch
from urllib.parse import urlencode

from caselawclient.Client import MarklogicResourceNotFoundError
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestJudgment(TestCase):
    @patch(
        "judgments.models.MarklogicApiClient.get_judgment_citation",
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
        "judgments.models.MarklogicApiClient.get_judgment_citation",
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
