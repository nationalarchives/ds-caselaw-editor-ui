from unittest.mock import MagicMock, patch

from caselawclient.search_parameters import SearchParameters
from django.http import QueryDict
from django.test import SimpleTestCase

from judgments.utils import api_client
from judgments.utils.document_list import (
    PUBLICATION_STATUS_ALL,
    PUBLICATION_STATUS_PUBLISHED,
    PUBLICATION_STATUS_UNPUBLISHED,
    DocumentListFilters,
)
from judgments.utils.view_helpers import get_document_list_filters, get_search_results_from_filters


class TestDocumentListFilters(SimpleTestCase):
    def test_defaults_to_unpublished_when_requested(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict(""),
            default_publication_status=PUBLICATION_STATUS_UNPUBLISHED,
        )
        assert filters.publication_status == PUBLICATION_STATUS_UNPUBLISHED
        assert filters.only_unpublished is True
        assert filters.show_unpublished is True
        assert filters.order == "-date"

    def test_published_uses_show_unpublished_false(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict("publication_status=published"),
        )
        assert filters.publication_status == PUBLICATION_STATUS_PUBLISHED
        assert filters.only_unpublished is False
        assert filters.show_unpublished is False

    def test_all_shows_unpublished(self):
        filters = DocumentListFilters.from_query_params(QueryDict("publication_status=all"))
        assert filters.publication_status == PUBLICATION_STATUS_ALL
        assert filters.only_unpublished is False
        assert filters.show_unpublished is True

    def test_order_stays_newest_with_query(self):
        filters = DocumentListFilters.from_query_params(QueryDict("query=foo"))
        assert filters.order == "-date"

    def test_invalid_order_falls_back(self):
        filters = DocumentListFilters.from_query_params(QueryDict("order=not-a-real-order"))
        assert filters.order == "-date"

    def test_courts_and_years(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict("court=ewca/civ&court=uksc&from_year=2020&to_year=2019"),
        )
        assert filters.courts == ["ewca/civ", "uksc"]
        assert filters.from_year == 2019
        assert filters.to_year == 2020
        assert filters.date_from == "2019-01-01"
        assert filters.date_to == "2020-12-31"
        assert filters.court_param == "ewca/civ,uksc"

    def test_total_count_postfix(self):
        unpublished = DocumentListFilters(publication_status=PUBLICATION_STATUS_UNPUBLISHED)
        published = DocumentListFilters(publication_status=PUBLICATION_STATUS_PUBLISHED)
        all_docs = DocumentListFilters(publication_status=PUBLICATION_STATUS_ALL)
        assert unpublished.total_count_postfix() == "unpublished documents"
        assert published.total_count_postfix() == "published documents"
        assert all_docs.total_count_postfix() == "documents"

    def test_invalid_page_falls_back_to_one(self):
        filters = DocumentListFilters.from_query_params(QueryDict("page=not-a-number"))
        assert filters.page == 1

    def test_blank_query_and_unknown_court_ignored(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict("query=%20%20&court=not-a-real-court&order=-date"),
        )
        assert filters.query is None
        assert filters.courts == []
        assert filters.court_param is None

    def test_invalid_publication_status_uses_default(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict("publication_status=nope"),
            default_publication_status=PUBLICATION_STATUS_UNPUBLISHED,
        )
        assert filters.publication_status == PUBLICATION_STATUS_UNPUBLISHED

    def test_invalid_years_ignored(self):
        filters = DocumentListFilters.from_query_params(QueryDict("from_year=abc&to_year=99"))
        assert filters.from_year is None
        assert filters.to_year is None
        assert filters.date_from is None
        assert filters.date_to is None

    def test_out_of_range_year_ignored(self):
        filters = DocumentListFilters.from_query_params(QueryDict("from_year=10000"))
        assert filters.from_year is None

    def test_single_year_bounds(self):
        filters = DocumentListFilters.from_query_params(QueryDict("from_year=2020"))
        assert filters.from_year == 2020
        assert filters.to_year is None
        assert filters.date_from == "2020-01-01"
        assert filters.date_to is None

    def test_context_dict(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict("query=foo&search_filter=default&publication_status=all&order=-updated&page=2"),
        )
        assert filters.context_dict() == {
            "query": "foo",
            "search_filter": "default",
            "page": 2,
            "order": "-updated",
            "publication_status": PUBLICATION_STATUS_ALL,
            "total_count_postfix": "documents",
        }


class TestSearchResultsFromFilters(SimpleTestCase):
    def _mock_response(self):
        mock_response = MagicMock()
        mock_response.total = 0
        mock_response.results = []
        mock_response.facets = {}
        return mock_response

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_home_defaults_unpublished(self, mock_search):
        mock_search.return_value = self._mock_response()
        filters = get_document_list_filters(
            QueryDict(""),
            default_publication_status=PUBLICATION_STATUS_UNPUBLISHED,
        )
        get_search_results_from_filters(filters)
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
    def test_order_and_court_passed_through(self, mock_search):
        mock_search.return_value = self._mock_response()
        filters = get_document_list_filters(
            QueryDict("publication_status=all&order=-updated&court=uksc&from_year=2022&to_year=2023"),
        )
        get_search_results_from_filters(filters)
        mock_search.assert_called_with(
            api_client,
            SearchParameters(
                query=None,
                order="-updated",
                only_unpublished=False,
                show_unpublished=True,
                page=1,
                court="uksc",
                date_from="2022-01-01",
                date_to="2023-12-31",
            ),
        )

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_published_status(self, mock_search):
        mock_search.return_value = self._mock_response()
        filters = get_document_list_filters(QueryDict("publication_status=published&order=-date"))
        get_search_results_from_filters(filters)
        mock_search.assert_called_with(
            api_client,
            SearchParameters(
                query=None,
                order="-date",
                only_unpublished=False,
                show_unpublished=False,
                page=1,
            ),
        )

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_ncn_search(self, mock_search):
        mock_search.return_value = self._mock_response()
        filters = get_document_list_filters(
            QueryDict("query=[2023] UKSC 1&search_filter=ncn&publication_status=all"),
        )
        get_search_results_from_filters(filters)
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
