from datetime import UTC, datetime
from unittest.mock import patch

from caselawclient.types import DocumentLock, DocumentURIString
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from judgments.views.reports import get_rows_from_result


class TestReportsHelpers(TestCase):
    def test_get_rows_from_result(self):
        assert get_rows_from_result(["header 1", "header 2"]) == []

        assert get_rows_from_result(
            [["header 1", "header 2"], ["value 1", "value 2"]],
        ) == [["value 1", "value 2"]]


class TestReportsIndex(TestCase):
    def test_index_view(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(reverse("reports"))

        decoded_response = response.content.decode("utf-8")
        assert "Reports" in decoded_response
        assert response.status_code == 200


class TestEnrichmentReports(TestCase):
    @patch("judgments.views.reports.api_client")
    def test_awaiting_enrichment_view(self, mock_api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        mock_api_client.get_pending_enrichment_for_version.return_value = [
            ["uri", "enrich_version_string", "minutes_since_enrichment_request"],
            ["/test/123", "1.2.3", 45],
        ]

        response = self.client.get(reverse("report_awaiting_enrichment"))

        decoded_response = response.content.decode("utf-8")
        assert "Documents awaiting enrichment" in decoded_response

        assert "/test/123" in decoded_response
        assert "1.2.3" in decoded_response
        assert "45" in decoded_response

        assert "enrich_version_string" not in decoded_response

        assert response.status_code == 200


class TestReparseReports(TestCase):
    @patch("judgments.views.reports.api_client")
    def test_awaiting_parse_view(self, mock_api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        mock_api_client.get_documents_pending_parse_for_version.return_value = [
            ["uri", "parser_version_string", "minutes_since_parse_request"],
            ["/test/123", "1.2.3", 45],
        ]

        response = self.client.get(reverse("report_awaiting_parse"))

        decoded_response = response.content.decode("utf-8")
        assert "Documents awaiting reparsing" in decoded_response

        assert "/test/123" in decoded_response
        assert "1.2.3" in decoded_response
        assert "45" in decoded_response

        assert "parser_version_string" not in decoded_response

        assert response.status_code == 200


class TestLockedDocumentsReports(TestCase):
    @patch("judgments.views.reports.api_client")
    def test_awaiting_parse_view(self, mock_api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        mock_api_client.get_locked_documents.return_value = [
            DocumentLock(
                document_uri=DocumentURIString("test/1234"),
                owner="Owner string",
                timestamp=datetime(2025, 12, 9, 13, 0, 0, tzinfo=UTC),
                timeout=0,
            ),
        ]

        response = self.client.get(reverse("report_locked_documents"))

        assert response.status_code == 200

        self.assertContains(response, "Locked documents", html=True)
        self.assertContains(response, "test/1234", html=True)
        self.assertContains(response, "Owner string", html=True)
        self.assertContains(response, "9 Dec 2025, 1 p.m.", html=True)
