from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.permissions import editor_or_developer_required
from judgments.utils.view_helpers import get_document_by_uri_or_404


@editor_or_developer_required
def reparse(request):
    document_uri = request.POST.get("document_uri")
    document = get_document_by_uri_or_404(document_uri)
    document.reparse()
    messages.success(request, f"Reparsing requested for {document.body.name}")
    return HttpResponseRedirect(
        reverse("full-text-html", kwargs={"document_uri": document.uri}),
    )
