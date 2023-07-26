import re
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import JudgmentFactory


def assert_match(regex, string):
    assert re.search(regex, string) is not None


class TestJudgmentEdit(TestCase):
    @patch("judgments.views.judgment_edit.get_judgment_by_uri_or_404")
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
        self.assertIn(
            '<option value="UKSC">United Kingdom Supreme Court</option>',
            decoded_response,
        )

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_judgment_by_uri_or_404")
    def test_edit_judgment(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri="edittest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")

        self.client.post(
            "/pubtest/4321/123/edit",
            {
                "judgment_uri": "/edittest/4321/123",
                "metadata_name": "New Name",
                "neutral_citation": "[4321] TEST 123",
                "court": "Court of Testing",
                "judgment_date": "2023-01-02",
                "assigned_to": "testuser2",
            },
        )

        api_client.set_judgment_name.assert_called_with(
            "/edittest/4321/123", "New Name"
        )
        api_client.set_judgment_citation.assert_called_with(
            "/edittest/4321/123", "[4321] TEST 123"
        )
        api_client.set_judgment_court.assert_called_with(
            "/edittest/4321/123", "Court of Testing"
        )
        api_client.set_judgment_date.assert_called_with(
            "/edittest/4321/123", "2023-01-02"
        )
        api_client.set_property.assert_called_with(
            "/edittest/4321/123", "assigned-to", "testuser2"
        )

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_judgment_by_uri_or_404")
    def test_edit_judgment_without_assignment(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri="edittest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")

        self.client.post(
            "/pubtest/4321/123/edit",
            {
                "judgment_uri": "/edittest/4321/123",
                "metadata_name": "New Name",
                "neutral_citation": "[4321] TEST 123",
                "court": "Court of Testing",
                "judgment_date": "2023-01-02",
            },
        )

        api_client.set_property.assert_not_called()


class TestJudgmentView(TestCase):
    @patch("judgments.views.full_text.get_judgment_by_uri_or_404")
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

    @patch("judgments.views.full_text.get_judgment_by_uri_or_404")
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
        "judgments.views.full_text.get_judgment_by_uri_or_404",
    )
    def test_judgment_pdf_view_no_pdf_response(self, mock_judgment):
        mock_judgment.return_value.name = "JUDGMENT v JUDGEMENT"
        mock_judgment.return_value.pdf_url = ""
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/test/1234/pdf")
        decoded_response = response.content.decode("utf-8")
        self.assertIn(
            "Document &quot;JUDGMENT v JUDGEMENT&quot; does not have a PDF.",
            decoded_response,
        )
        self.assertEqual(response.status_code, 404)

    def test_judgment_xml_view_redirect(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/xml?judgment_uri=ewca/civ/2004/63X")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-xml", kwargs={"judgment_uri": "ewca/civ/2004/63X"}
        )


