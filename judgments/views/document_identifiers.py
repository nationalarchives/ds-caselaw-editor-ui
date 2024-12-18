from judgments.utils.view_helpers import DocumentView


class DocumentIdentifiersView(DocumentView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["view"] = "document_identifiers"

        return context

    template_name = "judgment/identifiers.html"
