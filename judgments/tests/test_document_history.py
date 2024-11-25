import json
from datetime import datetime
from unittest.mock import patch

from caselawclient.client_helpers import VersionAnnotation, VersionType
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import VersionsDict
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from factories import DocumentVersionFactory
from waffle.testutils import override_flag

from judgments.views import document_history
from judgments.views.document_history import DocumentHistorySequencer


class TestDocumentHistory(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_history_view(self, document_type, document_exists, mock_get_document):
        document_type.return_value = Judgment
        document_exists.return_value = None

        document = JudgmentFactory.build(
            uri="ewca/civ/2005/1444",
            versions=[VersionsDict({"uri": "/ewca/civ/2005/1444_xml_versions/1-1444.xml", "version": 1})],
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )

        version_document = DocumentVersionFactory.build()
        document.versions_as_documents = [version_document]
        mock_get_document.return_value = document

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        assert reverse("document-history", kwargs={"document_uri": document.uri}) == "/ewca/civ/2005/1444/history"

        response = self.client.get(
            reverse("document-history", kwargs={"document_uri": document.uri}),
        )

        assert response.status_code == 200

        decoded_response = response.content.decode("utf-8")
        dt = document.versions_as_documents[0].version_created_datetime
        assert "Current (version 1)" in decoded_response
        assert dt.strftime("%d %b %Y") in decoded_response
        assert dt.strftime("%H:%M") in decoded_response
        assert "Submitted" in decoded_response


@override_flag("history_timeline", active=True)
class TestStructuredDocumentHistoryLogic(TestCase):
    def test_build_event_object_without_submitter(self):
        version_document = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Test v Tested",
            annotation=VersionAnnotation(
                VersionType.SUBMISSION,
                automated=True,
            ),
            version_created_datetime=datetime(2023, 9, 26, 12),
        )

        annotation_as_dict = json.loads(version_document.annotation)

        assert document_history.build_event_object(
            event_sequence_number=123,
            event_data=annotation_as_dict,
            event_document=version_document,
        ) == {
            "data": annotation_as_dict,
            "datetime": datetime(2023, 9, 26, 12),
            "document": version_document,
            "marklogic_version": 1,
            "event_sequence_number": 123,
        }

    def test_build_event_object_with_submitter(self):
        version_document = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Test v Tested",
            annotation=VersionAnnotation(
                VersionType.SUBMISSION,
                automated=True,
                payload={
                    "submitter": {"name": "Agent Name", "email": "agent@example.com"},
                },
            ),
            version_created_datetime=datetime(2023, 9, 26, 12),
        )

        annotation_as_dict = json.loads(version_document.annotation)

        assert document_history.build_event_object(
            event_sequence_number=123,
            event_data=annotation_as_dict,
            event_document=version_document,
        ) == {
            "data": annotation_as_dict,
            "datetime": datetime(2023, 9, 26, 12),
            "document": version_document,
            "marklogic_version": 1,
            "event_sequence_number": 123,
            "agent": "Agent Name",
            "agent_email": "agent@example.com",
        }

    @patch(
        "judgments.views.document_history.uuid4",
        return_value="94bd7c80-08d4-4093-8755-45d14ce61618",
    )
    def test_document_history_sequencer(self, mock_uuid):
        legacy_1 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document with legacy annotation",
            annotation="Legacy annotation 1",
            version_number=1,
            version_created_datetime=datetime(2023, 1, 1),
        )
        legacy_2 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document with legacy annotation",
            annotation="Legacy annotation 2",
            version_number=2,
            version_created_datetime=datetime(2023, 1, 2),
        )
        submission_1 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document submission",
            annotation=VersionAnnotation(
                VersionType.SUBMISSION,
                automated=False,
                message="Submission 1",
            ),
            version_number=3,
            version_created_datetime=datetime(2023, 1, 3),
        )
        edit_1 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document edit",
            annotation=VersionAnnotation(
                VersionType.EDIT,
                automated=False,
                message="Edit 1",
            ),
            version_number=4,
            version_created_datetime=datetime(2023, 1, 4),
        )
        submission_2 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document submission",
            annotation=VersionAnnotation(
                VersionType.SUBMISSION,
                automated=False,
                message="Submission 2",
            ),
            version_number=5,
            version_created_datetime=datetime(2023, 1, 5),
        )
        enrichment_1 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document enrichment",
            annotation=VersionAnnotation(
                VersionType.ENRICHMENT,
                automated=True,
                message="Enrichment 1",
            ),
            version_number=6,
            version_created_datetime=datetime(2023, 1, 6),
        )
        legacy_3 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document with legacy annotation",
            annotation="Legacy annotation 3",
            version_number=7,
            version_created_datetime=datetime(2023, 1, 7),
        )
        edit_2 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document edit",
            annotation=VersionAnnotation(
                VersionType.EDIT,
                automated=False,
                message="Edit 2",
            ),
            version_number=8,
            version_created_datetime=datetime(2023, 1, 8),
        )
        submission_3 = DocumentVersionFactory.build(
            uri="test/4321/123",
            name="Document submission",
            annotation=VersionAnnotation(
                VersionType.SUBMISSION,
                automated=False,
                message="Submission 3",
            ),
            version_number=9,
            version_created_datetime=datetime(2023, 1, 9),
        )

        history = [
            legacy_1,
            legacy_2,
            submission_1,
            edit_1,
            submission_2,
            enrichment_1,
            legacy_3,  # Test that legacy events correctly close a submission out
            edit_2,  # This should be an orphaned edit with no matching submission
            submission_3,  # Make sure the logic to close open submissions at the end of the loop is good
        ]
        assert DocumentHistorySequencer(history).structured_history == [
            {
                "annotation": "Legacy annotation 1",
                "datetime": datetime(2023, 1, 1, 0, 0),
                "marklogic_version": 1,
                "submission_sequence_number": 1,
                "event_sequence_number": 1,
                "submission_type": "legacy",
            },
            {
                "annotation": "Legacy annotation 2",
                "datetime": datetime(2023, 1, 2, 0, 0),
                "marklogic_version": 2,
                "submission_sequence_number": 2,
                "event_sequence_number": 2,
                "submission_type": "legacy",
            },
            {
                "document": submission_1,
                "events": [
                    {
                        "data": {
                            "automated": False,
                            "calling_agent": "EUI Test",
                            "calling_function": "factory build",
                            "type": "submission",
                            "message": "Submission 1",
                        },
                        "datetime": datetime(2023, 1, 3, 0, 0),
                        "document": submission_1,
                        "marklogic_version": 3,
                        "event_sequence_number": 3,
                    },
                    {
                        "data": {
                            "automated": False,
                            "calling_agent": "EUI Test",
                            "calling_function": "factory build",
                            "type": "edit",
                            "message": "Edit 1",
                        },
                        "datetime": datetime(2023, 1, 4, 0, 0),
                        "document": edit_1,
                        "marklogic_version": 4,
                        "event_sequence_number": 4,
                    },
                ],
                "marklogic_version": 3,
                "submission_sequence_number": 3,
                "submission_type": "structured",
                "submission_data": {
                    "automated": False,
                    "calling_agent": "EUI Test",
                    "calling_function": "factory build",
                    "type": "submission",
                    "message": "Submission 1",
                },
            },
            {
                "document": submission_2,
                "events": [
                    {
                        "data": {
                            "automated": False,
                            "calling_agent": "EUI Test",
                            "calling_function": "factory build",
                            "type": "submission",
                            "message": "Submission 2",
                        },
                        "datetime": datetime(2023, 1, 5, 0, 0),
                        "document": submission_2,
                        "marklogic_version": 5,
                        "event_sequence_number": 5,
                    },
                    {
                        "data": {
                            "automated": True,
                            "calling_agent": "EUI Test",
                            "calling_function": "factory build",
                            "type": "enrichment",
                            "message": "Enrichment 1",
                        },
                        "datetime": datetime(2023, 1, 6, 0, 0),
                        "document": enrichment_1,
                        "marklogic_version": 6,
                        "event_sequence_number": 6,
                    },
                ],
                "marklogic_version": 5,
                "submission_sequence_number": 4,
                "submission_type": "structured",
                "submission_data": {
                    "automated": False,
                    "calling_agent": "EUI Test",
                    "calling_function": "factory build",
                    "type": "submission",
                    "message": "Submission 2",
                },
            },
            {
                "annotation": "Legacy annotation 3",
                "datetime": datetime(2023, 1, 7, 0, 0),
                "marklogic_version": 7,
                "submission_sequence_number": 5,
                "event_sequence_number": 7,
                "submission_type": "legacy",
            },
            {
                "events": [
                    {
                        "data": {
                            "automated": False,
                            "calling_agent": "EUI Test",
                            "calling_function": "factory build",
                            "message": "Edit 2",
                            "type": "edit",
                        },
                        "datetime": datetime(2023, 1, 8, 0, 0),
                        "document": edit_2,
                        "marklogic_version": 8,
                        "event_sequence_number": 8,
                    },
                ],
                "submission_type": "orphan",
                "orphan_submission_identifier": mock_uuid.return_value,
            },
            {
                "document": submission_3,
                "events": [
                    {
                        "data": {
                            "automated": False,
                            "calling_agent": "EUI Test",
                            "calling_function": "factory build",
                            "message": "Submission 3",
                            "type": "submission",
                        },
                        "datetime": datetime(2023, 1, 9, 0, 0),
                        "document": submission_3,
                        "marklogic_version": 9,
                        "event_sequence_number": 9,
                    },
                ],
                "marklogic_version": 9,
                "submission_sequence_number": 6,
                "submission_data": {
                    "automated": False,
                    "calling_agent": "EUI Test",
                    "calling_function": "factory build",
                    "message": "Submission 3",
                    "type": "submission",
                },
                "submission_type": "structured",
            },
        ]


