import os
from unittest.mock import MagicMock, Mock, patch

import ds_caselaw_utils
import pytest
from caselawclient.errors import MarklogicAPIError
from django.contrib.auth.models import Group
from django.test import TestCase
from factories import UserFactory

import judgments
from judgments.utils import api_client as api_client_real
from judgments.utils import (
    editors_dict,
    ensure_local_referer_url,
    extract_version,
    get_judgment_root,
    render_versions,
    update_document_uri,
)
from judgments.utils.aws import build_new_key, invalidate_caches
from judgments.utils.paginator import paginator


class TestInvalidation:
    @patch.dict(
        os.environ,
        {
            "CLOUDFRONT_INVALIDATION_ACCESS_KEY_ID": "KEY",
            "CLOUDFRONT_INVALIDATION_ACCESS_SECRET": "SECRET",
            "CLOUDFRONT_PUBLIC_DISTRIBUTION_ID": "PUBLIC",
            "CLOUDFRONT_EDITOR_DISTRIBUTION_ID": "EDITOR",
            "CLOUDFRONT_ASSETS_DISTRIBUTION_ID": "ASSETS",
        },
    )
    @patch("judgments.utils.aws.boto3")
    def test_invalidation(self, mockboto):
        invalidate_caches("ewhc/2022/1")
        cf = mockboto.session.Session.return_value.client.return_value
        first, second, third = cf.create_invalidation.mock_calls
        assert first.kwargs["DistributionId"] == "PUBLIC"
        assert first.kwargs["InvalidationBatch"]["Paths"]["Items"] == ["/*"]
        assert second.kwargs["DistributionId"] == "ASSETS"
        assert second.kwargs["InvalidationBatch"]["Paths"]["Items"] == [
            "/ewhc/2022/1/*",
        ]
        assert third.kwargs["DistributionId"] == "EDITOR"
        assert third.kwargs["InvalidationBatch"]["Paths"]["Items"] == ["/*"]


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
    def test_update_document_uri_success(self, fake_boto3_client, fake_api_client):
        """Given the target document uri does not exist,
        we continue to move the document to the new location
        (where moving is copy + delete)"""
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        fake_api_client.document_exists.return_value = False
        fake_api_client.copy_document.return_value = True
        fake_api_client.delete_judgment.return_value = True
        fake_boto3_client.list_objects.return_value = []

        result = update_document_uri("old/uri", "[2002] EAT 1")

        fake_api_client.copy_document.assert_called_with("old/uri", "new/uri")
        fake_api_client.delete_judgment.assert_called_with("old/uri")
        assert result == "new/uri"

    @patch("judgments.utils.api_client")
    @patch("boto3.session.Session.client")
    def test_update_document_uri_strips_whitespace(
        self, fake_boto3_client, fake_api_client,
    ):
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        fake_api_client.copy_document.return_value = True
        fake_api_client.delete_judgment.return_value = True
        fake_api_client.document_exists.return_value = False
        fake_boto3_client.list_objects.return_value = []

        update_document_uri("old/uri", " [2002] EAT 1 ")

        ds_caselaw_utils.neutral_url.assert_called_with("[2002] EAT 1")

    @patch("judgments.utils.api_client")
    def test_update_document_uri_exception_copy(self, fake_client):
        """Given a document exists at the target uri, and copy_document fails,
        we raise a MoveJudgmentError"""
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        fake_client.copy_document.side_effect = MarklogicAPIError
        fake_client.delete_judgment.side_effect = True

        with pytest.raises(judgments.utils.MoveJudgmentError):
            update_document_uri("old/uri", "[2002] EAT 1")

    @patch("judgments.utils.api_client")
    def test_update_document_uri_exception_delete(self, fake_client):
        """If there's a target at the document uri and deleting fails,
        raise a MoveJudgmentError"""
        ds_caselaw_utils.neutral_url = MagicMock(return_value="new/uri")
        fake_client.copy_document.return_value = True
        fake_client.delete_judgment.side_effect = MarklogicAPIError

        with pytest.raises(judgments.utils.MoveJudgmentError):
            update_document_uri("old/uri", "[2002] EAT 1")

    def test_update_document_uri_unparseable_citation(self):
        ds_caselaw_utils.neutral_url = MagicMock(return_value=None)

        with pytest.raises(judgments.utils.NeutralCitationToUriError):
            update_document_uri("old/uri", "Wrong neutral citation")

    @patch("judgments.utils.api_client")
    def test_update_document_uri_duplicate_uri(self, fake_client):
        fake_client.document_exists.return_value = True
        with pytest.raises(judgments.utils.MoveJudgmentError):
            update_document_uri("old/uri", "[2002] EAT 1")

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


class TestVersionUtils:
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


class TestEditorsDict:
    @pytest.mark.django_db()
    def test_print_name_sorting(self, settings):
        settings.EDITORS_GROUP_ID = None

        UserFactory.create(username="joe_bloggs", first_name="", last_name="")
        UserFactory.create(
            username="ann_example", first_name="Ann", last_name="Example",
        )

        assert editors_dict() == [
            {"name": "ann_example", "print_name": "Ann Example"},
            {"name": "joe_bloggs", "print_name": "joe_bloggs"},
        ]

    @pytest.mark.django_db()
    def test_exclude_non_editors(self, settings):
        group = Group.objects.create(name="Editors")
        settings.EDITORS_GROUP_ID = group.id

        UserFactory.create(username="non_editor", first_name="", last_name="")
        editor = UserFactory.create(username="editor", first_name="", last_name="")

        editor.groups.add(group)

        assert editors_dict() == [
            {"name": "editor", "print_name": "editor"},
        ]

    @pytest.mark.django_db()
    def test_exclude_inactive_without_editor_group(self, settings):
        settings.EDITORS_GROUP_ID = None

        UserFactory.create(
            username="active_user", first_name="", last_name="", is_active=True,
        )
        UserFactory.create(
            username="inactive_user", first_name="", last_name="", is_active=False,
        )

        assert editors_dict() == [
            {"name": "active_user", "print_name": "active_user"},
        ]

    @pytest.mark.django_db()
    def test_exclude_inactive_with_editor_group(self, settings):
        group = Group.objects.create(name="Editors")
        settings.EDITORS_GROUP_ID = group.id

        UserFactory.create(
            username="active_non_editor", first_name="", last_name="", is_active=True,
        )
        UserFactory.create(
            username="inactive_non_editor", first_name="", last_name="", is_active=False,
        )

        active_editor = UserFactory.create(
            username="active_editor", first_name="", last_name="", is_active=True,
        )
        inactive_editor = UserFactory.create(
            username="inactive_editor", first_name="", last_name="", is_active=False,
        )

        active_editor.groups.add(group)
        inactive_editor.groups.add(group)

        assert editors_dict() == [
            {"name": "active_editor", "print_name": "active_editor"},
        ]


class TestApiClient:
    def test_user_agent(self):
        assert "ds-caselaw-editor" in api_client_real.session.headers["User-Agent"]
