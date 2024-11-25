from unittest.mock import patch

import pytest
from caselawclient.factories import DocumentBodyFactory, JudgmentFactory, PressSummaryFactory
from caselawclient.models.documents import DocumentURIString
from django.http import Http404
from django.test import Client, TestCase

from judgments.tests.factories import User


@pytest.mark.django_db
class TestBreadcrumbs(TestCase):
    client = Client(raise_request_exception=False)

    @patch("judgments.views.index.get_search_results")
    def test_breadcrumb_when_home(self, mock_get_search_results):
        """
        GIVEN an authenticated user
        WHEN a request is made to the homepage
        THEN the response should contain only
            the `Find and manage case law` breadcrumb
        """
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        mock_get_search_results.return_value = {
            "query": "",
            "total": 0,
            "judgments": [],
            "order": "",
            "paginator": {},
        }
        response = self.client.get("/")
        breadcrumb_html = """
        <nav class="page-header__breadcrumbs-container" aria-label="Breadcrumb">
            <span class="page-header__breadcrumbs-you-are-in">You are in:</span>
            <ol>
                <li>
                    <a href="/">Find and manage case law</a>
                </li>
            </ol>
        </nav>
        """
        self.assertContains(response, breadcrumb_html, html=True)

    @patch("judgments.views.results.get_search_results")
    def test_breadcrumb_when_search_results(self, mock_get_search_results):
        """
        GIVEN an authenticated user
        WHEN a on a results page
        THEN the response should contain
            the `Find and manage case law`
            and `Search results` breadcrumbs
        """
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        mock_get_search_results.return_value = {
            "query": "",
            "total": 0,
            "judgments": [],
            "order": "",
            "paginator": {},
        }
        response = self.client.get("/results?foo")
        breadcrumb_html = """
        <nav class="page-header__breadcrumbs-container" aria-label="Breadcrumb">
            <span class="page-header__breadcrumbs-you-are-in">You are in:</span>
            <ol>
                <li>
                    <a href="/">Find and manage case law</a>
                </li>
                <li>
                    Search results
                </li>
            </ol>
        </nav>
        """
        self.assertContains(response, breadcrumb_html, html=True)

    @patch("judgments.utils.view_helpers.get_linked_document_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_breadcrumb_when_press_summary(
        self,
        mock_get_document_by_uri,
        mock_get_linked_document_uri,
    ):
        """
        GIVEN a press summary
        WHEN a request is made with the press summary URI
        THEN the response should contain breadcrumbs including the press summary name
        AND an additional `Press Summary` breadcrumb
        """
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        mock_get_linked_document_uri.return_value = "my_related_document_uri"
        judgment = PressSummaryFactory.build(
            uri=DocumentURIString("eat/2023/1/press-summary/1"),
            document_noun="press summary",
            body=DocumentBodyFactory.build(name="Press Summary of Judgment A"),
        )

        mock_get_document_by_uri.return_value = judgment
        response = self.client.get("/eat/2023/1/press-summary/1")
        breadcrumb_html = """
        <nav class="page-header__breadcrumbs-container" aria-label="Breadcrumb">
            <span class="page-header__breadcrumbs-you-are-in">You are in:</span>
            <ol>
                <li>
                    <a href="/">Find and manage case law</a>
                </li>
                <li>
                    <a href="/my_related_document_uri">Judgment A</a>
                </li>
                <li>Press Summary</li>
            </ol>
        </nav>
        """
        self.assertContains(response, breadcrumb_html, html=True)

    @patch("judgments.utils.view_helpers.get_linked_document_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_breadcrumb_when_judgment(
        self,
        mock_get_document_by_uri,
        mock_get_linked_document_uri,
    ):
        """
        GIVEN a judgment
        WHEN a request is made with the judgment URI
        THEN the response should contain breadcrumbs including the judgment name
        AND NOT contain an additional `Press Summary` breadcrumb
        """
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        mock_get_document_by_uri.return_value = JudgmentFactory.build(
            uri=DocumentURIString("eat/2023/1"),
            document_noun="judgment",
            body=DocumentBodyFactory.build(name="Judgment A"),
        )
        response = self.client.get("/eat/2023/1")
        breadcrumb_html = """
        <nav class="page-header__breadcrumbs-container" aria-label="Breadcrumb">
            <span class="page-header__breadcrumbs-you-are-in">You are in:</span>
            <ol>
                <li>
                    <a href="/">Find and manage case law</a>
                </li>
                <li>Judgment A</li>
            </ol>
        </nav>
        """
        self.assertContains(response, breadcrumb_html, html=True)

    @patch("judgments.utils.view_helpers.get_linked_document_uri")
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_breadcrumb_when_unnamed_document(
        self,
        mock_get_document_by_uri,
        mock_get_linked_document_uri,
    ):
        """
        GIVEN a document with an empty string for the name
        WHEN a request is made with the document URI
        THEN the response should contain breadcrumbs including the `[Untitled Document]`
        """
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        judgment = JudgmentFactory.build(
            uri=DocumentURIString("eat/2023/1"),
            name="",
            document_noun="judgment",
        )
        judgment.body.name = ""
        mock_get_document_by_uri.return_value = judgment
        response = self.client.get("/eat/2023/1")
        breadcrumb_html = """
        <nav class="page-header__breadcrumbs-container" aria-label="Breadcrumb">
            <span class="page-header__breadcrumbs-you-are-in">You are in:</span>
            <ol>
                <li>
                    <a href="/">Find and manage case law</a>
                </li>
                <li>[Untitled Document]</li>
            </ol>
        </nav>"""
        self.assertContains(response, breadcrumb_html, html=True)

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_breadcrumb_when_404(
        self,
        mock_get_document_by_uri,
    ):
        """
        GIVEN an URI matching the detail URI structure but does not match a valid document
        WHEN a request is made with the URI
        THEN the response should contain breadcrumbs including the appropriate error reference
        """
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        mock_get_document_by_uri.side_effect = Http404

        response = self.client.get("/eat/2023/1")
        breadcrumb_html = """
        <nav class="page-header__breadcrumbs-container" aria-label="Breadcrumb">
            <span class="page-header__breadcrumbs-you-are-in">You are in:</span>
            <ol>
                <li>
                    <a href="/">Find and manage case law</a>
                </li>
                <li>Page not found</li>
            </ol>
        </nav>
        """
        self.assertContains(response, breadcrumb_html, html=True, status_code=404)

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_breadcrumb_when_server_error(
        self,
        mock_get_document_by_uri,
    ):
        """
        GIVEN an URI causing a server error
        WHEN a request is made with the URI
        THEN the response should contain breadcrumbs including the appropriate error reference
        """
        self.client.raise_request_exception = False
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        mock_get_document_by_uri.side_effect = Exception

        response = self.client.get("/eat/2023/1")
        breadcrumb_html = """
        <nav class="page-header__breadcrumbs-container" aria-label="Breadcrumb">
            <span class="page-header__breadcrumbs-you-are-in">You are in:</span>
            <ol>
                <li>
                    <a href="/">Find and manage case law</a>
                </li>
                <li>Server Error</li>
            </ol>
        </nav>
        """
        self.assertContains(response, breadcrumb_html, html=True, status_code=500)