@override_flag("history_timeline", active=True)
class TestStructuredDocumentHistoryView(TestCase):
    def sign_in_developer_user(self):
        developer_user = User.objects.get_or_create(username="testuser")[0]
        developer_group = Group.objects.get_or_create(name="Developers")[0]
        developer_user.groups.add(developer_group)
        developer_user.save()
        self.client.force_login(developer_user)

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_structured_history_with_legacy(
        self,
        document_type,
        document_exists,
        mock_document,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        document = JudgmentFactory.build(  # This was a DocumentFactory; this may not work properly with Press Summaries
            uri="test/4321/123",
            name="Test v Tested",
        )
        document.versions_as_documents = [
            DocumentVersionFactory.build(
                uri="test/4321/123",
                name="Test v Tested",
                annotation="Legacy annotation 1",
                version_number=123,
                version_created_datetime=datetime(2023, 1, 1),
            ),
        ]

        mock_document.return_value = document

        self.sign_in_developer_user()

        assert reverse("document-history", kwargs={"document_uri": document.uri}) == "/test/4321/123/history"

        response = self.client.get(
            reverse("document-history", kwargs={"document_uri": document.uri}),
        )

        assert response.status_code == 200

        self.assertContains(response, "Legacy version 123")
        self.assertContains(response, "Legacy annotation 1")
        self.assertContains(
            response,
            "Event #1 • Submission #1 • MarkLogic version #123",
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_structured_history(
        self,
        document_type,
        document_exists,
        mock_document,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        document = JudgmentFactory.build(uri="test/4321/123", body=DocumentBodyFactory.build(name="Test v Tested"))
        document.versions_as_documents = [
            DocumentVersionFactory.build(
                uri="test/4321/123",
                name="Test v Tested",
                annotation=VersionAnnotation(
                    VersionType.SUBMISSION,
                    automated=False,
                    message="Submission message 1",
                    payload={
                        "tdr_reference": "TDR-1234-ABC",
                        "submitter": {
                            "name": "Test Clerk",
                            "email": "clerk@example.com",
                        },
                    },
                ),
                version_number=123,
                version_created_datetime=datetime(2023, 1, 1, 12, 1),
            ),
            DocumentVersionFactory.build(
                uri="test/4321/123",
                name="Test v Tested",
                annotation=VersionAnnotation(
                    VersionType.EDIT,
                    automated=False,
                    message="Edit message 1",
                ),
                version_number=124,
                version_created_datetime=datetime(2023, 1, 2, 12, 2),
            ),
            DocumentVersionFactory.build(
                uri="test/4321/123",
                name="Test v Tested",
                annotation=VersionAnnotation(
                    VersionType.ENRICHMENT,
                    automated=True,
                    message="Enrichment message 1",
                ),
                version_number=125,
                version_created_datetime=datetime(2023, 1, 3, 12, 3),
            ),
            DocumentVersionFactory.build(
                uri="test/4321/123",
                name="Test v Tested",
                annotation="Legacy annotation 1",
                version_number=126,
                version_created_datetime=datetime(2023, 1, 4, 12, 4),
            ),
            DocumentVersionFactory.build(
                uri="test/4321/123",
                name="Test v Tested",
                annotation=VersionAnnotation(
                    VersionType.EDIT,
                    automated=False,
                    message="Edit message 2",
                ),
                version_number=127,
                version_created_datetime=datetime(2023, 1, 5, 12, 5),
            ),
        ]
        mock_document.return_value = document

        self.sign_in_developer_user()

        assert reverse("document-history", kwargs={"document_uri": document.uri}) == "/test/4321/123/history"

        response = self.client.get(
            reverse("document-history", kwargs={"document_uri": document.uri}),
        )

        assert response.status_code == 200

        self.assertContains(response, "Submission 1")
        self.assertContains(response, "TDR-1234-ABC")
        self.assertContains(response, "Submitted")
        self.assertContains(response, "Submission message 1")
        self.assertContains(response, "1 Jan 2023 12:01")
        self.assertContains(response, "Test Clerk")
        self.assertContains(response, "clerk@example.com")
        self.assertContains(response, "Event #1 • MarkLogic version #123")

        self.assertContains(response, "Edited")
        self.assertContains(response, "Edit message 1")
        self.assertContains(response, "2 Jan 2023 12:02")
        self.assertContains(response, "Event #2 • MarkLogic version #124")

        self.assertContains(response, "Enriched")
        self.assertContains(response, "Enrichment message 1")
        self.assertContains(response, "3 Jan 2023 12:03")
        self.assertContains(response, "Automated")
        self.assertContains(response, "Event #3 • MarkLogic version #125")

        self.assertContains(response, "Legacy version 126")
        self.assertContains(response, "4 Jan 2023 12:04")
        self.assertContains(response, "Legacy annotation 1")
        self.assertContains(
            response,
            "Event #4 • Submission #2 • MarkLogic version #126",
        )

        self.assertContains(response, "Orphaned events")
        self.assertContains(response, "Edit message 2")
        self.assertContains(response, "5 Jan 2023 12:05")
        self.assertContains(response, "Event #5 • MarkLogic version #127")

        self.assertNotContains(
            response,
            "Submission 2",
        )  # Validates we've not broken the submission stack somewhere
