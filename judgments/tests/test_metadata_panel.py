from datetime import datetime
from unittest.mock import patch

import lxml.html
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestMetadataPanel(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("hvtest/4321/123"),
            html="<h1>Test Judgment</h1>",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        root = lxml.html.fromstring(response.content)

        assert b'<input type="hidden" name="judgment_uri" value="hvtest/4321/123" />' in response.content
        assert root.xpath("//input[@id='court']/@value")[0] == "Court of Testing"
        assert root.xpath("//textarea[@class='metadata-component__metadata-name-input']")[0].text == "Test v Tested"
        assert response.status_code == 200

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_tdr_reference(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-9874f350-b187-4e1e-b301-c7d914d5db8c"),
            consignment_reference="TDR-1234",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        self.assertContains(
            response,
            '<aside for="metadata_name" class="metadata-component__main-labels">TDR ref</aside><p>TDR-1234</p>',
            html=True,
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_no_tdr_reference(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-9874f350-b187-4e1e-b301-c7d914d5db8c"),
            consignment_reference=None,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        self.assertContains(
            response,
            '<aside for="metadata_name" class="metadata-component__main-labels">TDR ref</aside><p>&mdash;</p>',
            html=True,
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_first_published_not_published(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-9874f350-b187-4e1e-b301-c7d914d5db8c"),
            first_published_datetime=None,
            has_ever_been_published=False,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        self.assertContains(
            response,
            '<aside for="metadata_name" class="metadata-component__main-labels">First pub</aside><p>&mdash;</p>',
            html=True,
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_first_published_unknown(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-9874f350-b187-4e1e-b301-c7d914d5db8c"),
            first_published_datetime=None,
            has_ever_been_published=True,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        self.assertContains(
            response,
            '<aside for="metadata_name" class="metadata-component__main-labels">First pub</aside><p>Unknown</p>',
            html=True,
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_first_published_known(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-9874f350-b187-4e1e-b301-c7d914d5db8c"),
            first_published_datetime=datetime(2025, 8, 31, 12, 34),
            has_ever_been_published=True,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        self.assertContains(
            response,
            '<aside for="metadata_name" class="metadata-component__main-labels">First pub</aside><p>31 Aug 2025 12:34</p>',
            html=True,
        )
