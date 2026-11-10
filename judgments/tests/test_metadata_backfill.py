from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents.metadata.fields.field import (
    MetadataDateValue,
    MetadataField,
    MetadataStringValue,
)
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.documents.versions import VersionType
from django.core.management import call_command
from django.test import SimpleTestCase

from judgments.utils.metadata_backfill import (
    MetadataBackfillPlan,
    MetadataBackfillResult,
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


def _version_document(*, name: str, document_date_as_string: str, version_type: str):
    version = JudgmentFactory.build(
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
        judgment.versions_as_documents = [
            _version_document(
                name="Ingest title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        ]

        plan = plan_metadata_backfill(judgment)

        assert plan.title == "Editor XML title"
        assert plan.date is None

    def test_skips_title_when_body_matches_latest_submission(self):
        judgment = _judgment(
            body_name="Reparsed title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        judgment.versions_as_documents = [
            _version_document(
                name="Reparsed title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        ]

        plan = plan_metadata_backfill(judgment)

        assert plan.has_changes is False

    def test_promotes_body_date_when_document_claim_is_stale(self):
        judgment = _judgment(
            body_name="Same title",
            body_date="2025-06-01",
            title_claim="Same title",
            date_claim=date(2024, 1, 1),
        )
        judgment.versions_as_documents = [
            _version_document(
                name="Same title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.RESTORE.value,
            ),
        ]

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


class TestBackfillDocumentMetadata(SimpleTestCase):
    def test_dry_run_does_not_save(self):
        judgment = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        judgment.versions_as_documents = [
            _version_document(
                name="Ingest title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        ]
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
        judgment.versions_as_documents = [
            _version_document(
                name="Ingest title",
                document_date_as_string="2024-01-01",
                version_type=VersionType.SUBMISSION.value,
            ),
        ]
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
    @patch("judgments.management.commands.backfill_body_metadata_claims.api_client")
    @patch("judgments.management.commands.backfill_body_metadata_claims.backfill_document_metadata")
    def test_uri_mode_calls_backfill(self, mock_backfill, mock_api_client):
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

    @patch("judgments.management.commands.backfill_body_metadata_claims.api_client")
    @patch("judgments.management.commands.backfill_body_metadata_claims.backfill_document_metadata")
    def test_apply_mode_disables_dry_run(self, mock_backfill, mock_api_client):
        document = _judgment(
            body_name="Editor XML title",
            body_date="2024-01-01",
            title_claim="Ingest title",
        )
        mock_api_client.get_document_by_uri.return_value = document
        mock_backfill.return_value = MetadataBackfillResult(
            uri="test/2023/123",
            planned=MetadataBackfillPlan(title="Editor XML title"),
            applied=True,
            notes=["title: 'Ingest title' -> 'Editor XML title'"],
        )

        call_command("backfill_body_metadata_claims", "--apply", "--uri", "test/2023/123")

        assert mock_backfill.call_args.kwargs["dry_run"] is False
