from judgments.utils import get_corrected_ncn_url
from judgments.utils.navigation import get_navigation_items
from judgments.utils.view_helpers import DocumentView


class DocumentDownloadsView(DocumentView):
    template_name = "judgment/downloads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["view"] = "document_downloads"
        context["corrected_ncn_url"] = get_corrected_ncn_url(context["judgment"])
        context["navigation_items"] = get_navigation_items(context)

        return context
