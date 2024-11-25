from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString


class TestJudgmentFactory:
    def test_default_uri(self):
        # The default URI gets a test where others don't because without a URI judgments fall apart
        judgment = JudgmentFactory.build()

        assert isinstance(judgment.uri, str)
        assert judgment.uri != ""

    def test_uri(self):
        judgment = JudgmentFactory.build(uri=DocumentURIString("test/1234/56"))

        assert judgment.uri == "test/1234/56"

    def test_name(self):
        judgment = JudgmentFactory.build(body=DocumentBodyFactory.build(name="Some Test Judgment"))

        assert judgment.name == "Some Test Judgment"

    def test_versions(self):
        judgment = JudgmentFactory.build()

        assert judgment.versions == []

    def test_html(self):
        judgment = JudgmentFactory.build(html="<h1>Testing HTML</h1>")

        assert judgment.content_as_html(DocumentURIString("example/2024/1")) == "<h1>Testing HTML</h1>"
