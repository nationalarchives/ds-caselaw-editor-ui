from datetime import UTC, datetime
from unittest.mock import patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import MetadataField
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
        self.assertContains(response, "Metadata for:")
        self.assertContains(response, "Test v Tested", html=True)
        self.assertContains(response, "Winning Court")
        self.assertContains(response, "Legacy Court")
        self.assertContains(response, "<th>Status</th>", html=True)
        self.assertContains(response, "<th>Source</th>", html=True)
        self.assertContains(response, "<td>Current</td>", html=True)
        self.assertContains(response, "<td>Superseded</td>", html=True)

        for metadata_item in judgment.metadata.values():
            self.assertContains(response, metadata_item.title)
