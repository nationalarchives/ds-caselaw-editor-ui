from datetime import date
from io import BytesIO
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, call, patch
from urllib.parse import parse_qs, urlparse

from caselawclient.metrics import MetricStatistics
from caselawclient.search_parameters import SearchParameters
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase
from openpyxl import load_workbook

from judgments.utils.metrics_xlsx import build_metrics_workbook
from judgments.views.metrics import CourtMetricsView, JourneyMetricsView, MetricsView, MetricsXlsxView

if TYPE_CHECKING:
    from django.template.response import TemplateResponse


def metric_statistics(**overrides: Any) -> MetricStatistics:
    values = {
        "count": 2,
        "sum": 180000,
        "mean": 90000,
        "median": 90000,
        "within_24_hours_count": 1,
        "over_24_hours_count": 1,
        "over_24_hours_mean": 176400,
        "over_24_hours_median": 176400,
        "over_24_hours_minimum": 172800,
        "over_24_hours_maximum": 180000,
        "over_24_hours_standard_deviation": 3600,
        "minimum": 3600,
        "maximum": 180000,
        "standard_deviation": 7200,
    }
    values.update(overrides)
    return cast("MetricStatistics", values)


class MetricsViewTestCase(SimpleTestCase):
    court_choices = [("example-court", "Example Court")]
    tribunal_choices = [("example-tribunal", "Example Tribunal")]

    def build_view(self, view_class, path: str, query: dict | None = None):
        request = RequestFactory().get(path, query or {})
        view = view_class()
        view.setup(request)
        return view

    def choice_patches(self, view_class):
        return (
            patch.object(view_class, "_get_court_choices", return_value=self.court_choices),
            patch.object(view_class, "_get_tribunal_choices", return_value=self.tribunal_choices),
        )


class TestMetricsTemplates(MetricsViewTestCase):
    def test_metrics_pages_render(self):
        for view_class, path, expected_text in (
            (MetricsView, "/metrics", "Publications over time"),
            (JourneyMetricsView, "/metrics/journeys", "Journey metrics"),
            (CourtMetricsView, "/metrics/courts", "Select one or more courts or tribunals"),
        ):
            request = RequestFactory().get(
                path,
                {"start_date": "2026-09-30", "end_date": "2026-09-01", "bucketing": "monthly"},
            )
            request.user = AnonymousUser()
            court_patch, tribunal_patch = self.choice_patches(view_class)

            with self.subTest(path=path), court_patch, tribunal_patch:
                response = cast("TemplateResponse", view_class.as_view()(request))
                response.render()

            assert expected_text in response.content.decode()


class TestMetricsOverview(MetricsViewTestCase):
    @patch("judgments.views.metrics.api_client.get_metrics")
    @patch("judgments.views.metrics.api_client.get_publication_counts")
    def test_get_context_data_uses_publication_counts_and_whole_period_metrics(
        self,
        mock_get_publication_counts,
        mock_get_metrics,
    ):
        def publication_counts(**kwargs):
            parameters = kwargs["search_parameters"]
            if parameters.collections == ["press-summary"]:
                return {"2026-08": 1, "2026-09": 2, "total": 3}
            if parameters.court == "example-court":
                return {"2026-08": 4, "2026-09": 6, "total": 10}
            return {"2026-08": 2, "2026-09": 2, "total": 4}

        mock_get_publication_counts.side_effect = publication_counts
        mock_get_metrics.return_value = {
            "2026-08": metric_statistics(),
            "2026-09": metric_statistics(count=1, sum=3600, mean=3600, median=3600),
            "total": metric_statistics(count=3, sum=183600, mean=61200, median=3600),
        }
        view = self.build_view(
            MetricsView,
            "/metrics",
            {"start_date": "2026-08-01", "end_date": "2026-09-30", "bucketing": "monthly"},
        )
        court_patch, tribunal_patch = self.choice_patches(MetricsView)

        with court_patch, tribunal_patch:
            context = view.get_context_data()

        assert context["summary_metrics"] == [
            {"label": "Court documents", "value": 10},
            {"label": "Tribunal documents", "value": 4},
            {"label": "Press summaries", "value": 3},
            {"label": "Total documents", "value": 17},
        ]
        assert context["publication_counts"]["rows"][0] == {
            "period": "August 2026",
            "period_raw": "2026-08",
            "court_documents": 4,
            "tribunal_documents": 2,
            "press_summaries": 1,
            "total_documents": 7,
        }
        assert context["publication_counts"]["total_row"]["total_documents"] == 17
        assert context["first_publication_metrics"]["total_row"]["period"] == "Total"
        assert mock_get_publication_counts.call_count == 3
        mock_get_metrics.assert_called_once_with(
            metric="tdr_to_first_publish",
            bucketing="monthly",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 10, 1),
            search_parameters=SearchParameters(),
            include_total=True,
        )

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

    def test_navigation_and_selected_filter_links_preserve_filters(self):
        view = self.build_view(
            MetricsView,
            "/metrics",
            {
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
                "bucketing": "daily",
                "courts": ["example-court"],
            },
        )
        filters = {
            "start_date": date(2026, 9, 1),
            "end_date": date(2026, 9, 30),
            "bucketing": "daily",
            "courts": ["example-court"],
        }

        navigation = view._get_navigation(filters)
        download_url = view._get_download_url(filters)
        selected = view._get_selected_court_filters(self.court_choices, filters)

        assert [item["active"] for item in navigation] == [True, False, False]
        assert parse_qs(urlparse(navigation[1]["url"]).query) == {
            "start_date": ["2026-09-01"],
            "end_date": ["2026-09-30"],
            "bucketing": ["daily"],
            "courts": ["example-court"],
        }
        assert parse_qs(urlparse(download_url).query) == {
            "start_date": ["2026-09-01"],
            "end_date": ["2026-09-30"],
            "bucketing": ["daily"],
            "courts": ["example-court"],
        }
        assert parse_qs(urlparse(selected[0]["remove_url"]).query) == {
            "start_date": ["2026-09-01"],
            "end_date": ["2026-09-30"],
            "bucketing": ["daily"],
        }


