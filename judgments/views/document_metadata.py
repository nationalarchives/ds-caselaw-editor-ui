from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any, cast

from caselawclient.models.documents.metadata.base import MultipleMetadata, SingleMetadata
from caselawclient.models.documents.metadata.fields.field import MetadataCategoryValue, MetadataField
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import DocumentView

if TYPE_CHECKING:
    from caselawclient.models.documents.metadata.types.judges import JudgesMetadata


@dataclass
class MetadataDisplayClaim:
    value: Any
    display_value: str
    source_label: str
    status: str
    status_badge_variant: str
    is_current: bool
    can_reject: bool
    reject_input_name: str | None = None
    reject_input_value: str | None = None
    reject_input_id_prefix: str | None = None
    timestamp: Any = None
    claim_id: str | None = None
    is_faux: bool = False


@dataclass
class MetadataDisplaySection:
    metadata_item: Any
    display_claims: list[MetadataDisplayClaim]

    @property
    def new_claim_input_id(self):
        return f"new-claim-{self.metadata_item.key}"

    @property
    def new_claim_input_name(self):
        return f"new_claim__{self.metadata_item.key}"


class MetadataFieldDisplayDecorator:
    def __init__(self, document, metadata_item):
        self.document = document
        self.metadata_item = metadata_item
        self.resolved = document.metadata_fields.resolve(metadata_item.key)
        self.active_claims = self.resolved.claims
        self.winning_claim = self.active_claims[-1] if self.active_claims else None

    @property
    def section(self):
        return MetadataDisplaySection(
            metadata_item=self.metadata_item,
            display_claims=self._display_claims(),
        )

    @property
    def is_single_value(self):
        return isinstance(self.metadata_item, SingleMetadata)

    def _display_claims(self):
        if not self.resolved.has_any_claims:
            return self._fallback_document_claims()

        display_claims = [self._real_claim(claim) for claim in reversed(self.resolved.all_claims)]
        display_claims.extend(self._faux_suppressed_document_claims())
        return display_claims

    def _real_claim(self, claim):
        if claim.rejected:
            status = "Rejected"
            badge_variant = "failure"
            is_current = False
        elif (
            self.is_single_value and self.winning_claim and claim.id == self.winning_claim.id
        ) or not self.is_single_value:
            status = "Current"
            badge_variant = "success"
            is_current = True
        else:
            status = "Superseded"
            badge_variant = "info"
            is_current = False

        return MetadataDisplayClaim(
            value=claim.value,
            display_value=self._format_value(claim.value),
            source_label=claim.source.value.title(),
            status=status,
            status_badge_variant=badge_variant,
            is_current=is_current,
            can_reject=is_current,
            reject_input_name="reject_claim_ids" if is_current else None,
            reject_input_value=claim.id if is_current else None,
            reject_input_id_prefix=f"reject-{claim.id}" if is_current else None,
            timestamp=claim.timestamp,
            claim_id=claim.id,
        )

    def _fallback_document_claims(self):
        return [
            MetadataDisplayClaim(
                value=value,
                display_value=self._format_value(value),
                source_label="Document",
                status="Current",
                status_badge_variant="success",
                is_current=True,
                can_reject=self.metadata_item.key == "judges",
                reject_input_name="suppress_body_judges" if self.metadata_item.key == "judges" else None,
                reject_input_value=value if self.metadata_item.key == "judges" else None,
                reject_input_id_prefix=(f"suppress-body-judge-{index}" if self.metadata_item.key == "judges" else None),
            )
            for index, value in enumerate(self._body_values(), start=1)
        ]

    def _faux_suppressed_document_claims(self):
        if any(claim.source is MetadataSource.DOCUMENT for claim in self.resolved.all_claims):
            return []

        return [
            MetadataDisplayClaim(
                value=value,
                display_value=self._format_value(value),
                source_label="Document",
                status="Suppressed" if self.active_claims else "Current",
                status_badge_variant="failure" if self.active_claims else "success",
                is_current=not self.active_claims,
                can_reject=False,
                is_faux=True,
            )
            for value in self._body_values()
        ]

    def _body_values(self):
        value = {
            "title": self.document.body.name,
            "court": self.document.body.court,
            "jurisdiction": self.document.body.jurisdiction,
            "date": self.document.body.document_date_as_date,
            "case_number": self.document.body.case_number,
            "categories": self.document.body.categories,
            "judges": self.document.body.judges,
        }.get(self.metadata_item.key)

        if value is None:
            return []

        values = value if isinstance(self.metadata_item, MultipleMetadata) and isinstance(value, list) else [value]
        return [body_value for body_value in values if body_value]

    def _format_value(self, value):
        if isinstance(value, date):
            return value.strftime("%-d %b %Y")

        if hasattr(value, "name"):
            parent = getattr(value, "parent", None)
            if parent:
                return f"{value.name} ({parent})"
            return value.name

        return value


class DocumentMetadataView(DocumentView):
    template_engine = "jinja"
    template_name = "judgment/metadata.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "document_metadata"
        context["metadata_claim_sections"] = [
            MetadataFieldDisplayDecorator(self.document, metadata_item).section
            for metadata_item in self.document.metadata.values()
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
        judges_metadata = cast("JudgesMetadata | None", self.document.metadata.get("judges"))

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
