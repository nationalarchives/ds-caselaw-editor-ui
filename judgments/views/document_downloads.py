from judgments.utils.view_helpers import DocumentView


class DocumentDownloadsView(DocumentView):
    template_name = "judgment/downloads.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["view"] = "document_downloads"

        return context
