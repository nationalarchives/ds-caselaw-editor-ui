# from django.db import models
import datetime
import logging
from functools import cached_property
from os.path import dirname, join

import caselawclient.Client
from caselawclient.Client import api_client
from django.urls import reverse
from djxml import xmlmodels
from lxml import etree
from requests_toolbelt.multipart import decoder

from judgments.utils import render_versions
from judgments.utils.aws import generate_docx_url, generate_pdf_url, uri_for_s3


def one(x):
    if len(x) > 1:
        raise RuntimeError("More than one found.")
    if len(x) > 0:
        return x[0]
    return None


class SearchResultMeta:
    def __init__(
        self,
        author="",
        author_email="",
        consignment_reference="",
        submission_datetime="",
        assigned_to="",
        editor_hold="",
        editor_priority="",
    ):
        self.author = author
        self.author_email = author_email
        self.consignment_reference = consignment_reference
        self.submission_datetime = (
            datetime.datetime.strptime(submission_datetime, "%Y-%m-%dT%H:%M:%SZ")
            if submission_datetime
            else datetime.datetime.min
        )
        self.assigned_to = assigned_to
        self.editor_hold = editor_hold or "false"
        self.editor_priority = editor_priority

        if editor_hold == "true":
            self.editor_status = "hold"
        elif assigned_to:
            self.editor_status = "in progress"
        else:
            self.editor_status = "new"

    @staticmethod
    def create_from_uri(uri: str):
        response_text = api_client.get_properties_for_search_results([uri])
        root = etree.fromstring(response_text)
        return SearchResultMeta.create_from_node(root)

    @staticmethod
    def create_from_node(node):
        # we assume that there is only one node in the search result XML.
        return SearchResultMeta(
            author=one(node.xpath("//source-name/text()")) or "",
            author_email=one(node.xpath("//source-email/text()")) or "",
            consignment_reference=one(
                node.xpath("//transfer-consignment-reference/text()")
            )
            or "",
            submission_datetime=one(node.xpath("//transfer-received-at/text()")) or "",
            assigned_to=one(node.xpath("//assigned-to/text()")) or "",
            editor_hold=one(node.xpath("//editor-hold/text()")) or "",
            editor_priority=one(node.xpath("//editor-priority/text()"))
            or "20",  # medium priority
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


class JudgmentManager:
    @classmethod
    def get_by_uri(cls, uri: str) -> "Judgment":
        return Judgment(uri)


class Judgment:
    def __init__(self, uri: str):
        self.uri = uri

    objects = JudgmentManager()

    @cached_property
    def neutral_citation(self) -> str:
        return api_client.get_judgment_citation(self.uri)

    @cached_property
    def name(self) -> str:
        return api_client.get_judgment_name(self.uri)

    @cached_property
    def court(self) -> str:
        return api_client.get_judgment_court(self.uri)

    @cached_property
    def judgment_date_as_string(self) -> str:
        return api_client.get_judgment_work_date(self.uri)

    @cached_property
    def judgment_date_as_date(self) -> datetime.date:
        return datetime.datetime.strptime(
            self.judgment_date_as_string, "%Y-%m-%d"
        ).date()

    @cached_property
    def is_published(self) -> bool:
        return api_client.get_published(self.uri)

    @cached_property
    def is_sensitive(self) -> bool:
        return api_client.get_sensitive(self.uri)

    @cached_property
    def is_anonymised(self) -> bool:
        return api_client.get_anonymised(self.uri)

    @cached_property
    def has_supplementary_materials(self) -> bool:
        return api_client.get_supplemental(self.uri)

    @cached_property
    def source_name(self) -> str:
        return api_client.get_property(self.uri, "source-name")

    @cached_property
    def source_email(self) -> str:
        return api_client.get_property(self.uri, "source-email")

    @cached_property
    def consignment_reference(self) -> str:
        return api_client.get_property(self.uri, "transfer-consignment-reference")

    @property
    def docx_url(self) -> str:
        return generate_docx_url(uri_for_s3(self.uri))

    @property
    def pdf_url(self) -> str:
        return generate_pdf_url(uri_for_s3(self.uri))

    @property
    def xml_url(self) -> str:
        return reverse("detail_xml") + "?judgment_uri=" + self.uri

    @cached_property
    def assigned_to(self) -> str:
        return api_client.get_property(self.uri, "assigned-to")

    @cached_property
    def versions(self) -> list:
        versions_response = api_client.list_judgment_versions(self.uri)

        try:
            decoded_versions = decoder.MultipartDecoder.from_response(versions_response)
            return render_versions(decoded_versions.parts)
        except AttributeError:
            return []

    def content_as_xml(self) -> str:
        return api_client.get_judgment_xml(self.uri, show_unpublished=True)
