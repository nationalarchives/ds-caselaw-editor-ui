from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import lxml.html
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory, PressSummaryFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.documents.metadata.fields.field import MetadataField, MetadataStringValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource
from caselawclient.models.identifiers.fclid import FindCaseLawIdentifier
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from caselawclient.models.judgments import Judgment
from caselawclient.types import DocumentCategory
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from factories import make_editor
from jinja2 import PackageLoader
from waffle.testutils import override_flag

from judgments.jinja import environment
from judgments.templatetags.navigation_tags import METADATA_ASIDE_JUDGES_FLAG
from judgments.tests.helpers.metadata_claims import judgment_with_title_claim
from judgments.utils.metadata_display import MetadataFieldDisplayDecorator


def form_control(element, control_id):
    return element.xpath(f'.//*[@id="{control_id}"]')[0]


def form_control_value(element, control_id):
    return form_control(element, control_id).value


@override_flag(METADATA_ASIDE_JUDGES_FLAG, active=True)
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
            identifiers=[NeutralCitationNumber("[2023] UKSC 1")],
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        root = lxml.html.fromstring(response.content)

        assert b'<input type="hidden" name="judgment_uri" value="hvtest/4321/123" />' in response.content
        assert form_control_value(root, "court") == "Court of Testing"
        assert form_control_value(root, "metadata_name") == "Test v Tested"
        assert form_control_value(root, "judgment_date-day") == "3"
        assert form_control_value(root, "judgment_date-month") == "2"
        assert form_control_value(root, "judgment_date-year") == "2023"
        assert form_control_value(root, "neutral_citation") == "[2023] UKSC 1"
        editable_metadata = root.xpath(
            '//details[summary/*[normalize-space(.)="Editable metadata"]]',
        )[0]
        identifiers = root.xpath('//details[summary/*[normalize-space(.)="Identifiers"]]')[0]
        other_metadata = root.xpath('//details[summary/*[normalize-space(.)="Other metadata"]]')[0]
        assert editable_metadata.xpath('.//*[@id="neutral_citation"]')
        assert not identifiers.xpath('.//*[@id="neutral_citation"]')
        assert identifiers.xpath('.//dt[normalize-space(.)="Case number"]')
        assert not other_metadata.xpath('.//dt[normalize-space(.)="Case number"]')
        edit_form = root.xpath("//form[@id='document-edit-form']")[0]
        assert edit_form.xpath(".//*[@id='metadata_name']")
        assert edit_form.xpath(".//*[@id='court']")
        assert edit_form.xpath(".//*[@id='judgment_date-day']")
        assert edit_form.xpath(".//*[@id='neutral_citation']")
        assert len(edit_form.xpath(".//button[@data-form-actions-submit]")) == 1
        assert not root.xpath("//div[contains(@class, 'metadata__container')]")
        assert response.status_code == 200

    def test_metadata_panel_is_read_only_for_non_judgments(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata.jinja" import document_metadata with context %}'
            "{{ document_metadata(document=document) }}",
        )
        preferred_ncn = NeutralCitationNumber("[2023] UKSC 1")
        press_summary = PressSummaryFactory.build(
            uri=DocumentURIString("press-summary/1"),
            name="Test press summary",
            identifiers=[preferred_ncn],
        )

        rendered = template.render(
            document=press_summary,
            preferred_ncn=preferred_ncn,
            user=make_editor(),
            metadata_aside_judges_enabled=True,
        )
        root = lxml.html.fromstring(rendered)

        assert root.xpath('//details[summary/*[normalize-space(.)="Metadata"]]')
        assert not root.xpath('//form[@id="document-edit-form"]')
        assert not root.xpath('//input[@id="metadata_name"]')
        assert not root.xpath('//input[@id="neutral_citation"]')
        assert not root.xpath('//input[@id="court"]')
        assert not root.xpath('//input[starts-with(@id, "judgment_date-")]')
        assert not root.xpath("//button[@data-form-actions-submit]")
        assert press_summary.metadata.title.value in root.text_content()
        assert "[2023] UKSC 1" in root.text_content()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    @override_flag(METADATA_ASIDE_JUDGES_FLAG, active=False)
    def test_metadata_panel_uses_legacy_interface_when_flag_inactive(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("hvtest/4321/123"),
            html="<h1>Test Judgment</h1>",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.body.judges = ["Lord Justice Test"]
        mock_judgment.return_value = judgment
        self.client.force_login(make_editor())

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )
        root = lxml.html.fromstring(response.content)
        metadata_aside = root.xpath("//div[contains(@class, 'main-container__aside')]")[0]

        assert response.status_code == 200
        assert root.xpath("//form[@data-document-edit-form]")
        assert root.xpath("//div[contains(@class, 'metadata__container')]")
        assert not metadata_aside.xpath(".//details")
        assert metadata_aside.xpath(".//div[contains(@class, 'aside__section-heading')]/dt/text()") == [
            "Metadata",
            "Identifiers",
            "Legacy",
        ]
        assert not metadata_aside.xpath(".//form[contains(@class, 'aside__metadata-compact-form')]")
        assert not metadata_aside.xpath(".//form[@id='document-edit-form']")
        assert not metadata_aside.xpath(".//*[@data-aside-resizer]")
        assert not root.xpath("//main[contains(@class, 'main-container--metadata-panel-editing')]")

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_metadata_panel_shows_resolved_structured_title_in_form(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = judgment_with_title_claim(
            body_name="Body title from XML",
            title_claim="Resolved structured title",
            source=MetadataSource.DOCUMENT,
            uri=DocumentURIString("hvtest/4321/123"),
            html="<h1>Test Judgment</h1>",
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        root = lxml.html.fromstring(response.content)

        assert form_control_value(root, "metadata_name") == "Resolved structured title"
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
            '{% from "components/document_metadata.jinja" import document_metadata with context %}'
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
            uri="test/2025/1",
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

        rendered = template.render(
            document=document,
            preferred_ncn=preferred,
            metadata_aside_judges_enabled=True,
        )
        root = lxml.html.fromstring(rendered)

        section_headings = root.xpath("//details/summary/span/text()")
        assert section_headings == ["Editable metadata", "Identifiers", "Other metadata"]

        judges_dd = root.xpath('//dt[normalize-space(.)="Judges"]/following-sibling::dd')[0]
        assert "Lord Justice Test" in judges_dd.text_content()
        assert "Lady Justice Example" in judges_dd.text_content()

        categories_dd = root.xpath('//dt[text()="Categories"]/following-sibling::dd')[0]
        assert "Civil" in categories_dd.text_content()
        assert "DocumentCategory" not in categories_dd.text_content()

        ncn_dd = root.xpath('//dt[text()="NCN"]/following-sibling::dd')[0]
        assert form_control_value(ncn_dd, "neutral_citation") == "[2023] EWCA Civ 1"

        other_dd = root.xpath('//dt[text()="Other"]/following-sibling::dd')[0]
        assert "Find Case Law Identifier: tn4t35ts" in other_dd.text_content()

        assert root.xpath('//dt[text()="TDR ref"]/following-sibling::dd')[0].text_content().strip() == "TDR-999"

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    @override_flag(METADATA_ASIDE_JUDGES_FLAG, active=False)
    def test_metadata_panel_hides_aside_judges_form_when_flag_inactive(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("hvtest/4321/123"),
            html="<h1>Test Judgment</h1>",
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.body.judges = ["Lord Justice Test"]
        mock_judgment.return_value = judgment

        self.client.force_login(make_editor())

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        assert response.status_code == 200
        assert b"aside__metadata-compact-form" not in response.content
        assert b"Judge/s" not in response.content

    def test_document_metadata_aside_judges_editable_for_editors(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata.jinja" import document_metadata with context %}'
            "{{ document_metadata(document=document) }}",
        )

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.body.judges = ["Lord Justice Test"]
        metadata_judges_section = MetadataFieldDisplayDecorator(judgment, judgment.metadata.judges).section

        class FakeRequest:
            def get_full_path(self):
                return "/d-a1b2c3/html"

        rendered = template.render(
            document=judgment,
            user=make_editor(),
            metadata_judges_section=metadata_judges_section,
            request=FakeRequest(),
            csrf_input="",
            metadata_aside_judges_enabled=True,
        )
        root = lxml.html.fromstring(rendered)

        judges_dd = root.xpath('//dt[normalize-space(.)="Judges"]/following-sibling::dd')[0]
        edit_form = root.xpath('//form[@id="document-edit-form"]')[0]
        assert edit_form.get("action").endswith("/d-a1b2c3/edit")
        assert not judges_dd.xpath('.//*[@name="new_claim__judges"]')
        assert judges_dd.xpath(".//template[@data-metadata-compact-new-template]")
        assert "data-metadata-compact-add" in rendered
        assert "data-metadata-compact-list" in rendered
        assert "aside__metadata-compact-entry" in rendered
        assert "Add another judge" in rendered
        assert "Update judges" not in rendered
        assert len(edit_form.xpath(".//button[@data-form-actions-submit]")) == 1
        remove_input = judges_dd.xpath('.//input[@name="suppress_body_judges"]')[0]
        remove_label = judges_dd.xpath('.//label[contains(@class, "aside__metadata-compact-remove-label")]')[0]
        assert "govuk-visually-hidden" in remove_input.get("class")
        assert "disabled" in remove_input.attrib
        assert remove_label.text.strip() == "Remove"
        assert remove_label.xpath('.//span[contains(@class, "govuk-visually-hidden")]')[0].text.strip() == (
            "Lord Justice Test"
        )
        assert "Lord Justice Test" in rendered

    def test_document_metadata_aside_shows_required_judge_input_when_there_are_no_judges(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata.jinja" import document_metadata with context %}'
            "{{ document_metadata(document=document) }}",
        )
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.body.judges = []
        metadata_judges_section = MetadataFieldDisplayDecorator(judgment, judgment.metadata.judges).section

        rendered = template.render(
            document=judgment,
            user=make_editor(),
            metadata_judges_section=metadata_judges_section,
            csrf_input="",
            metadata_aside_judges_enabled=True,
        )
        root = lxml.html.fromstring(rendered)
        judges_dd = root.xpath('//dt[normalize-space(.)="Judges"]/following-sibling::dd')[0]
        new_entries = judges_dd.xpath(
            ".//div[@data-metadata-compact-list]/div[@data-metadata-compact-new-entry]",
        )

        assert len(new_entries) == 1
        new_judge_control = new_entries[0].xpath(".//*[@data-metadata-compact-new-input]")[0]
        assert "required" in new_judge_control.attrib
        assert new_judge_control.get("name") is None
        assert "Add another judge" in judges_dd.text_content()

    def test_document_metadata_aside_judges_read_only_for_non_editors(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata.jinja" import document_metadata with context %}'
            "{{ document_metadata(document=document) }}",
        )

        judgment = JudgmentFactory.build(
            body=DocumentBodyFactory.build(name="Test v Tested"),
        )
        judgment.body.judges = ["Lord Justice Test"]
        metadata_judges_section = MetadataFieldDisplayDecorator(judgment, judgment.metadata.judges).section

        rendered = template.render(
            document=judgment,
            user=User.objects.get_or_create(username="not-an-editor")[0],
            metadata_judges_section=metadata_judges_section,
            csrf_input="",
            metadata_aside_judges_enabled=True,
        )

        assert 'name="new_claim__judges"' not in rendered
        assert "Lord Justice Test" in rendered

    def test_document_metadata_aside_shows_other_identifiers_without_preferred(self):
        template = environment(loader=PackageLoader("ds_caselaw_editor_ui", "templates")).from_string(
            '{% from "components/document_metadata.jinja" import document_metadata with context %}'
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
            uri="test/2025/1",
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

        rendered = template.render(document=document, metadata_aside_judges_enabled=True)
        root = lxml.html.fromstring(rendered)

        ncn_dd = root.xpath('//dt[text()="NCN"]/following-sibling::dd')[0]
        assert form_control_value(ncn_dd, "neutral_citation") == ""

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
        self.assertContains(response, "NCN")
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
                value=MetadataStringValue("Lord Justice Underhill"),
                source=MetadataSource.DOCUMENT,
            ),
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )

        root = lxml.html.fromstring(response.content)
        section_headings = root.xpath("//details/summary/span/text()")
        assert section_headings == ["Editable metadata", "Identifiers", "Other metadata"]
        assert "Lord Justice Underhill" in root.text_content()

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
