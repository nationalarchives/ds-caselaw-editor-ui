from unittest.mock import Mock, call, patch

from django.core.management import call_command
from django.test import TestCase


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

        document_1 = Mock()
        document_2 = Mock()

        mock_api_client.get_document_by_uri.side_effect = [document_1, document_2]

        call_command("enrich_next_in_reenrichment_queue")

        mock_api_client.get_document_by_uri.assert_has_calls(
            [call("test/123"), call("test/456")],
        )

        document_1.enrich.assert_called_once()
        document_2.enrich.assert_called_once()

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

        document_1 = Mock()
        document_2 = Mock()

        mock_api_client.get_document_by_uri.side_effect = [document_1, document_2]

        call_command("enrich_next_in_reenrichment_queue")

        mock_api_client.get_document_by_uri.assert_has_calls([call("test/123")])

        document_1.enrich.assert_called_once()
        document_2.enrich.assert_not_called()
