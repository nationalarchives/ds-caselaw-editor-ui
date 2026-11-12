from datetime import date
from unittest.mock import Mock, patch

import pytest
from caselawclient.errors import MarklogicAPIError
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory, PressSummaryFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import (
    MetadataDateValue,
    MetadataField,
    MetadataStringValue,
)
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.identifiers.neutral_citation import (
    NCNCannotConvertToValidURLSlugException,
    NCNDoesNotMatchExpectedPatternException,
    NeutralCitationNumber,
)
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from editing import document_form_judgment_date_fields, editing_order, record, tracking_editing_session
from factories import make_editor

from judgments.tests.helpers.metadata_claims import judgment_with_title_claim
from judgments.views.judgment_edit import CannotUpdateNCNOfNonJudgment, update_ncn_of_document


class TestDocumentEdit(TestCase):
    def test_judgment_edit_view_redirects(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/ewca/civ/2004/63X/edit")
        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": "ewca/civ/2004/63X"},
        )

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_rejects_non_judgments(self, mock_document, api_client):
        press_summary = PressSummaryFactory.build(
            uri=DocumentURIString("press-summary/1"),
            name="Test press summary",
        )
        mock_document.return_value = press_summary
        self.client.force_login(make_editor())

        response = self.client.post(
            reverse("edit-document", kwargs={"document_uri": press_summary.uri}),
            {
                "judgment_uri": press_summary.uri,
                "metadata_name": "Changed title",
                "neutral_citation": "",
                "court": "UKSC",
                **document_form_judgment_date_fields(),
            },
        )

        assert response.status_code == 404
        api_client.set_document_court_and_jurisdiction.assert_not_called()
        api_client.set_judgment_date.assert_not_called()

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    @patch("judgments.utils.aws.boto3")
    def test_edit_judgment_no_ncn_change(self, mock_boto, mock_judgment, api_client, mock_invalidate_caches):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )

        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        judgment.body.judges = ["Lord Justice Body"]
        editor_judge_claim = MetadataField(
            id="editor-judge",
            name="judges",
            value=MetadataStringValue("Lord Justice Previous"),
            source=MetadataSource.EDITOR,
        )
        judgment.metadata_fields.add(editor_judge_claim)
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())
        User.objects.get_or_create(username="testuser2")

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "new_claim__judges": ["Lord Justice Example"],
                    "reject_claim_ids": [editor_judge_claim.id],
                    "suppress_body_judges": ["Lord Justice Body"],
                    **document_form_judgment_date_fields(),
                },
            )

        api_client.set_document_name.assert_not_called()

        title_claims = judgment.metadata_fields.by_name("title")
        assert title_claims[0].value == MetadataStringValue("New Name")
        assert title_claims[0].source is MetadataSource.EDITOR

        api_client.set_document_court_and_jurisdiction.assert_called_with(
            "/edittest/4321/123",
            "Court of Testing",
        )
        api_client.set_judgment_date.assert_called_with(
            "/edittest/4321/123",
            "2023-01-02",
        )
        assert judgment.metadata.judges.values == ["Lord Justice Example"]
        assert editor_judge_claim.id not in judgment.metadata_fields

        assert order == [
            "editing_session",
            "save_metadata_fields",
            "set_court",
            "save_metadata_fields",
            "set_judgment_date",
            "save_metadata_fields",
            "editing_session_end",
        ]
        mock_invalidate_caches.assert_called_once_with(judgment.uri)

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_does_not_remove_last_judge(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.body.judges = ["Lord Justice Body"]
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session"),
            patch.object(judgment, "save_metadata_fields") as save_metadata_fields,
        ):
            response = self.client.post(
                reverse("edit-document", kwargs={"document_uri": judgment.uri}),
                {
                    "judgment_uri": judgment.uri,
                    "metadata_name": judgment.metadata.title.value,
                    "neutral_citation": "[4321] UKSC 123",
                    "court": judgment.body.court_and_jurisdiction_identifier_string,
                    "suppress_body_judges": ["Lord Justice Body"],
                    **document_form_judgment_date_fields(day=3, month=2, year=2023),
                },
            )

        response_messages = list(get_messages(response.wsgi_request))
        assert [message.message for message in response_messages] == ["A document must have at least one judge"]
        save_metadata_fields.assert_not_called()
        mock_invalidate_caches.assert_not_called()
        api_client.set_document_court_and_jurisdiction.assert_called_once()

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_does_not_invalidate_cache_when_api_save_fails(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )

        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()

        def fail_to_save_metadata(*args, **kwargs):
            order.append("save_metadata_fields")
            message = "Failed to save"
            raise MarklogicAPIError(message)

        judgment.save_metadata_fields = fail_to_save_metadata  # type:ignore[method-assign]

        self.client.force_login(make_editor())

        with patch.object(judgment, "editing_session", tracking_editing_session(order)):
            response = self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    **document_form_judgment_date_fields(),
                },
            )

        messages = list(get_messages(response.wsgi_request))

        assert "There was an error saving the Document" in messages[0].message
        assert order == ["editing_session", "save_metadata_fields"]
        mock_invalidate_caches.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    @patch("judgments.utils.aws.boto3")
    def test_edit_judgment_ncn_change(self, mock_boto, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_judgment_citation.side_effect = record(order, "set_judgment_citation")
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())
        User.objects.get_or_create(username="testuser2")

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_identifiers", side_effect=record(order, "save_identifiers")),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/uksc/4321/123/edit",
                {
                    "judgment_uri": "/uksc/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[2023] EWCC 456",
                    "court": "Court of Testing",
                    **document_form_judgment_date_fields(),
                },
            )
        api_client.set_judgment_citation.assert_called_once_with("uksc/4321/123", "[2023] EWCC 456")
        assert order == [
            "editing_session",
            "save_identifiers",
            "set_judgment_citation",
            "save_metadata_fields",
            "set_court",
            "save_metadata_fields",
            "set_judgment_date",
            "editing_session_end",
        ]

    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_date_error(self, mock_judgment, api_client):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            name="Test v Tested",
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")

        self.client.force_login(make_editor())
        User.objects.get_or_create(username="testuser2")

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            response = self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "New Name",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    "judgment_date-day": "31",
                    "judgment_date-month": "2",
                    "judgment_date-year": "2023",
                },
            )

        messages = list(get_messages(response.wsgi_request))
        assert messages[0].message == "Enter a real date"
        assert order == []
        api_client.set_judgment_date.assert_not_called()
        api_client.set_document_court_and_jurisdiction.assert_not_called()

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_skips_metadata_save_when_title_unchanged(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "Test v Tested",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    **document_form_judgment_date_fields(day=3, month=2, year=2023),
                },
            )

        assert "save_metadata_fields" not in order
        assert judgment.metadata_fields.by_name("title") == []
        assert judgment.metadata_fields.by_name("date") == []

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_skips_metadata_save_when_structured_title_unchanged(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = judgment_with_title_claim(
            body_name="Body title from XML",
            title_claim="Resolved structured title",
            source=MetadataSource.DOCUMENT,
            uri=DocumentURIString("edittest/4321/123"),
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "Resolved structured title",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    **document_form_judgment_date_fields(day=3, month=2, year=2023),
                },
            )

        assert "save_metadata_fields" not in order
        assert len(judgment.metadata_fields.by_name("title")) == 1
        assert judgment.metadata_fields.by_name("date") == []

    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_appends_title_claim_when_structured_title_changes(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = judgment_with_title_claim(
            body_name="Body title from XML",
            title_claim="Resolved structured title",
            source=MetadataSource.DOCUMENT,
            uri=DocumentURIString("edittest/4321/123"),
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment
        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "Editor updated title",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    **document_form_judgment_date_fields(),
                },
            )

        title_claims = judgment.metadata_fields.by_name("title")
        assert len(title_claims) == 2
        assert title_claims[0].value == MetadataStringValue("Resolved structured title")
        assert title_claims[1].value == MetadataStringValue("Editor updated title")
        assert title_claims[1].source is MetadataSource.EDITOR
        assert order == [
            "editing_session",
            "save_metadata_fields",
            "set_court",
            "save_metadata_fields",
            "set_judgment_date",
            "editing_session_end",
        ]


