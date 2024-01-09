from django.core.management.base import BaseCommand

from judgments.utils import api_client

TARGET_ENRICHMENT_VERSION = 6
NUMBER_TO_ENRICH = 1


class Command(BaseCommand):
    help = "Sends the next document in the re-enrichment queue to be enriched"  ## noqa: A003

    def handle(self, *args, **options):
        document_details_to_enrich = api_client.get_pending_enrichment_for_version(
            TARGET_ENRICHMENT_VERSION,
        )

        for document_details in document_details_to_enrich[1 : NUMBER_TO_ENRICH + 1]:
            document_uri = document_details[0]

            document = api_client.get_document_by_uri(document_uri.replace(".xml", ""))

            self.stdout.write(f"Sending document {document.name} to enrichment...")
            document.enrich()
