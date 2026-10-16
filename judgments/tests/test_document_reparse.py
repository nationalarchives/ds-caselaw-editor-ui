from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from editing import editing_order, record, tracking_editing_session
from factories import make_editor


class TestDocumentReparse(TestCase):
    def setUp(self):
        self.user = make_editor("user")

    @patch("judgments.views.document_reparse.get_document_by_uri_or_404")
    def test_document_reparse_flow(self, mock_document):
        """Reparsing happens inside an editing session."""
        order = editing_order()
        document = Mock()
        document.uri = "test/4321/123"
        document.body.name = "Example"
        document.editing_session = tracking_editing_session(order)
        document.reparse.side_effect = record(order, "reparse")
        mock_document.return_value = document

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("reparse"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse(
            "full-text-html",
            kwargs={"document_uri": document.uri},
        )
        assert order == ["editing_session", "reparse", "editing_session_end"]
