from django.core.management.base import BaseCommand

from judgments.utils import api_client
from judgments.views.reports import get_rows_from_result

NUMBER_TO_PARSE = 1


class Command(BaseCommand):
    help = "Sends the next document in the reparse queue to be reparsed"

    def handle(self, *args, **options):
        target_parser_version = api_client.get_highest_parser_version()

        document_details_to_parse = get_rows_from_result(
            api_client.get_pending_parse_for_version(
                target_version=target_parser_version,
            ),
        )

        for document_details in document_details_to_parse[:NUMBER_TO_PARSE]:
            document_uri = document_details[0]

            document = api_client.get_document_by_uri(document_uri.replace(".xml", ""))

            self.stdout.write(f"Attempting to reparse document {document.name}...")
            if document.reparse():
                self.stdout.write("Success!")
            else:
                self.stdout.write("Failed.")
