from urllib.parse import parse_qs, urlparse

from factories import JudgmentFactory

from judgments.views.judgment_edit import (
    build_confirmation_email_link,
    build_raise_issue_email_link,
)


def the_judgment():
    return JudgmentFactory.build(
        name="R v G & B",
        source_name="Darwin Núñez",
    )


def get_body_from_email_link(link):
    query = urlparse(link).query
    return parse_qs(query)["body"][0]


def test_issue_not_encoded():
    email_link = build_raise_issue_email_link(the_judgment(), "Sid Carrà")
    body = get_body_from_email_link(email_link)
    assert "R v G & B" in body
    assert "Sid Carrà" in body
    assert "Darwin Núñez" in body
    assert "please resubmit" in body
    assert "uploader@example.com" in email_link


def test_confirmation_issue_not_encoded():
    email_link = build_confirmation_email_link(the_judgment(), "Sid Carrà")
    body = get_body_from_email_link(email_link)
    assert "R v G & B" in body
    assert "Sid Carrà" in body
    assert "Darwin Núñez" in body
    assert "has been published" in body
    assert "uploader@example.com" in email_link
