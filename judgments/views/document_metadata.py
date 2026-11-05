from datetime import date

from caselawclient.models.documents.metadata.fields.field import (
    MetadataCategoryValue,
    MetadataDateValue,
    MetadataField,
    MetadataFieldValue,
    MetadataPartyValue,
    MetadataStringValue,
)
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from waffle import flag_is_active

from judgments.templatetags.navigation_tags import METADATA_ASIDE_JUDGES_FLAG
from judgments.utils.govuk_date import (
    METADATA_NEW_DATE_CLAIM_MESSAGES,
    GovukDateParseError,
    parse_optional_govuk_date_from_post,
)
from judgments.utils.metadata_display import (
    MetadataDisplayClaim,
    MetadataDisplaySection,
    MetadataFieldDisplayDecorator,
)
from judgments.utils.metadata_form_fields import (
    MetadataFormFieldKind,
    form_field_kind_for_metadata_key,
    new_claim_post_name_prefix,
)
from judgments.utils.permissions import EditorRequiredMixin
from judgments.utils.view_helpers import DocumentView

__all__ = [
    "DocumentMetadataView",
    "MetadataDisplayClaim",
    "MetadataDisplaySection",
    "MetadataFieldDisplayDecorator",
]


class DocumentMetadataView(EditorRequiredMixin, DocumentView):
    template_engine = "jinja"
    template_name = "judgment/metadata.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "document_metadata"
        context["metadata_claim_sections"] = [
            MetadataFieldDisplayDecorator(self.document, metadata_item).section
            for metadata_item in self.document.metadata
        ]
        return context

    def _reject_claims(self, claim_ids):
        changed = False

        for claim_id in claim_ids:
            if claim_id not in self.document.metadata_fields:
                messages.error(self.request, f'Claim "{claim_id}" does not exist for this document.')
                return False, changed

            claim = self.document.metadata_fields[claim_id]
            if claim.name == "judges" and claim.source is MetadataSource.EDITOR:
                self.document.metadata.judges.suppress_claim(claim_id)
            else:
                self.document.metadata_fields.reject(claim_id)
            changed = True

        return True, changed

    def _suppress_body_judges(self, judge_names):
        changed = False
        judges_metadata = self.document.metadata.judges

        for judge_name in judge_names:
            cleaned_judge_name = judge_name.strip()
            if not cleaned_judge_name:
                continue

            if cleaned_judge_name not in judges_metadata.values:
                messages.error(self.request, f'Judge "{cleaned_judge_name}" does not exist for this document.')
                return False, changed

            judges_metadata.suppress_body_value(cleaned_judge_name)
            changed = True

        return True, changed

    def _parse_optional_date_claims(self, post_data) -> tuple[bool, dict[str, date]]:
        parsed_dates: dict[str, date] = {}

        for metadata_item in self.document.metadata:
            if form_field_kind_for_metadata_key(metadata_item.key) is not MetadataFormFieldKind.DATE:
                continue

            try:
                submitted_date = parse_optional_govuk_date_from_post(
                    post_data,
                    new_claim_post_name_prefix(metadata_item.key),
                    messages=METADATA_NEW_DATE_CLAIM_MESSAGES,
                )
            except GovukDateParseError as error:
                messages.error(self.request, str(error))
                return False, {}

            if submitted_date is not None:
                parsed_dates[metadata_item.key] = submitted_date

        return True, parsed_dates

    def _add_new_claims(self, post_data) -> tuple[bool, bool]:
        parse_success, date_claims = self._parse_optional_date_claims(post_data)
        if not parse_success:
            return False, False

        changed = False

        for metadata_item in self.document.metadata:
            if form_field_kind_for_metadata_key(metadata_item.key) is MetadataFormFieldKind.DATE:
                continue

            for value in post_data.getlist(new_claim_post_name_prefix(metadata_item.key)):
                cleaned_value = value.strip()
                if not cleaned_value:
                    continue

                if metadata_item.key == "judges" and hasattr(metadata_item, "add_editor_judge"):
                    metadata_item.add_editor_judge(cleaned_value)
                else:
                    claim_value: MetadataFieldValue
                    if metadata_item.key == "categories":
                        claim_value = MetadataCategoryValue(name=cleaned_value)
                    elif metadata_item.key == "parties":
                        claim_value = MetadataPartyValue(name=cleaned_value)
                    else:
                        claim_value = MetadataStringValue(cleaned_value)
                    self.document.metadata_fields.add(
                        MetadataField(
                            name=metadata_item.key,
                            value=claim_value,
                            source=MetadataSource.EDITOR,
                        ),
                    )
                changed = True

        for metadata_key, submitted_date in date_claims.items():
            self.document.metadata_fields.add(
                MetadataField(
                    name=metadata_key,
                    value=MetadataDateValue(submitted_date),
                    source=MetadataSource.EDITOR,
                ),
            )
            changed = True

        return True, changed

    def post(self, request, *args, **kwargs):
        return_to = request.POST.get("return_to", "").strip()
        if return_to and not flag_is_active(request, METADATA_ASIDE_JUDGES_FLAG):
            messages.info(request, "Editing judges in the metadata aside is not enabled.")
            if url_has_allowed_host_and_scheme(
                return_to,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return HttpResponseRedirect(return_to)
            return HttpResponseRedirect(
                reverse("document-metadata", kwargs={"document_uri": self.document.uri}),
            )

        reject_success, reject_changed = self._reject_claims(request.POST.getlist("reject_claim_ids"))
        if not reject_success:
            return HttpResponseRedirect(self.get_success_url())

        suppress_success, suppress_changed = self._suppress_body_judges(request.POST.getlist("suppress_body_judges"))
        if not suppress_success:
            return HttpResponseRedirect(self.get_success_url())

        add_success, add_changed = self._add_new_claims(request.POST)
        if not add_success:
            return HttpResponseRedirect(self.get_success_url())

        changed = reject_changed or suppress_changed or add_changed

        if changed:
            with self.document.editing_session():
                self.document.save_metadata_fields()
            messages.success(request, "Metadata claims updated successfully.")
        else:
            messages.info(request, "No metadata claim changes submitted.")

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return_to = self.request.POST.get("return_to")
        if return_to and url_has_allowed_host_and_scheme(
            return_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return return_to

        return reverse("document-metadata", kwargs={"document_uri": self.document.uri})
