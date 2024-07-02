import sys
import time

from django.core.management.base import BaseCommand

from judgments.utils import api_client
from judgments.views.reports import get_rows_from_result

NUMBER_TO_PARSE = 1
MAX_DOCUMENTS_TO_TRY = 200

class Command(BaseCommand):
    help = "Sends the next document in the reparse queue to be reparsed"

    def handle(self, *args, **options):
        target_parser_version = api_client.get_highest_parser_version()

        document_details_to_parse = get_rows_from_result(
            api_client.get_pending_parse_for_version(
                target_version=target_parser_version,
            ),
        )

        counter = 0
        # Limit the number of documents so that when we run this job again
        # this one should have finished, no matter what.
        for document_details in document_details_to_parse[:MAX_DOCUMENTS_TO_TRY]:
            document_uri = document_details[0]

            document = api_client.get_document_by_uri(document_uri.replace(".xml", ""))

            sys.stdout.write(f"Attempting to reparse document {document.name}...\n")
            if document.reparse():
                sys.stdout.write("Reparse request sent.\n")
                counter += 1
            else:
                sys.stdout.write("Reparse not sent.\n")

            if counter >= NUMBER_TO_PARSE:
                break

            # Give other things a chance to run
            time.sleep(3)
