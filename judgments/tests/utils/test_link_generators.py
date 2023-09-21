from django.test.client import RequestFactory

from judgments.tests.factories import JudgmentFactory
from judgments.utils.link_generators import (
    build_confirmation_email_link,
    build_email_link_with_content,
    build_jira_create_link,
    build_raise_issue_email_link,
)


class TestLinkGeneratorUtils:
    def test_build_email_link_with_content_without_body(self):
        assert (
            build_email_link_with_content("test@example.com", "FAO: Email Subject")
            == r"mailto:test@example.com?subject=Find%20Case%20Law%20-%20FAO%3A%20Email%20Subject"
        )

    def test_build_email_link_with_content_with_body(self):
        assert (
            build_email_link_with_content(
                "test@example.com",
                "FAO: Email Subject",
                """Dear Test,

This is an email.""",
            )
            == r"mailto:test@example.com?subject=Find%20Case%20Law%20-%20FAO%3A%20Email%20Subject&body=Dear%20Test%2C%0A%0AThis%20is%20an%20email."
        )

    def test_build_email_link_with_content_with_special_chars(self):
        assert (
            build_email_link_with_content(
                "test@example.com",
                "Subject",
                """Ampersand: & Quote: ' Double Quote: " LT: < GT: >""",
            )
            == r"mailto:test@example.com?subject=Find%20Case%20Law%20-%20Subject&body=Ampersand%3A%20%26%20Quote%3A%20%27%20Double%20Quote%3A%20%22%20LT%3A%20%3C%20GT%3A%20%3E"
        )

    def test_build_confirmation_email_link(self):
        judgment = JudgmentFactory.build()
        link = build_confirmation_email_link(judgment, "Test Signature")

        assert "mailto:uploader@example.com" in link
        assert "TDR-12345" in link
        assert "Judgment%20v%20Judgement" in link
        assert "Test%20Signature" in link

    def test_build_raise_issue_email_link(self):
        judgment = JudgmentFactory.build()
        link = build_raise_issue_email_link(judgment, "Test Signature")

        assert "mailto:uploader@example.com" in link
        assert "TDR-12345" in link

    def test_build_jira_create_link(self, settings):
        settings.JIRA_INSTANCE = "tna-test.jira.com"
        judgment = JudgmentFactory.build()
        request = RequestFactory().get(judgment.uri)
        link = build_jira_create_link(judgment, request)

        assert "https://tna-test.jira.com/secure/CreateIssueDetails!init.jspa?" in link
        assert r"http%3A%2F%2Ftestserver%2Ftest%2F2023%2F123" in link
