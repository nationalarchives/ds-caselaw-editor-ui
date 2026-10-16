from caselawclient.errors import MarklogicCheckoutConflictError
from caselawclient.models.identifiers.exceptions import IdentifierValidationException
from caselawclient.types import MarkLogicDocumentURIString
from django.core.management.base import BaseCommand

from judgments.utils import api_client

NUMBER_PER_LOOP = 100


class Command(BaseCommand):
    help = "Assign FCLIDs to documents which don't have them"

    def handle(self, *args, **options):
        """Assign FCLIDs, widening the fetch when a page is entirely blocked.

        ``get_missing_fclid`` has no offset, so it always returns the first matches. Checked-out and
        invalid documents stay at the front of that list. A pass that assigns nothing asks for a
        larger page. The run stops when a wider page contains only documents already skipped.
        """
        window = NUMBER_PER_LOOP
        skipped: set[str] = set()
        loop = 0
        doc_count = 0

        while True:
            loop += 1

            documents_missing_fclid = api_client.get_missing_fclid(maximum_records=window)
            if not documents_missing_fclid:
                break

            pending = [document for document in documents_missing_fclid if document not in skipped]
            if not pending:
                if len(documents_missing_fclid) < window:
                    break
                window += NUMBER_PER_LOOP
                continue

            assigned_this_loop = 0
            total = len(pending)

            for i, document in enumerate(pending):
                doc_count += 1
                prefix_string = f"L{loop}, {i + 1}/{total} ({doc_count})"
                if self._assign_fclid(document, prefix_string, skipped):
                    assigned_this_loop += 1

            if assigned_this_loop > 0:
                continue
            if len(documents_missing_fclid) < window:
                break
            window += NUMBER_PER_LOOP

    def _assign_fclid(self, document: str, prefix_string: str, skipped: set[str]) -> bool:
        try:
            document_object = api_client.get_document_by_uri(
                MarkLogicDocumentURIString(document).as_document_uri(),
            )

            self.stdout.write(f"{prefix_string}: {document_object.name}:")

            with document_object.editing_session():
                new_fclid = document_object.assign_fclid_if_missing()
            if new_fclid:
                self.stdout.write(f"\tAssigned FCLID {new_fclid.value}.")
                return True

            skipped.add(document)
            self.stdout.write("\tFAILED to assign FCLID!")
        except IdentifierValidationException as e:
            skipped.add(document)
            self.stdout.write(
                f"{prefix_string}: FAILED to assign FCLID for document at {document} with exception:",
            )
            self.stdout.write("\t" + str(e))
        except MarklogicCheckoutConflictError:
            skipped.add(document)
            self.stdout.write(f"{prefix_string}: skipped {document}, already checked out.")

        return False
