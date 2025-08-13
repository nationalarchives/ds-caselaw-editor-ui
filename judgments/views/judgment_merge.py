from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import DocumentView, get_document_by_uri_or_404


class ConfirmMergeDocumentView(DocumentView):
    template_name = "judgment/merge-confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document_uri_to_merge = self.kwargs["document_uri_to_merge"]
        document_to_merge = get_document_by_uri_or_404(document_uri_to_merge)

        # TODO: Update with comparison method
        # documents_comparison = document.compare_to(document_to_merge)
        documents_comparison = [
            {
                "attribute": "court",
                "attribute_label": "Court",
                "match": False,
            },
            {
                "attribute": "date",
                "attribute_label": "Date",
                "match": False,
            },
            {
                "attribute": "name",
                "attribute_label": "Name",
                "match": False,
            },
        ]

        context["document_to_merge"] = document_to_merge
        # TODO: Update with comparison check
        # context["documents_mergable"] = documents_comparison.match()
        context["documents_mergable"] = False
        # TODO: Update with comparison data
        context["documents_comparison"] = documents_comparison
        context["view"] = "merge_document"
        return context


class MergeDocumentView(DocumentView):
    template_name = "judgment/merge.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "merge_document"
        return context


class MergeDocumentSuccessView(DocumentView):
    template_name = "judgment/merge-success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document_uri_to_merge = self.kwargs["document_uri_to_merge"]
        document_to_merge = get_document_by_uri_or_404(document_uri_to_merge)
        context["document_to_merge"] = document_to_merge
        context["view"] = "merge_document"
        return context


def confirm_merge(request):
    document_uri = request.POST.get("document_uri", None)
    document = get_document_by_uri_or_404(document_uri)

    document_uri_to_merge = request.POST.get("document_uri_to_merge", None)
    document_to_merge = get_document_by_uri_or_404(document_uri_to_merge)

    return HttpResponseRedirect(
        reverse(
            "confirm-merge-document",
            kwargs={"document_uri": document.uri, "document_uri_to_merge": document_to_merge.uri},
        ),
    )


def merge(request):
    document_uri = request.POST.get("document_uri", None)
    document = get_document_by_uri_or_404(document_uri)

    document_uri_to_merge = request.POST.get("document_uri_to_merge", None)
    document_to_merge = get_document_by_uri_or_404(document_uri_to_merge)

    # TODO: How do we merge?
    # document.merge(document_to_merge)

    # invalidate_caches(document.uri)
    # invalidate_caches(document_to_merge.uri)
    messages.success(request, "Document successfully merged")
    return HttpResponseRedirect(
        reverse(
            "merge-document-success",
            kwargs={"document_uri": document.uri, "document_uri_to_merge": document_to_merge.uri},
        ),
    )
