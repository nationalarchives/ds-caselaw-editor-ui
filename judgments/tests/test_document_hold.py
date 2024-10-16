from unittest.mock import Mock, patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestDocumentHold(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_hold_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="holdtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        hold_uri = reverse("hold-document", kwargs={"document_uri": judgment.uri})

        assert hold_uri == "/holdtest/4321/123/hold"

        response = self.client.get(hold_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.judgment_hold.invalidate_caches")
    @patch("judgments.views.judgment_hold.get_document_by_uri_or_404")
    def test_document_hold_flow(self, mock_judgment, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri="holdtest/4321/123",
            body=DocumentBodyFactory.build(name="Hold Test"),
            is_published=False,
        )
        judgment.hold = Mock()  # type: ignore[method-assign]
        judgment.unhold = Mock()  # type: ignore[method-assign]
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
            "hold-document-success",
            kwargs={"document_uri": judgment.uri},
        )
        mock_judgment.return_value.hold.assert_called_once()
        mock_judgment.return_value.unhold.assert_not_called()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_hold_success_view(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="holdtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        hold_success_uri = reverse(
            "hold-document-success",
            kwargs={"document_uri": judgment.uri},
        )

        assert hold_success_uri == "/holdtest/4321/123/onhold"

        response = self.client.get(hold_success_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200


class TestJudgmentUnhold(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_unhold_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="unholdtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unhold_uri = reverse("unhold-document", kwargs={"document_uri": judgment.uri})

        assert unhold_uri == "/unholdtest/4321/123/unhold"

        response = self.client.get(unhold_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.judgment_hold.invalidate_caches")
    @patch("judgments.views.judgment_hold.get_document_by_uri_or_404")
    def test_document_unhold_flow(self, mock_judgment, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri="unholdtest/4321/123",
            body=DocumentBodyFactory.build(name="Unhold Test"),
            is_published=False,
        )
        judgment.unhold = Mock()
        judgment.hold = Mock()
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
            "unhold-document-success",
            kwargs={"document_uri": judgment.uri},
        )
        mock_judgment.return_value.unhold.assert_called_once()
        mock_judgment.return_value.hold.assert_not_called()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_hold_success_view(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="unholdtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unhold_success_uri = reverse(
            "unhold-document-success",
            kwargs={"document_uri": judgment.uri},
        )

        assert unhold_success_uri == "/unholdtest/4321/123/unheld"

        response = self.client.get(unhold_success_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200
