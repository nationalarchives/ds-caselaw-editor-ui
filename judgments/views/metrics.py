from datetime import UTC, date, datetime
from typing import Any, Literal, TypedDict, cast
from urllib.parse import urlencode

from caselawclient.client_helpers.search_helpers import (
    search_and_parse_response,
    search_judgments_and_parse_response,
)
from caselawclient.search_parameters import SearchParameters
from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.views.generic import TemplateView
from ds_caselaw_utils import courts

from judgments.utils import api_client

MetricBucketing = Literal["daily", "monthly"]
LifecycleMetric = Literal["tdr_to_first_publish", "tdr_to_latest_publish"]


class CourtOrTribunalDocumentCount(TypedDict):
    name: str
    type: str
    document_count: int


class DisplayValue(TypedDict):
    display: str
    raw: int | float


class MetricRow(TypedDict, total=False):
    period: str
    period_raw: str
    count: int
    total: int
    mean: DisplayValue | None
    median: DisplayValue | None


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


class SummaryMetric(TypedDict):
    label: str
    value: int


class MetricTable(TypedDict):
    label: str
    rows: list[MetricRow]


class MetricsContext(TypedDict):
    cases_by_court: list[CourtOrTribunalDocumentCount]
    lifecycle_metrics: list[MetricTable]
    submission_metrics: list[MetricTable]
    summary_metrics: list[SummaryMetric]


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