class TestJourneyMetrics(MetricsViewTestCase):
    @patch("judgments.views.metrics.api_client.get_metrics")
    def test_formats_totals_and_outlier_statistics(self, mock_get_metrics):
        responses = {
            "tdr_to_first_publish": {
                "2026-08": metric_statistics(),
                "2026-09": metric_statistics(over_24_hours_count=0, over_24_hours_mean=None),
                "total": metric_statistics(count=4, sum=360000, mean=90000, median=90000),
            },
            "tdr_to_latest_publish": {
                "2026-08": metric_statistics(),
                "2026-09": metric_statistics(),
                "total": metric_statistics(count=4),
            },
            "submissions_before_first_publish": {
                "2026-08": metric_statistics(
                    sum=5,
                    mean=2.5,
                    median=2.5,
                    within_24_hours_count=None,
                    over_24_hours_count=None,
                ),
                "2026-09": metric_statistics(
                    sum=3,
                    mean=1.5,
                    median=1.5,
                    within_24_hours_count=None,
                    over_24_hours_count=None,
                ),
                "total": metric_statistics(
                    count=4,
                    sum=8,
                    mean=2,
                    median=2,
                    within_24_hours_count=None,
                    over_24_hours_count=None,
                ),
            },
        }
        mock_get_metrics.side_effect = lambda **kwargs: responses[kwargs["metric"]]
        view = self.build_view(
            JourneyMetricsView,
            "/metrics/journeys",
            {"start_date": "2026-08-01", "end_date": "2026-09-30", "bucketing": "monthly"},
        )
        court_patch, tribunal_patch = self.choice_patches(JourneyMetricsView)

        with court_patch, tribunal_patch:
            context = view.get_context_data()

        assert context["lifecycle_metrics"][0]["total_row"]["period"] == "Total"
        assert context["submission_metrics"]["total_row"]["total"] == 8
        assert context["outlier_metrics"]["rows"][0] == {
            "period": "August 2026",
            "period_raw": "2026-08",
            "count": 1,
            "minimum": {"display": "2 days", "raw": 172800},
            "maximum": {"display": "2 days 2 hours", "raw": 180000},
            "mean": {"display": "2 days 1 hour", "raw": 176400},
            "median": {"display": "2 days 1 hour", "raw": 176400},
            "standard_deviation": {"display": "1 hour", "raw": 3600},
        }
        assert context["outlier_metrics"]["rows"][1]["count"] == 0
        assert context["outlier_metrics"]["total_row"]["period"] == "Total"
        assert context["outlier_threshold"] == "1 day"
        assert mock_get_metrics.call_count == 3
        assert all(item.kwargs["include_total"] is True for item in mock_get_metrics.call_args_list)


