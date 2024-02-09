from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import get_document_by_uri_or_404


def enrich(request):
    document_uri = request.POST.get("document_uri", None)
    document = get_document_by_uri_or_404(document_uri)
    successfully_submitted_for_enrichment = document.enrich()
    if successfully_submitted_for_enrichment:
        messages.success(request, f"Enrichment requested for {document.name}")
    else:
        messages.error(
            request,
            f"Unable to enrich {document.name}. Not submitted.",
        )
    return HttpResponseRedirect(
        reverse("full-text-html", kwargs={"document_uri": document.uri}),
    )
