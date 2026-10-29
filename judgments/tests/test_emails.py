from urllib.parse import parse_qs, unquote, urlparse

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents.metadata.fields.field import MetadataField, MetadataStringValue
from caselawclient.models.documents.metadata.fields.source import MetadataSource

from judgments.utils.link_generators import (
    build_confirmation_email_link,
    build_raise_issue_email_link,
)


def the_judgment():
    return JudgmentFactory.build(
        source_name="Darwin Núñez",
        body=DocumentBodyFactory.build(name="R v G & B"),
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


def test_raise_issue_uses_metadata_title_when_present():
    judgment = JudgmentFactory.build(
        source_name="Darwin Núñez",
        body=DocumentBodyFactory.build(name="R v G & B"),
    )
    judgment.metadata_fields.add(
        MetadataField(
            name="title",
            value=MetadataStringValue("Metadata title for email"),
            source=MetadataSource.EDITOR,
        ),
    )
    email_link = build_raise_issue_email_link(judgment, "Sid Carrà")
    body = unquote(get_body_from_email_link(email_link))
    assert "Metadata title for email" in body
    assert "R v G & B" not in body
