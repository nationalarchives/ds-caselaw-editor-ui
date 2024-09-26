from judgments.utils import get_corrected_ncn_url
from judgments.utils.view_helpers import (
    DocumentView,
)


class AssociatedDocumentsView(DocumentView):
    template_name = "judgment/associated_documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "associated_documents"
        context["corrected_ncn_url"] = get_corrected_ncn_url(context["judgment"])
        return context
