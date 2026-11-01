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

from judgments.utils.metadata_display import (
    MetadataDisplayClaim,
    MetadataDisplaySection,
    MetadataFieldDisplayDecorator,
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

    def _add_new_claims(self, post_data):
        changed = False

        for metadata_item in self.document.metadata:
            for value in post_data.getlist(f"new_claim__{metadata_item.key}"):
                cleaned_value = value.strip()
                if not cleaned_value:
                    continue

                if metadata_item.key == "judges" and hasattr(metadata_item, "add_editor_judge"):
                    metadata_item.add_editor_judge(cleaned_value)
                else:
                    claim_value: MetadataFieldValue
                    if metadata_item.key == "categories":
                        claim_value = MetadataCategoryValue(name=cleaned_value)
                    elif metadata_item.key == "date":
                        claim_value = MetadataDateValue(date.fromisoformat(cleaned_value))
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

        return changed

    def post(self, request, *args, **kwargs):
        reject_success, reject_changed = self._reject_claims(request.POST.getlist("reject_claim_ids"))
        if not reject_success:
            return HttpResponseRedirect(self.get_success_url())

        suppress_success, suppress_changed = self._suppress_body_judges(request.POST.getlist("suppress_body_judges"))
        if not suppress_success:
            return HttpResponseRedirect(self.get_success_url())

        add_changed = self._add_new_claims(request.POST)
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
