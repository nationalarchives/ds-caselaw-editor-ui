from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import get_document_by_uri_or_404


def reparse(request):
    document_uri = request.POST.get("document_uri")
    document = get_document_by_uri_or_404(document_uri)
    successfully_sent_for_reparsing = document.reparse()
    if successfully_sent_for_reparsing:
        messages.success(request, f"Reparsing requested for {document.name}")
    else:
        messages.error(request, f"Unable to reparse {document.name}. Not submitted.")
    return HttpResponseRedirect(
        reverse("full-text-html", kwargs={"document_uri": document.uri}),
    )
