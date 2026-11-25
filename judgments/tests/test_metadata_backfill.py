import json
from datetime import UTC, date, datetime
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from caselawclient.errors import MarklogicCheckoutConflictError
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import (
    MetadataDateValue,
    MetadataField,
    MetadataStringValue,
)
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.documents.versions import VersionType
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from judgments.utils.metadata_backfill import (
    MetadataBackfillPlan,
    MetadataBackfillResult,
    apply_metadata_backfill_plan,
    backfill_document_metadata,
    plan_metadata_backfill,
)

COMMAND = "judgments.management.commands.backfill_body_metadata_claims"


def _add_claim(document, *, name: str, value, source: MetadataSource, claim_id: str) -> None:
    document.metadata_fields.add(
        MetadataField(
            id=claim_id,
            name=name,
            value=value,
            source=source,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    )


def _judgment(*, body_name: str, body_date: str, title_claim: str | None = None, date_claim: date | None = None):
    judgment = JudgmentFactory.build(
        body=DocumentBodyFactory.build(
            name=body_name,
            document_date_as_string=body_date,
        ),
    )
    if title_claim is not None:
        _add_claim(
            judgment,
            name="title",
            value=MetadataStringValue(title_claim),
            source=MetadataSource.DOCUMENT,
            claim_id="title-claim",
        )
    if date_claim is not None:
        _add_claim(
            judgment,
            name="date",
            value=MetadataDateValue(date_claim),
            source=MetadataSource.DOCUMENT,
            claim_id="date-claim",
        )
    return judgment


def _reject_editor_claim(document, *, name: str, value) -> None:
    claim_id = f"rejected-editor-{name}"
    _add_claim(document, name=name, value=value, source=MetadataSource.EDITOR, claim_id=claim_id)
    document.metadata_fields.reject(claim_id)


def _version_document(
    *,
    name: str,
    document_date_as_string: str,
    version_type: str,
    version_number: int = 1,
):
    version = JudgmentFactory.build(
        uri=DocumentURIString(f"test/2023/123/_xml_versions/{version_number}-123"),
        body=DocumentBodyFactory.build(
            name=name,
            document_date_as_string=document_date_as_string,
        ),
    )
    version.structured_annotation = {
        "type": version_type,
        "automated": True,
        "calling_function": "t",
        "calling_agent": "t",
    }
    return version


def _attach_versions(judgment, *versions) -> None:
    """Expose version URIs on ``judgment`` and load a body only when asked for one."""
    judgment.versions = [{"uri": version.uri, "version": version.version_number} for version in versions]
    by_uri = {version.uri: version for version in versions}
    judgment.api_client.get_version_annotation.side_effect = lambda uri: json.dumps(by_uri[uri].structured_annotation)
    judgment.api_client.get_document_by_uri.side_effect = lambda uri: by_uri[uri]


def _checked_out(document):
    session = MagicMock()
    session.__enter__.return_value = document
    session.__exit__.return_value = False
    return session


class TestPlanMetadataBackfill(SimpleTestCase):
    def test_no_claims_means_no_backfill(self):
        judgment = _judgment(body_name="Body title", body_date="2024-01-01")

        plan = plan_metadata_backfill(judgment)

        assert plan.has_changes is False

    def test_matching_document_claim_is_skipped(self):
        judgment = _judgment(
            body_name="Same title",
            body_date="2024-01-01",
            title_claim="Same title",
            date_claim=date(2024, 1, 1),
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.has_changes is False

    def test_promotes_body_title_when_document_claim_is_stale(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _attach_versions(
            judgment,
            _version_document(
                name="Ingest title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.title == "Editor XML title"
        assert plan.date is None

    def test_skips_title_when_body_matches_latest_submission(self):
        judgment = _judgment(
            body_name="Reparsed title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _attach_versions(
            judgment,
            _version_document(
                name="Reparsed title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.has_changes is False

    def test_skips_date_when_body_matches_latest_submission(self):
        judgment = _judgment(
            body_name="Same title",
            body_date="2025-06-01",
            title_claim="Same title",
            date_claim=date(2024, 1, 1),
        )
        _attach_versions(
            judgment,
            _version_document(
                name="Same title",
                document_date_as_string="2025-06-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.has_changes is False

    def test_uses_newest_submission_when_versions_are_oldest_first(self):
        judgment = _judgment(
            body_name="Reparsed title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        older = _version_document(
            name="Ingest title",
            document_date_as_string="2024-01-01",
            version_type=VersionType.SUBMISSION.value,
            version_number=1,
        )
        newer = _version_document(
            name="Reparsed title",
            document_date_as_string="2024-01-01",
            version_type=VersionType.SUBMISSION.value,
            version_number=4,
        )
        _attach_versions(judgment, older, newer)

        plan = plan_metadata_backfill(judgment)

        assert plan.has_changes is False
        judgment.api_client.get_document_by_uri.assert_called_once_with(newer.uri)
        judgment.api_client.get_version_annotation.assert_called_once_with(newer.uri)

    def test_promotes_when_only_an_older_submission_matches_the_body(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _attach_versions(
            judgment,
            _version_document(
                name="Editor XML title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
                version_number=1,
            ),
            _version_document(
                name="Ingest title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
                version_number=4,
            ),
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.title == "Editor XML title"

    def test_does_not_load_a_newer_edit_when_an_older_submission_is_the_baseline(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        submission = _version_document(
            name="Ingest title",
            document_date_as_string="2024-01-01",
            version_type=VersionType.SUBMISSION.value,
            version_number=2,
        )
        edit = _version_document(
            name="Editor XML title",
            document_date_as_string="2024-01-01",
            version_type=VersionType.EDIT.value,
            version_number=5,
        )
        _attach_versions(judgment, submission, edit)

        plan = plan_metadata_backfill(judgment)

        assert plan.title == "Editor XML title"
        judgment.api_client.get_document_by_uri.assert_called_once_with(submission.uri)

    def test_skips_versions_whose_annotation_cannot_be_read(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        submission = _version_document(
            name="Ingest title",
            document_date_as_string="2024-01-01",
            version_type=VersionType.SUBMISSION.value,
            version_number=1,
        )
        legacy = _version_document(
            name="Editor XML title",
            document_date_as_string="2024-01-01",
            version_type=VersionType.SUBMISSION.value,
            version_number=3,
        )
        _attach_versions(judgment, submission, legacy)
        read_annotation = judgment.api_client.get_version_annotation.side_effect
        judgment.api_client.get_version_annotation.side_effect = lambda uri: (
            "a plain string annotation" if uri == legacy.uri else read_annotation(uri)
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.title == "Editor XML title"
        judgment.api_client.get_document_by_uri.assert_called_once_with(submission.uri)

    def test_promotes_body_date_when_document_claim_is_stale(self):
        judgment = _judgment(
            body_name="Same title",
            body_date="2025-06-01",
            title_claim="Same title",
            date_claim=date(2024, 1, 1),
        )
        _attach_versions(
            judgment,
            _version_document(
                name="Same title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.RESTORE.value,
            ),
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.title is None
        assert plan.date == date(2025, 6, 1)

    def test_title_and_date_share_one_submission_lookup(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2025-06-01",
            title_claim="Ingest title",
            date_claim=date(2024, 1, 1),
        )
        submission = _version_document(
            name="Ingest title",
            document_date_as_string="2024-01-01",
            version_type=VersionType.SUBMISSION.value,
        )
        _attach_versions(judgment, submission)

        plan = plan_metadata_backfill(judgment)

        assert plan.title == "Editor XML title"
        assert plan.date == date(2025, 6, 1)
        judgment.api_client.get_document_by_uri.assert_called_once_with(submission.uri)

    def test_editor_claim_winner_is_not_overridden(self):
        judgment = _judgment(
            body_name="Body title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _add_claim(
            judgment,
            name="title",
            value=MetadataStringValue("Editor claim title"),
            source=MetadataSource.EDITOR,
            claim_id="editor-title",
        )

        plan = plan_metadata_backfill(judgment)

        assert plan.has_changes is False

    def test_rejected_editor_title_claim_with_the_body_value_is_left_alone(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _reject_editor_claim(judgment, name="title", value=MetadataStringValue("Editor XML title"))

        plan = plan_metadata_backfill(judgment)

        assert plan.title is None
        assert plan.has_changes is False
        assert plan.already_claimed == ("title",)

    def test_rejected_editor_date_claim_with_the_body_value_is_left_alone(self):
        judgment = _judgment(
            body_name="Same title",
            body_date="2025-06-01",
            title_claim="Same title",
            date_claim=date(2024, 1, 1),
        )
        _reject_editor_claim(judgment, name="date", value=MetadataDateValue(date(2025, 6, 1)))

        plan = plan_metadata_backfill(judgment)

        assert plan.date is None
        assert plan.already_claimed == ("date",)

    def test_rejected_editor_claim_with_a_different_value_does_not_block_the_backfill(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _reject_editor_claim(judgment, name="title", value=MetadataStringValue("Some other title"))

        plan = plan_metadata_backfill(judgment)

        assert plan.title == "Editor XML title"
        assert plan.already_claimed == ()

    def test_apply_adds_editor_claims(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2025-06-01",
            title_claim="Ingest title",
            date_claim=date(2024, 1, 1),
        )
        plan = plan_metadata_backfill(judgment)
        # No submission version, so both divergences are treated as stale XML edits.
        assert plan.title == "Editor XML title"
        assert plan.date == date(2025, 6, 1)

        apply_metadata_backfill_plan(judgment, plan)

        assert judgment.metadata.title.value == "Editor XML title"
        assert judgment.metadata.date.value == date(2025, 6, 1)
        assert any(
            claim.source is MetadataSource.EDITOR and claim.value == MetadataStringValue("Editor XML title")
            for claim in judgment.metadata_fields.by_name("title")
        )

    def test_apply_adds_only_the_planned_fields(self):
        judgment = _judgment(
            body_name="Same title",
            body_date="2025-06-01",
            title_claim="Same title",
            date_claim=date(2024, 1, 1),
        )

        apply_metadata_backfill_plan(judgment, MetadataBackfillPlan(date=date(2025, 6, 1)))

        assert judgment.metadata.date.value == date(2025, 6, 1)
        assert [claim.source for claim in judgment.metadata_fields.by_name("title")] == [MetadataSource.DOCUMENT]


class TestBackfillDocumentMetadata(SimpleTestCase):
    def _stale_title_judgment(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _attach_versions(
            judgment,
            _version_document(
                name="Ingest title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        )
        judgment.save_metadata_fields = MagicMock()
        return judgment

    def test_dry_run_does_not_save(self):
        judgment = self._stale_title_judgment()
        judgment.editing_session = MagicMock()

        result = backfill_document_metadata(judgment, dry_run=True)

        assert result.planned.title == "Editor XML title"
        assert result.applied is False
        judgment.editing_session.assert_not_called()
        judgment.save_metadata_fields.assert_not_called()
        assert judgment.metadata.title.value == "Ingest title"

    def test_write_saves_inside_editing_session(self):
        judgment = self._stale_title_judgment()
        judgment.editing_session = MagicMock(return_value=_checked_out(judgment))

        result = backfill_document_metadata(judgment, dry_run=False)

        assert result.applied is True
        judgment.editing_session.assert_called_once_with()
        judgment.save_metadata_fields.assert_called_once_with()
        assert judgment.metadata.title.value == "Editor XML title"

    def test_write_with_the_lock_already_held_does_not_open_another_session(self):
        judgment = self._stale_title_judgment()
        judgment.editing_session = MagicMock()

        result = backfill_document_metadata(judgment, dry_run=False, lock_held=True)

        assert result.applied is True
        judgment.editing_session.assert_not_called()
        judgment.save_metadata_fields.assert_called_once_with()

    def test_nothing_stale_is_skipped_without_saving(self):
        judgment = _judgment(body_name="Body title", body_date="2024-01-01")
        judgment.save_metadata_fields = MagicMock()

        result = backfill_document_metadata(judgment, dry_run=False, lock_held=True)

        assert result.applied is False
        assert result.skipped_reason == "no stale document-source title/date"
        judgment.save_metadata_fields.assert_not_called()

    def test_rejected_editor_claim_is_reported_and_not_restored(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _reject_editor_claim(judgment, name="title", value=MetadataStringValue("Editor XML title"))
        judgment.save_metadata_fields = MagicMock()

        result = backfill_document_metadata(judgment, dry_run=False, lock_held=True)

        assert result.applied is False
        assert result.skipped_reason == "editor claim with this value already exists"
        judgment.save_metadata_fields.assert_not_called()
        assert judgment.metadata_fields["rejected-editor-title"].rejected is True
        assert judgment.metadata.title.value == "Ingest title"

    def test_applies_one_field_and_reports_the_other_as_skipped(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2025-06-01",
            title_claim="Ingest title",
            date_claim=date(2024, 1, 1),
        )
        _reject_editor_claim(judgment, name="date", value=MetadataDateValue(date(2025, 6, 1)))
        judgment.save_metadata_fields = MagicMock()

        result = backfill_document_metadata(judgment, dry_run=False, lock_held=True)

        assert result.applied is True
        assert result.planned.title == "Editor XML title"
        assert result.planned.date is None
        assert "date: skipped, editor claim with this value already exists" in result.notes
        judgment.save_metadata_fields.assert_called_once_with()
        assert judgment.metadata.date.value == date(2024, 1, 1)

    def test_dry_run_notes_only_describe_the_date_when_just_the_date_is_stale(self):
        judgment = _judgment(
            body_name="Same title",
            body_date="2025-06-01",
            title_claim="Same title",
            date_claim=date(2024, 1, 1),
        )

        result = backfill_document_metadata(judgment, dry_run=True)

        assert result.notes == ["date: datetime.date(2024, 1, 1) -> datetime.date(2025, 6, 1)"]

    def test_dry_run_notes_describe_title_and_date_changes(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2025-06-01",
            title_claim="Ingest title",
            date_claim=date(2024, 1, 1),
        )

        result = backfill_document_metadata(judgment, dry_run=True)

        assert result.notes == [
            "title: 'Ingest title' -> 'Editor XML title'",
            "date: datetime.date(2024, 1, 1) -> datetime.date(2025, 6, 1)",
        ]


def _planned_result(uri: str = "test/2023/1", *, applied: bool = False) -> MetadataBackfillResult:
    return MetadataBackfillResult(
        uri=uri,
        planned=MetadataBackfillPlan(title="Editor XML title"),
        applied=applied,
        notes=["title: 'Ingest title' -> 'Editor XML title'"],
    )


def _skipped_result(uri: str = "test/2023/2") -> MetadataBackfillResult:
    return MetadataBackfillResult(
        uri=uri,
        planned=MetadataBackfillPlan(),
        skipped_reason="no stale document-source title/date",
    )


def _run_command(*args: str) -> tuple[str, str]:
    stdout, stderr = StringIO(), StringIO()
    call_command("backfill_body_metadata_claims", *args, stdout=stdout, stderr=stderr)
    return stdout.getvalue(), stderr.getvalue()


def _search_page(uris: list[str], *, total: int):
    return SimpleNamespace(results=[SimpleNamespace(uri=uri) for uri in uris], total=total)


@patch(f"{COMMAND}.api_client")
@patch(f"{COMMAND}.backfill_document_metadata")
class TestBackfillBodyMetadataClaimsCommandUriMode(SimpleTestCase):
    def test_dry_run_loads_the_document_without_checking_it_out(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Editor XML title", body_date="2024-01-01", title_claim="Ingest title")
        mock_api_client.get_document_by_uri.return_value = document
        mock_backfill.return_value = _planned_result("test/2023/123")

        stdout, _ = _run_command("--uri", "test/2023/123")

        mock_api_client.get_document_by_uri.assert_called_once()
        mock_backfill.assert_called_once_with(document, dry_run=True)
        assert "Backfilling body metadata claims (DRY-RUN)" in stdout
        assert "test/2023/123: planned (title: 'Ingest title' -> 'Editor XML title')" in stdout
        assert "Done. considered=1 changed=1 applied=0 skipped=0 failed=0" in stdout

    @override_settings(DEBUG=False)
    def test_apply_checks_out_before_loading_and_invalidates_the_cache(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Editor XML title", body_date="2024-01-01", title_claim="Ingest title")
        mock_backfill.return_value = _planned_result("test/2023/123", applied=True)

        with (
            patch(f"{COMMAND}.Document.open_for_editing", return_value=_checked_out(document)) as mock_open,
            patch(f"{COMMAND}.invalidate_caches_for_uris") as mock_invalidate,
        ):
            stdout, _ = _run_command("--apply", "--uri", "test/2023/123")

        mock_open.assert_called_once_with(mock_api_client, "test/2023/123")
        mock_api_client.get_document_by_uri.assert_not_called()
        mock_backfill.assert_called_once_with(document, dry_run=False, lock_held=True)
        mock_invalidate.assert_called_once_with(["test/2023/123"])
        assert "Backfilling body metadata claims (APPLY)" in stdout
        assert "test/2023/123: applied" in stdout
        assert "Done. considered=1 changed=1 applied=1 skipped=0 failed=0" in stdout

    @override_settings(DEBUG=True)
    def test_apply_does_not_invalidate_the_cache_when_debugging(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Editor XML title", body_date="2024-01-01", title_claim="Ingest title")
        mock_backfill.return_value = _planned_result(applied=True)

        with (
            patch(f"{COMMAND}.Document.open_for_editing", return_value=_checked_out(document)),
            patch(f"{COMMAND}.invalidate_caches_for_uris") as mock_invalidate,
        ):
            _run_command("--apply", "--uri", "test/2023/1")

        mock_invalidate.assert_not_called()

    @override_settings(DEBUG=False)
    def test_apply_does_not_invalidate_the_cache_when_nothing_was_written(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Body title", body_date="2024-01-01")
        mock_backfill.return_value = _skipped_result("test/2023/1")

        with (
            patch(f"{COMMAND}.Document.open_for_editing", return_value=_checked_out(document)),
            patch(f"{COMMAND}.invalidate_caches_for_uris") as mock_invalidate,
        ):
            stdout, _ = _run_command("--apply", "--uri", "test/2023/1")

        mock_invalidate.assert_not_called()
        assert "test/2023/1: skipped (no stale document-source title/date)" in stdout
        assert "Done. considered=1 changed=0 applied=0 skipped=1 failed=0" in stdout

    @override_settings(DEBUG=False)
    def test_a_cache_invalidation_failure_is_reported_but_the_write_still_counts(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Editor XML title", body_date="2024-01-01", title_claim="Ingest title")
        mock_backfill.return_value = _planned_result(applied=True)

        with (
            patch(f"{COMMAND}.Document.open_for_editing", return_value=_checked_out(document)),
            patch(f"{COMMAND}.invalidate_caches_for_uris", side_effect=RuntimeError("cloudfront down")),
        ):
            stdout, stderr = _run_command("--apply", "--uri", "test/2023/1")

        assert "saved 1 document(s), but cache invalidation failed: cloudfront down" in stderr
        assert "Done. considered=1 changed=1 applied=1 skipped=0 failed=0" in stdout

    @override_settings(DEBUG=False)
    def test_the_cache_is_invalidated_once_for_every_document_written(self, mock_backfill, mock_api_client):
        documents = [
            _judgment(body_name="Editor XML title", body_date="2024-01-01", title_claim="Ingest title")
            for _ in range(3)
        ]
        mock_backfill.side_effect = [
            _planned_result("test/2023/1", applied=True),
            _skipped_result("test/2023/2"),
            _planned_result("test/2023/3", applied=True),
        ]

        with (
            patch(
                f"{COMMAND}.Document.open_for_editing",
                side_effect=[_checked_out(document) for document in documents],
            ),
            patch(f"{COMMAND}.invalidate_caches_for_uris") as mock_invalidate,
        ):
            _run_command("--apply", "--uri", "test/2023/1", "--uri", "test/2023/2", "--uri", "test/2023/3")

        mock_invalidate.assert_called_once_with(["test/2023/1", "test/2023/3"])

    def test_a_checked_out_document_is_reported_as_failed_and_the_run_continues(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Editor XML title", body_date="2024-01-01", title_claim="Ingest title")
        mock_backfill.return_value = _planned_result("test/2023/2", applied=True)

        with (
            patch(
                f"{COMMAND}.Document.open_for_editing",
                side_effect=[MarklogicCheckoutConflictError("locked"), _checked_out(document)],
            ),
            patch(f"{COMMAND}.invalidate_caches_for_uris"),
        ):
            stdout, stderr = _run_command("--apply", "--uri", "test/2023/1", "--uri", "test/2023/2")

        assert "test/2023/1: ERROR already checked out" in stderr
        assert "Done. considered=2 changed=1 applied=1 skipped=0 failed=1" in stdout

    def test_an_unexpected_error_is_reported_as_failed_and_the_run_continues(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Body title", body_date="2024-01-01")
        mock_api_client.get_document_by_uri.side_effect = [RuntimeError("boom"), document]
        mock_backfill.return_value = _skipped_result("test/2023/2")

        stdout, stderr = _run_command("--uri", "test/2023/1", "--uri", "test/2023/2")

        assert "test/2023/1: ERROR boom" in stderr
        assert "Done. considered=2 changed=0 applied=0 skipped=1 failed=1" in stdout

    def test_limit_applies_to_explicit_uris(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Body title", body_date="2024-01-01")
        mock_api_client.get_document_by_uri.return_value = document
        mock_backfill.return_value = _skipped_result("test/2023/1")

        with patch(f"{COMMAND}.Document.open_for_editing", return_value=_checked_out(document)) as mock_open:
            _run_command("--apply", "--limit", "1", "--uri", "test/2023/1", "--uri", "test/2023/2")

        mock_open.assert_called_once_with(mock_api_client, "test/2023/1")

    def test_without_a_limit_every_explicit_uri_is_considered(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Body title", body_date="2024-01-01")
        mock_api_client.get_document_by_uri.return_value = document
        mock_backfill.return_value = _skipped_result("test/2023/1")

        _run_command("--uri", "test/2023/1", "--uri", "test/2023/2")

        assert mock_api_client.get_document_by_uri.call_count == 2

    def test_planned_and_skipped_documents_are_counted_separately(self, mock_backfill, mock_api_client):
        document = _judgment(body_name="Body title", body_date="2024-01-01")
        mock_api_client.get_document_by_uri.return_value = document
        mock_backfill.side_effect = [_planned_result("test/2023/1"), _skipped_result("test/2023/2")]

        stdout, _ = _run_command("--uri", "test/2023/1", "--uri", "test/2023/2")

        assert "test/2023/1: planned" in stdout
        assert "test/2023/2: skipped (no stale document-source title/date)" in stdout
        assert "Done. considered=2 changed=1 applied=0 skipped=1 failed=0" in stdout


@patch(f"{COMMAND}.api_client")
@patch(f"{COMMAND}.backfill_document_metadata")
@patch(f"{COMMAND}.search_and_parse_response")
class TestBackfillBodyMetadataClaimsCommandScanMode(SimpleTestCase):
    def test_scans_every_page_of_search_results(self, mock_search, mock_backfill, mock_api_client):
        mock_search.side_effect = [
            _search_page(["test/2023/1", "test/2023/2"], total=3),
            _search_page(["test/2023/3"], total=3),
        ]
        mock_backfill.return_value = _skipped_result()

        stdout, _ = _run_command("--page-size", "2")

        assert [call.args[0] for call in mock_api_client.get_document_by_uri.call_args_list] == [
            "test/2023/1",
            "test/2023/2",
            "test/2023/3",
        ]
        first_search, second_search = (call.args[1] for call in mock_search.call_args_list)
        assert (first_search.page, first_search.page_size) == (1, 2)
        assert second_search.page == 2
        assert first_search.show_unpublished is True
        assert "Done. considered=3 changed=0 applied=0 skipped=3 failed=0" in stdout

    def test_stops_when_a_page_comes_back_empty(self, mock_search, mock_backfill, mock_api_client):
        mock_search.side_effect = [
            _search_page(["test/2023/1"], total=10),
            _search_page([], total=10),
        ]
        mock_backfill.return_value = _skipped_result()

        stdout, _ = _run_command("--page-size", "1")

        assert mock_search.call_count == 2
        assert "Done. considered=1" in stdout

    @override_settings(DEBUG=False)
    def test_documents_already_written_are_invalidated_when_the_scan_fails_part_way(
        self,
        mock_search,
        mock_backfill,
        mock_api_client,
    ):
        document = _judgment(body_name="Editor XML title", body_date="2024-01-01", title_claim="Ingest title")
        mock_search.side_effect = [
            _search_page(["test/2023/1"], total=2),
            RuntimeError("search unavailable"),
        ]
        mock_backfill.return_value = _planned_result("test/2023/1", applied=True)

        with (
            patch(f"{COMMAND}.Document.open_for_editing", return_value=_checked_out(document)),
            patch(f"{COMMAND}.invalidate_caches_for_uris") as mock_invalidate,
            pytest.raises(RuntimeError, match="search unavailable"),
        ):
            _run_command("--apply", "--page-size", "1")

        mock_invalidate.assert_called_once_with(["test/2023/1"])

    def test_limit_stops_the_scan_part_way_through_a_page(self, mock_search, mock_backfill, mock_api_client):
        mock_search.return_value = _search_page(["test/2023/1", "test/2023/2"], total=50)
        mock_backfill.return_value = _skipped_result()

        stdout, _ = _run_command("--limit", "1")

        mock_search.assert_called_once()
        assert mock_api_client.get_document_by_uri.call_count == 1
        assert "Done. considered=1" in stdout


class TestBackfillBodyMetadataClaimsCommandArguments(SimpleTestCase):
    def test_page_size_must_be_positive(self):
        with pytest.raises(CommandError, match="--page-size must be at least 1"):
            _run_command("--page-size", "0")

    def test_limit_must_be_positive(self):
        with pytest.raises(CommandError, match="--limit must be at least 1"):
            _run_command("--limit", "0")
