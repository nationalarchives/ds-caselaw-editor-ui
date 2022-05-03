# from django.db import models
from datetime import datetime
from os.path import dirname, join

from caselawclient.Client import api_client
from djxml import xmlmodels
from lxml import etree


class SearchResultMeta:
    def __init__(
        self,
        author="",
        author_email="",
        consignment_reference="",
        submission_datetime="",
    ):
        self.author = author
        self.author_email = author_email
        self.consignment_reference = consignment_reference
        self.submission_datetime = (
            datetime.strptime(submission_datetime, "%Y-%m-%dT%H:%M:%SZ")
            if submission_datetime
            else datetime.min
        )

    @staticmethod
    def create_from_uri(uri: str):
        return SearchResultMeta(
            author=api_client.get_property(uri, "source-name"),
            author_email=api_client.get_property(uri, "source-email"),
            consignment_reference=api_client.get_property(
                uri, "transfer-consignment-reference"
            ),
            submission_datetime=api_client.get_property(uri, "transfer-received-at"),
        )


class Judgment(xmlmodels.XmlModel):
    class Meta:
        namespaces = {
            "akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0",
            "uk": "https:/judgments.gov.uk/",
        }

    metadata_name = xmlmodels.XPathTextField(
        "//akn:FRBRname/@value", ignore_extra_nodes=True
    )
    neutral_citation = xmlmodels.XPathTextField(
        "//akn:neutralCitation", ignore_extra_nodes=True
    )
    date = xmlmodels.XPathTextField(
        "//akn:FRBRdate[@name='judgment']/@date", ignore_extra_nodes=True
    )
    court = xmlmodels.XPathTextField("//akn:proprietary/uk:court")


class SearchResult:
    def __init__(
        self,
        uri="",
        neutral_citation="",
        name="",
        court="",
        date="",
        matches=[],
        meta=SearchResultMeta(),
    ) -> None:
        self.uri = uri
        self.neutral_citation = neutral_citation
        self.name = name
        self.date = date
        self.court = court
        self.matches = matches
        self.meta = meta
        self.is_failure = "failures" in self.uri

    @staticmethod
    def create_from_node(node):
        uri = node.xpath("@uri")[0].lstrip("/").split(".xml")[0]
        matches = SearchMatch.create_from_string(
            etree.tostring(node, encoding="UTF-8").decode("UTF-8")
        )
        judgment_xml = api_client.get_judgment_xml(uri, show_unpublished=True)
        judgment = Judgment.create_from_string(judgment_xml)

        return SearchResult(
            uri=uri,
            neutral_citation=judgment.neutral_citation,
            name=judgment.metadata_name,
            matches=matches.transform_to_html(),
            court=judgment.court,
            date=judgment.date,
            meta=SearchResultMeta.create_from_uri(uri),
        )


class SearchResults(xmlmodels.XmlModel):
    class Meta:
        namespaces = {"search": "http://marklogic.com/appservices/search"}

    total = xmlmodels.XPathTextField("//search:response/@total")
    results = xmlmodels.XPathListField("//search:response/search:result")


class SearchMatch(xmlmodels.XmlModel):
    class Meta:
        namespaces = {"search": "http://marklogic.com/appservices/search"}

    transform_to_html = xmlmodels.XsltField(join(dirname(__file__), "search_match.xsl"))
