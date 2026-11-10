from __future__ import annotations

from typing import TYPE_CHECKING, Any

from caselawclient.client_helpers.search_helpers import search_and_parse_response
from caselawclient.errors import MarklogicCheckoutConflictError
from caselawclient.models.documents import DocumentURIString
from caselawclient.search_parameters import SearchParameters
from django.core.management.base import BaseCommand, CommandError, CommandParser

from judgments.utils import api_client
from judgments.utils.metadata_backfill import (
    MetadataBackfillPlan,
    MetadataBackfillResult,
    backfill_document_metadata,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

PAGE_SIZE = 50


class Command(BaseCommand):
    help = (
        "Promote FRBRname / FRBRdate into editor metadata claims when the winning "
        "document-source claim is stale relative to the body, and the body does not "
        "match the latest submission/restore version."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist editor claims. Without this flag the command only reports planned changes.",
        )
        parser.add_argument(
            "--uri",
            action="append",
            dest="uris",
            default=[],
            help="Limit to one or more document URIs. May be repeated.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after considering this many documents.",
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=PAGE_SIZE,
            help=f"Search page size when scanning all documents (default {PAGE_SIZE}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = not bool(options["apply"])
        uris = [DocumentURIString(uri) for uri in options["uris"]]
        limit = options["limit"]
        page_size = options["page_size"]

        if page_size < 1:
            page_size_error = "--page-size must be at least 1"
            raise CommandError(page_size_error)
        if limit is not None and limit < 1:
            limit_error = "--limit must be at least 1"
            raise CommandError(limit_error)

        mode = "DRY-RUN" if dry_run else "APPLY"
        self.stdout.write(f"Backfilling body metadata claims ({mode})")

        considered = 0
        changed = 0
        applied = 0
        skipped = 0
        failed = 0

        for document_uri in self._iter_document_uris(uris=uris, page_size=page_size, limit=limit):
            considered += 1
            result = self._backfill_uri(document_uri, dry_run=dry_run)
            self._write_result(result)

            if result.error:
                failed += 1
            elif result.planned.has_changes:
                changed += 1
                if result.applied:
                    applied += 1
            else:
                skipped += 1

        self.stdout.write(
            f"Done. considered={considered} changed={changed} applied={applied} skipped={skipped} failed={failed}",
        )

    def _iter_document_uris(
        self,
        *,
        uris: list[DocumentURIString],
        page_size: int,
        limit: int | None,
    ) -> Iterator[DocumentURIString]:
        if uris:
            yield from uris
            return

        page = 1
        yielded = 0
        while True:
            response = search_and_parse_response(
                api_client,
                SearchParameters(
                    page=page,
                    page_size=page_size,
                    show_unpublished=True,
                    # Avoid date order: MarkLogic drops undated documents from that sort.
                    order="-updated",
                ),
            )
            if not response.results:
                break

            for result in response.results:
                yield result.uri
                yielded += 1
                if limit is not None and yielded >= limit:
                    return

            if page * page_size >= response.total:
                break
            page += 1

    def _backfill_uri(self, document_uri: DocumentURIString, *, dry_run: bool) -> MetadataBackfillResult:
        empty_plan = MetadataBackfillPlan()
        try:
            document = api_client.get_document_by_uri(document_uri)
            return backfill_document_metadata(document, dry_run=dry_run)
        except MarklogicCheckoutConflictError:
            return MetadataBackfillResult(
                uri=str(document_uri),
                planned=empty_plan,
                error="already checked out",
            )
        except Exception as exc:  # noqa: BLE001 - keep scanning when one document fails
            return MetadataBackfillResult(
                uri=str(document_uri),
                planned=empty_plan,
                error=str(exc),
            )

    def _write_result(self, result: MetadataBackfillResult) -> None:
        if result.error:
            self.stderr.write(f"{result.uri}: ERROR {result.error}")
            return
        if not result.planned.has_changes:
            self.stdout.write(f"{result.uri}: skipped ({result.skipped_reason})")
            return
        status = "applied" if result.applied else "planned"
        detail = "; ".join(result.notes)
        self.stdout.write(f"{result.uri}: {status} ({detail})")
