from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext

from judgments.utils.aws import invalidate_caches
from judgments.utils.link_generators import build_confirmation_email_link
from judgments.utils.view_helpers import get_document_by_uri_or_404

from ..utils.view_helpers import DocumentView


class PublishDocumentView(DocumentView):
    template_name = "judgment/publish.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "publish_judgment"
        return context


class PublishDocumentSuccessView(DocumentView):
    template_name = "judgment/publish-success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["email_confirmation_link"] = build_confirmation_email_link(
            document=context["document"],
            signature=(
                self.request.user.get_full_name()
                if self.request.user.is_authenticated
                else None
            ),
        )

        return context


def publish(request):
    judgment_uri = request.POST.get("judgment_uri")
    judgment = get_document_by_uri_or_404(judgment_uri)
    judgment.publish()
    invalidate_caches(judgment.uri)
    messages.success(request, gettext("judgment.publish.publish_success_flash_message"))
    return HttpResponseRedirect(
        reverse("publish-document-success", kwargs={"document_uri": judgment.uri})
    )


class UnpublishDocumentView(DocumentView):
    template_name = "judgment/unpublish.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "unpublish_judgment"
        return context


class UnpublishDocumentSuccessView(DocumentView):
    template_name = "judgment/unpublish-success.html"


def unpublish(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    judgment = get_document_by_uri_or_404(judgment_uri)
    judgment.unpublish()
    invalidate_caches(judgment.uri)
    messages.success(
        request, gettext("judgment.publish.unpublish_success_flash_message")
    )
    return HttpResponseRedirect(
        reverse("unpublish-document-success", kwargs={"document_uri": judgment.uri})
    )
