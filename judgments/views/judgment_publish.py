import waffle
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext
from django.views.generic import TemplateView

from judgments.utils import editors_dict
from judgments.utils.aws import invalidate_caches
from judgments.utils.view_helpers import get_judgment_by_uri_or_404

from .judgment_edit import build_confirmation_email_link


class PublishJudgmentView(TemplateView):
    template_name = "judgment/publish.html"

    def get_context_data(self, **kwargs):
        context = super(PublishJudgmentView, self).get_context_data(**kwargs)
        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.publish.publish_title"),
                    judgment=judgment.name,
                ),
                "view": "publish_judgment",
                "judgment": judgment,
                "editors": editors_dict(),
            }
        )

        context["feature_flag_embedded_pdfs"] = waffle.flag_is_active(
            self.request, "embedded_pdf_view"
        )

        context["feature_flag_log_minor_issues_on_publish"] = waffle.flag_is_active(
            self.request, "log_minor_issues_on_publish"
        )

        context["feature_flag_publish_flow"] = waffle.flag_is_active(
            self.request, "publish_flow"
        )

        return context


class PublishJudgmentSuccessView(TemplateView):
    template_name = "judgment/publish-success.html"

    def get_context_data(self, **kwargs):
        context = super(PublishJudgmentSuccessView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.publish.publish_success_title"),
                    judgment=judgment.name,
                ),
                "judgment": judgment,
                "email_confirmation_link": build_confirmation_email_link(
                    self.request, judgment
                ),
                "editors": editors_dict(),
            }
        )

        context["feature_flag_embedded_pdfs"] = waffle.flag_is_active(
            self.request, "embedded_pdf_view"
        )

        context["feature_flag_publish_flow"] = waffle.flag_is_active(
            self.request, "publish_flow"
        )

        return context


def publish(request):
    judgment_uri = request.POST.get("judgment_uri")
    judgment = get_judgment_by_uri_or_404(judgment_uri)
    judgment.publish()
    invalidate_caches(judgment.uri)
    messages.success(request, gettext("judgment.publish.publish_success_flash_message"))
    return HttpResponseRedirect(
        reverse("publish-judgment-success", kwargs={"judgment_uri": judgment.uri})
    )


class UnpublishJudgmentView(TemplateView):
    template_name = "judgment/unpublish.html"

    def get_context_data(self, **kwargs):
        context = super(UnpublishJudgmentView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.publish.unpublish_title"),
                    judgment=judgment.name,
                ),
                "view": "publish_judgment",
                "judgment": judgment,
                "editors": editors_dict(),
            }
        )

        context["feature_flag_embedded_pdfs"] = waffle.flag_is_active(
            self.request, "embedded_pdf_view"
        )

        return context


class UnpublishJudgmentSuccessView(TemplateView):
    template_name = "judgment/unpublish-success.html"

    def get_context_data(self, **kwargs):
        context = super(UnpublishJudgmentSuccessView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.publish.unpublish_success_title"),
                    judgment=judgment.name,
                ),
                "judgment": judgment,
                "editors": editors_dict(),
            }
        )

        context["feature_flag_embedded_pdfs"] = waffle.flag_is_active(
            self.request, "embedded_pdf_view"
        )

        return context


def unpublish(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    judgment = get_judgment_by_uri_or_404(judgment_uri)
    judgment.unpublish()
    invalidate_caches(judgment.uri)
    messages.success(
        request, gettext("judgment.publish.unpublish_success_flash_message")
    )
    return HttpResponseRedirect(
        reverse("unpublish-judgment-success", kwargs={"judgment_uri": judgment.uri})
    )
