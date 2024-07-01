from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext

from judgments.utils.aws import invalidate_caches
from judgments.utils.link_generators import build_raise_issue_email_link
from judgments.utils.view_helpers import DocumentView, get_document_by_uri_or_404


class HoldDocumentView(DocumentView):
    template_name = "judgment/hold.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "hold_judgment"
        return context


class HoldDocumentSuccessView(DocumentView):
    template_name = "judgment/hold-success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email_issue_link"] = build_raise_issue_email_link(
            document=context["document"],
            signature=(self.request.user.get_full_name() if self.request.user.is_authenticated else None),
        )
        return context


def hold(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    judgment = get_document_by_uri_or_404(judgment_uri)
    judgment.hold()
    invalidate_caches(judgment.uri)
    messages.success(request, "Document successfully put on hold")
    return HttpResponseRedirect(
        reverse("hold-document-success", kwargs={"document_uri": judgment.uri}),
    )


class UnholdDocumentView(DocumentView):
    template_name = "judgment/unhold.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "unhold_judgment"

        return context


class UnholdDocumentSuccessView(DocumentView):
    template_name = "judgment/unhold-success.html"


def unhold(request):
    judgment_uri = request.POST.get("judgment_uri", "")
    judgment = get_document_by_uri_or_404(judgment_uri)
    judgment.unhold()
    invalidate_caches(judgment.uri)
    messages.success(request, gettext("Document successfully taken off hold"))
    return HttpResponseRedirect(
        reverse("unhold-document-success", kwargs={"document_uri": judgment.uri}),
    )
