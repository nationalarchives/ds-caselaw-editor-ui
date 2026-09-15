import re
from unittest.mock import MagicMock, patch

from caselawclient.search_parameters import SearchParameters
from django.contrib.auth.models import User
from django.test import TestCase
from waffle.testutils import override_flag

from judgments.utils import api_client
from judgments.views.document_list import DOCUMENT_LIST_QUEUE_FLAG


def assert_match(regex, string):
    assert re.search(regex, string) is not None


class TestSearchResults(TestCase):
    def _mock_search_response(self):
        mock_response = MagicMock()
        mock_response.results = []
        mock_response.total = 0
        mock_response.facets = {}
        return mock_response

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_home_searches_unpublished_only(self, mock_search):
        mock_search.return_value = self._mock_search_response()
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

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_results_searches_all_documents(self, mock_search):
        mock_search.return_value = self._mock_search_response()
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        self.client.get("/results")
        mock_search.assert_called_with(
            api_client,
            SearchParameters(
                query=None,
                order="-date",
                only_unpublished=False,
                show_unpublished=True,
                page=1,
            ),
        )

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_results_ncn_search(self, mock_search):
        mock_search.return_value = self._mock_search_response()
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/results", {"query": "[2023] UKSC 1", "search_filter": "ncn"})
        assert response.status_code == 200
        decoded = response.content.decode("utf-8")
        assert "Search results" in decoded
        assert "0 documents" in decoded
        mock_search.assert_called_with(
            api_client,
            SearchParameters(
                neutral_citation="[2023] UKSC 1",
                order="-date",
                only_unpublished=False,
                show_unpublished=True,
                page=1,
            ),
        )

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_home_flag_off_keeps_classic_list(self, mock_search):
        mock_search.return_value = self._mock_search_response()
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/")
        decoded = response.content.decode("utf-8")
        assert response.status_code == 200
        assert "document-list-sidebar" not in decoded
        assert "Document details" in decoded

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    @override_flag(DOCUMENT_LIST_QUEUE_FLAG, active=True)
    def test_home_flag_on_shows_queue_and_sidebar(self, mock_search):
        mock_search.return_value = self._mock_search_response()
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/")
        decoded = response.content.decode("utf-8")
        assert response.status_code == 200
        assert "document-list-sidebar" in decoded
        assert "document-list-form" in decoded
        assert "Order by" in decoded
        assert "Unpublished documents" in decoded


class TestCheckPrefixUrls(TestCase):
    def test_just_check_ok(self):
        """The /check endpoint can be used when not logged in"""
        response = self.client.get("/check")
        assert response.status_code == 200
        assert b'"OK"' in response.content
        assert response["X-Clacks-Overhead"] == "GNU Terry Pratchett"

    def test_check_prefix_not_ok(self):
        """Urls starting with /check cannot be used when not logged in"""
        response = self.client.get("/checkblahblahblah")
        assert response.status_code == 302
        assert response["Location"] == "/accounts/login/?next=/checkblahblahblah"
