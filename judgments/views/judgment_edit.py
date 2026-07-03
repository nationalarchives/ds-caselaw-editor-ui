import ds_caselaw_utils as caselawutils
from caselawclient.Client import MarklogicAPIError
from caselawclient.models.documents import Document
from caselawclient.models.identifiers.neutral_citation import NCNValidationException, NeutralCitationNumber
from django.conf import settings
from django.contrib import messages
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from judgments.forms.document_edit import build_document_edit_forms
from judgments.templatetags.document_utils import display_datetime
from judgments.utils import api_client, editors_dict
from judgments.utils.aws import invalidate_caches
from judgments.utils.link_generators import build_jira_create_link
from judgments.utils.view_helpers import get_document_by_uri_or_404


class CannotUpdateNCNOfNonJudgment(Exception):
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


class EditJudgmentView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(
            reverse("full-text-html", kwargs={"document_uri": kwargs["document_uri"]}),
        )

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        judgment = get_document_by_uri_or_404(judgment_uri)

        return_to = request.POST.get("return_to", None)
        forms = build_document_edit_forms(judgment, self._get_courts(), data=request.POST)
        document_form = forms["document_edit_form"]
        identifier_formset = forms["identifier_formset"]

        # TODO: confirm that the stub we are about to set does not already have a mapping that isn't for this document

        if not document_form.is_valid() or not identifier_formset.is_valid():
            messages.error(request, "There was an error updating the document")
            return self.render_invalid_form(request, judgment, return_to, document_form, identifier_formset)

        try:
            changed_ncn = self.update_identifiers_from_formset(judgment, identifier_formset)
            valid_identifiers, identifier_errors = judgment.validate_identifiers()
            if not valid_identifiers:
                self.add_formset_non_form_errors(identifier_formset, identifier_errors)
                messages.error(request, "There was an error updating the document identifiers.")
                return self.render_invalid_form(request, judgment, return_to, document_form, identifier_formset)

            if identifier_formset.has_changed():
                judgment.save_identifiers()

            if changed_ncn is not None:
                api_client.set_judgment_citation(judgment.uri, changed_ncn)

            api_client.set_document_name(judgment_uri, document_form.cleaned_data["metadata_name"])
            api_client.set_document_court_and_jurisdiction(judgment_uri, document_form.cleaned_data["court"])
            api_client.set_judgment_date(judgment_uri, document_form.judgment_date_as_iso)

            messages.success(request, "Document successfully updated")

        except (NCNValidationException, CannotUpdateNCNOfNonJudgment) as e:
            messages.error(
                request,
                f"There was an error updating the Document's neutral citation: {e}",
            )

        except MarklogicAPIError as e:
            messages.error(request, f"There was an error saving the Document: {e}")

        if not settings.DEBUG:
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

    def _get_courts(self):

        return caselawutils.courts.get_all(with_jurisdictions=True)

    def update_identifiers_from_formset(self, judgment, identifier_formset):
        changed_ncn = None

        for form in identifier_formset.forms:
            if not form.cleaned_data or not form.has_changed():
                continue

            identifier_uuid = form.cleaned_data.get("uuid")
            namespace = form.cleaned_data.get("type")
            value = form.cleaned_data.get("value")
            deprecated = form.cleaned_data.get("deprecated")
            identifier_type = identifier_formset.identifier_type_map.get(namespace)

            if form.cleaned_data.get("DELETE"):
                if identifier_uuid:
                    identifier = judgment.identifiers[identifier_uuid]
                    if isinstance(identifier, NeutralCitationNumber):
                        changed_ncn = ""
                        del judgment.identifiers[identifier_uuid]
                continue

            if identifier_uuid:
                identifier = judgment.identifiers[identifier_uuid]
                if isinstance(identifier, NeutralCitationNumber) and identifier.value != value:
                    changed_ncn = value
                identifier.value = value
                identifier.deprecated = deprecated
            elif namespace and value:
                identifier = identifier_type(value=value, deprecated=deprecated)
                judgment.identifiers.add(identifier)
                if isinstance(identifier, NeutralCitationNumber):
                    changed_ncn = value

        return changed_ncn

    def add_formset_non_form_errors(self, formset, error_messages):
        formset._non_form_errors = ErrorList(error_messages, renderer=getattr(formset, "renderer", None))  # noqa: SLF001

    def render_invalid_form(self, request, judgment, return_to, document_form, identifier_formset):
        template_name = "judgment/full_text_pdf.jinja" if return_to == "pdf" else "judgment/full_text_html.jinja"
        context = self.get_invalid_context(request, judgment, return_to, document_form, identifier_formset)

        return render(request, template_name, context, using="jinja", status=400)

    def get_invalid_context(self, request, judgment, return_to, document_form, identifier_formset):

        courts = self._get_courts()
        version_uri = request.GET.get("version_uri", None)
        document_html = (
            get_document_by_uri_or_404(version_uri).content_as_html() if version_uri else judgment.content_as_html()
        )

        document_type = judgment.document_noun.replace(" ", "_")

        context = {
            "document": judgment,
            "judgment": judgment,
            "document_uri": judgment.uri,
            "document_html": document_html,
            "page_title": judgment.body.name,
            "courts": courts,
            "editors": editors_dict(),
            "jira_create_link": build_jira_create_link(document=judgment, request=request),
            "linked_document_uri": None,
            "document_type": document_type,
            "preferred_ncn": judgment.identifiers.preferred(type=NeutralCitationNumber),
            "document_edit_form": document_form,
            "document_form": document_form,
            "identifiers_formset": identifier_formset,
            "view": "judgment_pdf" if return_to == "pdf" else "judgment_html",
        }

        if judgment.has_ever_been_published:
            context["first_published_date"] = (
                display_datetime(judgment.first_published_datetime_display)
                if judgment.first_published_datetime_display
                else "Unknown"
            )
        else:
            context["first_published_date"] = "-"

        return context


def edit_view_redirect(request):
    params = request.GET
    document_uri = params.get("judgment_uri", None)
    return HttpResponseRedirect(
        reverse("edit-document", kwargs={"document_uri": document_uri}),
    )
