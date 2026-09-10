from django.core.exceptions import BadRequest

from judgments.utils.document_list import (
    SAVED_VIEW_ALL,
    SAVED_VIEW_UNPUBLISHED,
    InvalidDocumentListFilterError,
    get_saved_view_preset,
)
from judgments.utils.view_helpers import get_document_list_filters, get_search_results_from_filters

from .paginated_view import PaginatedView


class DocumentListView(PaginatedView):
    """Shared home / results list view."""

    template_engine = "jinja"
    template_name = "pages/document_list.jinja"
    base_saved_view_id: str
    is_results_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            filters = get_document_list_filters(
                self.request.GET,
                base_saved_view=get_saved_view_preset(self.base_saved_view_id),
            )
        except InvalidDocumentListFilterError as exc:
            raise BadRequest(str(exc)) from exc

        search_context = get_search_results_from_filters(filters)

        context.update(search_context)
        context["pagination_data"] = self.get_pagination_context(
            request=self.request,
            paginator=search_context["paginator"],
        )

        if self.is_results_view:
            context["page_title"] = "Search results"

        return context


class HomeView(DocumentListView):
    base_saved_view_id = SAVED_VIEW_UNPUBLISHED


class ResultsView(DocumentListView):
    """Search/results alias of the document list; stacked on all documents."""

    template_name = "judgment/results.jinja"
    base_saved_view_id = SAVED_VIEW_ALL
    is_results_view = True
