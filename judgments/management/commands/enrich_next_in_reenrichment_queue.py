import time
from typing import TYPE_CHECKING

from caselawclient.models.documents import DocumentURIString
from caselawclient.types import MarkLogicDocumentURIString
from django.core.management.base import BaseCommand

from judgments.utils import api_client
from judgments.views.reports import get_rows_from_result

if TYPE_CHECKING:
    from caselawclient.models.documents import DocumentURIString

NUMBER_TO_ENRICH = 25


class Command(BaseCommand):
    help = "Sends the next document in the re-enrichment queue to be enriched"

    def handle(self, *args, **options):
        target_enrichment_version = api_client.get_highest_enrichment_version()
        target_parser_version = api_client.get_highest_parser_version()

        document_details_to_enrich = get_rows_from_result(
            api_client.get_pending_enrichment_for_version(
                target_enrichment_version=target_enrichment_version,
                target_parser_version=target_parser_version,
            ),
        )

        for document_details in document_details_to_enrich[:NUMBER_TO_ENRICH]:
            marklogic_document_uri: MarkLogicDocumentURIString = MarkLogicDocumentURIString(document_details[0])
            document_uri: DocumentURIString = marklogic_document_uri.as_document_uri()

            document = api_client.get_document_by_uri(document_uri)

            self.stdout.write(f"Sending document {document.name} to enrichment...")
            document.enrich()
            time.sleep(3)
