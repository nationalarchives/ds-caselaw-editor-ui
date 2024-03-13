from django.core.management.base import BaseCommand

from judgments.utils import api_client
from judgments.views.reports import get_rows_from_result

NUMBER_TO_ENRICH = 1


class Command(BaseCommand):
    help = "Sends the next document in the re-enrichment queue to be enriched"

    def handle(self, *args, **options):
        """
        2024-03-13: Disabled this function in order to make sure that documents were not being sent to enrichment
        (and therefore locked) before editors had a chance to edit them. We intend to revisit this decision later
        so keeping the code intact makes sense.
        """
        self.stdout.write("enrich_next_in_reenrichment_queue.py: currently disabled")
        return

        target_enrichment_version = api_client.get_highest_enrichment_version()
        target_parser_version = api_client.get_highest_parser_version()

        document_details_to_enrich = get_rows_from_result(
            api_client.get_pending_enrichment_for_version(
                target_enrichment_version=target_enrichment_version,
                target_parser_version=target_parser_version,
            ),
        )

        for document_details in document_details_to_enrich[:NUMBER_TO_ENRICH]:
            document_uri = document_details[0]

            document = api_client.get_document_by_uri(document_uri.replace(".xml", ""))

            self.stdout.write(f"Sending document {document.name} to enrichment...")
            document.enrich()
