from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, TypedDict, cast
from urllib.parse import urlencode

from caselawclient.metrics import MetricName, MetricStatistics
from caselawclient.search_parameters import SearchParameters
from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.views.generic import TemplateView
from ds_caselaw_utils import courts

from judgments.utils import api_client
from judgments.utils.metrics_xlsx import build_metrics_workbook

MetricBucketing = Literal["daily", "monthly"]
OUTLIER_THRESHOLD_SECONDS = 86400


class DisplayValue(TypedDict):
    display: str
    raw: int | float


class PercentageValue(DisplayValue):
    numerator: int
    denominator: int


class MetricRow(TypedDict, total=False):
    period: str
    period_raw: str
    count: int
    total: int
    mean: DisplayValue | None
    median: DisplayValue | None
    within_24_hours_percentage: PercentageValue | None


class MetricTable(TypedDict):
    label: str
    rows: list[MetricRow]
    total_row: MetricRow | None
    show_within_24_hours_percentage: bool


class OutlierMetricRow(TypedDict):
    period: str
    period_raw: str
    count: int
    minimum: DisplayValue | None
    maximum: DisplayValue | None
    mean: DisplayValue | None
    median: DisplayValue | None
    standard_deviation: DisplayValue | None


class OutlierMetricTable(TypedDict):
    rows: list[OutlierMetricRow]
    total_row: OutlierMetricRow | None


class PublicationCountRow(TypedDict):
    period: str
    period_raw: str
    count: int


class PublicationOverviewRow(TypedDict):
    period: str
    period_raw: str
    court_documents: int
    tribunal_documents: int
    press_summaries: int
    total_documents: int


class PublicationOverviewTable(TypedDict):
    rows: list[PublicationOverviewRow]
    total_row: PublicationOverviewRow | None


class CourtDefinition(TypedDict):
    canonical_param: str
    name: str
    type: str


class CourtPublicationTable(TypedDict):
    name: str
    type: str
    rows: list[PublicationCountRow]
    total_row: PublicationCountRow | None


class CourtLifecycleMetricRow(TypedDict):
    period: str
    period_raw: str
    first_publication: MetricRow | None
    latest_publication: MetricRow | None


class CourtLifecycleMetricTable(TypedDict):
    name: str
    type: str
    rows: list[CourtLifecycleMetricRow]
    total_row: CourtLifecycleMetricRow | None


class MetricFilters(TypedDict):
    start_date: date
    end_date: date
    bucketing: MetricBucketing
    courts: list[str]


class SelectedCourtFilter(TypedDict):
    label: str
    remove_url: str


class CheckboxOption(TypedDict):
    value: str
    text: str
    checked: bool


class MetricsNavigationItem(TypedDict):
    label: str
    url: str
    active: bool


class RawMetricResponse(TypedDict):
    metric: MetricName
    court: str
    response: dict[str, MetricStatistics]


class MetricsFilterForm(forms.Form):
    start_date = forms.DateField(
        label="Start date",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"class": "govuk-input", "type": "date"}),
    )
    end_date = forms.DateField(
        label="End date",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"class": "govuk-input", "type": "date"}),
    )
    bucketing = forms.ChoiceField(
        label="Group results by",
        choices=(("daily", "Day"), ("monthly", "Month")),
        widget=forms.Select(attrs={"class": "govuk-select"}),
    )
    courts = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, court_choices: list[tuple[str, str]], **kwargs):
        super().__init__(*args, **kwargs)
        court_field = cast("forms.MultipleChoiceField", self.fields["courts"])
        court_field.choices = court_choices

    def clean(self):
        cleaned_data = super().clean() or {}
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date >= end_date:
            error_message = "End date must be after start date."
            raise ValidationError(error_message)
        return cleaned_data