class MetricsView(TemplateView):
    template_engine = "jinja"
    template_name = "metrics/index.jinja"

    @staticmethod
    def _get_documents_count(
        *,
        court: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        judgments_only: bool = True,
    ) -> int:
        search_parameters = SearchParameters(
            court=court,
            date_from=start_date.isoformat() if start_date else None,
            date_to=end_date.isoformat() if end_date else None,
            page_size=1,
        )
        search = search_judgments_and_parse_response if judgments_only else search_and_parse_response
        return int(search(api_client, search_parameters).total)

    @staticmethod
    def _get_court_choices() -> list[tuple[str, str]]:
        return MetricsView._get_choices(courts.get_grouped_show_to_editors_courts())

    @staticmethod
    def _get_tribunal_choices() -> list[tuple[str, str]]:
        return MetricsView._get_choices(courts.get_grouped_show_to_editors_tribunals())

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

    def _get_court_and_tribunal_document_counts(
        self,
        *,
        selected_courts: set[str],
        start_date: date,
        end_date: date,
    ) -> list[CourtOrTribunalDocumentCount]:
        court_and_tribunal_document_counts: list[CourtOrTribunalDocumentCount] = []
        grouped_courts_and_tribunals = [
            ("Court", courts.get_grouped_show_to_editors_courts()),
            ("Tribunal", courts.get_grouped_show_to_editors_tribunals()),
        ]

        for court_type, groups in grouped_courts_and_tribunals:
            for group in groups:
                for court_or_tribunal in group.courts:
                    if selected_courts and court_or_tribunal.canonical_param not in selected_courts:
                        continue
                    documents_count = self._get_documents_count(
                        court=court_or_tribunal.canonical_param,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    if documents_count:
                        court_and_tribunal_document_counts.append(
                            {
                                "name": str(court_or_tribunal.name),
                                "type": court_type,
                                "document_count": documents_count,
                            },
                        )

        return court_and_tribunal_document_counts

    @staticmethod
    def _format_period(value: str, bucketing: MetricBucketing) -> str:
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

    @classmethod
    def _format_duration_metrics(
        cls,
        metrics: dict[str, Any],
        bucketing: MetricBucketing,
    ) -> list[MetricRow]:
        return [
            {
                "period": cls._format_period(period, bucketing),
                "period_raw": period,
                "count": values["count"],
                "mean": cls._display_duration(values["mean"]),
                "median": cls._display_duration(values["median"]),
            }
            for period, values in sorted(metrics.items())
        ]

    @classmethod
    def _format_submission_metrics(
        cls,
        metrics: dict[str, Any],
        bucketing: MetricBucketing,
    ) -> list[MetricRow]:
        return [
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
            for period, values in sorted(metrics.items())
        ]

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
    def _get_selected_court_filters(
        choices: list[tuple[str, str]],
        filters: MetricFilters | None,
    ) -> list[SelectedCourtFilter]:
        if filters is None:
            return []

        selected_courts = set(filters["courts"])
        return [
            {
                "label": label,
                "remove_url": f"{reverse('metrics')}?{
                    urlencode(
                        {
                            'start_date': filters['start_date'].isoformat(),
                            'end_date': filters['end_date'].isoformat(),
                            'bucketing': filters['bucketing'],
                            'courts': [court for court in filters['courts'] if court != value],
                        },
                        doseq=True,
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

    def _get_document_metrics(
        self,
        filters: MetricFilters,
        *,
        court_filter: str | None,
    ) -> tuple[list[CourtOrTribunalDocumentCount], list[SummaryMetric]]:
        document_counts = self._get_court_and_tribunal_document_counts(
            selected_courts=set(filters["courts"]),
            start_date=filters["start_date"],
            end_date=filters["end_date"],
        )
        total_judgment_count = self._get_documents_count(
            court=court_filter,
            start_date=filters["start_date"],
            end_date=filters["end_date"],
        )
        total_document_count = self._get_documents_count(
            court=court_filter,
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            judgments_only=False,
        )
        return document_counts, self._get_summary_metrics(
            document_counts,
            total_judgment_count=total_judgment_count,
            total_document_count=total_document_count,
        )

    @staticmethod
    def _get_summary_metrics(
        document_counts: list[CourtOrTribunalDocumentCount],
        *,
        total_judgment_count: int,
        total_document_count: int,
    ) -> list[SummaryMetric]:
        court_document_count = sum(item["document_count"] for item in document_counts if item["type"] == "Court")
        tribunal_document_count = sum(item["document_count"] for item in document_counts if item["type"] == "Tribunal")
        return [
            {"label": "Court documents", "value": court_document_count},
            {"label": "Tribunal documents", "value": tribunal_document_count},
            {"label": "Press summaries", "value": max(total_document_count - total_judgment_count, 0)},
            {"label": "Total documents", "value": total_document_count},
            {"label": "Courts and tribunals", "value": len(document_counts)},
        ]

    def _get_lifecycle_metrics(
        self,
        filters: MetricFilters,
        search_parameters: SearchParameters,
    ) -> list[MetricTable]:
        metric_types: tuple[tuple[str, LifecycleMetric], ...] = (
            ("Time to first publication", "tdr_to_first_publish"),
            ("Time to latest publication", "tdr_to_latest_publish"),
        )
        return [
            {
                "label": label,
                "rows": self._format_duration_metrics(
                    api_client.get_metrics(
                        metric=metric,
                        bucketing=filters["bucketing"],
                        start_date=filters["start_date"],
                        end_date=filters["end_date"],
                        search_parameters=search_parameters,
                    ),
                    filters["bucketing"],
                ),
            }
            for label, metric in metric_types
        ]

    def _get_submission_metrics(
        self,
        filters: MetricFilters,
        search_parameters: SearchParameters,
    ) -> list[MetricTable]:
        return [
            {
                "label": "Submissions before first publication",
                "rows": self._format_submission_metrics(
                    api_client.get_metrics(
                        metric="submissions_before_first_publish",
                        bucketing=filters["bucketing"],
                        start_date=filters["start_date"],
                        end_date=filters["end_date"],
                        search_parameters=search_parameters,
                    ),
                    filters["bucketing"],
                ),
            },
        ]

    def _get_metrics_context(self, filters: MetricFilters | None) -> MetricsContext:
        if filters is None:
            return {
                "cases_by_court": [],
                "lifecycle_metrics": [],
                "submission_metrics": [],
                "summary_metrics": self._get_summary_metrics(
                    [],
                    total_judgment_count=0,
                    total_document_count=0,
                ),
            }

        court_filter = ",".join(filters["courts"]) or None
        document_counts, summary_metrics = self._get_document_metrics(filters, court_filter=court_filter)
        search_parameters = SearchParameters(court=court_filter)
        return {
            "cases_by_court": document_counts,
            "lifecycle_metrics": self._get_lifecycle_metrics(filters, search_parameters),
            "submission_metrics": self._get_submission_metrics(filters, search_parameters),
            "summary_metrics": summary_metrics,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        court_choices = self._get_court_choices()
        tribunal_choices = self._get_tribunal_choices()
        filter_form, metric_filters = self._get_metric_filters([*court_choices, *tribunal_choices])
        selected_courts = set(filter_form["courts"].value() or [])
        context.update(
            {
                "page_title": "Metrics",
                "filter_form": filter_form,
                "court_options": self._get_checkbox_options(court_choices, selected_courts),
                "tribunal_options": self._get_checkbox_options(tribunal_choices, selected_courts),
                "selected_court_filters": self._get_selected_court_filters(
                    [*court_choices, *tribunal_choices],
                    metric_filters,
                ),
                **self._get_metrics_context(metric_filters),
            },
        )
        return context
