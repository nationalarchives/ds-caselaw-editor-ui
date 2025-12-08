import sys
import time
from datetime import UTC, datetime

import environ
from botocore.exceptions import EndpointConnectionError
from caselawclient.errors import MarklogicResourceLockedError
from django.core.management.base import BaseCommand, CommandParser

from judgments.models import BulkReparseRunLog
from judgments.models.telemetry import RunStatus
from judgments.utils import api_client
from judgments.views.reports import get_rows_from_result

env = environ.Env()


class Command(BaseCommand):
    help = "Sends the next document in the reparse queue to be reparsed"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--max_try",
            help="The number of documents to select from the database to attempt re-parsing",
            type=int,
            default=int(env("MAX_DOCUMENTS_TO_REPARSE", default="200")),
        )
        parser.add_argument(
            "--max_parse",
            help="The maximum number of documents to successfully re-parse in a run before finishing",
            type=int,
            default=int(env("NUMBER_OF_DOCUMENTS_TO_REPARSE", default="8")),
        )

    def _reparse_selected_document(self, document_details, run_log):
        document_uri = document_details[0]

        document = api_client.get_document_by_uri(document_uri.replace(".xml", ""))

        sys.stdout.write(f"Attempting to reparse document {document.body.name}...\n")
        try:
            if document.reparse():  # This returns `False` if the document fails `can_reparse` checks.
                sys.stdout.write("Reparse attempted.\n")
                run_log.detail += f"\nAttempted {document_uri}"
                run_log.documents_attempted += 1
            else:
                sys.stdout.write("Reparse skipped.\n")
                run_log.detail += f"\nSkipped {document_uri}"
                run_log.documents_skipped += 1
        except (EndpointConnectionError, MarklogicResourceLockedError) as e:
            sys.stdout.write(f"Reparse failed: {e}\n")
            run_log.detail += f"\nFAILED {document_uri}: {e}"
            run_log.documents_failed += 1

        run_log.save()

        # Give other things a chance to run
        time.sleep(3)

    def handle(self, *args, **options):
        # Get all the information we need to open a run log
        target_parser_version = api_client.get_highest_parser_version()
        total_in_queue = api_client.get_count_pending_parse_for_version(target_parser_version)

        start_time = datetime.now(UTC)

        # Log the fact that this run has started
        run_log = BulkReparseRunLog.objects.create(
            start_time=start_time,
            documents_in_queue=total_in_queue,
            target_parser_version=f"{target_parser_version[0]}.{target_parser_version[1]}",
            documents_attempted=0,
            documents_skipped=0,
            documents_failed=0,
            status=RunStatus.STARTED,
            detail=f"STARTED: {start_time}",
        )

        # If any uncaught exceptions happen during this, we want to be able to report them back
        try:
            document_details_to_parse = get_rows_from_result(
                api_client.get_documents_pending_parse_for_version(
                    target_version=target_parser_version,
                    maximum_records=options["max_try"],
                ),
            )

            # Save the number of documents we've loaded to attempt
            run_log.documents_selected = len(document_details_to_parse)
            run_log.save()

            for document_details in document_details_to_parse:
                self._reparse_selected_document(document_details, run_log)

                if run_log.documents_attempted >= options["max_parse"]:
                    break

        # Any uncaught exception above? Record the run as failed.
        except Exception as e:  # noqa: BLE001
            run_log.status = RunStatus.FAILED
            run_log.detail += f"\nUNCAUGHT EXCEPTION: {e}"

        # Everything worked? Mark as finished
        else:
            run_log.status = RunStatus.FINISHED

        # Log the run counts and time, and save our state.
        finally:
            end_time = datetime.now(UTC)
            run_log.end_time = end_time
            run_log.detail += f"\nENDED: {end_time}"
            run_log.save()