class BaseMetricsView(TemplateView):
    template_engine = "jinja"
    route_name = "metrics"
    court_filter_hint = "Select one or more, or leave blank to include them all"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.raw_metric_responses: list[RawMetricResponse] = []

    @staticmethod
    def _get_court_choices() -> list[tuple[str, str]]:
        return BaseMetricsView._get_choices(courts.get_grouped_show_to_editors_courts())

    @staticmethod
    def _get_tribunal_choices() -> list[tuple[str, str]]:
        return BaseMetricsView._get_choices(courts.get_grouped_show_to_editors_tribunals())

    @staticmethod
    def _get_choices(groups: Any) -> list[tuple[str, str]]:
        return sorted(
            [
                (court.canonical_param, str(court.name))
                for group in groups
                for court in group.courts
                if court.canonical_param
            ],
            key=lambda choice: choice[1],
        )

    @staticmethod
    def _default_date_range() -> tuple[date, date]:
        today = datetime.now(UTC).date()
        return today - relativedelta(months=3), today

    def _get_metric_filters(
        self,
        court_choices: list[tuple[str, str]],
    ) -> tuple[MetricsFilterForm, MetricFilters | None]:
        start_date, end_date = self._default_date_range()
        initial: MetricFilters = {
            "start_date": start_date,
            "end_date": end_date,
            "bucketing": "monthly",
            "courts": [],
        }
        request = getattr(self, "request", None)
        data = None
        if request is not None and request.GET:
            data = request.GET.copy()
            data["start_date"] = data.get("start_date") or start_date.isoformat()
            data["end_date"] = data.get("end_date") or end_date.isoformat()
            data["bucketing"] = data.get("bucketing") or "monthly"
        form = MetricsFilterForm(data=data, initial=initial, court_choices=court_choices)
        if not form.is_bound:
            return form, initial
        if form.is_valid():
            return form, cast("MetricFilters", form.cleaned_data)
        return form, None

    @staticmethod
    def _filter_query(filters: MetricFilters) -> str:
        return urlencode(
            {
                "start_date": filters["start_date"].isoformat(),
                "end_date": filters["end_date"].isoformat(),
                "bucketing": filters["bucketing"],
                "courts": filters["courts"],
            },
            doseq=True,
        )

    def _get_selected_court_filters(
        self,
        choices: list[tuple[str, str]],
        filters: MetricFilters | None,
    ) -> list[SelectedCourtFilter]:
        if filters is None:
            return []

        selected_courts = set(filters["courts"])
        return [
            {
                "label": label,
                "remove_url": f"{reverse(self.route_name)}?{
                    self._filter_query(
                        {
                            **filters,
                            'courts': [court for court in filters['courts'] if court != value],
                        },
                    )
                }",
            }
            for value, label in choices
            if value in selected_courts
        ]

    @staticmethod
    def _get_checkbox_options(
        choices: list[tuple[str, str]],
        selected_courts: set[str],
    ) -> list[CheckboxOption]:
        return [{"value": value, "text": label, "checked": value in selected_courts} for value, label in choices]

    def _get_navigation(self, filters: MetricFilters | None) -> list[MetricsNavigationItem]:
        query = f"?{self._filter_query(filters)}" if filters else ""
        return [
            {"label": label, "url": f"{reverse(route_name)}{query}", "active": route_name == self.route_name}
            for label, route_name in (
                ("Overview", "metrics"),
                ("Journey metrics", "metrics-journeys"),
                ("Courts and tribunals", "metrics-courts"),
            )
        ]

    @staticmethod
    def _get_download_url(filters: MetricFilters | None) -> str | None:
        if filters is None:
            return None
        return f"{reverse('metrics-xlsx')}?{BaseMetricsView._filter_query(filters)}"

    @staticmethod
    def _court_definitions(
        court_choices: list[tuple[str, str]],
        tribunal_choices: list[tuple[str, str]],
    ) -> list[CourtDefinition]:
        court_definitions: list[CourtDefinition] = [
            {"canonical_param": value, "name": label, "type": "Court"} for value, label in court_choices
        ]
        tribunal_definitions: list[CourtDefinition] = [
            {"canonical_param": value, "name": label, "type": "Tribunal"} for value, label in tribunal_choices
        ]
        return [*court_definitions, *tribunal_definitions]

    @staticmethod
    def _format_period(value: str, bucketing: MetricBucketing) -> str:
        if value == "total":
            return "Total"
        date_format = "%Y-%m" if bucketing == "monthly" else "%Y-%m-%d"
        parsed_date = datetime.strptime(value, date_format).date()
        if bucketing == "monthly":
            return parsed_date.strftime("%B %Y")
        return f"{parsed_date.day} {parsed_date:%B %Y}"

    @staticmethod
    def _format_duration(value: float) -> str:
        remaining = round(value)
        parts: list[str] = []
        for unit_seconds, label in ((86400, "day"), (3600, "hour"), (60, "minute"), (1, "second")):
            amount, remaining = divmod(remaining, unit_seconds)
            if amount:
                parts.append(f"{amount} {label}{'' if amount == 1 else 's'}")
            if len(parts) == 2:
                break
        return " ".join(parts) or "0 seconds"

    @classmethod
    def _display_duration(cls, value: float | None) -> DisplayValue | None:
        if value is None:
            return None
        return {"display": cls._format_duration(value), "raw": value}

    @staticmethod
    def _display_percentage(numerator: int | None, denominator: int) -> PercentageValue | None:
        if numerator is None or denominator == 0:
            return None
        percentage = numerator / denominator * 100
        return {
            "display": f"{percentage:.1f}%",
            "raw": percentage,
            "numerator": numerator,
            "denominator": denominator,
        }

    @staticmethod
    def _mean_within_24_hours(values: MetricStatistics) -> float | None:
        within_count = values["within_24_hours_count"]
        over_count = values["over_24_hours_count"]
        if within_count in (None, 0) or over_count is None:
            return None
        if over_count and values["over_24_hours_mean"] is None:
            return None
        over_total = over_count * (values["over_24_hours_mean"] or 0)
        return (values["sum"] - over_total) / within_count

    @staticmethod
    def _ordered_items(values: dict[str, Any]):
        return sorted(values.items(), key=lambda item: (item[0] == "total", item[0]))

    @staticmethod
    def _split_total_row[T](rows: list[T], period_getter) -> tuple[list[T], T | None]:
        dated_rows = [row for row in rows if period_getter(row) != "total"]
        total_row = next((row for row in rows if period_getter(row) == "total"), None)
        return dated_rows, total_row if len(dated_rows) > 1 else None

    @classmethod
    def _format_duration_metrics(
        cls,
        metrics: dict[str, MetricStatistics],
        bucketing: MetricBucketing,
        *,
        include_within_24_hours_percentage: bool = False,
        exclude_over_24_hours_from_mean: bool = False,
    ) -> tuple[list[MetricRow], MetricRow | None]:
        rows: list[MetricRow] = []
        for period, values in cls._ordered_items(metrics):
            row: MetricRow = {
                "period": cls._format_period(period, bucketing),
                "period_raw": period,
                "count": values["count"],
                "mean": cls._display_duration(
                    cls._mean_within_24_hours(values) if exclude_over_24_hours_from_mean else values["mean"],
                ),
                "median": cls._display_duration(values["median"]),
            }
            if include_within_24_hours_percentage:
                row["within_24_hours_percentage"] = cls._display_percentage(
                    values["within_24_hours_count"],
                    values["count"],
                )
            rows.append(row)
        return cls._split_total_row(rows, lambda row: row["period_raw"])

    @classmethod
    def _duration_table(
        cls,
        label: str,
        metrics: dict[str, MetricStatistics],
        bucketing: MetricBucketing,
        *,
        show_within_24_hours_percentage: bool,
    ) -> MetricTable:
        rows, total_row = cls._format_duration_metrics(
            metrics,
            bucketing,
            include_within_24_hours_percentage=show_within_24_hours_percentage,
            exclude_over_24_hours_from_mean=show_within_24_hours_percentage,
        )
        return {
            "label": label,
            "rows": rows,
            "total_row": total_row,
            "show_within_24_hours_percentage": show_within_24_hours_percentage,
        }

    @classmethod
    def _submission_table(
        cls,
        metrics: dict[str, MetricStatistics],
        bucketing: MetricBucketing,
    ) -> MetricTable:
        rows: list[MetricRow] = [
            {
                "period": cls._format_period(period, bucketing),
                "period_raw": period,
                "count": values["count"],
                "total": values["sum"],
                "mean": None if values["mean"] is None else {"display": f"{values['mean']:.1f}", "raw": values["mean"]},
                "median": None
                if values["median"] is None
                else {"display": f"{values['median']:.1f}", "raw": values["median"]},
            }
            for period, values in cls._ordered_items(metrics)
        ]
        dated_rows, total_row = cls._split_total_row(rows, lambda row: row["period_raw"])
        return {
            "label": "Submissions before first publication",
            "rows": dated_rows,
            "total_row": total_row,
            "show_within_24_hours_percentage": False,
        }

    @classmethod
    def _outlier_table(
        cls,
        metrics: dict[str, MetricStatistics],
        bucketing: MetricBucketing,
    ) -> OutlierMetricTable:
        rows: list[OutlierMetricRow] = [
            {
                "period": cls._format_period(period, bucketing),
                "period_raw": period,
                "count": values["over_24_hours_count"] or 0,
                "minimum": cls._display_duration(values["over_24_hours_minimum"]),
                "maximum": cls._display_duration(values["over_24_hours_maximum"]),
                "mean": cls._display_duration(values["over_24_hours_mean"]),
                "median": cls._display_duration(values["over_24_hours_median"]),
                "standard_deviation": cls._display_duration(values["over_24_hours_standard_deviation"]),
            }
            for period, values in cls._ordered_items(metrics)
        ]
        dated_rows, total_row = cls._split_total_row(rows, lambda row: row["period_raw"])
        return {"rows": dated_rows, "total_row": total_row}

    @classmethod
    def _publication_count_rows(
        cls,
        counts: dict[str, int],
        bucketing: MetricBucketing,
    ) -> tuple[list[PublicationCountRow], PublicationCountRow | None]:
        rows: list[PublicationCountRow] = [
            {
                "period": cls._format_period(period, bucketing),
                "period_raw": period,
                "count": count,
            }
            for period, count in cls._ordered_items(counts)
        ]
        return cls._split_total_row(rows, lambda row: row["period_raw"])

    def _get_metric(
        self,
        metric: MetricName,
        filters: MetricFilters,
        search_parameters: SearchParameters,
    ) -> dict[str, MetricStatistics]:
        response = api_client.get_metrics(
            metric=metric,
            bucketing=filters["bucketing"],
            start_date=filters["start_date"],
            end_date=filters["end_date"] + timedelta(days=1),
            search_parameters=search_parameters,
            include_total=True,
        )
        court = search_parameters.court or ""
        if not any(item["metric"] == metric and item["court"] == court for item in self.raw_metric_responses):
            self.raw_metric_responses.append({"metric": metric, "court": court, "response": response})
        return response

    def _get_publication_counts(
        self,
        filters: MetricFilters,
        search_parameters: SearchParameters,
    ) -> dict[str, int]:
        return api_client.get_publication_counts(
            bucketing=filters["bucketing"],
            start_date=filters["start_date"],
            end_date=filters["end_date"] + timedelta(days=1),
            search_parameters=search_parameters,
            include_total=True,
        )

    def get_metrics_context(
        self,
        filters: MetricFilters | None,
        court_definitions: list[CourtDefinition],
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        court_choices = self._get_court_choices()
        tribunal_choices = self._get_tribunal_choices()
        all_choices = [*court_choices, *tribunal_choices]
        filter_form, metric_filters = self._get_metric_filters(all_choices)
        selected_courts = set(filter_form["courts"].value() or [])
        court_definitions = self._court_definitions(court_choices, tribunal_choices)
        context.update(
            {
                "page_title": "Metrics",
                "filter_form": filter_form,
                "court_options": self._get_checkbox_options(court_choices, selected_courts),
                "tribunal_options": self._get_checkbox_options(tribunal_choices, selected_courts),
                "court_filter_hint": self.court_filter_hint,
                "download_url": self._get_download_url(metric_filters),
                "selected_court_filters": self._get_selected_court_filters(all_choices, metric_filters),
                "metrics_navigation": self._get_navigation(metric_filters),
                **self.get_metrics_context(metric_filters, court_definitions),
            },
        )
        return context


class MetricsView(BaseMetricsView):
    template_name = "metrics/index.jinja"
    route_name = "metrics"

    @classmethod
    def _overview_table(
        cls,
        court_counts: dict[str, int],
        tribunal_counts: dict[str, int],
        press_summary_counts: dict[str, int],
        bucketing: MetricBucketing,
    ) -> PublicationOverviewTable:
        periods = court_counts.keys() | tribunal_counts.keys() | press_summary_counts.keys()
        rows: list[PublicationOverviewRow] = []
        for period in sorted(periods, key=lambda value: (value == "total", value)):
            court_count = court_counts.get(period, 0)
            tribunal_count = tribunal_counts.get(period, 0)
            press_summary_count = press_summary_counts.get(period, 0)
            rows.append(
                {
                    "period": cls._format_period(period, bucketing),
                    "period_raw": period,
                    "court_documents": court_count,
                    "tribunal_documents": tribunal_count,
                    "press_summaries": press_summary_count,
                    "total_documents": court_count + tribunal_count + press_summary_count,
                },
            )
        dated_rows, total_row = cls._split_total_row(rows, lambda row: row["period_raw"])
        return {"rows": dated_rows, "total_row": total_row}

    def get_metrics_context(
        self,
        filters: MetricFilters | None,
        court_definitions: list[CourtDefinition],
    ) -> dict[str, Any]:
        if filters is None:
            return {
                "publication_counts": {"rows": [], "total_row": None},
                "summary_metrics": [],
                "first_publication_metrics": None,
            }

        selected = set(filters["courts"])
        applicable = [court for court in court_definitions if not selected or court["canonical_param"] in selected]
        court_codes = [court["canonical_param"] for court in applicable if court["type"] == "Court"]
        tribunal_codes = [court["canonical_param"] for court in applicable if court["type"] == "Tribunal"]
        selected_filter = ",".join(filters["courts"]) or None

        court_counts = (
            self._get_publication_counts(
                filters,
                SearchParameters(court=",".join(court_codes), collections=["judgment"]),
            )
            if court_codes
            else {}
        )
        tribunal_counts = (
            self._get_publication_counts(
                filters,
                SearchParameters(court=",".join(tribunal_codes), collections=["judgment"]),
            )
            if tribunal_codes
            else {}
        )
        press_summary_counts = self._get_publication_counts(
            filters,
            SearchParameters(court=selected_filter, collections=["press-summary"]),
        )
        publication_counts = self._overview_table(
            court_counts,
            tribunal_counts,
            press_summary_counts,
            filters["bucketing"],
        )
        totals = publication_counts["total_row"]
        if totals is None:
            rows = publication_counts["rows"]
            totals = rows[0] if rows else None

        first_publication = self._get_metric(
            "tdr_to_first_publish",
            filters,
            SearchParameters(court=selected_filter),
        )
        return {
            "publication_counts": publication_counts,
            "summary_metrics": []
            if totals is None
            else [
                {"label": "Court documents", "value": totals["court_documents"]},
                {"label": "Tribunal documents", "value": totals["tribunal_documents"]},
                {"label": "Press summaries", "value": totals["press_summaries"]},
                {"label": "Total documents", "value": totals["total_documents"]},
            ],
            "first_publication_metrics": self._duration_table(
                "Time to first publication",
                first_publication,
                filters["bucketing"],
                show_within_24_hours_percentage=True,
            ),
        }


class JourneyMetricsView(BaseMetricsView):
    template_name = "metrics/journeys.jinja"
    route_name = "metrics-journeys"

    def get_metrics_context(
        self,
        filters: MetricFilters | None,
        court_definitions: list[CourtDefinition],
    ) -> dict[str, Any]:
        if filters is None:
            return {"lifecycle_metrics": [], "submission_metrics": None, "outlier_metrics": None}

        search_parameters = SearchParameters(court=",".join(filters["courts"]) or None)
        first_publication = self._get_metric("tdr_to_first_publish", filters, search_parameters)
        latest_publication = self._get_metric("tdr_to_latest_publish", filters, search_parameters)
        submissions = self._get_metric("submissions_before_first_publish", filters, search_parameters)
        return {
            "lifecycle_metrics": [
                self._duration_table(
                    "Time to first publication",
                    first_publication,
                    filters["bucketing"],
                    show_within_24_hours_percentage=True,
                ),
                self._duration_table(
                    "Time to latest publication",
                    latest_publication,
                    filters["bucketing"],
                    show_within_24_hours_percentage=False,
                ),
            ],
            "submission_metrics": self._submission_table(submissions, filters["bucketing"]),
            "outlier_metrics": self._outlier_table(first_publication, filters["bucketing"]),
            "outlier_threshold": self._format_duration(OUTLIER_THRESHOLD_SECONDS),
        }


class CourtMetricsView(BaseMetricsView):
    template_name = "metrics/courts.jinja"
    route_name = "metrics-courts"
    court_filter_hint = "Select one or more courts or tribunals to view their metrics."

    @classmethod
    def _combine_court_lifecycle_metrics(
        cls,
        first_publication: MetricTable,
        latest_publication: MetricTable,
    ) -> tuple[list[CourtLifecycleMetricRow], CourtLifecycleMetricRow | None]:
        first_rows = {row["period_raw"]: row for row in first_publication["rows"]}
        latest_rows = {row["period_raw"]: row for row in latest_publication["rows"]}
        rows: list[CourtLifecycleMetricRow] = [
            {
                "period": (first_rows.get(period) or latest_rows[period])["period"],
                "period_raw": period,
                "first_publication": first_rows.get(period),
                "latest_publication": latest_rows.get(period),
            }
            for period in sorted(first_rows.keys() | latest_rows.keys())
        ]
        first_total = first_publication["total_row"]
        latest_total = latest_publication["total_row"]
        total_row: CourtLifecycleMetricRow | None = None
        if first_total is not None or latest_total is not None:
            total_row = {
                "period": "Total",
                "period_raw": "total",
                "first_publication": first_total,
                "latest_publication": latest_total,
            }
        return rows, total_row

    def get_metrics_context(
        self,
        filters: MetricFilters | None,
        court_definitions: list[CourtDefinition],
    ) -> dict[str, Any]:
        if filters is None:
            return {
                "court_publication_metrics": [],
                "court_lifecycle_metrics": [],
                "court_filters_open": True,
            }

        selected = set(filters["courts"])
        selected_definitions = [court for court in court_definitions if court["canonical_param"] in selected]
        publication_tables: list[CourtPublicationTable] = []
        lifecycle_tables: list[CourtLifecycleMetricTable] = []
        for court in selected_definitions:
            search_parameters = SearchParameters(court=court["canonical_param"])
            publication_search_parameters = SearchParameters(
                court=court["canonical_param"],
                collections=["judgment"],
            )
            publication_rows, publication_total = self._publication_count_rows(
                self._get_publication_counts(filters, publication_search_parameters),
                filters["bucketing"],
            )
            publication_tables.append(
                {
                    "name": court["name"],
                    "type": court["type"],
                    "rows": publication_rows,
                    "total_row": publication_total,
                },
            )

            first_table = self._duration_table(
                "Time to first publication",
                self._get_metric("tdr_to_first_publish", filters, search_parameters),
                filters["bucketing"],
                show_within_24_hours_percentage=True,
            )
            latest_table = self._duration_table(
                "Time to latest publication",
                self._get_metric("tdr_to_latest_publish", filters, search_parameters),
                filters["bucketing"],
                show_within_24_hours_percentage=False,
            )
            lifecycle_rows, lifecycle_total = self._combine_court_lifecycle_metrics(first_table, latest_table)
            lifecycle_tables.append(
                {
                    "name": court["name"],
                    "type": court["type"],
                    "rows": lifecycle_rows,
                    "total_row": lifecycle_total,
                },
            )

        return {
            "court_publication_metrics": publication_tables,
            "court_lifecycle_metrics": lifecycle_tables,
            "court_filters_open": not selected_definitions,
        }


class MetricsXlsxView(BaseMetricsView):
    @staticmethod
    def _get_filename(filters: MetricFilters) -> str:
        parts = [
            "metrics",
            filters["start_date"].isoformat(),
            filters["end_date"].isoformat(),
            filters["bucketing"],
            *(court.replace("/", "-") for court in filters["courts"]),
        ]
        return f"{'_'.join(parts)}.xlsx"

    def _get_report_context(
        self,
        filters: MetricFilters,
        court_definitions: list[CourtDefinition],
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        raw_metrics: list[RawMetricResponse] = []
        for view_class in (MetricsView, JourneyMetricsView, CourtMetricsView):
            view = view_class()
            context.update(view.get_metrics_context(filters, court_definitions))
            for response in view.raw_metric_responses:
                if not any(
                    item["metric"] == response["metric"] and item["court"] == response["court"] for item in raw_metrics
                ):
                    raw_metrics.append(response)
        context["raw_metrics"] = raw_metrics
        return context

    def get(self, request, *args, **kwargs):
        court_choices = self._get_court_choices()
        tribunal_choices = self._get_tribunal_choices()
        _, metric_filters = self._get_metric_filters([*court_choices, *tribunal_choices])
        if metric_filters is None:
            return HttpResponseBadRequest("The metrics filters are invalid.")

        report_context = self._get_report_context(
            metric_filters,
            self._court_definitions(court_choices, tribunal_choices),
        )
        response = HttpResponse(
            build_metrics_workbook(report_context),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{self._get_filename(metric_filters)}"'
        return response