class TestEditJudgmentDateMetadata(TestCase):
    @patch("judgments.views.judgment_edit.invalidate_caches")
    @patch("judgments.views.judgment_edit.api_client")
    @patch("judgments.views.judgment_edit.get_document_by_uri_or_404")
    def test_edit_judgment_adds_date_claim_when_document_has_no_date_claim_or_body_date(
        self,
        mock_judgment,
        api_client,
        mock_invalidate_caches,
    ):
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("edittest/4321/123"),
            body=DocumentBodyFactory.build(name="Test v Tested", document_date_as_string=None),
        )
        judgment.identifiers.add(NeutralCitationNumber("[4321] UKSC 123"))
        mock_judgment.return_value = judgment

        assert judgment.metadata.date.value is None
        assert judgment.metadata_fields.by_name("date") == []

        order = editing_order()
        api_client.set_document_court_and_jurisdiction.side_effect = record(order, "set_court")
        api_client.set_judgment_date.side_effect = record(order, "set_judgment_date")

        self.client.force_login(make_editor())

        with (
            patch.object(judgment, "editing_session", tracking_editing_session(order)),
            patch.object(judgment, "save_metadata_fields", side_effect=record(order, "save_metadata_fields")),
        ):
            self.client.post(
                "/pubtest/4321/123/edit",
                {
                    "judgment_uri": "/edittest/4321/123",
                    "metadata_name": "Test v Tested",
                    "neutral_citation": "[4321] UKSC 123",
                    "court": "Court of Testing",
                    **document_form_judgment_date_fields(),
                },
            )

        date_claims = judgment.metadata_fields.by_name("date")
        assert len(date_claims) == 1
        assert date_claims[0].value == MetadataDateValue(date(2023, 1, 2))
        assert date_claims[0].source is MetadataSource.EDITOR
        assert judgment.metadata.date.value == date(2023, 1, 2)

        api_client.set_judgment_date.assert_called_with("/edittest/4321/123", "2023-01-02")
        assert order == [
            "editing_session",
            "set_court",
            "save_metadata_fields",
            "set_judgment_date",
            "editing_session_end",
        ]


