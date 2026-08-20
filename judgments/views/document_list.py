from waffle import flag_is_active

from judgments.utils.document_list import PUBLICATION_STATUS_ALL, PUBLICATION_STATUS_UNPUBLISHED
from judgments.utils.view_helpers import get_document_list_filters, get_search_results_from_filters

from .paginated_view import PaginatedView

DOCUMENT_LIST_QUEUE_FLAG = "document_list_queue"


class DocumentListView(PaginatedView):
    """Shared home / results list view."""

    template_engine = "jinja"
    template_name = "pages/document_list.jinja"
    default_publication_status = PUBLICATION_STATUS_UNPUBLISHED
    is_results_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filters = get_document_list_filters(
            self.request.GET,
            default_publication_status=self.default_publication_status,
        )
        search_context = get_search_results_from_filters(filters)

        context.update(search_context)
        context["pagination_data"] = self.get_pagination_context(
            request=self.request,
            paginator=search_context["paginator"],
        )
        context["document_list_queue_enabled"] = flag_is_active(self.request, DOCUMENT_LIST_QUEUE_FLAG)

        if self.is_results_view:
            context["page_title"] = "Search results"
        elif context["document_list_queue_enabled"] and filters.matching_preset():
            context["page_title"] = filters.matching_preset().label

        return context


class HomeView(DocumentListView):
    default_publication_status = PUBLICATION_STATUS_UNPUBLISHED


class ResultsView(DocumentListView):
    """Search/results alias of the document list; defaults to all documents."""

    template_name = "judgment/results.jinja"
    default_publication_status = PUBLICATION_STATUS_ALL
    is_results_view = True