class TestJudgmentPublish(TestCase):
    @patch("judgments.views.judgment_publish.get_judgment_by_uri_or_404")
    def test_judgment_publish_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        publish_uri = reverse("publish-judgment", kwargs={"judgment_uri": judgment.uri})

        assert publish_uri == "/pubtest/4321/123/publish"

        response = self.client.get(publish_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200

    @patch("judgments.views.judgment_publish.invalidate_caches")
    @patch("judgments.views.judgment_publish.get_judgment_by_uri_or_404")
    def test_judgment_publish_flow(self, mock_judgment, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Publication Test",
            is_published=False,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("publish"),
            data={
                "judgment_uri": judgment.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "publish-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )
        mock_judgment.return_value.publish.assert_called_once()
        mock_judgment.return_value.unpublish.assert_not_called()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.views.judgment_publish.get_judgment_by_uri_or_404")
    def test_judgment_publish_success_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        publish_success_uri = reverse(
            "publish-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )

        assert publish_success_uri == "/pubtest/4321/123/published"

        response = self.client.get(publish_success_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200


class TestJudgmentHold(TestCase):
    @patch("judgments.views.judgment_hold.get_judgment_by_uri_or_404")
    def test_judgment_hold_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="holdtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        hold_uri = reverse("hold-judgment", kwargs={"judgment_uri": judgment.uri})

        assert hold_uri == "/holdtest/4321/123/hold"

        response = self.client.get(hold_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200

    @patch("judgments.views.judgment_hold.invalidate_caches")
    @patch("judgments.views.judgment_hold.get_judgment_by_uri_or_404")
    def test_judgment_hold_flow(self, mock_judgment, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri="holdtest/4321/123",
            name="Hold Test",
            is_published=False,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("hold"),
            data={
                "judgment_uri": judgment.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "hold-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )
        mock_judgment.return_value.hold.assert_called_once()
        mock_judgment.return_value.unhold.assert_not_called()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.views.judgment_hold.get_judgment_by_uri_or_404")
    def test_judgment_hold_success_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="holdtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        hold_success_uri = reverse(
            "hold-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )

        assert hold_success_uri == "/holdtest/4321/123/onhold"

        response = self.client.get(hold_success_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200


class TestJudgmentUnhold(TestCase):
    @patch("judgments.views.judgment_hold.get_judgment_by_uri_or_404")
    def test_judgment_unhold_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="unholdtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unhold_uri = reverse("unhold-judgment", kwargs={"judgment_uri": judgment.uri})

        assert unhold_uri == "/unholdtest/4321/123/unhold"

        response = self.client.get(unhold_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200

    @patch("judgments.views.judgment_hold.invalidate_caches")
    @patch("judgments.views.judgment_hold.get_judgment_by_uri_or_404")
    def test_judgment_unhold_flow(self, mock_judgment, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri="unholdtest/4321/123",
            name="Unhold Test",
            is_published=False,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("unhold"),
            data={
                "judgment_uri": judgment.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "unhold-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )
        mock_judgment.return_value.unhold.assert_called_once()
        mock_judgment.return_value.hold.assert_not_called()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.views.judgment_hold.get_judgment_by_uri_or_404")
    def test_judgment_hold_success_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="unholdtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unhold_success_uri = reverse(
            "unhold-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )

        assert unhold_success_uri == "/unholdtest/4321/123/unheld"

        response = self.client.get(unhold_success_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200


class TestJudgmentUnpublish(TestCase):
    @patch("judgments.views.judgment_publish.get_judgment_by_uri_or_404")
    def test_judgment_unpublish_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unpublish_uri = reverse(
            "unpublish-judgment", kwargs={"judgment_uri": judgment.uri}
        )

        assert unpublish_uri == "/pubtest/4321/123/unpublish"

        response = self.client.get(unpublish_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200

    @patch("judgments.views.judgment_publish.invalidate_caches")
    @patch("judgments.views.judgment_publish.get_judgment_by_uri_or_404")
    def test_judgment_unpublish_flow(self, mock_judgment, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Publication Test",
            is_published=True,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("unpublish"),
            data={
                "judgment_uri": judgment.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "unpublish-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )
        mock_judgment.return_value.publish.assert_not_called()
        mock_judgment.return_value.unpublish.assert_called_once()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.views.judgment_publish.get_judgment_by_uri_or_404")
    def test_judgment_unpublish_success_view(self, mock_judgment):
        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            name="Test v Tested",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unpublish_success_uri = reverse(
            "unpublish-judgment-success", kwargs={"judgment_uri": judgment.uri}
        )

        assert unpublish_success_uri == "/pubtest/4321/123/unpublished"

        response = self.client.get(unpublish_success_uri)

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Test v Tested", decoded_response)
        assert response.status_code == 200


class TestJudgmentAssign(TestCase):
    @patch("judgments.views.button_handlers.api_client")
    def test_judgment_assigns_to_user(self, api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        User.objects.get_or_create(username="testuser2")
        self.client.post(
            "/assign", {"judgment_uri": "/test/judgment", "assigned_to": "testuser2"}
        )
        api_client.set_property.assert_called_with(
            "/test/judgment", "assigned-to", "testuser2"
        )

    @patch("judgments.views.button_handlers.api_client")
    def test_judgment_assignment_defaults_to_current_user(self, api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        self.client.post("/assign", {"judgment_uri": "/test/judgment"})
        api_client.set_property.assert_called_with(
            "/test/judgment", "assigned-to", "testuser"
        )

    @patch("judgments.views.button_handlers.api_client")
    def test_judgment_assignment_handles_explicit_unassignment(self, api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        self.client.post(
            "/assign", {"judgment_uri": "/test/judgment", "assigned_to": ""}
        )
        api_client.set_property.assert_called_with("/test/judgment", "assigned-to", "")
