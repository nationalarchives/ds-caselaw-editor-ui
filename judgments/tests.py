import re
from unittest import skip
from unittest.mock import MagicMock, Mock, patch

import ds_caselaw_utils
from caselawclient.Client import MarklogicAPIError
from django.test import TestCase

import judgments
from judgments import converters, views
from judgments.models import Judgment
from judgments.utils import get_judgment_root, update_judgment_uri
from judgments.views import extract_version, render_versions


class TestJudgment(TestCase):
    @skip
    def test_valid_content(self):
        response = self.client.get("/judgments/ewca/civ/2004/632")
        decoded_response = response.content.decode("utf-8")
        self.assertIn("[2004] EWCA Civ 632", decoded_response)
        self.assertEqual(response.status_code, 200)

    @skip
    def test_404_response(self):
        response = self.client.get("/judgments/ewca/civ/2004/63X")
        decoded_response = response.content.decode("utf-8")
        self.assertIn("Judgment was not found", decoded_response)
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


class TestJudgmentModel(TestCase):
    def test_can_parse_judgment(self):
        xml = """
            <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
                <judgment name="judgment" contains="originalVersion">
                    <meta>
                        <identification source="#tna">
                            <FRBRdate date="2004-06-10" name="judgment"/>
                            <FRBRname value="My Judgment Name"/>
                        </identification>
                        <proprietary source="ewca/civ/2004/811/eng/docx" xmlns:uk="https:/judgments.gov.uk/">
                            <uk:court>EWCA-Civil</uk:court>
                        </proprietary>
                    </meta>
                    <header>
                        <p>
                            <neutralCitation>[2017] EWHC 3289 (QB)</neutralCitation>
                        </p>
                    </header>
                </judgment>
            </akomaNtoso>
        """

        model = Judgment.create_from_string(xml)
        self.assertEqual("My Judgment Name", model.metadata_name)
        self.assertEqual("[2017] EWHC 3289 (QB)", model.neutral_citation)
        self.assertEqual("2004-06-10", model.date)
        self.assertEqual("EWCA-Civil", model.court)


class TestPaginator(TestCase):
    def test_paginator(self):
        expected_result = {
            "current_page": 10,
            "has_next_page": True,
            "has_prev_page": True,
            "next_page": 11,
            "prev_page": 9,
            "next_pages": [11, 12, 13, 14, 15, 16, 17, 18, 19],
            "number_of_pages": 200,
        }
        self.assertEqual(views.paginator(10, 2000), expected_result)


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
    def test_update_judgment_uri_success(self, fake_client):
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        attrs = {
            "get_judgment_xml.return_value": "",
            "copy_judgment.return_value": True,
            "delete_judgment.return_value": True,
        }
        fake_client.configure_mock(**attrs)

        result = update_judgment_uri("old/uri", "[2002] EAT 1")

        fake_client.copy_judgment.assert_called_with("old/uri", "new/uri")
        fake_client.delete_judgment.assert_called_with("old/uri")
        assert result == "new/uri"

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
