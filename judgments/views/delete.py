from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.aws import invalidate_caches
from judgments.utils.permissions import editor_required
from judgments.utils.view_helpers import DocumentView, get_document_by_uri_or_404


class DeleteDocumentView(DocumentView):
    template_engine = "jinja"
    template_name = "judgment/delete.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "delete_judgment"
        return context


@editor_required
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
        request,
        f"The document at URI {document.uri} was successfully deleted.",
    )
    return HttpResponseRedirect(reverse("home"))
