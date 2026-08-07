from caselawclient.models.documents.metadata.fields.field import MetadataCategoryValue, MetadataField
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import DocumentView


class DocumentMetadataView(DocumentView):
    template_engine = "jinja"
    template_name = "judgment/metadata.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "document_metadata"
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
        judges_metadata = self.document.metadata.get("judges")

        for judge_name in judge_names:
            cleaned_judge_name = judge_name.strip()
            if not cleaned_judge_name:
                continue

            if judges_metadata is None:
                messages.error(self.request, "Judge metadata is not available for this document.")
                return False, changed
            if cleaned_judge_name not in judges_metadata.values:
                messages.error(self.request, f'Judge "{cleaned_judge_name}" does not exist for this document.')
                return False, changed

            judges_metadata.suppress_body_value(cleaned_judge_name)
            changed = True

        return True, changed

    def _add_new_claims(self, post_data):
        changed = False

        for metadata_item in self.document.metadata.values():
            for value in post_data.getlist(f"new_claim__{metadata_item.key}"):
                cleaned_value = value.strip()
                if not cleaned_value:
                    continue

                if metadata_item.key == "judges" and hasattr(metadata_item, "add_editor_judge"):
                    metadata_item.add_editor_judge(cleaned_value)
                else:
                    claim_value = (
                        MetadataCategoryValue(name=cleaned_value)
                        if metadata_item.key == "categories"
                        else cleaned_value
                    )
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
            self.document.save_metadata_fields()
            messages.success(request, "Metadata claims updated successfully.")
        else:
            messages.info(request, "No metadata claim changes submitted.")

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("document-metadata", kwargs={"document_uri": self.document.uri})
