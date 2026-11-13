import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import (
    MetadataDateValue,
    MetadataField,
    MetadataStringValue,
)
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.documents.versions import VersionType
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from judgments.utils.metadata_backfill import (
    MetadataBackfillPlan,
    MetadataBackfillResult,
    MetadataClaimUpdate,
    apply_metadata_backfill_plan,
    backfill_document_metadata,
    plan_metadata_backfill,
)


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

    def test_restores_a_rejected_editor_claim_with_the_same_value(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        _add_claim(
            judgment,
            name="title",
            value=MetadataStringValue("Editor XML title"),
            source=MetadataSource.EDITOR,
            claim_id="rejected-editor-title",
        )
        judgment.metadata_fields.reject("rejected-editor-title")

        updates = apply_metadata_backfill_plan(judgment, MetadataBackfillPlan(title="Editor XML title"))

        assert updates == [MetadataClaimUpdate(name="title", status="restored")]
        assert judgment.metadata_fields["rejected-editor-title"].rejected is False
        editor_claims = [
            claim for claim in judgment.metadata_fields.by_name("title") if claim.source is MetadataSource.EDITOR
        ]
        assert editor_claims == [judgment.metadata_fields["rejected-editor-title"]]

    def test_apply_adds_editor_claims_reports_added(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        updates = apply_metadata_backfill_plan(judgment, MetadataBackfillPlan(title="Editor XML title"))

        assert updates == [MetadataClaimUpdate(name="title", status="added")]


class TestBackfillDocumentMetadata(SimpleTestCase):
    def test_dry_run_does_not_save(self):
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
        judgment.editing_session = MagicMock()
        judgment.save_metadata_fields = MagicMock()

        result = backfill_document_metadata(judgment, dry_run=True)

        assert result.planned.title == "Editor XML title"
        assert result.applied is False
        judgment.editing_session.assert_not_called()
        judgment.save_metadata_fields.assert_not_called()
        assert judgment.metadata.title.value == "Ingest title"

    def test_write_saves_inside_editing_session(self):
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
        session = MagicMock()
        session.__enter__.return_value = judgment
        session.__exit__.return_value = None
        judgment.editing_session = MagicMock(return_value=session)
        judgment.save_metadata_fields = MagicMock()

        result = backfill_document_metadata(judgment, dry_run=False)

        assert result.applied is True
        judgment.editing_session.assert_called_once_with()
        judgment.save_metadata_fields.assert_called_once_with()
        assert judgment.metadata.title.value == "Editor XML title"


class TestBackfillBodyMetadataClaimsCommand(SimpleTestCase):
    @patch("judgments.management.commands.backfill_body_metadata_claims.invalidate_caches")
    @patch("judgments.management.commands.backfill_body_metadata_claims.api_client")
    @patch("judgments.management.commands.backfill_body_metadata_claims.backfill_document_metadata")
    @override_settings(DEBUG=False)
    def test_uri_mode_calls_backfill(self, mock_backfill, mock_api_client, mock_invalidate):
        document = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        mock_api_client.get_document_by_uri.return_value = document
        mock_backfill.return_value = MetadataBackfillResult(
            uri="test/2023/123",
            planned=MetadataBackfillPlan(title="Editor XML title"),
            notes=["title: 'Ingest title' -> 'Editor XML title'"],
        )

        call_command("backfill_body_metadata_claims", "--uri", "test/2023/123")

        mock_api_client.get_document_by_uri.assert_called_once()
        mock_backfill.assert_called_once()
        assert mock_backfill.call_args.kwargs["dry_run"] is True
        mock_invalidate.assert_not_called()

    @patch("judgments.management.commands.backfill_body_metadata_claims.invalidate_caches")
    @patch(
        "judgments.management.commands.backfill_body_metadata_claims.Document.open_for_editing",
        create=True,
    )
    @patch("judgments.management.commands.backfill_body_metadata_claims.api_client")
    @patch("judgments.management.commands.backfill_body_metadata_claims.backfill_document_metadata")
    @override_settings(DEBUG=False)
    def test_apply_checks_out_before_loading_and_invalidates_cache(
        self,
        mock_backfill,
        mock_api_client,
        mock_open,
        mock_invalidate,
    ):
        document = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        mock_open.return_value = _checked_out(document)
        mock_backfill.return_value = MetadataBackfillResult(
            uri="test/2023/123",
            planned=MetadataBackfillPlan(title="Editor XML title"),
            applied=True,
            notes=["title: 'Ingest title' -> 'Editor XML title'"],
        )

        call_command("backfill_body_metadata_claims", "--apply", "--uri", "test/2023/123")

        mock_open.assert_called_once()
        assert str(mock_open.call_args.args[1]) == "test/2023/123"
        mock_api_client.get_document_by_uri.assert_not_called()
        assert mock_backfill.call_args.kwargs == {"dry_run": False, "lock_held": True}
        mock_invalidate.assert_called_once_with("test/2023/123")

    @patch(
        "judgments.management.commands.backfill_body_metadata_claims.Document.open_for_editing",
        create=True,
    )
    @patch("judgments.management.commands.backfill_body_metadata_claims.api_client")
    @patch("judgments.management.commands.backfill_body_metadata_claims.backfill_document_metadata")
    def test_uri_mode_honours_limit(self, mock_backfill, mock_api_client, mock_open):
        document = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        mock_open.return_value = _checked_out(document)
        mock_backfill.return_value = MetadataBackfillResult(
            uri="test/2023/1",
            planned=MetadataBackfillPlan(),
        )

        call_command(
            "backfill_body_metadata_claims",
            "--apply",
            "--limit",
            "1",
            "--uri",
            "test/2023/1",
            "--uri",
            "test/2023/2",
        )

        mock_open.assert_called_once()
        assert str(mock_open.call_args.args[1]) == "test/2023/1"
        mock_api_client.get_document_by_uri.assert_not_called()

    @patch("judgments.management.commands.backfill_body_metadata_claims.api_client")
    @patch("judgments.management.commands.backfill_body_metadata_claims.backfill_document_metadata")
    def test_uri_mode_without_limit_considers_every_uri(self, mock_backfill, mock_api_client):
        document = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        mock_api_client.get_document_by_uri.return_value = document
        mock_backfill.return_value = MetadataBackfillResult(
            uri="test/2023/1",
            planned=MetadataBackfillPlan(),
        )

        call_command(
            "backfill_body_metadata_claims",
            "--uri",
            "test/2023/1",
            "--uri",
            "test/2023/2",
        )

        assert mock_api_client.get_document_by_uri.call_count == 2
