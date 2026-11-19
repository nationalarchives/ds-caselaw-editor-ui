from datetime import date, timedelta
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, call, patch
from urllib.parse import parse_qs, urlparse

from caselawclient.search_parameters import SearchParameters
from django.test import RequestFactory, SimpleTestCase
from openpyxl import load_workbook

from judgments.utils import api_client
from judgments.utils.metrics_xlsx import build_metrics_workbook
from judgments.views.metrics import MetricsView, MetricsXlsxView


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
        metric_responses = {
            "tdr_to_first_publish": {
                "2026-08": {
                    "count": 2,
                    "sum": 180000,
                    "mean": 90000,
                    "median": 90000,
                    "within_24_hours_count": 1,
                    "over_24_hours_count": 1,
                    "over_24_hours_mean": 176400,
                },
            },
            "tdr_to_latest_publish": {
                "2026-08": {
                    "count": 2,
                    "sum": 360000,
                    "mean": 180000,
                    "median": 180000,
                    "within_24_hours_count": 0,
                },
            },
            "submissions_before_first_publish": {
                "2026-08": {"count": 2, "sum": 5, "mean": 2.5, "median": 2.5},
            },
        }
        mock_get_metrics.side_effect = lambda **kwargs: metric_responses[kwargs["metric"]]

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
            {
                "canonical_param": "example-court",
                "name": "Example Court",
                "type": "Court",
                "document_count": 10,
            },
            {
                "canonical_param": "example-tribunal",
                "name": "Example Tribunal",
                "type": "Tribunal",
                "document_count": 4,
            },
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
                "mean": {"display": "1 hour", "raw": 3600.0},
                "median": {"display": "1 day 1 hour", "raw": 90000},
                "within_24_hours_percentage": {
                    "display": "50.0%",
                    "raw": 50.0,
                    "numerator": 1,
                    "denominator": 2,
                },
            },
        ]
        assert context["lifecycle_metrics"][0]["show_within_24_hours_percentage"] is True
        assert context["lifecycle_metrics"][1]["show_within_24_hours_percentage"] is False
        assert [table["name"] for table in context["court_lifecycle_metrics"]] == [
            "Example Court",
            "Example Tribunal",
        ]
        assert context["court_lifecycle_metrics"][0]["rows"][0] == {
            "period": "August 2026",
            "period_raw": "2026-08",
            "first_publication": context["lifecycle_metrics"][0]["rows"][0],
            "latest_publication": context["lifecycle_metrics"][1]["rows"][0],
        }
        assert context["submission_metrics"][0]["rows"][0]["total"] == 5
        assert len(context["raw_metrics"]) == 7
        assert context["raw_metrics"][0] == {
            "metric": "tdr_to_first_publish",
            "court": "example-court",
            "response": metric_responses["tdr_to_first_publish"],
        }
        assert mock_get_metrics.call_count == 7
        mock_get_metrics.assert_any_call(
            metric="tdr_to_first_publish",
            bucketing="monthly",
            start_date=start_date,
            end_date=end_date + timedelta(days=1),
            search_parameters=SearchParameters(),
        )
        mock_get_metrics.assert_any_call(
            metric="tdr_to_first_publish",
            bucketing="monthly",
            start_date=start_date,
            end_date=end_date + timedelta(days=1),
            search_parameters=SearchParameters(court="example-court"),
        )

    def test_within_24_hours_percentage_has_no_data_when_bucket_is_empty(self):
        rows = MetricsView._format_duration_metrics(
            {
                "2026-08": {
                    "count": 0,
                    "mean": None,
                    "median": None,
                    "within_24_hours_count": 0,
                },
            },
            "monthly",
            include_within_24_hours_percentage=True,
            exclude_over_24_hours_from_mean=True,
        )

        assert rows[0]["within_24_hours_percentage"] is None
        assert rows[0]["mean"] is None

    def test_within_24_hours_percentage_has_no_data_when_api_field_is_unavailable(self):
        rows = MetricsView._format_duration_metrics(
            {
                "2026-08": {
                    "count": 2,
                    "mean": 90000,
                    "median": 90000,
                },
            },
            "monthly",
            include_within_24_hours_percentage=True,
            exclude_over_24_hours_from_mean=True,
        )

        assert rows[0]["within_24_hours_percentage"] is None
        assert rows[0]["mean"] is None

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
            "2026-09-01": {
                "count": 1,
                "sum": 3661,
                "mean": 3661,
                "median": 3661,
                "within_24_hours_count": 1,
                "over_24_hours_count": 0,
                "over_24_hours_mean": None,
            },
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
        assert parse_qs(urlparse(context["download_url"]).query) == {
            "start_date": ["2026-09-01"],
            "end_date": ["2026-09-30"],
            "bucketing": ["daily"],
            "courts": ["example-court", "example-tribunal"],
        }
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
            "within_24_hours_percentage": {
                "display": "100.0%",
                "raw": 100.0,
                "numerator": 1,
                "denominator": 1,
            },
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
            end_date=date(2026, 10, 1),
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


