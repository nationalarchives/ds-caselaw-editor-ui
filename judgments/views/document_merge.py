from caselawclient.errors import MarklogicAPIError, MarklogicCheckoutConflictError
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.exceptions import DocumentMergeNotPossibleError
from django.contrib import messages
from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from waffle import flag_is_active

from judgments.templatetags.navigation_tags import DOCUMENT_MERGE_FLAG
from judgments.utils.aws import invalidate_caches
from judgments.utils.document_list import (
    SAVED_VIEW_ALL,
    InvalidDocumentListFilterError,
    get_saved_view_preset,
)
from judgments.utils.merge_helpers import (
    build_merge_comparison,
    merge_annotation_message,
    merge_review_url,
    merge_target_search_results,
)
from judgments.utils.paginator import paginator as build_paginator
from judgments.utils.permissions import editor_required
from judgments.utils.view_helpers import (
    DocumentView,
    get_document_by_uri_or_404,
    get_document_list_filters,
)
from judgments.views.paginated_view import PaginatedView


def _require_merge_flag(request):
    if not flag_is_active(request, DOCUMENT_MERGE_FLAG):
        raise Http404


class MergeDocumentSearchView(DocumentView, PaginatedView):
    template_engine = "jinja"
    template_name = "judgment/merge.jinja"

    def setup(self, request, *args, **kwargs):
        _require_merge_flag(request)
        super().setup(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "merge_document"

        try:
            filters = get_document_list_filters(
                self.request.GET,
                base_saved_view=get_saved_view_preset(SAVED_VIEW_ALL),
            )
        except InvalidDocumentListFilterError as exc:
            raise BadRequest(str(exc)) from exc

        search_context, visible_documents, adjusted_total = merge_target_search_results(
            filters,
            self.document.uri,
        )
        backend_total = search_context["total"]
        context.update(search_context)
        context["total"] = adjusted_total
        context["pagination_data"] = self.get_pagination_context(
            request=self.request,
            paginator=build_paginator(filters.page, backend_total),
        )
        context["merge_results"] = [
            {
                "document": result,
                "select_url": merge_review_url(self.document.uri, result.uri),
            }
            for result in visible_documents
        ]
        return context


class MergeDocumentReviewView(DocumentView):
    template_engine = "jinja"
    template_name = "judgment/merge_review.jinja"

    def setup(self, request, *args, **kwargs):
        _require_merge_flag(request)
        super().setup(request, *args, **kwargs)
        target_uri = request.GET.get("target")
        if not target_uri:
            raise Http404
        self.target = get_document_by_uri_or_404(target_uri)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "merge_document"
        context["target"] = self.target
        context["target_title"] = self.target.metadata.title.value or "Untitled document"
        context["comparison_sections"] = build_merge_comparison(self.target, self.document)

        validation = self.document.merge.check_can_merge_into(self.target)
        context["can_merge"] = bool(validation.success)
        context["merge_failure_messages"] = [] if validation.success else list(validation.messages)
        return context


def merge(request):
    _require_merge_flag(request)
    return _merge_documents(request)


@editor_required
def _merge_documents(request):
    source_uri = request.POST.get("source_uri") or ""
    target_uri = request.POST.get("target_uri") or ""
    source = get_document_by_uri_or_404(source_uri)
    target = get_document_by_uri_or_404(target_uri)
    message = merge_annotation_message(request.POST.get("note") or "", source.uri)
    review_url = merge_review_url(source.uri, target.uri)

    try:
        # merge_into checks out both documents itself. Opening a session here would
        # merge the copy loaded before that checkout.
        source.merge_into(DocumentURIString(target.uri), message)
    except DocumentMergeNotPossibleError as exc:
        for message_text in exc.messages:
            messages.error(request, message_text)
        return HttpResponseRedirect(review_url)
    except MarklogicCheckoutConflictError:
        messages.error(request, "These documents cannot be merged while one of them is locked.")
        return HttpResponseRedirect(review_url)
    except MarklogicAPIError as exc:
        messages.error(request, f"There was an error merging the documents: {exc}")
        return HttpResponseRedirect(review_url)

    invalidate_caches(source.uri)
    invalidate_caches(target.uri)
    messages.success(request, f"{source.uri} was merged into {target.uri}.")
    return HttpResponseRedirect(reverse("full-text-html", kwargs={"document_uri": target.uri}))
