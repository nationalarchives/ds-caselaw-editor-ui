import re
from unittest.mock import MagicMock, Mock, patch

import ds_caselaw_utils
from caselawclient.Client import MarklogicAPIError
from django.contrib.auth.models import User
from django.test import TestCase
from lxml import etree

import judgments
from judgments import converters
from judgments.models import SearchResult, SearchResultMeta
from judgments.utils import (
    ensure_local_referer_url,
    extract_version,
    get_judgment_root,
    render_versions,
    update_judgment_uri,
)
from judgments.utils.aws import build_new_key
from judgments.utils.paginator import paginator


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


class TestPaginator(TestCase):
    def test_paginator_2500(self):
        expected_result = {
            "current_page": 10,
            "has_next_page": True,
            "has_prev_page": True,
            "next_page": 11,
            "prev_page": 9,
            "next_pages": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            "number_of_pages": 250,
        }
        self.assertEqual(paginator(10, 2500), expected_result)

    def test_paginator_25(self):
        # 25 items has 5 items on page 3.
        expected_result = {
            "current_page": 1,
            "has_next_page": True,
            "has_prev_page": False,
            "next_page": 2,
            "prev_page": 0,
            "next_pages": [2, 3],
            "number_of_pages": 3,
        }
        self.assertEqual(paginator(1, 25), expected_result)

    def test_paginator_5(self):
        expected_result = {
            "current_page": 1,
            "has_next_page": False,
            "has_prev_page": False,
            "next_page": 2,  # Note: remember to check has_next_page
            "prev_page": 0,
            "next_pages": [],
            "number_of_pages": 1,
        }
        self.assertEqual(paginator(1, 5), expected_result)


class TestConverters(TestCase):
    def test_year_converter_parses_year(self):
        converter = converters.YearConverter()
        match = re.match(converter.regex, "1994")

        self.assertEqual(match.group(0), "1994")

    def test_year_converter_converts_to_python(self):
        converter = converters.YearConverter()
        self.assertEqual(converter.to_python("1994"), 1994)

    def test_year_converter_converts_to_url(self):
        converter = converters.YearConverter()
        self.assertEqual(converter.to_url(1994), "1994")

    def test_date_converter_parses_date(self):
        converter = converters.DateConverter()
        match = re.match(converter.regex, "2022-02-28")
        self.assertEqual(match.group(0), "2022-02-28")

    def test_date_converter_fails_to_parse_string(self):
        converter = converters.DateConverter()
        match = re.match(converter.regex, "202L-ab-er")
        self.assertIsNone(match)

    def test_court_converter_parses_court(self):
        converter = converters.CourtConverter()
        match = re.match(converter.regex, "ewhc")
        self.assertEqual(match.group(0), "ewhc")

    def test_court_converter_fails_to_parse(self):
        converter = converters.CourtConverter()
        self.assertIsNone(re.match(converter.regex, "notacourt"))

    def test_subdivision_converter_parses_court(self):
        converter = converters.SubdivisionConverter()
        match = re.match(converter.regex, "comm")
        self.assertEqual(match.group(0), "comm")

    def test_subdivision_converter_fails_to_parse(self):
        converter = converters.SubdivisionConverter()
        self.assertIsNone(re.match(converter.regex, "notasubdivision"))


