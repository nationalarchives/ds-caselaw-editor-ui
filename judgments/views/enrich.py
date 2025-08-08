from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import get_document_by_uri_or_404


def enrich(request):
    document_uri = request.POST.get("document_uri", None)
    document = get_document_by_uri_or_404(document_uri)
    enrichment_triggered = document.enrich(accept_failures=True, even_if_recent=True)
    if not enrichment_triggered:
        messages.error(
            request,
            f"Enrichment request failed for {document.body.name}.",
        )
    else:
        messages.success(
            request,
            f"Enrichment requested for {document.body.name}.",
        )
    return HttpResponseRedirect(
        reverse("full-text-html", kwargs={"document_uri": document.uri}),
    )
