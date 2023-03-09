import datetime
from functools import cached_property
from typing import Optional

from caselawclient.Client import MarklogicApiClient
from django.conf import settings
from django.urls import reverse
from requests_toolbelt.multipart import decoder

from judgments.utils import get_judgment_root, render_versions
from judgments.utils.aws import (
    generate_docx_url,
    generate_pdf_url,
    notify_changed,
    publish_documents,
    unpublish_documents,
    uri_for_s3,
)


class CannotPublishUnpublishableJudgment(Exception):
    pass


class Judgment:
    def __init__(self, uri: str, api_client: Optional[MarklogicApiClient] = None):
        self.uri = uri.strip("/")
        if api_client:
            self.api_client = api_client
        else:
            self.api_client = MarklogicApiClient(
                host=settings.MARKLOGIC_HOST,
                username=settings.MARKLOGIC_USER,
                password=settings.MARKLOGIC_PASSWORD,
                use_https=settings.MARKLOGIC_USE_HTTPS,
            )

        # As part of initialisation, we preload the NCN so we can generate a MarklogicResourceNotFoundError early
        self.neutral_citation

    @property
    def public_uri(self) -> str:
        return "https://caselaw.nationalarchives.gov.uk/{uri}".format(uri=self.uri)

    @cached_property
    def neutral_citation(self) -> str:
        return self.api_client.get_judgment_citation(self.uri)

    @cached_property
    def name(self) -> str:
        return self.api_client.get_judgment_name(self.uri)

    @cached_property
    def court(self) -> str:
        return self.api_client.get_judgment_court(self.uri)

    @cached_property
    def judgment_date_as_string(self) -> str:
        return self.api_client.get_judgment_work_date(self.uri)

    @cached_property
    def judgment_date_as_date(self) -> datetime.date:
        return datetime.datetime.strptime(
            self.judgment_date_as_string, "%Y-%m-%d"
        ).date()

    @cached_property
    def is_published(self) -> bool:
        return self.api_client.get_published(self.uri)

    @cached_property
    def is_held(self) -> bool:
        return self.api_client.get_property(self.uri, "editor-hold")

    @cached_property
    def is_sensitive(self) -> bool:
        return self.api_client.get_sensitive(self.uri)

    @cached_property
    def is_anonymised(self) -> bool:
        return self.api_client.get_anonymised(self.uri)

    @cached_property
    def has_supplementary_materials(self) -> bool:
        return self.api_client.get_supplemental(self.uri)

    @cached_property
    def source_name(self) -> str:
        return self.api_client.get_property(self.uri, "source-name")

    @cached_property
    def source_email(self) -> str:
        return self.api_client.get_property(self.uri, "source-email")

    @cached_property
    def consignment_reference(self) -> str:
        return self.api_client.get_property(self.uri, "transfer-consignment-reference")

    @property
    def docx_url(self) -> str:
        return generate_docx_url(uri_for_s3(self.uri))

    @property
    def pdf_url(self) -> str:
        return generate_pdf_url(uri_for_s3(self.uri))

    @property
    def xml_url(self) -> str:
        return reverse("full-text-xml", kwargs={"judgment_uri": self.uri})

    @cached_property
    def assigned_to(self) -> str:
        return self.api_client.get_property(self.uri, "assigned-to")

    @cached_property
    def versions(self) -> list:
        versions_response = self.api_client.list_judgment_versions(self.uri)

        try:
            decoded_versions = decoder.MultipartDecoder.from_response(versions_response)
            return render_versions(decoded_versions.parts)
        except AttributeError:
            return []

    def content_as_xml(self) -> str:
        return self.api_client.get_judgment_xml(self.uri, show_unpublished=True)

    def content_as_html(self, version_uri: str) -> str:
        results = self.api_client.eval_xslt(
            self.uri, version_uri, show_unpublished=True
        )
        multipart_data = decoder.MultipartDecoder.from_response(results)
        return multipart_data.parts[0].text

    @cached_property
    def is_failure(self) -> bool:
        if "failures" in self.uri:
            return True
        return False

    @cached_property
    def is_editable(self) -> bool:
        if "error" in self._get_root():
            return False
        return True

    def _get_root(self) -> str:
        return get_judgment_root(self.content_as_xml())

    @cached_property
    def is_publishable(self) -> bool:
        if self.is_held:
            return False

        return True

    def publish(self):
        if not self.is_publishable:
            raise CannotPublishUnpublishableJudgment

        publish_documents(uri_for_s3(self.uri))
        self.api_client.set_published(self.uri, True)
        notify_changed(
            uri=self.uri,
            status="published",
            enrich=True,
        )

    def unpublish(self):
        unpublish_documents(uri_for_s3(self.uri))
        self.api_client.set_published(self.uri, False)
        notify_changed(
            uri=self.uri,
            status="not published",
            enrich=False,
        )