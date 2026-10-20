# ruff: noqa: EM101

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from judgments.utils import api_client
from judgments.utils.local_dev_safety import LocalDevSafetyError, assert_local_marklogic_host
from judgments.utils.marklogic_test_corpus import reload_marklogic_test_corpus


class Command(BaseCommand):
    help = (
        "Reload the MarkLogic test document corpus from the API client harness. "
        "Requires the caselaw MarkLogic application (fab deploy-marklogic). "
        "Does not change the Django database. "
        "Refuses to run unless MarkLogic is configured for local development only."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Do not prompt for confirmation before replacing MarkLogic test documents.",
        )

    def handle(self, *args, **options):
        try:
            assert_local_marklogic_host(settings.MARKLOGIC_HOST, use_https=settings.MARKLOGIC_USE_HTTPS)
        except LocalDevSafetyError as exc:
            raise CommandError(str(exc)) from exc

        if not options["noinput"]:
            self.stdout.write(
                "This will delete and re-insert the MarkLogic harness test documents "
                "(smoketest, merge test pair, metadata_writes, etc.).",
            )
            if input("Type yes to continue: ").strip().lower() != "yes":
                raise CommandError("Aborted.")

        try:
            document_count = reload_marklogic_test_corpus(api_client)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Reloaded {document_count} MarkLogic test corpus documents."))