class TestUtils(TestCase):
    def test_get_judgment_root_error(self):
        xml = "<error>parser.log contents</error>"
        assert get_judgment_root(xml) == "error"

    def test_get_judgment_root_akomantoso(self):
        xml = (
            "<akomaNtoso xmlns:uk='https://caselaw.nationalarchives.gov.uk/akn' "
            "xmlns='http://docs.oasis-open.org/legaldocml/ns/akn/3.0'>judgment</akomaNtoso>"
        )
        assert (
            get_judgment_root(xml)
            == "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}akomaNtoso"
        )

    def test_get_judgment_root_malformed_xml(self):
        # Should theoretically never happen but test anyway
        xml = "<error>malformed xml"
        assert get_judgment_root(xml) == "error"

    @patch("judgments.utils.api_client")
    @patch("boto3.session.Session.client")
    def test_update_judgment_uri_success(self, fake_boto3_client, fake_api_client):
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        api_attrs = {
            "get_judgment_xml.side_effect": MarklogicAPIError,
            "copy_judgment.return_value": True,
            "delete_judgment.return_value": True,
        }
        fake_api_client.configure_mock(**api_attrs)
        boto_attrs: dict[str, list] = {"list_objects.return_value": []}
        fake_boto3_client.configure_mock(**boto_attrs)

        result = update_judgment_uri("old/uri", "[2002] EAT 1")

        fake_api_client.copy_judgment.assert_called_with("old/uri", "new/uri")
        fake_api_client.delete_judgment.assert_called_with("old/uri")
        assert result == "new/uri"

    @patch("judgments.utils.api_client")
    @patch("boto3.session.Session.client")
    def test_update_judgment_uri_strips_whitespace(
        self, fake_boto3_client, fake_api_client
    ):
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        api_attrs = {
            "get_judgment_xml.side_effect": MarklogicAPIError,
            "copy_judgment.return_value": True,
            "delete_judgment.return_value": True,
        }
        fake_api_client.configure_mock(**api_attrs)
        boto_attrs: dict[str, list] = {"list_objects.return_value": []}
        fake_boto3_client.configure_mock(**boto_attrs)

        update_judgment_uri("old/uri", " [2002] EAT 1 ")

        ds_caselaw_utils.neutral_url.assert_called_with("[2002] EAT 1")

    @patch("judgments.utils.api_client")
    def test_update_judgment_uri_exception_copy(self, fake_client):
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        attrs = {
            "copy_judgment.side_effect": MarklogicAPIError,
            "delete_judgment.return_value": True,
        }
        fake_client.configure_mock(**attrs)

        with self.assertRaises(judgments.utils.MoveJudgmentError):
            update_judgment_uri("old/uri", "[2002] EAT 1")

    @patch("judgments.utils.api_client")
    def test_update_judgment_uri_exception_delete(self, fake_client):
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        attrs = {
            "copy_judgment.return_value": True,
            "delete_judgment.side_effect": MarklogicAPIError,
        }
        fake_client.configure_mock(**attrs)

        with self.assertRaises(judgments.utils.MoveJudgmentError):
            update_judgment_uri("old/uri", "[2002] EAT 1")

    def test_update_judgment_uri_unparseable_citation(self):
        ds_caselaw_utils.neutral_url = MagicMock(return_value=None)

        with self.assertRaises(judgments.utils.NeutralCitationToUriError):
            update_judgment_uri("old/uri", "Wrong neutral citation")

    @patch("judgments.utils.api_client")
    def test_update_judgment_uri_duplicate_uri(self, fake_client):
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        attrs = {
            "get_judgment_xml.return_value": "<akomaNtoso><judgment></judgment></akomaNtoso>",
        }
        fake_client.configure_mock(**attrs)

        with self.assertRaises(judgments.utils.MoveJudgmentError):
            update_judgment_uri("old/uri", "[2002] EAT 1")

    def test_build_new_key_docx(self):
        old_key = "failures/TDR-2022-DNWR/failures_TDR-2022-DNWR.docx"
        new_uri = "ukpc/2023/120"
        assert build_new_key(old_key, new_uri) == "ukpc/2023/120/ukpc_2023_120.docx"

    def test_build_new_key_pdf(self):
        old_key = "failures/TDR-2022-DNWR/failures_TDR-2022-DNWR.pdf"
        new_uri = "ukpc/2023/120"
        assert build_new_key(old_key, new_uri) == "ukpc/2023/120/ukpc_2023_120.pdf"

    def test_build_new_key_image(self):
        old_key = "failures/TDR-2022-DNWR/image1.jpg"
        new_uri = "ukpc/2023/120"
        assert build_new_key(old_key, new_uri) == "ukpc/2023/120/image1.jpg"


class TestJudgmentEditor(TestCase):
    @patch("judgments.views.edit_judgment.api_client")
    def test_assigned(self, mock_api):
        mock_api.get_published.return_value = "6"
        mock_api.get_sensitive.return_value = "6"
        mock_api.get_supplemental.return_value = "6"
        mock_api.get_anonymised.return_value = "6"
        mock_api.list_judgment_versions.return_value = []
        mock_api.get_property.side_effect = (
            lambda _, property: "otheruser" if property == "assigned-to" else "xxx"
        )
        User.objects.get_or_create(username="otheruser")[0]
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/edit?judgment_uri=ewhc/ch/1999/1")
        mock_api.get_property.assert_called_with("ewhc/ch/1999/1", "assigned-to")
        assert b"selected>otheruser" in response.content


class TestReferrerUrlHelper(TestCase):
    @patch("django.http.request.HttpRequest")
    def test_when_referrer_is_relative(self, request):
        request.META = {"HTTP_REFERER": "/foo/bar"}
        assert ensure_local_referer_url(request, "/default") == "/foo/bar"

    @patch("django.http.request.HttpRequest")
    def test_when_referrer_is_absolute_and_local(self, request):
        request.META = {"HTTP_REFERER": "https://www.example.com/foo/bar"}
        request.get_host.return_value = "www.example.com"
        assert (
            ensure_local_referer_url(request, "/default")
            == "https://www.example.com/foo/bar"
        )

    @patch("django.http.request.HttpRequest")
    def test_when_referrer_is_absolute_and_remote(self, request):
        request.META = {"HTTP_REFERER": "https://www.someone-nefarious.com/foo/bar"}
        request.get_host.return_value = "www.example.com"
        assert ensure_local_referer_url(request, "/default") == "/default"
