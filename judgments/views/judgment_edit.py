import datetime

from caselawclient.Client import MarklogicAPIError
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber, NeutralCitationNumberSchema
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View
from ds_caselaw_utils.types import NeutralCitationString

from judgments.utils import (
    MoveJudgmentError,
    NeutralCitationToUriError,
    api_client,
)
from judgments.utils.aws import invalidate_caches
from judgments.utils.view_helpers import get_document_by_uri_or_404


class StubAlreadyUsedError(Exception):
    pass


def verify_stub_not_used(old_uri, new_citation) -> None:
    new_ncn_slug = NeutralCitationNumberSchema.compile_identifier_url_slug(new_citation)
    existing_matches = api_client.resolve_from_identifier(new_ncn_slug)
    existing_matches_except_this_one = [x for x in existing_matches if x.document_uri not in [new_ncn_slug, old_uri]]
    if existing_matches_except_this_one:
        msg = f"At least one identifier for slug {new_ncn_slug} already exists, {existing_matches_except_this_one}"
        raise StubAlreadyUsedError(msg)


class EditJudgmentView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(
            reverse("full-text-html", kwargs={"document_uri": kwargs["document_uri"]}),
        )

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        judgment = get_document_by_uri_or_404(judgment_uri)

        return_to = request.POST.get("return_to", None)

        # TODO: confirm that the stub we are about to set does not already have a mapping that isn't for this document

        try:
            form_neutral_citation = request.POST["neutral_citation"]

            existing_preferred_ncn = judgment.identifiers.preferred(NeutralCitationNumber)

            # If the NCN is now empty and wasn't before, fail out and don't do anything else.
            # TODO: This is horrible nested logic and needs refactoring into something with better guard clause behaviours

            if form_neutral_citation == "" and existing_preferred_ncn:
                messages.error(
                    request,
                    "A document with a pre-existing NCN cannot be saved with an empty NCN",
                )

            else:
                # If there is a submitted NCN, and EITHER one doesn't already exist OR one does exist and the value is different, process changes
                if form_neutral_citation != "" and (
                    existing_preferred_ncn is None or form_neutral_citation != existing_preferred_ncn.value
                ):
                    # Convert the submitted NCN to a proper class (which will perform validation)
                    neutral_citation = NeutralCitationString(form_neutral_citation)

                    # Confirm that the identifier isn't used elsewhere
                    verify_stub_not_used(judgment_uri, neutral_citation)

                    # Set neutral citation in the identifiers
                    judgment.identifiers.delete_type(NeutralCitationNumber)
                    judgment.identifiers.add(NeutralCitationNumber(value=neutral_citation))
                    judgment.save_identifiers()

                    # Set neutral citation in the document XML
                    api_client.set_judgment_citation(judgment_uri, neutral_citation)

                # Set name
                new_name = request.POST["metadata_name"]
                api_client.set_document_name(judgment_uri, new_name)

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

                messages.success(request, "Document successfully updated")

        except (MoveJudgmentError, NeutralCitationToUriError, StubAlreadyUsedError) as e:
            messages.error(
                request,
                f"There was an error updating the Document's neutral citation: {e}",
            )

        except MarklogicAPIError as e:
            messages.error(request, f"There was an error saving the Document: {e}")

        invalidate_caches(judgment.uri)

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
