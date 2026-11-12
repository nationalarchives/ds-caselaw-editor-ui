from caselawclient.Client import MarklogicAPIError
from caselawclient.models.documents import Document
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.identifiers.neutral_citation import NCNValidationException, NeutralCitationNumber
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View
from waffle import flag_is_active

from judgments.templatetags.navigation_tags import METADATA_ASIDE_JUDGES_FLAG
from judgments.utils import api_client
from judgments.utils.aws import invalidate_caches
from judgments.utils.govuk_date import JUDGMENT_DATE_FIELD_MESSAGES, GovukDateParseError, parse_govuk_date_from_post
from judgments.utils.metadata_editing import (
    save_judgment_date_from_document_form,
    save_judgment_title_from_document_form,
)
from judgments.utils.permissions import EditorRequiredMixin
from judgments.utils.view_helpers import get_document_by_uri_or_404


class CannotUpdateNCNOfNonJudgment(Exception):
    pass


class CannotSaveJudgmentWithoutJudges(Exception):
    pass


def update_ncn_of_document(document: Document, new_neutral_citation_number_string: str) -> None:
    """Given a document and a new NCN string, validate that NCN and perform necessary operations to update the document with it."""

    # Perform sense-check on document type
    if document.document_noun != "judgment":
        msg = f"Cannot update the NCN of non-judgment at {document.uri}"
        raise CannotUpdateNCNOfNonJudgment(msg)

    # Convert the submitted NCN to a proper class (which will perform validation)
    new_neutral_citation = NeutralCitationNumber(value=new_neutral_citation_number_string)

    # Set neutral citation in the identifiers
    document.identifiers.delete_type(NeutralCitationNumber)
    document.identifiers.add(new_neutral_citation)
    document.save_identifiers()

    # Set neutral citation in the document XML
    api_client.set_judgment_citation(document.uri, new_neutral_citation.value)


class EditJudgmentView(EditorRequiredMixin, View):
    @staticmethod
    def _get_return_path(judgment: Document, return_to: str | None) -> str:
        if return_to == "html":
            view_name = "full-text-html"
        elif return_to == "pdf":
            view_name = "full-text-pdf"
        else:
            view_name = "edit-document"

        return reverse(view_name, kwargs={"document_uri": judgment.uri})

    @staticmethod
    def _save_changed_judges(judgment: Document, changed: bool) -> None:
        if not changed:
            return

        if not judgment.metadata.judges.values:
            msg = "A document must have at least one judge"
            raise CannotSaveJudgmentWithoutJudges(msg)

        judgment.save_metadata_fields()

    @classmethod
    def _save_judges_from_document_form(cls, request: HttpRequest, judgment: Document) -> None:
        if not flag_is_active(request, METADATA_ASIDE_JUDGES_FLAG):
            return

        post_data = request.POST
        changed = False
        judges_metadata = judgment.metadata.judges

        for claim_id in post_data.getlist("reject_claim_ids"):
            if claim_id not in judgment.metadata_fields:
                continue

            claim = judgment.metadata_fields[claim_id]
            if claim.name != "judges":
                continue

            if claim.source is MetadataSource.EDITOR:
                judges_metadata.suppress_claim(claim_id)
            else:
                judgment.metadata_fields.reject(claim_id)
            changed = True

        for judge_name in post_data.getlist("suppress_body_judges"):
            cleaned_judge_name = judge_name.strip()
            if cleaned_judge_name and cleaned_judge_name in judges_metadata.values:
                judges_metadata.suppress_body_value(cleaned_judge_name)
                changed = True

        for judge_name in post_data.getlist("new_claim__judges"):
            cleaned_judge_name = judge_name.strip()
            if cleaned_judge_name:
                judges_metadata.add_editor_judge(cleaned_judge_name)
                changed = True

        cls._save_changed_judges(judgment, changed)

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(
            reverse("full-text-html", kwargs={"document_uri": kwargs["document_uri"]}),
        )

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        judgment = get_document_by_uri_or_404(judgment_uri)

        if judgment.document_noun != "judgment":
            msg = f"Cannot edit non-judgment at {judgment.uri}"
            raise Http404(msg)

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
                try:
                    new_date = parse_govuk_date_from_post(
                        request.POST,
                        "judgment_date",
                        messages=JUDGMENT_DATE_FIELD_MESSAGES,
                    )
                except GovukDateParseError as error:
                    messages.error(request, str(error))
                    return HttpResponseRedirect(
                        reverse(
                            "full-text-html",
                            kwargs={"document_uri": kwargs["document_uri"]},
                        ),
                    )

                with judgment.editing_session():
                    # If there is a submitted NCN, and EITHER one doesn't already exist OR one does exist and the value is different, process changes
                    if form_neutral_citation != "" and (
                        existing_preferred_ncn is None or form_neutral_citation != existing_preferred_ncn.value
                    ):
                        update_ncn_of_document(judgment, form_neutral_citation)

                    save_judgment_title_from_document_form(judgment, request.POST["metadata_name"])

                    # Set court
                    new_court = request.POST["court"]
                    api_client.set_document_court_and_jurisdiction(judgment_uri, new_court)

                    save_judgment_date_from_document_form(judgment, new_date)
                    api_client.set_judgment_date(judgment_uri, new_date.isoformat())

                    self._save_judges_from_document_form(request, judgment)

                    messages.success(request, "Document successfully updated")

        except (NCNValidationException, CannotUpdateNCNOfNonJudgment) as e:
            messages.error(
                request,
                f"There was an error updating the Document's neutral citation: {e}",
            )

        except CannotSaveJudgmentWithoutJudges as e:
            messages.error(request, str(e))

        except MarklogicAPIError as e:
            messages.error(request, f"There was an error saving the Document: {e}")
        else:
            if not settings.DEBUG:
                invalidate_caches(judgment.uri)

        return HttpResponseRedirect(self._get_return_path(judgment, return_to))


def edit_view_redirect(request):
    params = request.GET
    document_uri = params.get("judgment_uri", None)
    return HttpResponseRedirect(
        reverse("edit-document", kwargs={"document_uri": document_uri}),
    )
