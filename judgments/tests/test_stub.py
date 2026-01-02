from unittest.mock import ANY, patch

from caselawclient.models.judgments import Judgment
from defusedxml import ElementTree
from django.contrib.auth.models import User
from django.test import TestCase

from judgments.views.stub import ANNOTATION


class TestStubView(TestCase):
    def test_judgment_stub_view(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/stub")
        decoded_response = response.content.decode("utf-8")
        assert "I want to create a stub:" in decoded_response
        assert "Case numbers:" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.stub.uuid4", return_value="uuid")
    @patch("judgments.views.stub.render_stub_xml", return_value="<xml />")
    @patch("judgments.views.stub.api_client.insert_document_xml")
    def test_judgment_stub_post(self, mock_insert_xml, mock_render_stub, mock_uuid):
        superuser = User.objects.create_superuser(username="clark")
        self.client.force_login(superuser)
        _response = self.client.post(
            "/create_stub",
            {
                "decision_date": "2024-01-01",
                "court_code": "UkSc",
                "title": "A title",
                "year": "2024",
                "case_numbers": "ABC123\nDEF123",
                "claimants": "Amy\nBarry",
                "respondants": "Cathy\nDarren",
            },
        )
        mock_render_stub.assert_called_with(
            {
                "decision_date": "2024-01-01",
                "transform_datetime": ANY,
                "court_code": "UkSc",
                "title": "A title",
                "year": "2024",
                "case_numbers": ["ABC123", "DEF123"],
                "parties": [
                    {"role": "claimant", "name": "Amy"},
                    {"role": "claimant", "name": "Barry"},
                    {"role": "respondant", "name": "Cathy"},
                    {"role": "respondant", "name": "Darren"},
                ],
            },
        )

        # date has a T in the right place and is exactly long enough to have seconds
        transform = mock_render_stub.call_args.args[0]["transform_datetime"]
        assert transform[10] == "T"
        assert len(transform) == 19

        mock_insert_xml.assert_called_with(
            document_uri="d-uuid",
            document_xml=ANY,
            document_type=Judgment,
            annotation=ANNOTATION,
        )

        document_xml = mock_insert_xml.call_args.kwargs["document_xml"]
        assert ElementTree.tostring(document_xml) == b"<xml />"
