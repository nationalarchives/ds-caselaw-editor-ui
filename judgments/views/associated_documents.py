from judgments.utils.view_helpers import (
    DocumentView,
)


class AssociatedDocumentsView(DocumentView):
    template_name = "judgment/associated_documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "associated_documents"
        return context
