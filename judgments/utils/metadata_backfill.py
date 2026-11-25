"""Promote body title/date into editor claims when document claims are stale.

Documents materialised before the editor wrote structured metadata can have a
document-source title/date claim that freezes the ingest snapshot, while a later
``set_document_name`` / date patch only updated the body XML. Search and the
document page both prefer the structured claim, so those edits disappear.

A later reparse can also leave body and document claim disagreeing. In that case
the body matches the latest submission/restore version, and the document claim
is the value we mean to keep — do not promote the body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, cast

from caselawclient.models.documents.metadata.fields.field import (
    MetadataDateValue,
    MetadataField,
    MetadataStringValue,
)
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.documents.versions import AnnotationDataDict, VersionType
from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from datetime import date

    from caselawclient.models.documents import Document
    from caselawclient.models.utilities import VersionsDict

FieldName = Literal["title", "date"]

_SUBMISSION_OR_RESTORE = {
    VersionType.SUBMISSION.value,
    VersionType.RESTORE.value,
}


@dataclass(frozen=True)
class MetadataBackfillPlan:
    """Fields that should receive an editor claim copied from the body.

    ``already_claimed`` lists fields where an editor claim with the body's value
    already exists. Only a rejected claim can get here, because an active editor
    claim would already be winning. They are left alone so that an editor's
    rejection is not undone.
    """

    title: str | None = None
    date: date | None = None
    already_claimed: tuple[FieldName, ...] = ()

    @property
    def has_changes(self) -> bool:
        return self.title is not None or self.date is not None


@dataclass
class MetadataBackfillResult:
    uri: str
    planned: MetadataBackfillPlan
    applied: bool = False
    skipped_reason: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)


def latest_submission_or_restore_body(document: Document) -> Document | None:
    """Return the newest submission/restore version, loading only that body.

    ``document.versions`` is the version list (URI and number). Annotations are
    read until the newest submission or restore is found, and only that version's
    document is loaded. ``versions_as_documents`` would fetch every version body.
    """
    # MarkLogic usually returns versions newest-first, but that order is not guaranteed.
    versions = sorted(document.versions, key=lambda version: version["version"], reverse=True)
    for version in versions:
        annotation = _version_annotation(document, version)
        if annotation is None or annotation.get("type") not in _SUBMISSION_OR_RESTORE:
            continue
        return document.api_client.get_document_by_uri(version["uri"])
    return None


def _version_annotation(document: Document, version: VersionsDict) -> AnnotationDataDict | None:
    try:
        raw_annotation = document.api_client.get_version_annotation(version["uri"])
        return TypeAdapter(AnnotationDataDict).validate_json(raw_annotation)
    except (ValidationError, ValueError, TypeError, AttributeError):
        return None


def _winning_document_title(document: Document) -> str | None:
    resolved = document.metadata_fields.resolve("title")
    if resolved.winning_source is not MetadataSource.DOCUMENT or resolved.value is None:
        return None
    return cast("MetadataStringValue", resolved.value).value


def _winning_document_date(document: Document) -> date | None:
    resolved = document.metadata_fields.resolve("date")
    if resolved.winning_source is not MetadataSource.DOCUMENT or resolved.value is None:
        return None
    return cast("MetadataDateValue", resolved.value).value


def plan_metadata_backfill(document: Document) -> MetadataBackfillPlan:
    """Decide which body values should become editor claims for ``document``."""
    title_to_promote: str | None = None
    date_to_promote: date | None = None
    already_claimed: list[FieldName] = []
    submission = None

    claim_title = _winning_document_title(document)
    body_title = document.body.name.strip()
    if claim_title is not None and body_title and body_title != claim_title:
        submission = latest_submission_or_restore_body(document)
        submission_title = submission.body.name.strip() if submission is not None else None
        if submission_title is None or body_title != submission_title:
            if document.metadata_fields.has_claim("title", MetadataStringValue(body_title), MetadataSource.EDITOR):
                already_claimed.append("title")
            else:
                title_to_promote = body_title

    claim_date = _winning_document_date(document)
    body_date = document.body.document_date_as_date
    if claim_date is not None and body_date is not None and body_date != claim_date:
        if submission is None:
            submission = latest_submission_or_restore_body(document)
        submission_date = submission.body.document_date_as_date if submission is not None else None
        if submission_date is None or body_date != submission_date:
            if document.metadata_fields.has_claim("date", MetadataDateValue(body_date), MetadataSource.EDITOR):
                already_claimed.append("date")
            else:
                date_to_promote = body_date

    return MetadataBackfillPlan(
        title=title_to_promote,
        date=date_to_promote,
        already_claimed=tuple(already_claimed),
    )


def apply_metadata_backfill_plan(document: Document, plan: MetadataBackfillPlan) -> None:
    """Add editor claims from ``plan`` onto ``document`` in memory."""
    if plan.title is not None:
        document.metadata_fields.add(
            MetadataField(
                name="title",
                value=MetadataStringValue(plan.title),
                source=MetadataSource.EDITOR,
            ),
        )
    if plan.date is not None:
        document.metadata_fields.add(
            MetadataField(
                name="date",
                value=MetadataDateValue(plan.date),
                source=MetadataSource.EDITOR,
            ),
        )


def backfill_document_metadata(
    document: Document,
    *,
    dry_run: bool,
    lock_held: bool = False,
) -> MetadataBackfillResult:
    """Plan and optionally persist editor claims for a single document.

    ``lock_held`` means the caller already checked the document out, as
    ``Document.open_for_editing`` does before loading it. A second
    ``editing_session`` would be rejected.
    """
    if dry_run or lock_held:
        return _backfill_loaded_document(document, persist=not dry_run)

    with document.editing_session():
        return _backfill_loaded_document(document, persist=True)


def _backfill_loaded_document(document: Document, *, persist: bool) -> MetadataBackfillResult:
    plan = plan_metadata_backfill(document)
    result = MetadataBackfillResult(uri=str(document.uri), planned=plan)

    if not plan.has_changes:
        result.skipped_reason = (
            "editor claim with this value already exists"
            if plan.already_claimed
            else "no stale document-source title/date"
        )
        return result

    if plan.title is not None:
        result.notes.append(f"title: {document.metadata.title.value!r} -> {plan.title!r}")
    if plan.date is not None:
        result.notes.append(f"date: {document.metadata.date.value!r} -> {plan.date!r}")
    result.notes.extend(
        f"{name}: skipped, editor claim with this value already exists" for name in plan.already_claimed
    )

    if not persist:
        return result

    apply_metadata_backfill_plan(document, plan)
    document.save_metadata_fields()
    result.applied = True
    return result
