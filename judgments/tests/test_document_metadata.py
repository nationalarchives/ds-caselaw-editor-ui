from datetime import UTC, datetime
from unittest.mock import Mock, patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import MetadataCategoryValue, MetadataField
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestDocumentMetadata(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_metadata_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested", court="Court of Testing"),
        )
        judgment.metadata_fields.add(
            MetadataField(
                name="court",
                value="Legacy Court",
                source=MetadataSource.DOCUMENT,
                timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            ),
        )
        judgment.metadata_fields.add(
            MetadataField(
                name="court",
                value="Winning Court",
                source=MetadataSource.EDITOR,
                timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            ),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        metadata_uri = reverse("document-metadata", kwargs={"document_uri": judgment.uri})

        assert metadata_uri == "/d-a1b2c3/metadata"

        response = self.client.get(metadata_uri)

        assert response.status_code == 200
        self.assertContains(response, "Metadata for Test v Tested")
        self.assertContains(response, "Test v Tested", html=True)
        self.assertContains(response, "Winning Court")
        self.assertContains(response, "Legacy Court")
        self.assertContains(response, "Current")
        self.assertContains(response, "Superseded")
        self.assertContains(response, 'name="reject_claim_ids"')
        self.assertContains(response, 'name="new_claim__court"')

        for metadata_item in judgment.metadata.values():
            self.assertContains(response, metadata_item.title)

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_metadata_post_adds_multiple_new_claims(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested", court="Court of Testing"),
        )
        judgment.save_metadata_fields = Mock()  # type:ignore[method-assign]
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("document-metadata", kwargs={"document_uri": judgment.uri}),
            data={
                "new_claim__court": ["First Court", "Second Court", " "],
                "new_claim__categories": ["Public law"],
            },
        )

        assert response.status_code == 302
        assert response.url == "/d-a1b2c3/metadata"
        judgment.save_metadata_fields.assert_called_once()

        court_claims = judgment.metadata_fields.by_name("court")
        assert [claim.value for claim in court_claims] == ["First Court", "Second Court"]
        assert all(claim.source is MetadataSource.EDITOR for claim in court_claims)

        category_claims = judgment.metadata_fields.by_name("categories")
        assert category_claims[0].value == MetadataCategoryValue(name="Public law")

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_metadata_post_rejects_existing_claim(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested", court="Court of Testing"),
        )
        claim = MetadataField(
            id="claim-1",
            name="court",
            value="Rejected Court",
            source=MetadataSource.EXTERNAL,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
        )
        judgment.metadata_fields.add(claim)
        judgment.save_metadata_fields = Mock()  # type:ignore[method-assign]
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("document-metadata", kwargs={"document_uri": judgment.uri}),
            data={"reject_claim_ids": [claim.id]},
        )

        assert response.status_code == 302
        judgment.save_metadata_fields.assert_called_once()
        assert judgment.metadata_fields[claim.id].rejected is True

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_metadata_post_suppresses_body_derived_judge(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(
                name="Test v Tested",
                court="Court of Testing",
            ),
        )
        judgment.body.judges = ["Judge One", "Judge Two"]
        judgment.save_metadata_fields = Mock()  # type:ignore[method-assign]
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("document-metadata", kwargs={"document_uri": judgment.uri}),
            data={"suppress_body_judges": ["Judge One"]},
        )

        assert response.status_code == 302
        judgment.save_metadata_fields.assert_called_once()

        judge_claims = judgment.metadata_fields.by_name("judges")
        assert len(judge_claims) == 2
        assert {claim.value: claim.rejected for claim in judge_claims} == {
            "Judge One": True,
            "Judge Two": False,
        }

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_metadata_post_invalid_claim_id_does_not_save(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested", court="Court of Testing"),
        )
        judgment.save_metadata_fields = Mock()  # type:ignore[method-assign]
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("document-metadata", kwargs={"document_uri": judgment.uri}),
            data={"reject_claim_ids": ["missing-claim"]},
        )

        assert response.status_code == 302
        judgment.save_metadata_fields.assert_not_called()
