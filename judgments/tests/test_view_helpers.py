from unittest.mock import patch

import pytest
from caselawclient.errors import DocumentNotFoundError
from django.contrib.auth.models import Group, User
from django.http import Http404
from django.test import TestCase
from factories import JudgmentFactory

from judgments.utils.view_helpers import (
    get_document_by_uri_or_404,
    user_is_developer,
    user_is_superuser_or_editor,
)


class TestGetDocumentByURIOr404:
    @patch("judgments.utils.view_helpers.api_client.get_document_by_uri")
    def test_published_judgment_returns(self, mock_judgment):
        judgment = JudgmentFactory.build(is_published=True)
        mock_judgment.return_value = judgment
        assert get_document_by_uri_or_404("2022/eat/1") == judgment

    @patch("judgments.utils.view_helpers.api_client.get_document_by_uri")
    def test_unpublished_judgment_returns(self, mock_judgment):
        judgment = JudgmentFactory.build(is_published=False)
        mock_judgment.return_value = judgment
        assert get_document_by_uri_or_404("2022/eat/1") == judgment

    @patch(
        "judgments.utils.view_helpers.api_client.get_document_by_uri",
        side_effect=DocumentNotFoundError,
    )
    def test_judgment_missing(self, mock_judgment):
        with pytest.raises(Http404):
            get_document_by_uri_or_404("not-a-judgment")


class TestGroupCheck(TestCase):
    def setUp(self):
        editor_group = Group(name="Editors")
        editor_group.save()
        developer_group = Group(name="Developers")
        developer_group.save()
        self.editor_user = User.objects.get_or_create(username="ed")[0]
        self.editor_user.groups.add(editor_group)
        self.editor_user.save()
        self.developer_user = User.objects.get_or_create(username="dev")[0]
        self.developer_user.groups.add(developer_group)
        self.developer_user.save()
        self.standard_user = User.objects.get_or_create(username="alice")[0]
        self.super_user = User.objects.create_superuser(username="clark")

    def test_editor_or_superuser(self):
        assert user_is_superuser_or_editor(self.standard_user) is False
        assert user_is_superuser_or_editor(self.super_user) is True
        assert user_is_superuser_or_editor(self.editor_user) is True
        assert user_is_superuser_or_editor(self.developer_user) is False

    def test_developer(self):
        assert user_is_developer(self.standard_user) is False
        assert user_is_developer(self.super_user) is False
        assert user_is_developer(self.editor_user) is False
        assert user_is_developer(self.developer_user) is True