class TestCourtMetrics(MetricsViewTestCase):
    @patch("judgments.views.metrics.api_client.get_metrics")
    @patch("judgments.views.metrics.api_client.get_publication_counts")
    def test_does_not_fetch_metrics_until_a_court_is_selected(self, mock_get_counts, mock_get_metrics):
        view = self.build_view(CourtMetricsView, "/metrics/courts")
        court_patch, tribunal_patch = self.choice_patches(CourtMetricsView)

        with court_patch, tribunal_patch:
            context = view.get_context_data()

        assert context["court_publication_metrics"] == []
        assert context["court_lifecycle_metrics"] == []
        assert context["court_filters_open"] is True
        mock_get_counts.assert_not_called()
        mock_get_metrics.assert_not_called()

    @patch("judgments.views.metrics.api_client.get_metrics")
    @patch("judgments.views.metrics.api_client.get_publication_counts")
    def test_fetches_counts_and_lifecycle_metrics_for_selected_courts_only(
        self,
        mock_get_counts,
        mock_get_metrics,
    ):
        mock_get_counts.return_value = {"2026-08": 2, "2026-09": 3, "total": 5}
        mock_get_metrics.return_value = {
            "2026-08": metric_statistics(),
            "2026-09": metric_statistics(),
            "total": metric_statistics(count=4),
        }
        view = self.build_view(
            CourtMetricsView,
            "/metrics/courts",
            {
                "start_date": "2026-08-01",
                "end_date": "2026-09-30",
                "bucketing": "monthly",
                "courts": ["example-court"],
            },
        )
        court_patch, tribunal_patch = self.choice_patches(CourtMetricsView)

        with court_patch, tribunal_patch:
            context = view.get_context_data()

        assert context["court_filters_open"] is False
        assert context["court_publication_metrics"][0]["name"] == "Example Court"
        assert context["court_publication_metrics"][0]["total_row"]["count"] == 5
        assert context["court_lifecycle_metrics"][0]["total_row"]["period"] == "Total"
        mock_get_counts.assert_called_once_with(
            bucketing="monthly",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 10, 1),
            search_parameters=SearchParameters(court="example-court", collections=["judgment"]),
            include_total=True,
        )
        assert mock_get_metrics.call_args_list == [
            call(
                metric="tdr_to_first_publish",
                bucketing="monthly",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 10, 1),
                search_parameters=SearchParameters(court="example-court"),
                include_total=True,
            ),
            call(
                metric="tdr_to_latest_publish",
                bucketing="monthly",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 10, 1),
                search_parameters=SearchParameters(court="example-court"),
                include_total=True,
            ),
        ]

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
        assert filters is not None
        assert filters["start_date"] == date(2026, 7, 7)
        assert filters["end_date"] == date(2026, 10, 7)
        mock_default_date_range.assert_called_once_with()


class TestMetricsXlsxView(MetricsViewTestCase):
    def test_builds_workbook_from_refactored_metrics_context(self):
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
            "publication_counts": {
                "rows": [
                    {
                        "period_raw": "2026-08",
                        "court_documents": 2,
                        "tribunal_documents": 0,
                        "press_summaries": 0,
                        "total_documents": 2,
                    },
                ],
                "total_row": None,
            },
            "lifecycle_metrics": [
                {
                    "show_within_24_hours_percentage": True,
                    "rows": [first_publication_row],
                    "total_row": None,
                },
                {
                    "show_within_24_hours_percentage": False,
                    "rows": [latest_publication_row],
                    "total_row": None,
                },
            ],
            "outlier_metrics": {
                "rows": [
                    {
                        "period_raw": "2026-08",
                        "count": 1,
                        "minimum": duration,
                        "maximum": duration,
                        "mean": duration,
                        "median": duration,
                        "standard_deviation": duration,
                    },
                ],
                "total_row": None,
            },
            "submission_metrics": {
                "rows": [
                    {
                        "period_raw": "2026-08",
                        "count": 2,
                        "total": 3,
                        "median": {"display": "1.5", "raw": 1.5},
                        "mean": {"display": "1.5", "raw": 1.5},
                    },
                ],
                "total_row": None,
            },
            "court_publication_metrics": [
                {
                    "name": "Example Court",
                    "type": "Court",
                    "rows": [{"period_raw": "2026-08", "count": 2}],
                    "total_row": None,
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
                    "total_row": None,
                },
            ],
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
            "Publications",
            "First publication",
            "Latest publication",
            "Outliers",
            "Submissions",
            "Court publications",
            "Court lifecycle",
            "Raw metrics",
        ]
        assert workbook["First publication"]["C2"].value == 1
        assert workbook["Latest publication"]["C1"].value == "Median time (seconds)"
        assert workbook["Court publications"]["D2"].value == 2
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
    @patch.object(MetricsXlsxView, "_get_report_context", return_value=MagicMock())
    def test_downloads_workbook_with_filename_from_filters(
        self,
        mock_get_report_context,
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
        view = MetricsXlsxView.as_view()

        with (
            patch.object(MetricsXlsxView, "_get_court_choices", return_value=[("ewcc", "County Court")]),
            patch.object(MetricsXlsxView, "_get_tribunal_choices", return_value=[("ewca/civ", "Civil Court")]),
        ):
            response = view(request)

        assert response.status_code == 200
        assert response.content == b"workbook"
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert (
            response["Content-Disposition"]
            == 'attachment; filename="metrics_2026-08-12_2026-11-20_daily_ewcc_ewca-civ.xlsx"'
        )
        mock_get_report_context.assert_called_once()
        report_filters, court_definitions = mock_get_report_context.call_args.args
        assert report_filters == {
            "start_date": date(2026, 8, 12),
            "end_date": date(2026, 11, 20),
            "bucketing": "daily",
            "courts": ["ewcc", "ewca/civ"],
        }
        assert court_definitions == [
            {"canonical_param": "ewcc", "name": "County Court", "type": "Court"},
            {"canonical_param": "ewca/civ", "name": "Civil Court", "type": "Tribunal"},
        ]
        mock_build_metrics_workbook.assert_called_once_with(mock_get_report_context.return_value)
