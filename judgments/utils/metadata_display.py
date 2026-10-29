from dataclasses import dataclass
from datetime import date
from typing import Any

from caselawclient.models.documents.metadata.base import MultipleMetadata, SingleMetadata
from caselawclient.models.documents.metadata.fields.field import MetadataDateValue, MetadataStringValue


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

    @property
    def current_display_claims(self):
        return [claim for claim in self.display_claims if claim.is_current]


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

        return [self._real_claim(claim) for claim in reversed(self.resolved.all_claims)]

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
        if isinstance(value, (MetadataStringValue, MetadataDateValue)):
            value = value.value

        if isinstance(value, date):
            return value.strftime("%-d %b %Y")

        if hasattr(value, "name"):
            parent = getattr(value, "parent", None)
            if parent:
                return f"{value.name} ({parent})"
            return value.name

        return value
