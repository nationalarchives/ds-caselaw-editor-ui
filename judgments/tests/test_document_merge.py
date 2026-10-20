import datetime
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from caselawclient.errors import InvalidContentHashError, MarklogicCheckoutConflictError
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.exceptions import DocumentMergeNotPossibleError
from caselawclient.models.documents.metadata.base import MultipleMetadata, SingleMetadata
from caselawclient.models.judgments import Judgment
from caselawclient.types import SuccessFailureMessageTuple
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from factories import make_editor
from waffle.testutils import override_flag

from judgments.templatetags.navigation_tags import DOCUMENT_MERGE_FLAG
from judgments.views.document_merge import (
    IDENTIFIER_REPLACEMENT,
    MULTIPLE_VALUE_CHANGE,
    PROPERTY_REPLACEMENT,
    SINGLE_VALUE_CHANGE,
    MergeComparisonRow,
    MergeComparisonSection,
    build_merge_comparison,
    merge_annotation_message,
)


class TitleMetadata(SingleMetadata[str]):
    key = "title"
    title = "Title"
    description = ""
    LOGIC_VERSION = 1

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class DateMetadata(SingleMetadata[datetime.date | None]):
    key = "date"
    title = "Date"
    description = ""
    LOGIC_VERSION = 1

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class JudgesMetadata(MultipleMetadata[str]):
    key = "judges"
    title = "Judges"
    description = ""
    LOGIC_VERSION = 1

    def __init__(self, values):
        self._values = values

    @property
    def values(self):
        return self._values


def identifier(schema_name, value, *, allow_multiple=False, deprecated=False):
    return SimpleNamespace(
        value=value,
        deprecated=deprecated,
        schema=SimpleNamespace(name=schema_name, allow_multiple=allow_multiple),
    )


def document_stub(uri, metadata, identifiers=None, **attributes):
    document = SimpleNamespace(
        uri=uri,
        metadata=metadata,
        identifiers=identifiers or {},
        source_name=attributes.get("source_name", ""),
        source_email=attributes.get("source_email", ""),
        consignment_reference=attributes.get("consignment_reference", ""),
        api_client=Mock(),
    )
    stored_properties = attributes.get("properties", {})
    document.api_client.get_property.side_effect = lambda _uri, name: stored_properties.get(name, "")
    return document


class TestMergeComparison(TestCase):
    def test_comparison_highlights_metadata_identifiers_and_submitter_changes(self):
        target = document_stub(
            "target/1",
            [
                TitleMetadata("Target title"),
                DateMetadata(datetime.date(2024, 1, 2)),
                JudgesMetadata(["Ada"]),
            ],
            {"ncn": identifier("Neutral citation", "[2020] UKSC 1")},
            source_name="Old submitter",
            source_email="old@example.com",
            consignment_reference="TDR-OLD",
            properties={"source-organisation": "Old court", "transfer-received-at": "2020-01-01"},
        )
        source = document_stub(
            "source/1",
            [
                TitleMetadata("Source title"),
                DateMetadata(datetime.date(2024, 1, 2)),
                JudgesMetadata(["Ada", "Grace"]),
            ],
            {
                "ncn": identifier("Neutral citation", "[2024] UKSC 1"),
                "old-ncn": identifier("Neutral citation", "[2019] UKSC 9", deprecated=True),
            },
            source_name="New submitter",
            source_email="",
            consignment_reference="TDR-OLD",
            properties={"source-organisation": "", "transfer-received-at": "2024-05-01"},
        )

        sections = {section.title: section for section in build_merge_comparison(target, source)}

        metadata = {row.label: row for row in sections["Case metadata"].rows}
        assert metadata["Title"] == MergeComparisonRow(
            label="Title",
            target_values=["Target title"],
            source_values=["Source title"],
            changed=True,
            detail=SINGLE_VALUE_CHANGE,
        )
        assert metadata["Date"].changed is False
        assert metadata["Date"].target_values == ["2 Jan 2024"]
        assert metadata["Judges"] == MergeComparisonRow(
            label="Judges",
            target_values=["Ada"],
            source_values=["Ada", "Grace"],
            changed=True,
            detail=MULTIPLE_VALUE_CHANGE,
        )

        identifiers = {row.label: row for row in sections["Identifiers"].rows}
        assert identifiers["Neutral citation"] == MergeComparisonRow(
            label="Neutral citation",
            target_values=["[2020] UKSC 1"],
            source_values=["[2024] UKSC 1"],
            changed=True,
            detail=IDENTIFIER_REPLACEMENT,
        )

        properties = {row.label: row for row in sections["Submitter and TDR"].rows}
        assert properties["Submitter name"].changed is True
        assert properties["Submitter name"].detail == PROPERTY_REPLACEMENT
        assert properties["Submitter email"].changed is False
        assert properties["Submitter email"].target_values == ["old@example.com"]
        assert properties["TDR reference"].changed is False
        assert properties["Submitter organisation"].changed is False
        assert properties["TDR received"] == MergeComparisonRow(
            label="TDR received",
            target_values=["2020-01-01"],
            source_values=["2024-05-01"],
            changed=True,
            detail=PROPERTY_REPLACEMENT,
        )

    def test_blank_note_uses_the_source_uri(self):
        assert merge_annotation_message("  ", "source/1") == "Merged from source/1"
        assert merge_annotation_message("Keep the citation", "source/1") == "Keep the citation"


