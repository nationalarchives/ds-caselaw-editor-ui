import re
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext
from factories import SearchResultFactory, SearchResultMetadataFactory


def assert_match(regex, string):
    assert re.search(regex, string) is not None


class TestJudgmentView(TestCase):
    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_judgment_list_smoketest(self, mock_search_results):
        mock_search_results.return_value.results = []
        mock_search_results.return_value.total = 0

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(reverse("home"))

        assert response.status_code == 200

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_judgment_list_total_count(self, mock_search_results):
        mock_search_results.return_value.results = [
            SearchResultFactory.build(),
            SearchResultFactory.build(),
        ]
        mock_search_results.return_value.total = 2

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(reverse("home"))

        decoded_response = response.content.decode("utf-8")
        assert "2 unpublished documents" in decoded_response

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_judgment_list_items(self, mock_search_results):
        mock_search_results.return_value.results = [
            SearchResultFactory.build(
                uri="test/2023/123",
                name="Test Judgment 1",
                metadata=SearchResultMetadataFactory.build(
                    author="Author One",
                    consignment_reference="TDR-2023-AB1",
                ),
            ),
            SearchResultFactory.build(
                uri="test/2023/456",
                name="Test Judgment 2",
                metadata=SearchResultMetadataFactory.build(
                    author="Author Two",
                    consignment_reference="TDR-2023-CD2",
                ),
            ),
        ]
        mock_search_results.return_value.total = 2

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(reverse("home"))

        decoded_response = response.content.decode("utf-8")

        assert "Test Judgment 1" in decoded_response
        assert "Author One" in decoded_response
        assert "TDR-2023-AB1" in decoded_response

        assert "Test Judgment 2" in decoded_response
        assert "Author Two" in decoded_response
        assert "TDR-2023-CD2" in decoded_response
