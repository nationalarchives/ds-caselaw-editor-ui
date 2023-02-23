from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from lxml import etree

from judgments.models import Judgment, SearchResult, SearchResultMeta
from judgments.utils import extract_version, render_versions


class TestJudgment(TestCase):
    def test_404_response(self):
        response = self.client.get("/judgments/ewca/civ/2004/63X")
        decoded_response = response.content.decode("utf-8")
        self.assertIn("Page not found", decoded_response)
        self.assertEqual(response.status_code, 404)

    def test_extract_version_uri(self):
        uri = "/ewhc/ch/2022/1178_xml_versions/2-1178.xml"
        assert extract_version(uri) == 2

    def test_extract_version_failure(self):
        uri = "/failures/TDR-2022-DBF_xml_versions/1-TDR-2022-DBF.xml"
        assert extract_version(uri) == 1

    def test_extract_version_not_found(self):
        uri = "some-other-string"
        assert extract_version(uri) == 0

    def test_render_versions(self):
        version_parts = (
            Mock(text="/ewhc/ch/2022/1178_xml_versions/3-1178.xml"),
            Mock(text="/ewhc/ch/2022/1178_xml_versions/2-1178.xml"),
            Mock(text="/ewhc/ch/2022/1178_xml_versions/1-1178.xml"),
        )
        requests_toolbelt = Mock()
        requests_toolbelt.multipart.decoder.BodyPart.return_value = version_parts

        expected_result = [
            {"uri": "/ewhc/ch/2022/1178_xml_versions/3-1178", "version": 3},
            {"uri": "/ewhc/ch/2022/1178_xml_versions/2-1178", "version": 2},
            {"uri": "/ewhc/ch/2022/1178_xml_versions/1-1178", "version": 1},
        ]

        assert render_versions(version_parts) == expected_result


class TestSearchResults(TestCase):
    @patch("judgments.utils.view_helpers.perform_advanced_search")
    def test_oldest(self, advanced_search):
        advanced_search.results.return_value = []
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("?order=-date")
        advanced_search.assert_called_with(
            query=None, order="-date", only_unpublished=True, page=1
        )
        assert b"<option value=\"-date\" selected='selected'>" in response.content

    @patch("judgments.utils.view_helpers.perform_advanced_search")
    def test_newest(self, advanced_search):
        advanced_search.results.return_value = []
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("?order=date")
        advanced_search.assert_called_with(
            query=None, order="date", only_unpublished=True, page=1
        )
        assert b"<option value=\"date\" selected='selected'>" in response.content


class TestSearchResultMeta(TestCase):
    def test_create_from_node(self):
        meta_str = """
        <property-results>
          <property-result uri="/ukut/lc/2022/241.xml">
            <source-name>Fireman Sam</source-name>
            <transfer-consignment-reference>TDR-2022-BAG</transfer-consignment-reference>
            <transfer-received-at>2022-09-09T09:18:45Z</transfer-received-at>
            <assigned-to>dragon</assigned-to>
          </property-result>
        </property-results>
        """
        metadata = SearchResultMeta.create_from_node(etree.fromstring(meta_str))
        assert metadata.author == "Fireman Sam"
        assert metadata.author_email == ""  # most things default to empty string
        assert metadata.assigned_to == "dragon"
        assert metadata.editor_priority == "20"  # default priority, medium

    def test_editor_status(self):
        assigned = """
        <property-results>
          <property-result uri="/ukut/lc/2022/241.xml">
            <assigned-to>dragon</assigned-to>
          </property-result>
        </property-results>
        """
        unassigned = """
        <property-results>
          <property-result uri="/ukut/lc/2022/241.xml">
          </property-result>
        </property-results>
        """

        held = """
        <property-results>
          <property-result uri="/ukut/lc/2022/241.xml">
            <assigned-to>dragon</assigned-to>
            <editor-hold>true</editor-hold>
          </property-result>
        </property-results>
        """
        metadata = SearchResultMeta.create_from_node(etree.fromstring(assigned))
        assert metadata.editor_status == "in progress"
        assert metadata.editor_hold == "false"
        metadata = SearchResultMeta.create_from_node(etree.fromstring(unassigned))
        assert metadata.editor_status == "new"
        assert metadata.editor_hold == "false"
        metadata = SearchResultMeta.create_from_node(etree.fromstring(held))
        assert metadata.editor_status == "hold"
        assert metadata.editor_hold == "true"


class TestSearchResultModel(TestCase):
    @patch("judgments.models.SearchResultMeta")
    def test_create_from_node(self, fake_meta):
        fake_meta.create_from_uri.return_value.assigned_to = "someone"
        search_result_str = """
        <search:result xmlns:search="http://marklogic.com/appservices/search" index="1" uri="/ukut/lc/2022/241.xml">
            <search:snippet/>
            <search:extracted kind="element">
                <FRBRdate xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0" date="2022-09-09" name="decision"/>
                <FRBRname xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                          value="London Borough of Waltham Forest v Nasim Hussain"/>
                <uk:court xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn">UKUT-LC</uk:court>
                <uk:cite xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn">[2022] UKUT 241 (LC)</uk:cite>
                <neutralCitation xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
                    [2022] UKUT 241 (LC)
                </neutralCitation>
            </search:extracted>
        </search:result>
        """
        search_result_xml = etree.fromstring(search_result_str)
        search_result = SearchResult.create_from_node(search_result_xml)
        self.assertEqual(
            "London Borough of Waltham Forest v Nasim Hussain", search_result.name
        )
        self.assertEqual("ukut/lc/2022/241", search_result.uri)
        self.assertEqual("[2022] UKUT 241 (LC)", search_result.neutral_citation)
        self.assertEqual("UKUT-LC", search_result.court)
        self.assertEqual("someone", search_result.meta.assigned_to)

    @patch("judgments.models.SearchResultMeta")
    def test_create_from_node_with_missing_elements(self, fake_model):
        model_attrs = {"create_from_uri.return_value": "a/fake/uri.xml"}
        fake_model.configure_mock(**model_attrs)
        search_result_str = """
        <search:result xmlns:search="http://marklogic.com/appservices/search" index="1" uri="/ukut/lc/2022/241.xml">
            <search:snippet/>
            <search:extracted kind="element">
                <FRBRdate xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0" date="2022-09-09" name="decision"/>
                <FRBRname xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                          value="London Borough of Waltham Forest v Nasim Hussain"/>
                <uk:cite xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn"></uk:cite>
                <uk:court xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn"></uk:court>
            </search:extracted>
        </search:result>
        """
        search_result_xml = etree.fromstring(search_result_str)
        search_result = SearchResult.create_from_node(search_result_xml)
        self.assertEqual(
            "London Borough of Waltham Forest v Nasim Hussain", search_result.name
        )
        self.assertEqual("ukut/lc/2022/241", search_result.uri)
        self.assertEqual(None, search_result.neutral_citation)
        self.assertEqual(None, search_result.court)


class TestJudgmentEditor(TestCase):
    @patch(
        "judgments.views.edit_judgment.Judgment",
        autospec=Judgment,
    )
    def test_assigned(self, mock_judgment):
        mock_judgment.return_value.assigned_to = "otheruser"
        mock_judgment.return_value.versions = []

        User.objects.get_or_create(username="otheruser")[0]
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/edit?judgment_uri=ewhc/ch/1999/1")

        assert b"selected>otheruser" in response.content
