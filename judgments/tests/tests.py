import re
from unittest.mock import patch

from caselawclient.search_parameters import SearchParameters
from django.contrib.auth.models import User
from django.test import TestCase

from judgments.utils import api_client


def assert_match(regex, string):
    assert re.search(regex, string) is not None


class TestSearchResults(TestCase):
    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_oldest(self, mock_search):
        mock_search.results.return_value = []
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        self.client.get("/")
        mock_search.assert_called_with(
            api_client,
            SearchParameters(
                query=None,
                order="-date",
                only_unpublished=True,
                show_unpublished=True,
                page=1,
            ),
        )


class TestCheckPrefixUrls(TestCase):
    def test_just_check_ok(self):
        """The /check endpoint can be used when not logged in"""
        response = self.client.get("/check")
        assert response.status_code == 200
        assert b'"OK"' in response.content

    def test_check_prefix_not_ok(self):
        """Urls starting with /check cannot be used when not logged in"""
        response = self.client.get("/checkblahblahblah")
        assert response.status_code == 302
        assert response["Location"] == "/accounts/login/?next=/checkblahblahblah"
