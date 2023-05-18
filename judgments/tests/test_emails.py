from factories import JudgmentFactory

from judgments.views.judgment_edit import (
    build_confirmation_email_link,
    build_raise_issue_email_link,
)


def test_issue_email():
    judgment = JudgmentFactory.build()
    email_link = build_raise_issue_email_link(judgment, "Username")
    assert r"Username" in email_link
    assert r"please%20resubmit" in email_link
    assert r"uploader@example.com" in email_link
    assert r"Example%20Uploader" in email_link


def test_confirmation_email():
    judgment = JudgmentFactory.build()
    email_link = build_confirmation_email_link(judgment, "Username")
    assert r"Username" in email_link
    assert r"uploader@example.com" in email_link
    assert r"Example%20Uploader" in email_link
    assert r"has%20been%20published" in email_link
