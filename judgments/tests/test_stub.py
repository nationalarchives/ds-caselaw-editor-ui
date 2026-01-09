from pathlib import Path
from unittest.mock import ANY, patch

from caselawclient.Client import ROOT_DIR
from caselawclient.models.judgments import Judgment
from defusedxml import ElementTree
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase

from judgments.views.stub import ANNOTATION

post_data = {
    "decision_date": "2024-01-01",
    "court_code": "UkSc",
    "title": "A title",
    "year": "2024",
    "case_numbers": "ABC123\nDEF123",
    "claimants": "Amy\nBarry",
    "respondents": "Cathy\nDarren",
    "appellants": "Emily\nFred",
    "defendants": "Gertrude",
}

formatted_data = {
    "decision_date": "2024-01-01",
    "transform_datetime": ANY,
    "court_code": "UKSC",
    "title": "A title",
    "year": "2024",
    "case_numbers": ["ABC123", "DEF123"],
    "parties": [
        {"role": "Claimant", "name": "Amy"},
        {"role": "Claimant", "name": "Barry"},
        {"role": "Respondent", "name": "Cathy"},
        {"role": "Respondent", "name": "Darren"},
        {"role": "Appellant", "name": "Emily"},
        {"role": "Appellant", "name": "Fred"},
        {"role": "Defendant", "name": "Gertrude"},
    ],
}


class TestStubView(TestCase):
    def test_judgment_stub_view(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/stub")
        decoded_response = response.content.decode("utf-8")
        assert "I want to create a stub:" in decoded_response
        assert "Case numbers" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.stub.uuid4", return_value="uuid")
    @patch("judgments.views.stub.render_stub_xml")
    @patch("judgments.views.stub.api_client.insert_document_xml")
    def test_judgment_stub_post(self, mock_insert_xml, mock_render_stub, mock_uuid):
        judgment_template_path = Path(ROOT_DIR) / "models" / "documents" / "templates" / "judgment.xml"
        with (judgment_template_path).open("r") as f:
            template = f.read()
        mock_render_stub.return_value = template
        superuser = User.objects.create_superuser(username="clark")
        self.client.force_login(superuser)
        _response = self.client.post(
            "/create_stub",
            post_data,
        )
        mock_render_stub.assert_called_with(
            formatted_data,
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

        document_xml_bytes = ElementTree.tostring(mock_insert_xml.call_args.kwargs["document_xml"])

        assert b"ns0" not in document_xml_bytes
        assert b"<uk:" in document_xml_bytes
        assert b"<akomaNtoso " in document_xml_bytes

    @patch("judgments.views.stub.uuid4", return_value="uuid")
    @patch("judgments.views.stub.render_stub_xml", return_value="<xml />")
    @patch("judgments.views.stub.api_client.insert_document_xml")
    def test_judgment_stub_post_invalid_court(self, mock_insert_xml, mock_render_stub, mock_uuid):
        superuser = User.objects.create_superuser(username="clark")
        self.client.force_login(superuser)
        modified_post_data = dict(**post_data)
        modified_post_data["court_code"] = "not_a_court_code"
        response = self.client.post(
            "/create_stub",
            modified_post_data,
        )
        mock_render_stub.assert_not_called()
        mock_insert_xml.assert_not_called()
        messages = list(get_messages(response.wsgi_request))
        assert "Court code not_a_court_code" in messages[0].message
