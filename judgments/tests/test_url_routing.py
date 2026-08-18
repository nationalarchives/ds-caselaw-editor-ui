from unittest.mock import patch

from django.test import TestCase
from django.urls import resolve, reverse
from django.urls.resolvers import URLPattern, URLResolver

from config import urls as project_urls


def get_project_route_names(urlpatterns):
    """Collect named route names from the project URL configuration.

    Args:
        urlpatterns: URL patterns to inspect.

    Returns:
        A set of route names found in the configured URL patterns.
    """
    route_names = set()

    for pattern in urlpatterns:
        if isinstance(pattern, URLPattern):
            if pattern.name:
                route_names.add(pattern.name)
        elif isinstance(pattern, URLResolver) and str(pattern.pattern) == "":
            route_names.update(get_project_route_names(pattern.url_patterns))

    return route_names


class TestUnmatchedAccountUrls(TestCase):
    """Unmatched /accounts/* URLs are treated as public by Stronghold, so they must not
    fall through to the judgments catch-all document view."""

    unmatched_urls = [
        "/accounts/does-not-exist",
        "/accounts/does-not-exist/",
        "/accounts/nested/path/here",
        "/accounts/login/../../d-1234",
    ]

    def test_unmatched_account_urls_do_not_resolve_to_the_document_view(self):
        for url in self.unmatched_urls:
            with self.subTest(url=url):
                assert resolve(url).url_name != "full-text-html"

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    def test_unmatched_account_urls_return_404_without_calling_get_document_by_uri_or_404(self, mock_get_document):
        for url in self.unmatched_urls:
            with self.subTest(url=url):
                response = self.client.get(url)

                assert response.status_code == 404
                mock_get_document.assert_not_called()

    def test_existing_account_urls_still_resolve(self):
        for url_name in [
            "account_login",
            "account_logout",
            "account_reset_password",
            "account_reset_password_done",
            "account_reset_password_from_key_done",
        ]:
            with self.subTest(url_name=url_name):
                assert resolve(reverse(url_name)).url_name == url_name


class TestJudgmentViewsRequireAuthentication(TestCase):
    document_uris = ["test/1234", "d-1234"]

    def assert_redirects_to_login(self, url):
        response = self.client.get(url)

        assert response.status_code == 302
        assert "/accounts/login" in response["Location"]

    def auth_protected_top_level_urls(self):
        return [
            reverse("home"),
            reverse("components"),
            reverse("results"),
            reverse("signed-asset", kwargs={"key": "path/to/asset.xml"}),
            reverse("upload"),
            reverse("publish"),
            reverse("unpublish"),
            reverse("hold"),
            reverse("unhold"),
            reverse("delete"),
            reverse("enrich"),
            reverse("reparse"),
            reverse("unlock"),
            reverse("stub"),
            reverse("reports"),
            reverse("report_awaiting_parse"),
            reverse("report_bulk_reparse_run_logs"),
            reverse("report_bulk_reparse_run_log_detail", kwargs={"pk": 1}),
            reverse("report_awaiting_enrichment"),
            reverse("report_locked_documents"),
            reverse("tools"),
            reverse("tools_missing_fclid"),
            reverse("create-stub-document"),
        ]

    def judgment_view_urls(self, document_uri):
        return [
            reverse("associated-documents", kwargs={"document_uri": document_uri}),
            reverse("edit-document", kwargs={"document_uri": document_uri}),
            reverse("document-history", kwargs={"document_uri": document_uri}),
            reverse("document-identifiers", kwargs={"document_uri": document_uri}),
            reverse("document-identifiers-add", kwargs={"document_uri": document_uri}),
            reverse(
                "document-identifier-delete",
                kwargs={"document_uri": document_uri, "identifier_uuid": "test-identifier"},
            ),
            reverse("document-metadata", kwargs={"document_uri": document_uri}),
            reverse("publish-document", kwargs={"document_uri": document_uri}),
            reverse("publish-document-success", kwargs={"document_uri": document_uri}),
            reverse("unpublish-document", kwargs={"document_uri": document_uri}),
            reverse("unpublish-document-success", kwargs={"document_uri": document_uri}),
            reverse("hold-document", kwargs={"document_uri": document_uri}),
            reverse("hold-document-success", kwargs={"document_uri": document_uri}),
            reverse("unhold-document", kwargs={"document_uri": document_uri}),
            reverse("unhold-document-success", kwargs={"document_uri": document_uri}),
            reverse("document-upload", kwargs={"document_uri": document_uri}),
            reverse("upload-document-success", kwargs={"document_uri": document_uri}),
            reverse("delete-document", kwargs={"document_uri": document_uri}),
            reverse("full-text-pdf", kwargs={"document_uri": document_uri}),
            reverse("document-downloads", kwargs={"document_uri": document_uri}),
            reverse("full-text-xml", kwargs={"document_uri": document_uri}),
            reverse("full-text-html", kwargs={"document_uri": document_uri}),
        ]

    def public_view_urls(self):
        return [
            reverse("check"),
            reverse("account_login"),
            reverse("account_reset_password"),
            reverse("account_reset_password_done"),
            reverse("account_reset_password_from_key", kwargs={"uidb36": "abc", "key": "test-key"}),
            reverse("account_reset_password_from_key_done"),
        ]

    def test_unauthenticated_users_are_redirected_from_auth_protected_top_level_named_urls(self):
        for url in self.auth_protected_top_level_urls():
            with self.subTest(url=url):
                self.assert_redirects_to_login(url)

    def test_unauthenticated_users_are_redirected_from_auth_protected_legacy_redirect_urls(self):
        for url in ["/edit", "/detail", "/xml"]:
            with self.subTest(url=url):
                self.assert_redirects_to_login(url)

    def test_unauthenticated_users_are_redirected_from_judgment_views(self):
        for document_uri in self.document_uris:
            for url in self.judgment_view_urls(document_uri):
                with self.subTest(document_uri=document_uri, url=url):
                    self.assert_redirects_to_login(url)

    def test_project_route_names_match_the_explicit_url_lists(self):
        """Ensure the configured routes stay aligned with the explicit URL lists.

        This will fail if a new route is added to the project's URL config without also
        being added to one of the explicit URL lists above, which would otherwise leave
        the tests silently out of sync.
        """
        expected_route_names = {
            resolve(url).url_name
            for url in self.auth_protected_top_level_urls()
            + self.judgment_view_urls(self.document_uris[0])
            + self.public_view_urls()
        }

        assert get_project_route_names(project_urls.urlpatterns) == expected_route_names
