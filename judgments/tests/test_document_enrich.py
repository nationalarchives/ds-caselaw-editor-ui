from unittest.mock import Mock, patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from editing import editing_order, record, tracking_editing_session
from factories import make_editor


class TestDocumentEnrich(TestCase):
    def setUp(self):
        self.user = make_editor("user")

    @patch("judgments.views.enrich.get_document_by_uri_or_404")
    def test_document_enrich_failure(self, mock_document):
        order = editing_order()
        document = Mock()
        document.uri = "a uri"
        document.body.name = "Example"
        document.editing_session = tracking_editing_session(order)
        document.enrich.side_effect = record(order, "enrich", result=False)
        mock_document.return_value = document

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("enrich"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": document.uri},
        )
        assert order == ["editing_session", "enrich", "editing_session_end"]

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert str(messages[0]) == "Enrichment request failed for Example."

    @patch("judgments.views.enrich.get_document_by_uri_or_404")
    def test_document_enrich_success(self, mock_document):
        order = editing_order()
        document = Mock()
        document.uri = "a uri"
        document.body.name = "Example"
        document.editing_session = tracking_editing_session(order)
        document.enrich.side_effect = record(order, "enrich", result=True)
        mock_document.return_value = document

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("enrich"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": document.uri},
        )
        assert order == ["editing_session", "enrich", "editing_session_end"]

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert str(messages[0]) == "Enrichment requested for Example."
