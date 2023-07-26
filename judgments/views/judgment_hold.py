from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext
from django.views.generic import TemplateView

from judgments.utils import editors_dict, set_document_type_and_link
from judgments.utils.aws import invalidate_caches
from judgments.utils.link_generators import build_raise_issue_email_link
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


class HoldJudgmentView(TemplateView):
    template_name = "judgment/hold.html"

    def get_context_data(self, **kwargs):
        context = super(HoldJudgmentView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])

        context.update(
            {
                "page_title": judgment.name,
                "view": "hold_judgment",
                "judgment": judgment,
                "editors": editors_dict(),
            }
        )

        return context


class HoldJudgmentSuccessView(TemplateView):
    template_name = "judgment/hold-success.html"

    def get_context_data(self, **kwargs):
        context = super(HoldJudgmentSuccessView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])
        judgment_uri = kwargs["judgment_uri"]

        context = set_document_type_and_link(context, judgment_uri)

        context.update(
            {
                "page_title": judgment.name,
                "judgment": judgment,
                "email_issue_link": build_raise_issue_email_link(
                    judgment=judgment,
                    signature=(
                        self.request.user.get_full_name()
                        if self.request.user.is_authenticated
                        else None
                    ),
                ),
                "editors": editors_dict(),
            }
        )

        return context


def hold(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    judgment = get_judgment_by_uri_or_404(judgment_uri)
    judgment.hold()
    invalidate_caches(judgment.uri)
    messages.success(request, gettext("judgment.hold.hold_success_flash_message"))
    return HttpResponseRedirect(
        reverse("hold-judgment-success", kwargs={"judgment_uri": judgment.uri})
    )


class UnholdJudgmentView(TemplateView):
    template_name = "judgment/unhold.html"

    def get_context_data(self, **kwargs):
        context = super(UnholdJudgmentView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])
        judgment_uri = kwargs["judgment_uri"]

        context = set_document_type_and_link(context, judgment_uri)

        context.update(
            {
                "page_title": judgment.name,
                "view": "hold_judgment",
                "judgment": judgment,
                "editors": editors_dict(),
            }
        )

        return context


class UnholdJudgmentSuccessView(TemplateView):
    template_name = "judgment/unhold-success.html"

    def get_context_data(self, **kwargs):
        context = super(UnholdJudgmentSuccessView, self).get_context_data(**kwargs)

        judgment = get_judgment_by_uri_or_404(kwargs["judgment_uri"])
        judgment_uri = kwargs["judgment_uri"]

        context = set_document_type_and_link(context, judgment_uri)

        context.update(
            {
                "page_title": judgment.name,
                "judgment": judgment,
                "editors": editors_dict(),
            }
        )

        return context


def unhold(request):
    judgment_uri = request.POST.get("judgment_uri", "")
    judgment = get_judgment_by_uri_or_404(judgment_uri)
    judgment.unhold()
    invalidate_caches(judgment.uri)
    messages.success(request, gettext("judgment.hold.unhold_success_flash_message"))
    return HttpResponseRedirect(
        reverse("unhold-judgment-success", kwargs={"judgment_uri": judgment.uri})
    )
