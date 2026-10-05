from types import SimpleNamespace
from unittest.mock import call, patch

from caselawclient.search_parameters import SearchParameters
from django.test import SimpleTestCase

from judgments.utils import api_client
from judgments.views.metrics import MetricsView


class TestMetricsView(SimpleTestCase):
    @patch("judgments.views.metrics.courts")
    @patch("judgments.views.metrics.search_and_parse_response")
    @patch("judgments.views.metrics.search_judgments_and_parse_response")
    def test_get_context_data(
        self,
        mock_search_judgments_and_parse_response,
        mock_search_and_parse_response,
        mock_courts,
    ):
        court = SimpleNamespace(name="Example Court", canonical_param="example-court")
        court_without_documents = SimpleNamespace(name="Empty Court", canonical_param="empty-court")
        tribunal = SimpleNamespace(name="Example Tribunal", canonical_param="example-tribunal")
        mock_courts.get_grouped_show_to_editors_courts.return_value = [
            SimpleNamespace(courts=[court, court_without_documents]),
        ]
        mock_courts.get_grouped_show_to_editors_tribunals.return_value = [SimpleNamespace(courts=[tribunal])]
        mock_search_judgments_and_parse_response.side_effect = [
            SimpleNamespace(total="10"),
            SimpleNamespace(total="0"),
            SimpleNamespace(total="4"),
            SimpleNamespace(total="14"),
        ]
        mock_search_and_parse_response.return_value = SimpleNamespace(total="17")

        context = MetricsView().get_context_data()

        assert context["page_title"] == "Metrics"
        assert context["summary_metrics"] == [
            {"label": "Court documents", "value": 10},
            {"label": "Tribunal documents", "value": 4},
            {"label": "Press summaries", "value": 3},
            {"label": "Total documents", "value": 17},
            {"label": "Courts and tribunals", "value": 2},
        ]
        assert context["cases_by_court"] == [
            {"name": "Example Court", "type": "Court", "document_count": 10},
            {"name": "Example Tribunal", "type": "Tribunal", "document_count": 4},
        ]
        assert mock_search_judgments_and_parse_response.call_args_list == [
            call(api_client, SearchParameters(court="example-court", page_size=1)),
            call(api_client, SearchParameters(court="empty-court", page_size=1)),
            call(api_client, SearchParameters(court="example-tribunal", page_size=1)),
            call(api_client, SearchParameters(page_size=1)),
        ]
        mock_search_and_parse_response.assert_called_once_with(
            api_client,
            SearchParameters(page_size=1),
        )
