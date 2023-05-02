from typing import Any, Dict
from urllib.parse import urlencode

import ds_caselaw_utils as caselawutils
from caselawclient.Client import api_client
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from judgments.forms.judgment_move import MoveJudgmentForm, OverwriteJudgmentForm
from judgments.utils import overwrite_judgment, update_judgment_uri
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


class MoveJudgmentView(FormView):
    template_name = "judgment/move.html"
    form_class = MoveJudgmentForm

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super(MoveJudgmentView, self).get_context_data(**kwargs)
        context["judgment"] = get_judgment_by_uri_or_404(self.kwargs["judgment_uri"])
        return context

    def form_valid(self, form):
        old_judgment = get_judgment_by_uri_or_404(self.kwargs["judgment_uri"])
        old_uri = old_judgment.uri
        new_citation = form.cleaned_data["neutral_citation"]
        new_uri = caselawutils.neutral_url(new_citation)

        # if both URIs match, just update the neutral citation, there's not need to move.
        if new_uri.strip("/") == old_uri.strip("/"):
            api_client.set_judgment_citation(old_uri, new_citation)
            messages.success(
                self.request, "Updated neutral citation (did not move judgment)"
            )
            return redirect(new_uri)

        # there is an existing document at the URI
        elif api_client.judgment_exists(new_uri):
            # TODO: allow editors to see the two judgments and compare notes
            # TODO: tests
            # overwrite_judgment(old_uri, new_citation)
            # api_client.set_judgment_citation(new_uri, new_citation)
            # messages.success(
            #     self.request, f"Updated {new_uri} with content from {old_uri}"
            # )
            return redirect(
                "{path}?{params}".format(
                    path=reverse(
                        "overwrite-judgment", kwargs={"judgment_uri": old_judgment.uri}
                    ),
                    params=urlencode({"target": new_citation}),
                )
            )

        else:
            # the new document does not exist, we can just create it, using the existing behaviour
            update_judgment_uri(old_uri, new_citation)
            api_client.set_judgment_citation(new_uri, new_citation)
            # this will fail locally unless localstack is running as it will also update S3.

            messages.success(
                self.request, f"Successfully moved document at {old_uri} to {new_uri}"
            )
            return redirect(new_uri)


class OverwriteJudgmentView(FormView):
    # TODO: handle change of collections
    template_name = "judgment/overwrite.html"
    form_class = OverwriteJudgmentForm

    def get_initial(self):
        return {"neutral_citation": self.request.GET.get("target", None)}

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        target_neutral_citation = self.request.GET.get("target", default=None)
        if not target_neutral_citation:
            raise RuntimeError("The overwriter did not get a target to overwrite")
        context = super(OverwriteJudgmentView, self).get_context_data(**kwargs)
        context["incoming_judgment"] = get_judgment_by_uri_or_404(
            self.kwargs["judgment_uri"]
        )
        context["target_judgment"] = get_judgment_by_uri_or_404(
            caselawutils.neutral_url(target_neutral_citation)
        )

        return context

    def form_valid(self, form):
        source_judgment = get_judgment_by_uri_or_404(self.kwargs["judgment_uri"])
        source_uri = source_judgment.uri
        target_citation = form.cleaned_data["neutral_citation"]
        target_uri = caselawutils.neutral_url(target_citation)
        if not api_client.judgment_exists(target_uri):
            raise RuntimeError("Tried to overwrite something that didn't exist")
        # if both URIs match, just update the neutral citation, there's not need to move.
        if target_uri.strip("/") == source_uri.strip("/"):
            raise RuntimeError("collision: should have been handled in edit")

        overwrite_judgment(source_uri, target_citation)
        api_client.set_judgment_citation(target_uri, target_citation)
        messages.success(
            self.request, f"Updated {target_uri} with content from {source_uri}"
        )
        return redirect(target_uri)
