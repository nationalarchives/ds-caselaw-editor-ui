from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils import get_corrected_ncn_url
from judgments.utils.aws import invalidate_caches
from judgments.utils.navigation import get_navigation_items
from judgments.utils.view_helpers import (
    DocumentView,
    get_document_by_uri_or_404,
    user_is_editor,
    user_is_superuser,
)


class DeleteDocumentView(DocumentView):
    template_name = "judgment/delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "delete_judgment"
        context["corrected_ncn_url"] = get_corrected_ncn_url(context["judgment"])
        context["navigation_items"] = get_navigation_items(context)
        return context


def delete(request):
    if not (user_is_superuser(request.user) or user_is_editor(request.user)):
        msg = "Only superusers and editors can delete documents"
        raise PermissionDenied(msg)

    document_uri = request.POST.get("judgment_uri", None)
    document = get_document_by_uri_or_404(document_uri)
    if not document.safe_to_delete:
        msg = f"The document at URI {document.uri} is not safe to delete."
        raise PermissionDenied(
            msg,
        )

    document.delete()
    invalidate_caches(document.uri)

    messages.success(
        request,
        f"The document at URI {document.uri} was successfully deleted.",
    )
    return HttpResponseRedirect(reverse("home"))
