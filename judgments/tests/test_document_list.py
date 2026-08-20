from unittest.mock import MagicMock, patch

from caselawclient.search_parameters import SearchParameters
from django.http import QueryDict
from django.test import SimpleTestCase

from judgments.utils import api_client
from judgments.utils.document_list import (
    PUBLICATION_STATUS_ALL,
    PUBLICATION_STATUS_PUBLISHED,
    PUBLICATION_STATUS_UNPUBLISHED,
    SYSTEM_PRESETS,
    DocumentListFilters,
    catalogue_court_options,
    process_court_facets,
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

    def test_order_defaults_to_date_with_query(self):
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
        # Years swapped so from <= to
        assert filters.from_year == 2019
        assert filters.to_year == 2020
        assert filters.date_from == "2019-01-01"
        assert filters.date_to == "2020-12-31"
        assert filters.court_param == "ewca/civ,uksc"

    def test_matching_preset(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict("publication_status=unpublished&order=-date"),
        )
        preset = filters.matching_preset()
        assert preset is not None
        assert preset.id == "unpublished"

    def test_matching_preset_none_when_extra_filters(self):
        filters = DocumentListFilters.from_query_params(
            QueryDict("publication_status=unpublished&order=-date&court=uksc"),
        )
        assert filters.matching_preset() is None

    def test_system_presets_defined(self):
        assert [p.id for p in SYSTEM_PRESETS] == ["unpublished", "recently-published", "all"]


class TestCourtFacets(SimpleTestCase):
    def test_catalogue_includes_selected(self):
        options = catalogue_court_options(["uksc"])
        assert options
        selected = [opt for opt in options if opt.checked]
        assert len(selected) == 1
        assert selected[0].value == "uksc"

    def test_process_court_facets(self):
        options = process_court_facets({"EWCA-Civil": "12", "2024": "99", "UKSC": "3"}, ["uksc"])
        values = [opt.value for opt in options]
        assert "ewca/civ" in values
        assert "uksc" in values
        # Year facet ignored
        assert "2024" not in values
        uksc = next(opt for opt in options if opt.value == "uksc")
        assert uksc.checked is True
        assert uksc.count == "3"

    def test_selected_missing_from_facets_still_shown(self):
        options = process_court_facets({"EWCA-Civil": "12"}, ["uksc"])
        uksc = next(opt for opt in options if opt.value == "uksc")
        assert uksc.checked is True
        assert uksc.count is None


class TestSearchResultsFromFilters(SimpleTestCase):
    def _mock_response(self, *, facets=None):
        mock_response = MagicMock()
        mock_response.total = 0
        mock_response.results = []
        mock_response.facets = facets or {}
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
    def test_search_uses_facets_for_courts(self, mock_search):
        mock_search.return_value = self._mock_response(facets={"UKSC": "4", "EWCA-Civil": "2"})
        filters = get_document_list_filters(QueryDict("query=Imperial&publication_status=all"))
        result = get_search_results_from_filters(filters)
        assert result["uses_court_facets"] is True
        assert any(opt.count == "4" for opt in result["court_options"] if opt.value == "uksc")

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_published_preset(self, mock_search):
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
    def test_browse_uses_catalogue_not_facets(self, mock_search):
        mock_search.return_value = self._mock_response(facets={"UKSC": "4"})
        filters = get_document_list_filters(
            QueryDict("publication_status=unpublished"),
            default_publication_status=PUBLICATION_STATUS_UNPUBLISHED,
        )
        result = get_search_results_from_filters(filters)
        assert result["uses_court_facets"] is False
        # Catalogue mode: options present without relying on facet counts
        assert result["court_options"]
        assert all(opt.count is None for opt in result["court_options"])
