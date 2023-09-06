from unittest.mock import patch

import pytest
from django.http import Http404
from django.test import Client

from judgments.tests.factories import JudgmentFactory, User


@pytest.mark.django_db()
class TestBreadcrumbs:
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
        <div class="page-header__breadcrumb">
            <nav class="page-header__breadcrumb-container"aria-label="Breadcrumb">
                <span class="page-header__breadcrumb-you-are-in">You are in:</span>
                <ol>
                    <li>
                        <a href="/">Find and manage case law</a>
                    </li>
                </ol>
            </nav>
        </div>
        """
        assert_contains_html(response, breadcrumb_html)

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
        <div class="page-header__breadcrumb">
            <nav class="page-header__breadcrumb-container"aria-label="Breadcrumb">
                <span class="page-header__breadcrumb-you-are-in">You are in:</span>
                <ol>
                    <li>
                        <a href="/">Find and manage case law</a>
                    </li>
                    <li>
                        Search results
                    </li>
                </ol>
            </nav>
        </div>
        """
        assert_contains_html(response, breadcrumb_html)

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
        mock_get_document_by_uri.return_value = JudgmentFactory.build(
            uri="/eat/2023/1/press-summary/1/",
            name="Press Summary of Judgment A",
            document_noun="press summary",
        )
        response = self.client.get("/eat/2023/1/press-summary/1/")
        breadcrumb_html = """
        <div class="page-header__breadcrumb">
            <nav class="page-header__breadcrumb-container"aria-label="Breadcrumb">
                <span class="page-header__breadcrumb-you-are-in">You are in:</span>
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
        </div>
        """
        assert_contains_html(response, breadcrumb_html)

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
            uri="/eat/2023/1",
            name="Judgment A",
            document_noun="judgment",
        )
        response = self.client.get("/eat/2023/1")
        breadcrumb_html = """
        <div class="page-header__breadcrumb">
            <nav class="page-header__breadcrumb-container"aria-label="Breadcrumb">
                <span class="page-header__breadcrumb-you-are-in">You are in:</span>
                <ol>
                    <li>
                        <a href="/">Find and manage case law</a>
                    </li>
                    <li>Judgment A</li>
                </ol>
            </nav>
        </div>
        """
        assert_contains_html(response, breadcrumb_html)

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
        mock_get_document_by_uri.return_value = JudgmentFactory.build(
            uri="/eat/2023/1",
            name="",
            document_noun="judgment",
        )
        response = self.client.get("/eat/2023/1")
        breadcrumb_html = """
        <div class="page-header__breadcrumb">
            <nav class="page-header__breadcrumb-container"aria-label="Breadcrumb">
                <span class="page-header__breadcrumb-you-are-in">You are in:</span>
                <ol>
                    <li>
                        <a href="/">Find and manage case law</a>
                    </li>
                    <li>[Untitled Document]</li>
                </ol>
            </nav>
        </div>
        """
        assert_contains_html(response, breadcrumb_html)

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @pytest.mark.parametrize(
        ("http_error", "expected_breadcrumb"),
        [
            (Http404, "Page not found"),
            (Exception, "Server Error"),
        ],
    )
    def test_breadcrumb_when_errors(
        self,
        mock_get_document_by_uri,
        http_error,
        expected_breadcrumb,
    ):
        """
        GIVEN an URI matching the detail URI structure but does not match a valid document
        WHEN a request is made with the URI
        THEN the response should contain breadcrumbs including the appropriate error reference
        """
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        def get_document_by_uri_side_effect(document_uri):
            raise http_error

        mock_get_document_by_uri.side_effect = get_document_by_uri_side_effect

        response = self.client.get("/eat/2023/1/")
        breadcrumb_html = f"""
        <div class="page-header__breadcrumb">
            <nav class="page-header__breadcrumb-container"aria-label="Breadcrumb">
                <span class="page-header__breadcrumb-you-are-in">You are in:</span>
                <ol>
                    <li>
                        <a href="/">Find and manage case law</a>
                    </li>
                    <li>{expected_breadcrumb}</li>
                </ol>
            </nav>
        </div>
        """
        assert_contains_html(response, breadcrumb_html)


def assert_contains_html(response, html):
    """
    Asserts that the given HTML is contained within the response content.

    Raises:
        AssertionError: If the HTML is not found in the response content.
    """
    assert html.replace(" ", "").replace("\n", "") in response.content.decode().replace(
        " ",
        "",
    ).replace("\n", "")
