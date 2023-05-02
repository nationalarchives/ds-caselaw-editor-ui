from typing import Any, Dict

import ds_caselaw_utils as caselawutils
from caselawclient.Client import api_client
from django.contrib import messages
from django.views.generic import FormView

from judgments.forms.judgment_move import MoveJudgmentForm
from judgments.utils import get_judgment_by_uri, update_judgment_uri


class MoveJudgmentView(FormView):
    template_name = "judgment/move.html"
    form_class = MoveJudgmentForm
    success_url = "/"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super(MoveJudgmentView, self).get_context_data(**kwargs)
        context["judgment"] = get_judgment_by_uri(self.kwargs["judgment_uri"])
        return context

    def form_valid(self, form):
        old_judgment = get_judgment_by_uri(self.kwargs["judgment_uri"])
        old_uri = old_judgment.uri
        new_citation = form.cleaned_data["neutral_citation"]
        new_uri = caselawutils.neutral_url(new_citation)

        # if a URI is not generated, the citation is probably invalid
        if not new_uri:
            messages.error(
                self.request, f"Unable to parse neutral citation '{new_citation}'"
            )
            return super().form_valid(form)

        # if both URIs match, just update the neutral citation, there's not need to move.
        if new_uri.strip("/") == old_uri.strip("/"):
            api_client.set_judgment_citation(old_uri, new_citation)
            messages.success(
                self.request, "Updated neutral citation (did not move judgment)"
            )
            return super().form_valid(form)

        # otherwise proceed with the move.
        # If the document does not exist, we can just create it.
        # TODO: This is buggy and needs to be fixed or replaced
        # TODO: handle overwrite mechanic
        # TODO: write tests
        update_judgment_uri(old_uri, new_citation)
        # this also fails due to relying on S3 unless localstack is running

        messages.success(self.request, f"{new_uri}, {old_uri}")
        return super().form_valid(form)
