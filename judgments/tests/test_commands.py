from unittest.mock import Mock, call, patch

from caselawclient.errors import MarklogicCheckoutConflictError
from django.core.management import call_command
from django.test import TestCase
from editing import editing_order, record, tracking_editing_session

from judgments.models import BulkReparseRunLog
from judgments.models.telemetry import RunStatus

checkout_conflict_message = "already checked out"


def checked_out_session():
    raise MarklogicCheckoutConflictError(checkout_conflict_message)


class CommandsTestCase(TestCase):
    @patch("judgments.management.commands.enrich_next_in_reenrichment_queue.api_client")
    @patch(
        "judgments.management.commands.enrich_next_in_reenrichment_queue.NUMBER_TO_ENRICH",
        2,
    )
    def test_enrich_next_in_reenrichment_queue(self, mock_api_client):
        mock_api_client.get_pending_enrichment_for_version.return_value = [
            ["uri", "enrich_version_string", "minutes_since_enrichment_request"],
            ["/test/123.xml", "1.2.3", 45],
            ["/test/456.xml", None, None],
        ]

        order_1 = editing_order()
        order_2 = editing_order()
        document_1 = Mock()
        document_2 = Mock()
        document_1.editing_session = tracking_editing_session(order_1)
        document_2.editing_session = tracking_editing_session(order_2)
        document_1.enrich.side_effect = record(order_1, "enrich")
        document_2.enrich.side_effect = record(order_2, "enrich")

        mock_api_client.get_document_by_uri.side_effect = [document_1, document_2]

        call_command("enrich_next_in_reenrichment_queue")

        mock_api_client.get_document_by_uri.assert_has_calls(
            [call("test/123"), call("test/456")],
        )

        assert order_1 == ["editing_session", "enrich", "editing_session_end"]
        assert order_2 == ["editing_session", "enrich", "editing_session_end"]

    @patch("judgments.management.commands.enrich_next_in_reenrichment_queue.api_client")
    @patch(
        "judgments.management.commands.enrich_next_in_reenrichment_queue.NUMBER_TO_ENRICH",
        1,
    )
    def test_enrich_next_in_reenrichment_queue_with_limit(self, mock_api_client):
        mock_api_client.get_pending_enrichment_for_version.return_value = [
            ["uri", "enrich_version_string", "minutes_since_enrichment_request"],
            ["/test/123.xml", "1.2.3", 45],
            ["/test/456.xml", None, None],
        ]

        order_1 = editing_order()
        order_2 = editing_order()
        document_1 = Mock()
        document_2 = Mock()
        document_1.editing_session = tracking_editing_session(order_1)
        document_2.editing_session = tracking_editing_session(order_2)
        document_1.enrich.side_effect = record(order_1, "enrich")
        document_2.enrich.side_effect = record(order_2, "enrich")

        mock_api_client.get_document_by_uri.side_effect = [document_1, document_2]

        call_command("enrich_next_in_reenrichment_queue")

        mock_api_client.get_document_by_uri.assert_has_calls([call("test/123")])

        assert order_1 == ["editing_session", "enrich", "editing_session_end"]
        assert order_2 == []

    @patch("judgments.management.commands.enrich_next_in_reenrichment_queue.time.sleep")
    @patch("judgments.management.commands.enrich_next_in_reenrichment_queue.api_client")
    @patch(
        "judgments.management.commands.enrich_next_in_reenrichment_queue.NUMBER_TO_ENRICH",
        2,
    )
    def test_enrich_skips_a_checked_out_document_and_continues(self, mock_api_client, mock_sleep):
        mock_api_client.get_pending_enrichment_for_version.return_value = [
            ["uri", "enrich_version_string", "minutes_since_enrichment_request"],
            ["/test/123.xml", "1.2.3", 45],
            ["/test/456.xml", None, None],
        ]

        order_2 = editing_order()
        document_1 = Mock()
        document_2 = Mock()
        document_1.editing_session = checked_out_session
        document_2.editing_session = tracking_editing_session(order_2)
        document_2.enrich.side_effect = record(order_2, "enrich")

        mock_api_client.get_document_by_uri.side_effect = [document_1, document_2]

        call_command("enrich_next_in_reenrichment_queue")

        mock_api_client.get_document_by_uri.assert_has_calls(
            [call("test/123"), call("test/456")],
        )
        assert order_2 == ["editing_session", "enrich", "editing_session_end"]
        mock_sleep.assert_called()

    @patch("judgments.management.commands.reparse_next_in_reparse_queue.time.sleep")
    @patch("judgments.management.commands.reparse_next_in_reparse_queue.api_client")
    def test_reparse_records_a_checkout_conflict_and_continues(self, mock_api_client, mock_sleep):
        mock_api_client.get_highest_parser_version.return_value = (1, 2)
        mock_api_client.get_count_pending_parse_for_version.return_value = 2
        mock_api_client.get_documents_pending_parse_for_version.return_value = [
            ["uri"],
            ["/busy.xml"],
            ["/ready.xml"],
        ]

        order = editing_order()
        busy = Mock()
        ready = Mock()
        busy.editing_session = checked_out_session
        ready.editing_session = tracking_editing_session(order)
        ready.reparse.side_effect = record(order, "reparse", result=True)
        mock_api_client.get_document_by_uri.side_effect = [busy, ready]

        call_command("reparse_next_in_reparse_queue", max_try=2, max_parse=8)

        run_log = BulkReparseRunLog.objects.get()
        assert run_log.status == RunStatus.FINISHED
        assert run_log.documents_failed == 1
        assert run_log.documents_attempted == 1
        assert order == ["editing_session", "reparse", "editing_session_end"]
        mock_sleep.assert_called()

    @patch("judgments.management.commands.assign_missing_fclids.api_client")
    def test_assign_fclids_skips_a_checked_out_document_and_stops(self, mock_api_client):
        busy = Mock()
        ready = Mock()
        busy.editing_session = checked_out_session
        order = editing_order()
        ready.editing_session = tracking_editing_session(order)
        fclid = Mock()
        fclid.value = "fclid-1"
        ready.assign_fclid_if_missing.side_effect = record(order, "assign_fclid", result=fclid)

        mock_api_client.get_missing_fclid.side_effect = [
            ["/busy.xml", "/ready.xml"],
            ["/busy.xml"],
            ["/busy.xml"],
        ]
        mock_api_client.get_document_by_uri.side_effect = [busy, ready, busy]

        call_command("assign_missing_fclids")

        assert mock_api_client.get_missing_fclid.call_count == 2
        assert order == ["editing_session", "assign_fclid", "editing_session_end"]