class TestMetricsXlsxView(SimpleTestCase):
    def test_builds_workbook_with_display_and_raw_metrics_sheets(self):
        percentage = {"display": "50.0%", "raw": 50.0, "numerator": 1, "denominator": 2}
        duration = {"display": "1 hour", "raw": 3600}
        first_publication_row = {
            "period": "August 2026",
            "period_raw": "2026-08",
            "count": 2,
            "mean": duration,
            "median": duration,
            "within_24_hours_percentage": percentage,
        }
        latest_publication_row = {
            "period": "August 2026",
            "period_raw": "2026-08",
            "count": 2,
            "mean": duration,
            "median": duration,
        }
        context: dict[str, Any] = {
            "summary_metrics": [{"label": "Total documents", "value": 2}],
            "lifecycle_metrics": [
                {
                    "label": "Time to first publication",
                    "show_within_24_hours_percentage": True,
                    "rows": [first_publication_row],
                },
                {
                    "label": "Time to latest publication",
                    "show_within_24_hours_percentage": False,
                    "rows": [latest_publication_row],
                },
            ],
            "submission_metrics": [
                {
                    "rows": [
                        {
                            "period_raw": "2026-08",
                            "count": 2,
                            "total": 3,
                            "median": {"display": "1.5", "raw": 1.5},
                            "mean": {"display": "1.5", "raw": 1.5},
                        },
                    ],
                },
            ],
            "court_lifecycle_metrics": [
                {
                    "name": "Example Court",
                    "type": "Court",
                    "rows": [
                        {
                            "period_raw": "2026-08",
                            "first_publication": first_publication_row,
                            "latest_publication": latest_publication_row,
                        },
                    ],
                },
            ],
            "cases_by_court": [{"name": "Example Court", "type": "Court", "document_count": 2}],
            "raw_metrics": [
                {
                    "metric": "tdr_to_first_publish",
                    "court": "example-court",
                    "response": {
                        "2026-08": {
                            "count": 2,
                            "sum": 7200,
                            "mean": 3600,
                            "median": 3600,
                            "within_24_hours_count": 1,
                        },
                    },
                },
            ],
        }

        workbook = load_workbook(BytesIO(build_metrics_workbook(context)))

        assert workbook.sheetnames == [
            "Summary",
            "First publication",
            "Latest publication",
            "Submissions",
            "Court lifecycle",
            "Documents by court",
            "Raw metrics",
        ]
        assert workbook["First publication"]["C2"].value == 1
        raw_headers = [cell.value for cell in workbook["Raw metrics"][1]]
        raw_values = [cell.value for cell in workbook["Raw metrics"][2]]
        assert dict(zip(raw_headers, raw_values, strict=True)) == {
            "Metric": "tdr_to_first_publish",
            "Court filter": "example-court",
            "Period": "2026-08",
            "count": 2,
            "mean": 3600,
            "median": 3600,
            "sum": 7200,
            "within_24_hours_count": 1,
        }

    @patch("judgments.views.metrics.build_metrics_workbook", return_value=b"workbook")
    @patch.object(MetricsXlsxView, "_get_metrics_context", return_value=MagicMock())
    @patch.object(MetricsXlsxView, "_get_tribunal_choices", return_value=[])
    @patch.object(
        MetricsXlsxView,
        "_get_court_choices",
        return_value=[("ewcc", "County Court"), ("ewca/civ", "Civil Court")],
    )
    def test_downloads_workbook_with_filename_from_filters(
        self,
        mock_court_choices,
        mock_tribunal_choices,
        mock_get_metrics_context,
        mock_build_metrics_workbook,
    ):
        request = RequestFactory().get(
            "/metrics.xlsx",
            {
                "start_date": "2026-08-12",
                "end_date": "2026-11-20",
                "bucketing": "daily",
                "courts": ["ewcc", "ewca/civ"],
            },
        )
        response = MetricsXlsxView.as_view()(request)

        mock_court_choices.assert_called_once_with()
        mock_tribunal_choices.assert_called_once_with()
        assert response.status_code == 200
        assert response.content == b"workbook"
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert (
            response["Content-Disposition"]
            == 'attachment; filename="metrics_2026-08-12_2026-11-20_daily_ewcc_ewca-civ.xlsx"'
        )
        mock_get_metrics_context.assert_called_once_with(
            {
                "start_date": date(2026, 8, 12),
                "end_date": date(2026, 11, 20),
                "bucketing": "daily",
                "courts": ["ewcc", "ewca/civ"],
            },
        )
        mock_build_metrics_workbook.assert_called_once_with(mock_get_metrics_context.return_value)
