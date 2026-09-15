from unittest.mock import MagicMock, patch

import pytest
from caselawclient.search_parameters import SearchParameters
from django.http import QueryDict
from django.test import SimpleTestCase

from judgments.utils import api_client
from judgments.utils.document_list import (
    ORDER_CHOICES,
    PUBLICATION_STATUS_ALL,
    PUBLICATION_STATUS_CHOICES,
    PUBLICATION_STATUS_PUBLISHED,
    PUBLICATION_STATUS_UNPUBLISHED,
    SAVED_VIEW_ALL,
    SAVED_VIEW_PRESETS,
    SAVED_VIEW_UNPUBLISHED,
    DocumentListFilters,
    InvalidDocumentListFilterError,
    catalogue_court_options,
    get_saved_view_preset,
    process_court_facets,
)
from judgments.utils.view_helpers import get_document_list_filters, get_search_results_from_filters

UNPUBLISHED_VIEW = get_saved_view_preset(SAVED_VIEW_UNPUBLISHED)
ALL_VIEW = get_saved_view_preset(SAVED_VIEW_ALL)


def parse(query="", *, base=UNPUBLISHED_VIEW):
    return DocumentListFilters.from_query_params(QueryDict(query), base_saved_view=base)


class TestDocumentListFilters(SimpleTestCase):
    def test_empty_params_keep_base_saved_view(self):
        assert parse("").matching_saved_view() == UNPUBLISHED_VIEW
        assert parse("", base=ALL_VIEW).matching_saved_view() == ALL_VIEW

    def test_unpublished_uses_only_unpublished(self):
        filters = parse("publication_status=unpublished")
        assert filters.only_unpublished is True
        assert filters.show_unpublished is True

    def test_published_uses_show_unpublished_false(self):
        filters = parse("publication_status=published")
        assert filters.only_unpublished is False
        assert filters.show_unpublished is False

    def test_all_shows_unpublished(self):
        filters = parse("publication_status=all")
        assert filters.only_unpublished is False
        assert filters.show_unpublished is True

    def test_query_keeps_base_order(self):
        filters = parse("query=foo")
        assert filters.order == UNPUBLISHED_VIEW.order

    def test_invalid_order_raises(self):
        with pytest.raises(InvalidDocumentListFilterError):
            parse("order=not-a-real-order")

    def test_invalid_publication_status_raises(self):
        with pytest.raises(InvalidDocumentListFilterError):
            parse("publication_status=nope")

    def test_courts_and_years(self):
        filters = parse("court=ewca/civ&court=uksc&from_year=2020&to_year=2019")
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
        filters = parse("page=not-a-number")
        assert filters.page == 1

    def test_blank_query_and_unknown_court_ignored(self):
        filters = parse("query=%20%20&court=not-a-real-court&order=-date")
        assert filters.query is None
        assert filters.courts == []
        assert filters.court_param is None

    def test_invalid_years_ignored(self):
        filters = parse("from_year=abc&to_year=99")
        assert filters.from_year is None
        assert filters.to_year is None
        assert filters.date_from is None
        assert filters.date_to is None

    def test_out_of_range_year_ignored(self):
        filters = parse("from_year=10000")
        assert filters.from_year is None

    def test_single_year_bounds(self):
        filters = parse("from_year=2020")
        assert filters.from_year == 2020
        assert filters.to_year is None
        assert filters.date_from == "2020-01-01"
        assert filters.date_to is None
        assert filters.search_date_from == "2020-01-01"
        assert filters.search_date_to == "2020-12-31"

    def test_search_date_bounds_from_to_only(self):
        filters = parse("to_year=2018")
        assert filters.search_date_from == "2018-01-01"
        assert filters.search_date_to == "2018-12-31"

    def test_context_dict(self):
        filters = parse("query=foo&search_filter=default&publication_status=all&order=-updated&page=2")
        assert filters.context_dict() == {
            "query": "foo",
            "search_filter": "default",
            "page": 2,
            "order": "-updated",
            "publication_status": PUBLICATION_STATUS_ALL,
            "selected_courts": [],
            "from_year": None,
            "to_year": None,
            "order_choices": ORDER_CHOICES,
            "publication_status_choices": PUBLICATION_STATUS_CHOICES,
            "saved_view_presets": SAVED_VIEW_PRESETS,
            "active_saved_view": ALL_VIEW,
            "uses_court_facets": True,
            "total_count_postfix": "documents",
            "clear_filters_query_string": ("publication_status=all&order=-updated&query=foo&search_filter=default"),
            "clear_search_query_string": "publication_status=all&order=-updated",
        }

    def test_matching_saved_view_none_when_extra_filters(self):
        filters = parse("publication_status=unpublished&order=-date&court=uksc")
        assert filters.matching_saved_view() is None

    def test_clear_filters_drops_sidebar_refinements_keeps_search(self):
        filters = parse(
            "publication_status=published&order=-updated&court=uksc&from_year=2020&query=foo&search_filter=ncn&page=3",
        )
        cleared = filters.clear_filters_query_string()
        assert "court=" not in cleared
        assert "from_year=" not in cleared
        assert "page=" not in cleared
        assert "publication_status=published" in cleared
        assert "order=-updated" in cleared
        assert "query=foo" in cleared
        assert "search_filter=ncn" in cleared

    def test_clear_search_keeps_sidebar_filters(self):
        filters = parse(
            "publication_status=published&order=-updated&court=uksc&court=ewca/civ"
            "&from_year=2020&to_year=2021&query=foo&search_filter=ncn&page=3",
        )
        cleared = filters.clear_search_query_string()
        assert "query=" not in cleared
        assert "search_filter=" not in cleared
        assert "page=" not in cleared
        assert "publication_status=published" in cleared
        assert "order=-updated" in cleared
        assert "court=uksc" in cleared
        assert "court=ewca%2Fciv" in cleared
        assert "from_year=2020" in cleared
        assert "to_year=2021" in cleared

    def test_matching_saved_view_keeps_preset_with_query_and_order(self):
        filters = parse("publication_status=unpublished&query=foo&order=-updated")
        assert filters.matching_saved_view() == UNPUBLISHED_VIEW

    def test_matching_saved_view_none_when_courts_with_query(self):
        filters = parse("publication_status=unpublished&query=foo&court=uksc")
        assert filters.matching_saved_view() is None

    def test_matching_saved_view_keeps_preset_with_decision_year(self):
        filters = parse("publication_status=unpublished&from_year=2020")
        assert filters.matching_saved_view() == UNPUBLISHED_VIEW

    def test_saved_view_applies_status_and_order(self):
        for preset in SAVED_VIEW_PRESETS:
            filters = parse(preset.query_string())
            assert filters.publication_status == preset.publication_status
            assert filters.order == preset.order
            assert filters.matching_saved_view() == preset


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

    def _filters(self, query="", *, base=UNPUBLISHED_VIEW):
        return get_document_list_filters(QueryDict(query), base_saved_view=base)

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_unpublished_base_search_params(self, mock_search):
        mock_search.return_value = self._mock_response()
        get_search_results_from_filters(self._filters(""))
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
    def test_all_base_search_params(self, mock_search):
        mock_search.return_value = self._mock_response()
        filters = self._filters("", base=ALL_VIEW)
        assert filters.matching_saved_view() == ALL_VIEW
        get_search_results_from_filters(filters)
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
    def test_single_from_year_search_params(self, mock_search):
        mock_search.return_value = self._mock_response()
        get_search_results_from_filters(self._filters("publication_status=all&from_year=2020"))
        mock_search.assert_called_with(
            api_client,
            SearchParameters(
                query=None,
                order="-date",
                only_unpublished=False,
                show_unpublished=True,
                page=1,
                date_from="2020-01-01",
                date_to="2020-12-31",
            ),
        )

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_order_and_court_passed_through(self, mock_search):
        mock_search.return_value = self._mock_response()
        get_search_results_from_filters(
            self._filters("publication_status=all&order=-updated&court=uksc&from_year=2022&to_year=2023"),
        )
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
        result = get_search_results_from_filters(self._filters("query=Imperial&publication_status=all"))
        assert result["uses_court_facets"] is True
        assert any(opt.count == "4" for opt in result["court_options"] if opt.value == "uksc")

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_published_status(self, mock_search):
        mock_search.return_value = self._mock_response()
        get_search_results_from_filters(self._filters("publication_status=published&order=-date"))
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
        result = get_search_results_from_filters(self._filters("publication_status=unpublished"))
        assert result["uses_court_facets"] is False
        assert result["court_options"]
        assert all(opt.count is None for opt in result["court_options"])

    @patch("judgments.utils.view_helpers.search_and_parse_response")
    def test_ncn_search(self, mock_search):
        mock_search.return_value = self._mock_response()
        get_search_results_from_filters(
            self._filters("query=[2023] UKSC 1&search_filter=ncn&publication_status=all"),
        )
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
