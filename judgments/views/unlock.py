from caselawclient.Client import MarklogicResourceUnmanagedError
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from judgments.utils import api_client
from judgments.utils.view_helpers import get_document_by_uri_or_404


@require_http_methods(["POST", "GET", "HEAD"])
def unlock(request):
    """Unlock a judgment"""
    if request.method == "POST":
        return unlock_post(request)
    else:
        return unlock_get(request)


def unlock_get(request):
    """Confirmation screen for unlocking"""
    judgment_uri = request.GET["judgment_uri"]

    return render(
        request,
        "judgment/confirm-unlock.jinja",
        {
            "judgment_uri": judgment_uri,
            "page_title": "Unlock document",
        },
        using="jinja",
    )


def unlock_post(request):
    """Unlock the judgment in Marklogic and return to edit judgment"""

    judgment_uri = request.POST.get("judgment_uri")
    try:
        judgment = get_document_by_uri_or_404(judgment_uri)
        api_client.break_checkout(judgment.uri)
    except MarklogicResourceUnmanagedError as exc:
        msg = f"Resource Unmanaged: Document '{judgment_uri}' might not exist."
        raise Http404(
            msg,
        ) from exc
    else:
        messages.success(request, "Document unlocked.")
        return redirect(reverse("edit-document", kwargs={"document_uri": judgment.uri}))
