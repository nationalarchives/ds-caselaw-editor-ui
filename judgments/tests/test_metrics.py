from datetime import date
from types import SimpleNamespace
from unittest.mock import ANY, call, patch
from urllib.parse import parse_qs, urlparse

from caselawclient.search_parameters import SearchParameters
from django.test import RequestFactory, SimpleTestCase

from judgments.utils import api_client
from judgments.views.metrics import MetricsView


class TestMetricsView(SimpleTestCase):
    @patch("judgments.views.metrics.api_client.get_metrics")
    @patch("judgments.views.metrics.courts")
    @patch("judgments.views.metrics.search_and_parse_response")
    @patch("judgments.views.metrics.search_judgments_and_parse_response")
    def test_get_context_data(
        self,
        mock_search_judgments_and_parse_response,
        mock_search_and_parse_response,
        mock_courts,
        mock_get_metrics,
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
        mock_get_metrics.side_effect = [
            {"2026-08": {"count": 2, "sum": 180000, "mean": 90000, "median": 90000}},
            {"2026-08": {"count": 2, "sum": 360000, "mean": 180000, "median": 180000}},
            {"2026-08": {"count": 2, "sum": 5, "mean": 2.5, "median": 2.5}},
        ]

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
        start_date, end_date = MetricsView._default_date_range()
        assert mock_search_judgments_and_parse_response.call_args_list == [
            call(
                api_client,
                SearchParameters(
                    court="example-court",
                    date_from=start_date.isoformat(),
                    date_to=end_date.isoformat(),
                    page_size=1,
                ),
            ),
            call(
                api_client,
                SearchParameters(
                    court="empty-court",
                    date_from=start_date.isoformat(),
                    date_to=end_date.isoformat(),
                    page_size=1,
                ),
            ),
            call(
                api_client,
                SearchParameters(
                    court="example-tribunal",
                    date_from=start_date.isoformat(),
                    date_to=end_date.isoformat(),
                    page_size=1,
                ),
            ),
            call(
                api_client,
                SearchParameters(
                    date_from=start_date.isoformat(),
                    date_to=end_date.isoformat(),
                    page_size=1,
                ),
            ),
        ]
        mock_search_and_parse_response.assert_called_once_with(
            api_client,
            SearchParameters(
                date_from=start_date.isoformat(),
                date_to=end_date.isoformat(),
                page_size=1,
            ),
        )
        assert context["lifecycle_metrics"][0]["rows"] == [
            {
                "period": "August 2026",
                "period_raw": "2026-08",
                "count": 2,
                "mean": {"display": "1 day 1 hour", "raw": 90000},
                "median": {"display": "1 day 1 hour", "raw": 90000},
            },
        ]
        assert context["submission_metrics"][0]["rows"][0]["total"] == 5
        assert mock_get_metrics.call_count == 3
        mock_get_metrics.assert_any_call(
            metric="tdr_to_first_publish",
            bucketing="monthly",
            start_date=ANY,
            end_date=ANY,
            search_parameters=SearchParameters(),
        )

    @patch("judgments.views.metrics.api_client.get_metrics")
    @patch.object(MetricsView, "_get_tribunal_choices")
    @patch.object(MetricsView, "_get_court_choices")
    @patch.object(MetricsView, "_get_documents_count")
    @patch.object(MetricsView, "_get_court_and_tribunal_document_counts")
    def test_filters_metrics_by_dates_bucketing_and_multiple_courts(
        self,
        mock_get_counts,
        mock_get_documents_count,
        mock_get_court_choices,
        mock_get_tribunal_choices,
        mock_get_metrics,
    ):
        mock_get_counts.return_value = []
        mock_get_documents_count.side_effect = [0, 0]
        mock_get_court_choices.return_value = [("example-court", "Example Court")]
        mock_get_tribunal_choices.return_value = [("example-tribunal", "Example Tribunal")]
        mock_get_metrics.return_value = {
            "2026-09-01": {"count": 1, "sum": 3661, "mean": 3661, "median": 3661},
        }
        request = RequestFactory().get(
            "/metrics",
            {
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
                "bucketing": "daily",
                "courts": ["example-court", "example-tribunal"],
            },
        )
        view = MetricsView()
        view.setup(request)

        context = view.get_context_data()

        assert context["filter_form"].is_valid()
        assert context["court_options"] == [
            {"value": "example-court", "text": "Example Court", "checked": True},
        ]
        assert context["tribunal_options"] == [
            {"value": "example-tribunal", "text": "Example Tribunal", "checked": True},
        ]
        assert [item["label"] for item in context["selected_court_filters"]] == [
            "Example Court",
            "Example Tribunal",
        ]
        assert parse_qs(urlparse(context["selected_court_filters"][0]["remove_url"]).query) == {
            "start_date": ["2026-09-01"],
            "end_date": ["2026-09-30"],
            "bucketing": ["daily"],
            "courts": ["example-tribunal"],
        }
        assert parse_qs(urlparse(context["selected_court_filters"][1]["remove_url"]).query) == {
            "start_date": ["2026-09-01"],
            "end_date": ["2026-09-30"],
            "bucketing": ["daily"],
            "courts": ["example-court"],
        }
        assert context["lifecycle_metrics"][0]["rows"][0] == {
            "period": "1 September 2026",
            "period_raw": "2026-09-01",
            "count": 1,
            "mean": {"display": "1 hour 1 minute", "raw": 3661},
            "median": {"display": "1 hour 1 minute", "raw": 3661},
        }
        mock_get_counts.assert_called_once_with(
            selected_courts={"example-court", "example-tribunal"},
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )
        assert mock_get_documents_count.call_args_list == [
            call(
                court="example-court,example-tribunal",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 30),
            ),
            call(
                court="example-court,example-tribunal",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 30),
                judgments_only=False,
            ),
        ]
        mock_get_metrics.assert_any_call(
            metric="tdr_to_first_publish",
            bucketing="daily",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            search_parameters=SearchParameters(court="example-court,example-tribunal"),
        )

    @patch.object(MetricsView, "_default_date_range", return_value=(date(2026, 7, 7), date(2026, 10, 7)))
    def test_blank_dates_use_default_three_month_range(self, mock_default_date_range):
        request = RequestFactory().get(
            "/metrics",
            {"start_date": "", "end_date": "", "bucketing": "monthly"},
        )
        view = MetricsView()
        view.setup(request)

        form, filters = view._get_metric_filters([])

        assert form.is_valid()
        assert form["start_date"].value() == "2026-07-07"
        assert form["end_date"].value() == "2026-10-07"
        assert filters is not None
        assert filters["start_date"] == date(2026, 7, 7)
        assert filters["end_date"] == date(2026, 10, 7)
        mock_default_date_range.assert_called_once_with()

    @patch.object(MetricsView, "_default_date_range", return_value=(date(2026, 7, 7), date(2026, 10, 7)))
    def test_default_dates_are_rendered_for_initial_page_load(self, mock_default_date_range):
        form, filters = MetricsView()._get_metric_filters([])

        assert not form.is_bound
        assert 'value="2026-07-07"' in form["start_date"].as_widget()
        assert 'value="2026-10-07"' in form["end_date"].as_widget()
        assert filters is not None
        assert filters["start_date"] == date(2026, 7, 7)
        assert filters["end_date"] == date(2026, 10, 7)
        mock_default_date_range.assert_called_once_with()