class TestUpdateNCNOfDocument(TestCase):
    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_where_change_is_valid(
        self,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers = Mock()

        update_ncn_of_document(document, "[2025] EWCC 456")

        document.identifiers.delete_type.assert_called_once_with(NeutralCitationNumber)
        document.identifiers.add.assert_called_once()
        document.save_identifiers.assert_called_once()
        api_client.set_judgment_citation.assert_called_once_with("uksc/4321/123", "[2025] EWCC 456")

    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_rejects_non_judgment(
        self,
        api_client,
    ):
        document = PressSummaryFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(CannotUpdateNCNOfNonJudgment):
            update_ncn_of_document(document, "[2025] EWCC 456")

        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_rejects_malformed_ncn(
        self,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(NCNDoesNotMatchExpectedPatternException):
            update_ncn_of_document(document, "TEST-123")

        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()

    @patch("judgments.views.judgment_edit.api_client")
    def test_update_ncn_of_document_rejects_plausible_but_invalid_ncn(
        self,
        api_client,
    ):
        document = JudgmentFactory.build(
            uri=DocumentURIString("uksc/4321/123"),
            name="Test v Tested",
        )
        document.save_identifiers = Mock()  # type:ignore[method-assign]
        document.identifiers.add(NeutralCitationNumber("[2023] UKSC 123"))

        with pytest.raises(NCNCannotConvertToValidURLSlugException):
            update_ncn_of_document(document, "[2023] UKSC 123 (Fam)")

        document.save_identifiers.assert_not_called()
        api_client.set_judgment_citation.assert_not_called()
