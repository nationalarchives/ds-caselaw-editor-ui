import datetime

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import get_document_by_uri_or_404


def enrich(request):
    document_uri = request.POST.get("document_uri", None)
    document = get_document_by_uri_or_404(document_uri)
    last_enrichment = document.enrichment_datetime
    now = datetime.datetime.now(tz=datetime.UTC)
    if last_enrichment and now - last_enrichment < datetime.timedelta(hours=2):
        messages.error(
            request,
            f"Enrichment has been recently requested for {document.name}. Not resubmitted.",
        )
    else:
        document.enrich()
        messages.success(
            request,
            f"Enrichment requested for {document.name}.",
        )
    return HttpResponseRedirect(
        reverse("full-text-html", kwargs={"document_uri": document.uri}),
    )
