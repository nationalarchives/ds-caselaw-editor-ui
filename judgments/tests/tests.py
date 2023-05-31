import re
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase


def assert_match(regex, string):
    assert re.search(regex, string) is not None


class TestSearchResults(TestCase):
    @patch("judgments.utils.view_helpers.search_judgments_and_parse_response")
    def test_oldest(self, mock_search):
        mock_search.results.return_value = []
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("?order=-date")
        mock_search.assert_called_with(
            query=None, order="-date", only_unpublished=True, page=1
        )
        assert_match(
            b"<option(\\s+)value=\"-date\"(\\s+)selected='selected'(\\s*)>",
            response.content,
        )

    @patch("judgments.utils.view_helpers.search_judgments_and_parse_response")
    def test_newest(self, mock_search):
        mock_search.results.return_value = []
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("?order=date")
        mock_search.assert_called_with(
            query=None, order="date", only_unpublished=True, page=1
        )
        assert_match(
            b"<option(\\s+)value=\"date\"(\\s+)selected='selected'(\\s*)>",
            response.content,
        )
