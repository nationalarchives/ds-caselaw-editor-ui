import datetime
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from caselawclient.errors import InvalidContentHashError, MarklogicCheckoutConflictError
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.exceptions import DocumentMergeNotPossibleError
from caselawclient.models.documents.metadata.base import MultipleMetadata, SingleMetadata
from caselawclient.models.judgments import Judgment
from caselawclient.search_parameters import SearchParameters
from caselawclient.types import SuccessFailureMessageTuple
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from factories import make_editor
from waffle.testutils import override_flag

from judgments.templatetags.navigation_tags import DOCUMENT_MERGE_FLAG
from judgments.utils.merge_helpers import (
    IDENTIFIER_ADDITION,
    IDENTIFIER_ADDITIONS,
    IDENTIFIER_REPLACEMENT,
    MULTIPLE_VALUE_CHANGE,
    PROPERTY_REPLACEMENT,
    SINGLE_VALUE_CHANGE,
    MergeComparisonRow,
    MergeComparisonSection,
    build_merge_comparison,
    format_metadata_value,
    is_source_in_search_results,
    merge_annotation_message,
    merge_target_search_results,
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


class NotesMetadata(SingleMetadata[str]):
    key = "notes"
    title = "Notes"
    description = ""
    LOGIC_VERSION = 1

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


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

    def test_identifier_addition_when_target_has_no_value(self):
        target = document_stub("target/1", [TitleMetadata("Target")], {})
        source = document_stub(
            "source/1",
            [TitleMetadata("Source")],
            {"ncn": identifier("Neutral citation", "[2024] UKSC 1")},
        )

        sections = {section.title: section for section in build_merge_comparison(target, source)}
        identifiers = {row.label: row for row in sections["Identifiers"].rows}

        assert identifiers["Neutral citation"] == MergeComparisonRow(
            label="Neutral citation",
            target_values=[],
            source_values=["[2024] UKSC 1"],
            changed=True,
            detail=IDENTIFIER_ADDITION,
        )

    def test_multiple_metadata_unchanged_when_source_is_subset(self):
        target = document_stub("target/1", [JudgesMetadata(["Ada", "Grace"])], {})
        source = document_stub("source/1", [JudgesMetadata(["Ada"])], {})

        sections = {section.title: section for section in build_merge_comparison(target, source)}
        judges = sections["Case metadata"].rows[0]

        assert judges.changed is False
        assert judges.detail == ""

    def test_allow_multiple_identifiers_unchanged_when_source_is_subset(self):
        target = document_stub(
            "target/1",
            [TitleMetadata("Target")],
            {
                "judge": identifier("Judge", "Ada", allow_multiple=True),
                "other": identifier("Judge", "Grace", allow_multiple=True),
            },
        )
        source = document_stub(
            "source/1",
            [TitleMetadata("Source")],
            {"judge": identifier("Judge", "Ada", allow_multiple=True)},
        )

        sections = {section.title: section for section in build_merge_comparison(target, source)}
        judge_row = next(row for row in sections["Identifiers"].rows if row.label == "Judge")

        assert judge_row.changed is False

    def test_allow_multiple_identifiers_use_additions_detail(self):
        target = document_stub(
            "target/1",
            [TitleMetadata("Target")],
            {"judge": identifier("Judge", "Ada", allow_multiple=True)},
        )
        source = document_stub(
            "source/1",
            [TitleMetadata("Source")],
            {"judge": identifier("Judge", "Grace", allow_multiple=True)},
        )

        sections = {section.title: section for section in build_merge_comparison(target, source)}
        judge_row = sections["Identifiers"].rows[0]

        assert judge_row.changed is True
        assert judge_row.detail == IDENTIFIER_ADDITIONS

    def test_no_identifiers_shows_a_single_placeholder_row(self):
        target = document_stub("target/1", [TitleMetadata("Target")], {})
        source = document_stub("source/1", [TitleMetadata("Source")], {})

        sections = {section.title: section for section in build_merge_comparison(target, source)}
        assert sections["Identifiers"].rows == [
            MergeComparisonRow(
                label="Identifiers",
                target_values=[],
                source_values=[],
                changed=False,
                detail="",
            ),
        ]

    def test_metadata_only_on_source_appears_in_comparison(self):
        target = document_stub("target/1", [TitleMetadata("Target title")], {})
        source = document_stub(
            "source/1",
            [TitleMetadata("Source title"), NotesMetadata("Source-only note")],
            {},
        )

        sections = {section.title: section for section in build_merge_comparison(target, source)}
        metadata = {row.label: row for row in sections["Case metadata"].rows}
        assert metadata["Notes"] == MergeComparisonRow(
            label="Notes",
            target_values=[],
            source_values=["Source-only note"],
            changed=True,
            detail=SINGLE_VALUE_CHANGE,
        )

    def test_format_metadata_value_handles_courts_and_empty_values(self):
        court_with_parent = SimpleNamespace(name="Queen's Bench", parent="EWHC")
        assert format_metadata_value(court_with_parent) == "Queen's Bench (EWHC)"
        assert format_metadata_value(SimpleNamespace(name="UKSC")) == "UKSC"
        assert format_metadata_value(None) == ""
        assert format_metadata_value("  padded  ") == "padded"


class TestSourceIsInSearchResults(TestCase):
    @patch("judgments.utils.merge_helpers.search_and_parse_response")
    @patch("judgments.utils.merge_helpers._search_parameters_from_filters")
    def test_probe_finds_the_source_document(self, mock_params, mock_search):
        mock_params.return_value = SearchParameters(query="case", page=3)
        mock_search.return_value = SimpleNamespace(results=[SimpleNamespace(uri="source/1")])

        assert is_source_in_search_results("source/1", Mock(search_filter="default")) is True

        probe = mock_search.call_args[0][1]
        assert probe.specific_keyword == "source/1"
        assert probe.page == 1
        assert probe.page_size == 1
        assert probe.query == "case"
        mock_params.assert_called_once()
        assert mock_params.call_args.kwargs["neutral_citation"] is False

    @patch("judgments.utils.merge_helpers.search_and_parse_response")
    @patch("judgments.utils.merge_helpers._search_parameters_from_filters")
    def test_probe_uses_neutral_citation_mode_for_ncn_filter(self, mock_params, mock_search):
        mock_params.return_value = SearchParameters()
        mock_search.return_value = SimpleNamespace(results=[])

        assert is_source_in_search_results("source/1", Mock(search_filter="ncn")) is False

        mock_params.assert_called_once()
        assert mock_params.call_args.kwargs["neutral_citation"] is True

    @patch("judgments.utils.merge_helpers.is_source_in_search_results")
    @patch("judgments.utils.merge_helpers.get_search_results_from_filters")
    def test_merge_search_leaves_total_unchanged_when_source_not_in_results(
        self,
        mock_search,
        mock_source_in_results,
    ):
        mock_search.return_value = {
            "documents": [SimpleNamespace(uri="other/1")],
            "total": 5,
            "paginator": {"current_page": 1},
        }
        mock_source_in_results.return_value = False

        _, _, adjusted_total = merge_target_search_results(Mock(page=1, search_filter="default"), "source/1")

        assert adjusted_total == 5
        mock_source_in_results.assert_called_once()


def _judgment(uri, name):
    return JudgmentFactory.build(
        uri=DocumentURIString(uri),
        body=DocumentBodyFactory.build(name=name),
    )


class TestMergeSearchResults(TestCase):
    @patch("judgments.utils.merge_helpers.get_search_results_from_filters")
    def test_total_and_pagination_exclude_the_source_document(self, mock_search):
        other = SimpleNamespace(uri="other/1")
        source = SimpleNamespace(uri="source/1")
        mock_search.return_value = {
            "documents": [source, other],
            "total": 2,
            "paginator": {"current_page": 1},
        }

        search_context, visible_documents, adjusted_total = merge_target_search_results(
            Mock(page=1, search_filter="default"),
            "source/1",
        )

        assert search_context == mock_search.return_value
        assert visible_documents == [other]
        assert adjusted_total == 1

    @patch("judgments.utils.merge_helpers.is_source_in_search_results")
    @patch("judgments.utils.merge_helpers.get_search_results_from_filters")
    def test_total_excludes_source_on_another_page(self, mock_search, mock_source_in_results):
        mock_search.return_value = {
            "documents": [SimpleNamespace(uri="other/1")],
            "total": 11,
            "paginator": {"current_page": 1},
        }
        mock_source_in_results.return_value = True

        _, visible_documents, adjusted_total = merge_target_search_results(
            Mock(page=1, search_filter="default"),
            "source/1",
        )

        assert len(visible_documents) == 1
        assert adjusted_total == 10


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
    @patch("judgments.utils.view_helpers.api_client.document_exists")
    @patch("judgments.utils.view_helpers.api_client.get_document_type_from_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_review_without_target_returns_not_found(self, mock_get_document, document_type, document_exists):
        document_type.return_value = Judgment
        document_exists.return_value = None
        mock_get_document.return_value = _judgment("source/1", "Source v Target")

        self.client.force_login(self.editor)
        response = self.client.get(reverse("merge-document-review", kwargs={"document_uri": "source/1"}))

        assert response.status_code == 404

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.utils.view_helpers.api_client.document_exists")
    @patch("judgments.utils.view_helpers.api_client.get_document_type_from_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_search_rejects_invalid_publication_status(self, mock_get_document, document_type, document_exists):
        document_type.return_value = Judgment
        document_exists.return_value = None
        mock_get_document.return_value = _judgment("source/1", "Source v Target")

        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("merge-document", kwargs={"document_uri": "source/1"}),
            {"publication_status": "not-a-status"},
        )

        assert response.status_code == 400

    @override_flag(DOCUMENT_MERGE_FLAG, active=True)
    @patch("judgments.utils.merge_helpers.get_search_results_from_filters")
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
    @patch("judgments.utils.merge_helpers.get_search_results_from_filters")
    @patch("judgments.utils.view_helpers.api_client.document_exists")
    @patch("judgments.utils.view_helpers.api_client.get_document_type_from_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_search_keeps_pagination_when_source_is_the_only_result_on_the_page(
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
        mock_search.return_value = {
            "documents": [
                SimpleNamespace(
                    uri=source.uri,
                    name="Source v Target",
                    neutral_citation="[2024] SOURCE 1",
                    court=SimpleNamespace(name="UKSC"),
                    metadata=SimpleNamespace(
                        submission_datetime=datetime.datetime(2024, 1, 2, 3, 4),
                        author="Ada",
                        editor_status="New",
                        consignment_reference="TDR-9",
                    ),
                ),
            ],
            "total": 11,
            "total_count_postfix": "documents",
            "query": "",
            "search_filter": "default",
            "paginator": {
                "page_range": [1, 2],
                "current_page": 1,
                "has_prev_page": False,
                "has_next_page": True,
            },
        }

        self.client.force_login(self.editor)
        response = self.client.get(reverse("merge-document", kwargs={"document_uri": source.uri}))

        content = response.content.decode("utf-8")
        assert response.status_code == 200
        assert "No merge targets on this page" in content
        assert "No other documents matched" not in content
        assert "Next" in content or "page=2" in content

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
