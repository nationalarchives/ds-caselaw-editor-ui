import datetime

import ds_caselaw_utils as caselawutils
from caselawclient.Client import MarklogicAPIError
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

from judgments.utils import (
    MoveJudgmentError,
    NeutralCitationToUriError,
    api_client,
    update_document_uri,
)
from judgments.utils.aws import invalidate_caches
from judgments.utils.view_helpers import get_document_by_uri_or_404


class EditJudgmentView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(
            reverse("full-text-html", kwargs={"document_uri": kwargs["document_uri"]}),
        )

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        judgment = get_document_by_uri_or_404(judgment_uri)

        return_to = request.POST.get("return_to", None)
        save_and_move = bool(request.POST.get("save_and_move", False))

        # Does the NCN match the current URI?
        new_citation = request.POST["neutral_citation"]
        new_uri = caselawutils.neutral_url(new_citation.strip())

        try:
            # Set name
            new_name = request.POST["metadata_name"]
            api_client.set_document_name(judgment_uri, new_name)

            # Set neutral citation
            api_client.set_judgment_citation(judgment_uri, new_citation)

            # Set court
            new_court = request.POST["court"]
            api_client.set_document_court_and_jurisdiction(judgment_uri, new_court)

            # Date
            new_date = request.POST["judgment_date"]
            try:
                new_date_as_date = datetime.datetime.strptime(new_date, r"%d %b %Y")
            except ValueError:
                messages.error(
                    request,
                    f"Could not parse the date '{new_date}', should be like '2 Jan 2024'.",
                )
                return HttpResponseRedirect(
                    reverse(
                        "full-text-html",
                        kwargs={"document_uri": kwargs["document_uri"]},
                    ),
                )
            new_date_as_iso = new_date_as_date.strftime(r"%Y-%m-%d")
            api_client.set_judgment_date(judgment_uri, new_date_as_iso)

            # Editor assignment
            if new_assignment := request.POST.get("assigned_to", False):
                api_client.set_property(judgment_uri, "assigned-to", new_assignment)

            invalidate_caches(judgment.uri)

            if new_uri and new_uri.strip("/") != judgment_uri:
                # the document URI is wrong
                if not save_and_move:
                    messages.warning(
                        request,
                        f"Document metadata updated, but this document is at /{judgment_uri} but should probably be at {new_uri}.",
                    )
                    return redirect(
                        reverse("edit-document", kwargs={"document_uri": judgment_uri}),
                    )
                else:
                    new_judgment_uri = update_document_uri(judgment_uri, new_citation)
                    messages.success(request, f"Document moved from {judgment_uri} to {new_judgment_uri}")
                    return redirect(
                        reverse("edit-document", kwargs={"document_uri": new_judgment_uri}),
                    )

            messages.success(request, "Document metadata updated in place")

        except (MoveJudgmentError, NeutralCitationToUriError) as e:
            messages.error(
                request,
                f"There was an error updating the Document's neutral citation: {e}",
            )

        except MarklogicAPIError as e:
            messages.error(request, f"There was an error saving the Document: {e}")

        if return_to == "html":
            return_path = reverse(
                "full-text-html",
                kwargs={"document_uri": judgment.uri},
            )
        elif return_to == "pdf":
            return_path = reverse(
                "full-text-pdf",
                kwargs={"document_uri": judgment.uri},
            )
        else:
            return_path = reverse(
                "edit-document",
                kwargs={"document_uri": judgment.uri},
            )

        return HttpResponseRedirect(return_path)


def edit_view_redirect(request):
    params = request.GET
    document_uri = params.get("judgment_uri", None)
    return HttpResponseRedirect(
        reverse("edit-document", kwargs={"document_uri": document_uri}),
    )
