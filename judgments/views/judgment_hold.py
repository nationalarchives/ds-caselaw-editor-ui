import waffle
from caselawclient.Client import MarklogicResourceNotFoundError
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext
from django.views.generic import TemplateView

from judgments.utils import editors_dict, get_judgment_by_uri
from judgments.utils.aws import invalidate_caches

from .judgment_edit import build_confirmation_email_link


class HoldJudgmentView(TemplateView):
    template_name = "judgment/hold.html"

    def get_context_data(self, **kwargs):
        context = super(HoldJudgmentView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.hold.hold_title"), judgment=judgment.name
                ),
                "view": "hold_judgment",
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


class HoldJudgmentSuccessView(TemplateView):
    template_name = "judgment/hold-success.html"

    def get_context_data(self, **kwargs):
        context = super(HoldJudgmentSuccessView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.hold.hold_success_title"),
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


def hold(request):
    judgment_uri = request.POST.get("judgment_uri", None)

    if not judgment_uri:
        return HttpResponseBadRequest("judgment_uri not provided.")

    try:
        judgment = get_judgment_by_uri(judgment_uri)
        judgment.hold()
        invalidate_caches(judgment.uri)
        messages.success(request, gettext("judgment.hold.hold_success_flash_message"))
        return HttpResponseRedirect(
            reverse("hold-judgment-success", kwargs={"judgment_uri": judgment.uri})
        )
    except MarklogicResourceNotFoundError:
        return HttpResponseBadRequest(
            "Judgment {judgment_uri} could not be found.".format(
                judgment_uri=escape(judgment_uri)
            )
        )


class UnholdJudgmentView(TemplateView):
    template_name = "judgment/unhold.html"

    def get_context_data(self, **kwargs):
        context = super(UnholdJudgmentView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.hold.unhold_title"),
                    judgment=judgment.name,
                ),
                "view": "hold_judgment",
                "judgment": judgment,
                "editors": editors_dict(),
            }
        )

        context["feature_flag_embedded_pdfs"] = waffle.flag_is_active(
            self.request, "embedded_pdf_view"
        )

        return context


class UnholdJudgmentSuccessView(TemplateView):
    template_name = "judgment/unhold-success.html"

    def get_context_data(self, **kwargs):
        context = super(UnholdJudgmentSuccessView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": '{title}: "{judgment}"'.format(
                    title=gettext("judgment.hold.unhold_success_title"),
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


def unhold(request):
    judgment_uri = request.POST.get("judgment_uri", None)

    if not judgment_uri:
        return HttpResponseBadRequest("judgment_uri not provided.")

    try:
        judgment = get_judgment_by_uri(judgment_uri)
        judgment.unhold()
        invalidate_caches(judgment.uri)
        messages.success(request, gettext("judgment.hold.unhold_success_flash_message"))
        return HttpResponseRedirect(
            reverse("unhold-judgment-success", kwargs={"judgment_uri": judgment.uri})
        )
    except MarklogicResourceNotFoundError:
        return HttpResponseBadRequest(
            "Judgment {judgment_uri} could not be found.".format(
                judgment_uri=escape(judgment_uri)
            )
        )
