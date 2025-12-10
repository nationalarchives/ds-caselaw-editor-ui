from typing import Any

from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from judgments.models import BulkReparseRunLog
from judgments.utils import api_client


class Index(TemplateView):
    template_name = "reports/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Reports"

        return context


def get_rows_from_result(result: list | list[list[Any]]) -> list[list[Any]]:
    """
    If there are results, MarkLogic returns a list of lists where the first row is column names. If there are no
    results, it returns a single list of column names.

    :return: A list of results, which may be empty.
    """
    if isinstance(result[0], list):
        return result[1:]
    return []


class AwaitingParse(TemplateView):
    template_name = "reports/awaiting_parse.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        target_parser_version = api_client.get_highest_parser_version()

        context["page_title"] = "Documents awaiting reparsing"
        context["target_parser_version"] = f"{target_parser_version[0]}.{target_parser_version[1]}"
        context["report_limit"] = 200

        context["total"] = api_client.get_count_pending_parse_for_version(
            target_parser_version,
        )

        context["documents"] = get_rows_from_result(
            api_client.get_documents_pending_parse_for_version(
                target_parser_version,
                context["report_limit"],
            ),
        )

        return context


class BulkReparseRunLogListView(ListView):
    model = BulkReparseRunLog
    paginate_by = 50

    template_name = "reports/bulk_reparse_run_log_list.html"


class BulkReparseRunLogDetailView(DetailView):
    model = BulkReparseRunLog

    template_name = "reports/bulk_reparse_run_log_detail.html"


class AwaitingEnrichment(TemplateView):
    template_name = "reports/awaiting_enrichment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        target_enrichment_version = api_client.get_highest_enrichment_version()
        target_parser_version = api_client.get_highest_parser_version()

        context["page_title"] = "Documents awaiting enrichment"
        context["target_enrichment_version"] = f"{target_enrichment_version[0]}.{target_enrichment_version[1]}"
        context["target_parser_version"] = f"{target_parser_version[0]}.{target_parser_version[1]}"

        context["documents"] = get_rows_from_result(
            api_client.get_pending_enrichment_for_version(
                target_enrichment_version=target_enrichment_version,
                target_parser_version=target_parser_version,
            ),
        )

        return context


class LockedDocuments(TemplateView):
    template_name = "reports/locked_documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Locked documents"

        context["locks"] = api_client.get_locked_documents()

        context["lock_count"] = len(context["locks"])

        return context
