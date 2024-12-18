import os
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.test import TestCase
from factories import UserFactory

from judgments.utils import api_client as api_client_real
from judgments.utils import (
    editors_dict,
    ensure_local_referer_url,
    extract_version_number_from_filename,
)
from judgments.utils.aws import invalidate_caches
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
            "show_first_page": True,
            "show_first_page_divider": True,
            "show_last_page": True,
            "show_last_page_divider": True,
            "current_page": 10,
            "has_next_page": True,
            "has_prev_page": True,
            "next_page": 11,
            "prev_page": 9,
            "page_range": [8, 9, 10, 11, 12],
            "number_of_pages": 250,
        }
        assert paginator(10, 2500) == expected_result

    def test_paginator_25(self):
        # 25 items has 5 items on page 3.
        expected_result = {
            "show_first_page": False,
            "show_first_page_divider": False,
            "show_last_page": False,
            "show_last_page_divider": False,
            "current_page": 1,
            "has_next_page": True,
            "has_prev_page": False,
            "next_page": 2,
            "prev_page": 0,
            "page_range": [1, 2, 3],
            "number_of_pages": 3,
        }
        assert paginator(1, 25) == expected_result

    def test_paginator_5(self):
        expected_result = {
            "show_first_page": False,
            "show_first_page_divider": False,
            "show_last_page": False,
            "show_last_page_divider": False,
            "current_page": 1,
            "has_next_page": False,
            "has_prev_page": False,
            "next_page": 2,  # Note: remember to check has_next_page
            "prev_page": 0,
            "page_range": [1],
            "number_of_pages": 1,
        }
        assert paginator(1, 5) == expected_result


class TestReferrerUrlHelper(TestCase):
    @patch("django.http.request.HttpRequest")
    def test_when_referrer_is_relative(self, request):
        request.META = {"HTTP_REFERER": "/foo/bar"}
        assert ensure_local_referer_url(request, "/default") == "/foo/bar"

    @patch("django.http.request.HttpRequest")
    def test_when_referrer_is_absolute_and_local(self, request):
        request.META = {"HTTP_REFERER": "https://www.example.com/foo/bar"}
        request.get_host.return_value = "www.example.com"
        assert ensure_local_referer_url(request, "/default") == "https://www.example.com/foo/bar"

    @patch("django.http.request.HttpRequest")
    def test_when_referrer_is_absolute_and_remote(self, request):
        request.META = {"HTTP_REFERER": "https://www.someone-nefarious.com/foo/bar"}
        request.get_host.return_value = "www.example.com"
        assert ensure_local_referer_url(request, "/default") == "/default"


class TestVersionUtils:
    def test_extract_version_number_from_filename_uri(self):
        uri = "/ewhc/ch/2022/1178_xml_versions/2-1178.xml"
        assert extract_version_number_from_filename(uri) == 2

    def test_extract_version_number_from_filename_failure(self):
        uri = "/failures/TDR-2022-DBF_xml_versions/1-TDR-2022-DBF.xml"
        assert extract_version_number_from_filename(uri) == 1

    def test_extract_version_number_from_filename_not_found(self):
        uri = "some-other-string"
        assert extract_version_number_from_filename(uri) == 0


class TestEditorsDict:
    @pytest.mark.django_db
    def test_print_name_sorting(self, settings):
        settings.EDITORS_GROUP_ID = None

        UserFactory.create(username="joe_bloggs", first_name="", last_name="")
        UserFactory.create(
            username="ann_example",
            first_name="Ann",
            last_name="Example",
        )

        assert editors_dict() == [
            {"name": "ann_example", "print_name": "Ann Example"},
            {"name": "joe_bloggs", "print_name": "joe_bloggs"},
        ]

    @pytest.mark.django_db
    def test_exclude_non_editors(self, settings):
        group = Group.objects.create(name="Editors")
        settings.EDITORS_GROUP_ID = group.id

        UserFactory.create(username="non_editor", first_name="", last_name="")
        editor = UserFactory.create(username="editor", first_name="", last_name="")

        editor.groups.add(group)

        assert editors_dict() == [
            {"name": "editor", "print_name": "editor"},
        ]

    @pytest.mark.django_db
    def test_exclude_inactive_without_editor_group(self, settings):
        settings.EDITORS_GROUP_ID = None

        UserFactory.create(
            username="active_user",
            first_name="",
            last_name="",
            is_active=True,
        )
        UserFactory.create(
            username="inactive_user",
            first_name="",
            last_name="",
            is_active=False,
        )

        assert editors_dict() == [
            {"name": "active_user", "print_name": "active_user"},
        ]

    @pytest.mark.django_db
    def test_exclude_inactive_with_editor_group(self, settings):
        group = Group.objects.create(name="Editors")
        settings.EDITORS_GROUP_ID = group.id

        UserFactory.create(
            username="active_non_editor",
            first_name="",
            last_name="",
            is_active=True,
        )
        UserFactory.create(
            username="inactive_non_editor",
            first_name="",
            last_name="",
            is_active=False,
        )

        active_editor = UserFactory.create(
            username="active_editor",
            first_name="",
            last_name="",
            is_active=True,
        )
        inactive_editor = UserFactory.create(
            username="inactive_editor",
            first_name="",
            last_name="",
            is_active=False,
        )

        active_editor.groups.add(group)
        inactive_editor.groups.add(group)

        assert editors_dict() == [
            {"name": "active_editor", "print_name": "active_editor"},
        ]


class TestApiClient:
    def test_user_agent(self):
        assert "ds-caselaw-editor" in api_client_real.session.headers["User-Agent"]
