from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.aws import invalidate_caches
from judgments.utils.view_helpers import get_document_by_uri_or_404


def delete(request):
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
        request, f"The document at URI {document.uri} was successfully deleted.",
    )
    return HttpResponseRedirect(reverse("home"))
