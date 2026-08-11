from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import lxml.html
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import MetadataField
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.identifiers.fclid import FindCaseLawIdentifier
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from caselawclient.models.judgments import Judgment
from caselawclient.types import DocumentCategory
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from jinja2 import PackageLoader

from judgments.jinja import environment


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
        assert root.xpath("//textarea[@id='metadata_name']")[0].text == "Test v Tested"
        assert response.status_code == 200

    def test_metadata_item_renders_scalar_value(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata_item.jinja" import document_metadata_item %}{{ document_metadata_item(metadata_item=metadata_item) }}',
        )

        rendered = template.render(metadata_item=SimpleNamespace(value="Court of Testing"))

        assert "Court of Testing" in rendered
        assert "badge" not in rendered

    def test_metadata_item_renders_multi_value_badges(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata_item.jinja" import document_metadata_item %}{{ document_metadata_item(metadata_item=metadata_item) }}',
        )

        rendered = template.render(metadata_item=SimpleNamespace(values=["Tax", "Employment"]))

        assert "Tax" in rendered
        assert "Employment" in rendered

    def test_metadata_item_renders_category_names(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata_item.jinja" import document_metadata_item %}{{ document_metadata_item(metadata_item=metadata_item) }}',
        )

        rendered = template.render(
            metadata_item=SimpleNamespace(values=[DocumentCategory(name="Civil"), DocumentCategory(name="Tax")]),
        )

        assert "Civil" in rendered
        assert "Tax" in rendered
        assert "DocumentCategory" not in rendered

    def test_document_metadata_aside_sections_and_judges(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata.jinja" import document_metadata %}'
            "{{ document_metadata(document=document) }}",
        )

        preferred = SimpleNamespace(
            schema=SimpleNamespace(name="Neutral Citation Number"),
            value="[2023] EWCA Civ 1",
            uuid="id-preferred",
        )
        other = SimpleNamespace(
            schema=SimpleNamespace(name="Find Case Law Identifier"),
            value="tn4t35ts",
            uuid="id-other",
        )

        class FakeIdentifiers:
            def preferred(self):
                return preferred

            def by_score(self):
                return [preferred, other]

        document = SimpleNamespace(
            metadata={
                "title": SimpleNamespace(value="Test v Tested"),
                "court": SimpleNamespace(value="EWCA-Civil"),
                "date": SimpleNamespace(value=datetime(2025, 5, 23).date()),
                "jurisdiction": SimpleNamespace(value=""),
                "case_number": SimpleNamespace(value=""),
                "judges": SimpleNamespace(values=["Lord Justice Test", "Lady Justice Example"]),
                "categories": SimpleNamespace(values=[DocumentCategory(name="Civil")]),
            },
            identifiers=FakeIdentifiers(),
            consignment_reference="TDR-999",
            document_noun="judgment",
            has_ever_been_published=False,
            first_published_datetime_display=None,
            source_name="",
            source_email="",
        )

        rendered = template.render(document=document)
        root = lxml.html.fromstring(rendered)

        section_headings = root.xpath('//*[@data-test-id="metadata-section-heading"]/dt/text()')
        assert section_headings == ["Metadata", "Identifiers", "Legacy"]

        judges_dd = root.xpath('//dt[text()="Judges"]/following-sibling::dd')[0]
        assert "Lord Justice Test" in judges_dd.text_content()
        assert "Lady Justice Example" in judges_dd.text_content()

        categories_dd = root.xpath('//dt[text()="Categories"]/following-sibling::dd')[0]
        assert "Civil" in categories_dd.text_content()
        assert "DocumentCategory" not in categories_dd.text_content()

        preferred_dd = root.xpath('//dt[text()="Preferred"]/following-sibling::dd')[0]
        assert "Neutral Citation Number: [2023] EWCA Civ 1" in preferred_dd.text_content()

        other_dd = root.xpath('//dt[text()="Other"]/following-sibling::dd')[0]
        assert "Find Case Law Identifier: tn4t35ts" in other_dd.text_content()

        assert root.xpath('//dt[text()="TDR ref"]/following-sibling::dd')[0].text_content().strip() == "TDR-999"

    def test_document_metadata_aside_shows_other_identifiers_without_preferred(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata.jinja" import document_metadata %}'
            "{{ document_metadata(document=document) }}",
        )

        only = SimpleNamespace(
            schema=SimpleNamespace(name="Find Case Law Identifier"),
            value="tn4t35ts",
            uuid="id-only",
        )

        class FakeIdentifiers:
            def preferred(self):
                return None

            def by_score(self):
                return [only]

        document = SimpleNamespace(
            metadata={
                "title": SimpleNamespace(value="Test v Tested"),
                "court": SimpleNamespace(value="EWCA-Civil"),
                "date": SimpleNamespace(value=datetime(2025, 5, 23).date()),
                "jurisdiction": SimpleNamespace(value=""),
                "case_number": SimpleNamespace(value=""),
                "judges": SimpleNamespace(values=[]),
                "categories": SimpleNamespace(values=[]),
            },
            identifiers=FakeIdentifiers(),
            consignment_reference="",
            document_noun="judgment",
            has_ever_been_published=False,
            first_published_datetime_display=None,
            source_name="",
            source_email="",
        )

        rendered = template.render(document=document)
        root = lxml.html.fromstring(rendered)

        preferred_dd = root.xpath('//dt[text()="Preferred"]/following-sibling::dd')[0]
        assert preferred_dd.text_content().strip() == "No data available"

        other_dd = root.xpath('//dt[text()="Other"]/following-sibling::dd')[0]
        assert "Find Case Law Identifier: tn4t35ts" in other_dd.text_content()
        assert "No data available" not in other_dd.text_content()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_shows_identifiers_from_framework(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-9874f350-b187-4e1e-b301-c7d914d5db8c"),
            identifiers=[
                NeutralCitationNumber("[2023] EWCA Civ 1"),
                FindCaseLawIdentifier("tn4t35ts"),
            ],
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        self.assertContains(response, "Identifiers")
        self.assertContains(response, "Preferred")
        self.assertContains(response, "Other")
        preferred = judgment.identifiers.preferred()
        assert preferred is not None
        self.assertContains(response, preferred.value)
        for identifier in judgment.identifiers.by_score():
            if identifier.uuid != preferred.uuid:
                self.assertContains(response, identifier.value)

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_shows_framework_judges(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-9874f350-b187-4e1e-b301-c7d914d5db8c"),
        )
        judgment.metadata_fields.add(
            MetadataField(
                name="judges",
                value="Lord Justice Underhill",
                source=MetadataSource.DOCUMENT,
            ),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        self.assertContains(response, 'data-test-id="metadata-section-heading"')
        self.assertContains(response, "Legacy")
        self.assertContains(response, "Lord Justice Underhill")

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
            "<dt>TDR ref</dt><dd>TDR-1234</dd>",
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
            "<dt>TDR ref</dt><dd>No data available</dd>",
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
            "<dt>First pub</dt><dd>No data available</dd>",
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
            "<dt>First pub</dt><dd>Unknown</dd>",
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
            "<dt>First pub</dt><dd>31 Aug 2025 12:34</dd>",
            html=True,
        )
