from waffle import flag_is_active

from judgments.utils.document_list import PRESET_ALL, PRESET_UNPUBLISHED, get_system_preset
from judgments.utils.view_helpers import get_document_list_filters, get_search_results_from_filters

from .paginated_view import PaginatedView

DOCUMENT_LIST_QUEUE_FLAG = "document_list_queue"


class DocumentListView(PaginatedView):
    """Shared home / results list view."""

    template_engine = "jinja"
    template_name = "pages/document_list.jinja"
    default_preset_id = PRESET_UNPUBLISHED
    is_results_view = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filters = get_document_list_filters(
            self.request.GET,
            default_preset=get_system_preset(self.default_preset_id),
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
        else:
            matching_preset = filters.matching_preset()
            if context["document_list_queue_enabled"] and matching_preset is not None:
                context["page_title"] = matching_preset.label

        return context


class HomeView(DocumentListView):
    default_preset_id = PRESET_UNPUBLISHED


class ResultsView(DocumentListView):
    """Search/results alias of the document list; defaults to all documents."""

    template_name = "judgment/results.jinja"
    default_preset_id = PRESET_ALL
    is_results_view = True
