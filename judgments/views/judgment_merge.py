from caselawclient.managers.merge import MergeManager
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.aws import invalidate_caches
from judgments.utils.view_helpers import DocumentView, get_document_by_uri_or_404


class MergeDocumentSelectTargetView(DocumentView):
    """
    This view is where the user will select a merge target. If the merge source (ie the 'current' document) can't be used, the template will inform the user accordingly.
    """

    template_name = "judgment/merge/select-target.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "merge_document"
        merge_manager = MergeManager()
        context["safe_to_merge_source"] = merge_manager.check_document_is_safe_as_merge_source(context["document"])

        return context


class MergeDocumentCheckMetadataView(DocumentView):
    """
    This view is where the user gets visibility of how metadata will change. If the target is invalid, we'll tell the user here.
    """

    template_name = "judgment/merge/check-metadata.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document_uri_to_merge = self.kwargs["document_uri_to_merge"]
        target_document = get_document_by_uri_or_404(document_uri_to_merge)

        documents_comparison = self.document.compare_to(target_document)

        merge_manager = MergeManager()
        context["safe_to_merge_target"] = merge_manager.check_source_document_is_safe_to_merge_into_target(
            context["document"],
            target_document,
        )

        context["merge_target_document"] = target_document
        context["documents_comparison"] = documents_comparison
        context["view"] = "merge_document"

        return context


class MergeDocumentCheckSummaryView(DocumentView):
    """
    This view is where the user gets an overview of the changes as a result of a merge.
    """

    template_name = "judgment/merge/check-change-summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document_uri_to_merge = self.kwargs["document_uri_to_merge"]
        target_document = get_document_by_uri_or_404(document_uri_to_merge)

        documents_comparison = self.document.compare_to(target_document)

        merge_manager = MergeManager()
        context["safe_to_merge_target"] = merge_manager.check_source_document_is_safe_to_merge_into_target(
            context["document"],
            target_document,
        )

        context["merge_target_document"] = target_document
        context["documents_comparison"] = documents_comparison
        context["view"] = "merge_document"

        return context


class FailedMergeDocumentView(MergeDocumentSelectTargetView):
    template_name = "judgment/merge/failed.html"


class MergeDocumentSuccessView(DocumentView):
    template_name = "judgment/merge/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document_uri_to_merge = self.kwargs["document_uri_to_merge"]
        document_to_merge = get_document_by_uri_or_404(document_uri_to_merge)
        context["document_to_merge"] = document_to_merge
        context["view"] = "merge_document"
        return context


def merge(request):
    """This method actually handles form submissions from the merge flow and directs users to views accordingly."""
    document_uri = request.POST.get("document_uri", None)
    document = get_document_by_uri_or_404(document_uri)

    # Try get all the form fields we need to perform the merge
    merge_target_uri = request.POST.get("merge_target_uri", None)
    merge_checked_metadata = bool(request.POST.get("merge_checked_metadata", False))
    merge_checked_summary = bool(request.POST.get("merge_checked_summary", False))

    # Grab the target document
    merge_target_document = get_document_by_uri_or_404(merge_target_uri)

    # If we have everything in place, go ahead and actually do the merge!
    if merge_target_uri and merge_checked_metadata and merge_checked_summary:
        # Tell the MergeManager to perform merge operations. This will also run final safety checks. Failures raise an exception.
        MergeManager.merge_documents(source=document, target=merge_target_document)

        # Finally, nuke the caches so users get the latest and greatest
        invalidate_caches(document.uri)

    # We have the target and we've checked the metadata, show the user the merge summary
    elif merge_target_uri and merge_checked_metadata:
        return HttpResponseRedirect(
            reverse(
                "merge-document-check-summary",
                kwargs={"document_uri": document.uri, "document_uri_to_merge": merge_target_document.uri},
            ),
        )

    # We have the target but no checks yet; prompt to check metadata
    elif merge_target_uri:
        return HttpResponseRedirect(
            reverse(
                "merge-document-check-metadata",
                kwargs={"document_uri": document.uri, "document_uri_to_merge": merge_target_document.uri},
            ),
        )

    # We've run out of cases here and don't know what to do. Drop back to the target select.
    return HttpResponseRedirect(
        reverse(
            "merge-document",
            kwargs={"document_uri": document.uri},
        ),
    )
