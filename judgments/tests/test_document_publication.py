from unittest.mock import Mock, patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestJudgmentPublish(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_publish_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        publish_uri = reverse("publish-document", kwargs={"document_uri": judgment.uri})

        assert publish_uri == "/pubtest/4321/123/publish"

        response = self.client.get(publish_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.judgment_publish.invalidate_caches")
    @patch("judgments.views.judgment_publish.get_document_by_uri_or_404")
    def test_document_publish_flow(
        self,
        mock_judgment,
        mock_invalidate_caches,
    ):
        judgment = Mock()
        judgment.uri = "pubtest/4321/123"
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
            "publish-document-success",
            kwargs={"document_uri": judgment.uri},
        )
        mock_judgment.return_value.publish.assert_called_once()
        mock_judgment.return_value.unpublish.assert_not_called()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_publish_success_view(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        publish_success_uri = reverse(
            "publish-document-success",
            kwargs={"document_uri": judgment.uri},
        )

        assert publish_success_uri == "/pubtest/4321/123/published"

        response = self.client.get(publish_success_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200


class TestJudgmentUnpublish(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_unpublish_view(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unpublish_uri = reverse(
            "unpublish-document",
            kwargs={"document_uri": judgment.uri},
        )

        assert unpublish_uri == "/pubtest/4321/123/unpublish"

        response = self.client.get(unpublish_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.judgment_publish.invalidate_caches")
    @patch("judgments.views.judgment_publish.get_document_by_uri_or_404")
    def test_document_unpublish_flow(self, mock_judgment, mock_invalidate_caches):
        judgment = Mock()
        judgment.uri = "pubtest/4321/123"
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
            "unpublish-document-success",
            kwargs={"document_uri": judgment.uri},
        )
        mock_judgment.return_value.publish.assert_not_called()
        mock_judgment.return_value.unpublish.assert_called_once()
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_unpublish_success_view(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri="pubtest/4321/123",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        unpublish_success_uri = reverse(
            "unpublish-document-success",
            kwargs={"document_uri": judgment.uri},
        )

        assert unpublish_success_uri == "/pubtest/4321/123/unpublished"

        response = self.client.get(unpublish_success_uri)

        decoded_response = response.content.decode("utf-8")
        assert "Test v Tested" in decoded_response
        assert response.status_code == 200
