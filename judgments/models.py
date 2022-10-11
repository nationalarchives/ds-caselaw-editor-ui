# from django.db import models
import logging
from datetime import datetime
from os.path import dirname, join

import caselawclient.Client
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
        assigned_to="",
    ):
        self.author = author
        self.author_email = author_email
        self.consignment_reference = consignment_reference
        self.submission_datetime = (
            datetime.strptime(submission_datetime, "%Y-%m-%dT%H:%M:%SZ")
            if submission_datetime
            else datetime.min
        )
        self.assigned_to = assigned_to

    @staticmethod
    def create_from_uri(uri: str):
        return SearchResultMeta(
            author=api_client.get_property(uri, "source-name"),
            author_email=api_client.get_property(uri, "source-email"),
            consignment_reference=api_client.get_property(
                uri, "transfer-consignment-reference"
            ),
            submission_datetime=api_client.get_property(uri, "transfer-received-at"),
            assigned_to=api_client.get_property(uri, "assigned-to"),
        )


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
        assigned_to="",
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
        namespaces = {
            "search": "http://marklogic.com/appservices/search",
            "uk": "https://caselaw.nationalarchives.gov.uk/akn",
            "akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0",
        }
        uri = node.xpath("@uri")[0].lstrip("/").split(".xml")[0]
        neutral_citation = (
            node.xpath("search:extracted/uk:cite", namespaces=namespaces)[0].text
            if node.xpath("search:extracted/uk:cite", namespaces=namespaces)
            else ""
        )
        court = (
            node.xpath("search:extracted/uk:court", namespaces=namespaces)[0].text
            if node.xpath("search:extracted/uk:court", namespaces=namespaces)
            else ""
        )
        metadata_name = (
            node.xpath("search:extracted/akn:FRBRname/@value", namespaces=namespaces)[0]
            if node.xpath("search:extracted/akn:FRBRname/@value", namespaces=namespaces)
            else ""
        )
        date = (
            node.xpath("search:extracted/akn:FRBRdate/@date", namespaces=namespaces)[0]
            if node.xpath("search:extracted/akn:FRBRdate/@date", namespaces=namespaces)
            else ""
        )
        matches = SearchMatch.create_from_string(
            etree.tostring(node, encoding="UTF-8").decode("UTF-8")
        )

        try:
            return SearchResult(
                uri=uri,
                neutral_citation=neutral_citation,
                name=metadata_name,
                matches=matches.transform_to_html(),
                court=court,
                date=date,
                meta=SearchResultMeta.create_from_uri(uri),
            )
        except caselawclient.Client.MarklogicAPIError as e:
            logging.warning(
                f"Unable to create search result for {uri}. Has it been deleted? Full error: {e}"
            )
            return None


class SearchResults(xmlmodels.XmlModel):
    class Meta:
        namespaces = {"search": "http://marklogic.com/appservices/search"}

    total = xmlmodels.XPathTextField("//search:response/@total")
    results = xmlmodels.XPathListField("//search:response/search:result")


class SearchMatch(xmlmodels.XmlModel):
    class Meta:
        namespaces = {"search": "http://marklogic.com/appservices/search"}

    transform_to_html = xmlmodels.XsltField(join(dirname(__file__), "search_match.xsl"))
