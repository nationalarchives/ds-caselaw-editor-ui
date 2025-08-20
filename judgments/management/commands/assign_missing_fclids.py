from caselawclient.models.identifiers.exceptions import IdentifierValidationException
from caselawclient.types import MarkLogicDocumentURIString
from django.core.management.base import BaseCommand

from judgments.utils import api_client

NUMBER_PER_LOOP = 100


class Command(BaseCommand):
    help = "Assign FCLIDs to documents which don't have them"

    def handle(self, *args, **options):
        total = 1
        loop = 0
        doc_count = 0

        while total > 0:
            loop += 1

            documents_missing_fclid = api_client.get_missing_fclid(maximum_records=NUMBER_PER_LOOP)
            total = len(documents_missing_fclid)

            for i, document in enumerate(documents_missing_fclid):
                doc_count += 1

                prefix_string = f"L{loop}, {i + 1}/{total} ({doc_count})"

                try:
                    document_object = api_client.get_document_by_uri(
                        MarkLogicDocumentURIString(document).as_document_uri(),
                    )

                    self.stdout.write(f"{prefix_string}: {document_object.name}:")

                    if new_fclid := document_object.assign_fclid_if_missing():
                        self.stdout.write(f"\tAssigned FCLID {new_fclid.value}.")
                    else:
                        self.stdout.write("\tFAILED to assign FCLID!")

                except IdentifierValidationException as e:
                    self.stdout.write(
                        f"{prefix_string}: FAILED to assign FCLID for document at {document} with exception:",
                    )
                    self.stdout.write("\t" + str(e))
