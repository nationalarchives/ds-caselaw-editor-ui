import waffle
from caselawclient.Client import MarklogicResourceNotFoundError
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import escape
from django.views.generic import TemplateView

from judgments.models.judgments import Judgment
from judgments.utils.aws import invalidate_caches

from .judgment_edit import build_confirmation_email_link


class PublishJudgmentView(TemplateView):
    template_name = "judgment/publish.html"

    def get_context_data(self, **kwargs):
        context = super(PublishJudgmentView, self).get_context_data(**kwargs)

        judgment = Judgment(kwargs["judgment_uri"])

        context["context"] = {
            "page_title": "Publish judgment",
            "view": "publish_judgment",
            "judgment": judgment,
        }

        context["feature_flag_embedded_pdfs"] = waffle.flag_is_active(
            self.request, "embedded_pdf_view"
        )

        return context


class PublishJudgmentSuccessView(TemplateView):
    template_name = "judgment/publish-success.html"

    def get_context_data(self, **kwargs):
        context = super(PublishJudgmentSuccessView, self).get_context_data(**kwargs)

        judgment = Judgment(kwargs["judgment_uri"])

        context["context"] = {
            "page_title": "Successfully published judgment",
            "view": "publish_judgment",
            "judgment": judgment,
            "email_confirmation_link": build_confirmation_email_link(
                self.request, judgment
            ),
        }

        context["feature_flag_embedded_pdfs"] = waffle.flag_is_active(
            self.request, "embedded_pdf_view"
        )

        return context


def publish(request):
    judgment_uri = request.POST.get("judgment_uri", None)

    if not judgment_uri:
        return HttpResponseBadRequest("judgment_uri not provided.")

    try:
        judgment = Judgment(judgment_uri)
        judgment.publish()
        invalidate_caches(judgment.uri)
        messages.success(request, "Judgment published!")
        return HttpResponseRedirect(
            reverse("publish-judgment-success", kwargs={"judgment_uri": judgment.uri})
        )
    except MarklogicResourceNotFoundError:
        return HttpResponseBadRequest(
            escape(f"Judgment {judgment_uri} could not be found.")
        )
