from judgments.utils.view_helpers import DocumentView


class DocumentMetadataView(DocumentView):
    template_engine = "jinja"
    template_name = "judgment/metadata.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "document_metadata"
        return context
