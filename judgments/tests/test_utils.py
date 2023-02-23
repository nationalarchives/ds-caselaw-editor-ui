from unittest.mock import MagicMock, patch

import ds_caselaw_utils
from caselawclient.Client import MarklogicAPIError
from django.test import TestCase

import judgments
from judgments.utils import get_judgment_root, update_judgment_uri
from judgments.utils.aws import build_new_key
from judgments.utils.paginator import paginator


class TestPaginator:
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
        assert paginator(10, 2500) == expected_result

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
        assert paginator(1, 25) == expected_result

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
        assert paginator(1, 5) == expected_result


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
