from typing import TypedDict

from caselawclient.client_helpers.search_helpers import (
    search_and_parse_response,
    search_judgments_and_parse_response,
)
from caselawclient.search_parameters import SearchParameters
from django.views.generic import TemplateView
from ds_caselaw_utils import courts

from judgments.utils import api_client


class CourtOrTribunalDocumentCount(TypedDict):
    name: str
    type: str
    document_count: int


class MetricsView(TemplateView):
    template_engine = "jinja"
    template_name = "metrics/index.jinja"

    @staticmethod
    def _get_documents_count(*, court: str | None = None, judgments_only: bool = True) -> int:
        search_parameters = SearchParameters(court=court, page_size=1)
        search = search_judgments_and_parse_response if judgments_only else search_and_parse_response
        return int(search(api_client, search_parameters).total)

    def _get_court_and_tribunal_document_counts(self) -> list[CourtOrTribunalDocumentCount]:
        court_and_tribunal_document_counts: list[CourtOrTribunalDocumentCount] = []
        grouped_courts_and_tribunals = [
            ("Court", courts.get_grouped_show_to_editors_courts()),
            ("Tribunal", courts.get_grouped_show_to_editors_tribunals()),
        ]

        for court_type, groups in grouped_courts_and_tribunals:
            for group in groups:
                for court_or_tribunal in group.courts:
                    documents_count = self._get_documents_count(court=court_or_tribunal.canonical_param)

                    if documents_count:
                        court_and_tribunal_document_counts.append(
                            {
                                "name": str(court_or_tribunal.name),
                                "type": court_type,
                                "document_count": documents_count,
                            },
                        )

        return court_and_tribunal_document_counts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        court_and_tribunal_document_counts = self._get_court_and_tribunal_document_counts()
        total_judgment_count = self._get_documents_count()
        total_document_count = self._get_documents_count(judgments_only=False)

        court_document_count = sum(
            court_or_tribunal["document_count"]
            for court_or_tribunal in court_and_tribunal_document_counts
            if court_or_tribunal["type"] == "Court"
        )
        tribunal_document_count = sum(
            court_or_tribunal["document_count"]
            for court_or_tribunal in court_and_tribunal_document_counts
            if court_or_tribunal["type"] == "Tribunal"
        )

        context.update(
            {
                "page_title": "Metrics",
                "summary_metrics": [
                    {"label": "Court documents", "value": court_document_count},
                    {"label": "Tribunal documents", "value": tribunal_document_count},
                    {"label": "Press summaries", "value": max(total_document_count - total_judgment_count, 0)},
                    {"label": "Total documents", "value": total_document_count},
                    {
                        "label": "Courts and tribunals",
                        "value": len(court_and_tribunal_document_counts),
                    },
                ],
                "cases_by_court": court_and_tribunal_document_counts,
            },
        )
        return context
