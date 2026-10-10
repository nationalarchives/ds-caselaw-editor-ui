import re
from unittest.mock import patch

from caselawclient.factories import JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from judgments.utils.permissions import editors_only_hint


class TestDocumentToolbar(TestCase):
    def setUp(self):
        editor_group = Group(name="Editors")
        editor_group.save()
        self.editor_user = User.objects.get_or_create(username="ed")[0]
        self.editor_user.groups.add(editor_group)
        self.editor_user.save()
        self.standard_user = User.objects.get_or_create(username="alice")[0]
        self.super_user = User.objects.create_superuser(username="clark")

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    def test_editor_tools_if_editor(self, document_exists, mock_judgment):
        mock_judgment.return_value = JudgmentFactory.build(
            uri=DocumentURIString("failures/TDR-ref"),
            is_failure=True,
        )
        self.client.force_login(self.editor_user)
        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": mock_judgment.uri}),
        )
        assert b"Request enrichment" in response.content
        assert b"Delete" in response.content

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    def test_editor_tools_are_disabled_if_not_priviledged(
        self,
        document_exists,
        mock_judgment,
    ):
        mock_judgment.return_value = JudgmentFactory.build(
            uri=DocumentURIString("failures/TDR-ref"),
            is_failure=True,
        )
        self.client.force_login(self.standard_user)
        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": mock_judgment.uri}),
        )
        self.assertContains(
            response,
            f'<button class="button button--danger button--small" disabled aria-disabled="true" title="{editors_only_hint()}">Delete</button>',
            html=True,
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    def test_get_locked_banner_if_locked(
        self,
        document_exists,
        mock_judgment,
    ):
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("good-document"),
            is_failure=False,
        )
        judgment.is_locked = True

        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )
        self.assertContains(response, "is locked")

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    def test_get_no_locked_banner_if_not_locked(
        self,
        document_exists,
        mock_judgment,
    ):
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("good-document"),
            is_failure=False,
        )
        judgment.is_locked = False
        mock_judgment.return_value = judgment
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(
            reverse("full-text-html", kwargs={"document_uri": judgment.uri}),
        )
        self.assertNotContains(response, "is locked")

    def preprocess_html(self, html):
        """Removes leading and trailing whitespace, tabs, and line breaks"""
        return re.sub(r"\s+", " ", html).strip()