def _judgment(uri, name):
    return JudgmentFactory.build(
        uri=DocumentURIString(uri),
        body=DocumentBodyFactory.build(name=name),
    )


class TestDocumentMergeViews(TestCase):
    def setUp(self):
        self.editor = make_editor("merge-editor")
        self.reader = make_editor("merge-reader")
        self.reader.groups.clear()

    @override_flag(DOCUMENT_MERGE_FLAG, active=False)
    def test_merge_is_not_available_when_the_flag_is_off(self):
        self.client.force_login(self.editor)

        search_url = reverse("merge-document", kwargs={"document_uri": "source/1"})
        review_url = reverse("merge-document-review", kwargs={"document_uri": "source/1"})

        assert self.client.get(search_url).status_code == 404
        assert self.client.get(f"{review_url}?target=target/1").status_code == 404
        assert self.client.post("/merge", {"source_uri": "source/1", "target_uri": "target/1"}).status_code == 404

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.views.document_merge.get_search_results_from_filters")
    @patch("judgments.utils.view_helpers.api_client.document_exists")
    @patch("judgments.utils.view_helpers.api_client.get_document_type_from_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_search_offers_other_documents_as_targets(
        self,
        mock_get_document,
        document_type,
        document_exists,
        mock_search,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None
        source = _judgment("source/1", "Source v Target")
        mock_get_document.return_value = source
        other = SimpleNamespace(
            uri="other/1",
            name="Other v Case",
            neutral_citation="[2024] OTHER 1",
            court=SimpleNamespace(name="UKSC"),
            metadata=SimpleNamespace(
                submission_datetime=datetime.datetime(2024, 1, 2, 3, 4),
                author="Ada",
                editor_status="New",
                consignment_reference="TDR-9",
            ),
        )
        same = SimpleNamespace(
            uri=source.uri,
            name="Source v Target",
            neutral_citation="[2024] SOURCE 1",
            court=SimpleNamespace(name="UKSC"),
            metadata=other.metadata,
        )
        mock_search.return_value = {
            "documents": [same, other],
            "total": 2,
            "total_count_postfix": "documents",
            "query": "Other",
            "search_filter": "default",
            "paginator": {
                "page_range": [1],
                "current_page": 1,
                "has_prev_page": False,
                "has_next_page": False,
            },
        }

        self.client.force_login(self.reader)
        response = self.client.get(reverse("merge-document", kwargs={"document_uri": source.uri}), {"query": "Other"})

        content = response.content.decode("utf-8")
        assert response.status_code == 200
        assert "Other v Case" in content
        assert "Select as target" in content
        assert "/source/1/merge/review?target=other%2F1" in content
        assert content.count("Select as target") == 1

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.views.document_merge.build_merge_comparison")
    @patch("judgments.views.document_merge.get_document_by_uri_or_404")
    @patch("judgments.utils.view_helpers.api_client.document_exists")
    @patch("judgments.utils.view_helpers.api_client.get_document_type_from_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_review_shows_changes_and_hides_confirmation_when_merge_is_blocked(
        self,
        mock_source_document,
        document_type,
        document_exists,
        mock_target_document,
        mock_comparison,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None
        source = _judgment("source/1", "Source v Target")
        target = _judgment("target/1", "Kept v Document")
        merge_checks = Mock()
        merge_checks.check_can_merge_into.return_value = SuccessFailureMessageTuple(
            False,
            ["You cannot merge a document with itself"],
        )
        merge_property = patch.object(Judgment, "merge", merge_checks)
        merge_property.start()
        self.addCleanup(merge_property.stop)
        mock_source_document.return_value = source
        mock_target_document.return_value = target
        mock_comparison.return_value = [
            MergeComparisonSection(
                title="Case metadata",
                rows=[
                    MergeComparisonRow(
                        label="Title",
                        target_values=["Kept v Document"],
                        source_values=["Source v Target"],
                        changed=True,
                        detail=SINGLE_VALUE_CHANGE,
                    ),
                ],
            ),
        ]

        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("merge-document-review", kwargs={"document_uri": source.uri}),
            {"target": target.uri},
        )

        content = response.content.decode("utf-8")
        assert response.status_code == 200
        assert "Will change" in content
        assert "You cannot merge a document with itself" in content
        assert 'name="note"' not in content

        merge_checks.check_can_merge_into.return_value = SuccessFailureMessageTuple(True, [])
        allowed = self.client.get(
            reverse("merge-document-review", kwargs={"document_uri": source.uri}),
            {"target": target.uri},
        )
        allowed_content = allowed.content.decode("utf-8")
        assert 'name="note"' in allowed_content
        assert "aria-disabled" not in allowed_content

        self.client.force_login(self.reader)
        reader_response = self.client.get(
            reverse("merge-document-review", kwargs={"document_uri": source.uri}),
            {"target": target.uri},
        )
        assert 'name="note"' in reader_response.content.decode("utf-8")
        assert 'aria-disabled="true"' in reader_response.content.decode("utf-8")

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.views.document_merge.invalidate_caches")
    @patch("judgments.views.document_merge.get_document_by_uri_or_404")
    def test_editor_merge_uses_the_note_and_returns_to_the_target(self, mock_get_document, mock_invalidate_caches):
        source = Mock(uri="source/1")
        target = Mock(uri="target/1")
        mock_get_document.side_effect = lambda uri: source if uri == source.uri else target

        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("merge"),
            {"source_uri": source.uri, "target_uri": target.uri, "note": "Duplicate submission"},
        )

        assert response.status_code == 302
        assert response["Location"] == reverse("full-text-html", kwargs={"document_uri": target.uri})
        source.merge_into.assert_called_once_with(DocumentURIString(target.uri), "Duplicate submission")
        source.editing_session.assert_not_called()
        assert mock_invalidate_caches.call_args_list == [call(source.uri), call(target.uri)]
        assert "source/1 was merged into target/1." in [
            message.message for message in get_messages(response.wsgi_request)
        ]

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.views.document_merge.invalidate_caches")
    @patch("judgments.views.document_merge.get_document_by_uri_or_404")
    def test_merge_failure_returns_to_review_without_invalidating_caches(
        self,
        mock_get_document,
        mock_invalidate_caches,
    ):
        source = Mock(uri="source/1")
        target = Mock(uri="target/1")
        source.merge_into.side_effect = DocumentMergeNotPossibleError(["This document has more than one version"])
        mock_get_document.side_effect = lambda uri: source if uri == source.uri else target

        self.client.force_login(self.editor)
        response = self.client.post(reverse("merge"), {"source_uri": source.uri, "target_uri": target.uri})

        assert response.status_code == 302
        assert response["Location"] == "/source/1/merge/review?target=target%2F1"
        mock_invalidate_caches.assert_not_called()

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.views.document_merge.invalidate_caches")
    @patch("judgments.views.document_merge.get_document_by_uri_or_404")
    def test_invalid_content_hash_returns_to_review(self, mock_get_document, mock_invalidate_caches):
        source = Mock(uri="source/1")
        target = Mock(uri="target/1")
        source.merge_into.side_effect = InvalidContentHashError("Hash mismatch")
        mock_get_document.side_effect = lambda uri: source if uri == source.uri else target

        self.client.force_login(self.editor)
        response = self.client.post(reverse("merge"), {"source_uri": source.uri, "target_uri": target.uri})

        assert response.status_code == 302
        assert response["Location"] == "/source/1/merge/review?target=target%2F1"
        mock_invalidate_caches.assert_not_called()
        assert [message.message for message in get_messages(response.wsgi_request)] == [
            "There was an error merging the documents: Hash mismatch",
        ]

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.views.document_merge.invalidate_caches")
    @patch("judgments.views.document_merge.get_document_by_uri_or_404")
    def test_locked_document_returns_to_review(self, mock_get_document, mock_invalidate_caches):
        source = Mock(uri="source/1")
        target = Mock(uri="target/1")
        source.merge_into.side_effect = MarklogicCheckoutConflictError("locked")
        mock_get_document.side_effect = lambda uri: source if uri == source.uri else target

        self.client.force_login(self.editor)
        response = self.client.post(reverse("merge"), {"source_uri": source.uri, "target_uri": target.uri})

        assert response.status_code == 302
        assert [message.message for message in get_messages(response.wsgi_request)] == [
            "These documents cannot be merged while one of them is locked.",
        ]
        mock_invalidate_caches.assert_not_called()
