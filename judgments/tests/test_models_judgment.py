import datetime
from unittest.mock import ANY, Mock, patch

import pytest
from caselawclient.Client import MarklogicApiClient

from judgments.models import Judgment


@pytest.fixture
def mock_api_client():
    return Mock(spec=MarklogicApiClient)


class TestJudgment:
    @patch("judgments.models.MarklogicApiClient")
    def test_judgment_uses_default_api_client(self, mock_api_client_class):
        Judgment("test/1234")

        mock_api_client_class.assert_called_once_with(
            host=ANY, username=ANY, password=ANY, use_https=ANY
        )

    @patch("judgments.models.MarklogicApiClient")
    def test_judgment_doesnt_use_default_api_client_if_provided(
        self, mock_api_client_class, mock_api_client
    ):
        Judgment("test/1234", mock_api_client)

        mock_api_client_class.assert_not_called()

    def test_public_uri(self, mock_api_client):
        mock_api_client.get_judgment_citation.return_value = "2023/test/1234"

        judgment = Judgment("test/1234", mock_api_client)

        assert (
            judgment.public_uri == "https://caselaw.nationalarchives.gov.uk/test/1234"
        )

    def test_judgment_neutral_citation(self, mock_api_client):
        mock_api_client.get_judgment_citation.return_value = "2023/test/1234"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.neutral_citation == "2023/test/1234"
        mock_api_client.get_judgment_citation.assert_called_once_with("test/1234")

    def test_judgment_name(self, mock_api_client):
        mock_api_client.get_judgment_name.return_value = (
            "Test Judgment v Test Judgement"
        )

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.name == "Test Judgment v Test Judgement"
        mock_api_client.get_judgment_name.assert_called_once_with("test/1234")

    def test_judgment_court(self, mock_api_client):
        mock_api_client.get_judgment_court.return_value = "Court of Testing"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.court == "Court of Testing"
        mock_api_client.get_judgment_court.assert_called_once_with("test/1234")

    def test_judgment_date_as_string(self, mock_api_client):
        mock_api_client.get_judgment_work_date.return_value = "2023-02-03"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.judgment_date_as_string == "2023-02-03"
        assert judgment.judgment_date_as_date == datetime.date(2023, 2, 3)
        mock_api_client.get_judgment_work_date.assert_called_once_with("test/1234")

    def test_judgment_is_published(self, mock_api_client):
        mock_api_client.get_published.return_value = True

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.is_published is True
        mock_api_client.get_published.assert_called_once_with("test/1234")

    def test_judgment_is_sensitive(self, mock_api_client):
        mock_api_client.get_sensitive.return_value = True

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.is_sensitive is True
        mock_api_client.get_sensitive.assert_called_once_with("test/1234")

    def test_judgment_is_anonymised(self, mock_api_client):
        mock_api_client.get_anonymised.return_value = True

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.is_anonymised is True
        mock_api_client.get_anonymised.assert_called_once_with("test/1234")

    def test_judgment_has_supplementary_materials(self, mock_api_client):
        mock_api_client.get_supplemental.return_value = True

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.has_supplementary_materials is True
        mock_api_client.get_supplemental.assert_called_once_with("test/1234")

    def test_judgment_source_name(self, mock_api_client):
        mock_api_client.get_property.return_value = "Test Name"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.source_name == "Test Name"
        mock_api_client.get_property.assert_called_once_with("test/1234", "source-name")

    def test_judgment_source_email(self, mock_api_client):
        mock_api_client.get_property.return_value = "testemail@example.com"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.source_email == "testemail@example.com"
        mock_api_client.get_property.assert_called_once_with(
            "test/1234", "source-email"
        )

    def test_judgment_consignment_reference(self, mock_api_client):
        mock_api_client.get_property.return_value = "TDR-2023-ABC"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.consignment_reference == "TDR-2023-ABC"
        mock_api_client.get_property.assert_called_once_with(
            "test/1234", "transfer-consignment-reference"
        )

    @patch("judgments.models.generate_docx_url")
    def test_judgment_docx_url(self, mock_url_generator, mock_api_client):
        mock_url_generator.return_value = "https://example.com/mock.docx"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.docx_url == "https://example.com/mock.docx"
        mock_url_generator.assert_called_once

    @patch("judgments.models.generate_pdf_url")
    def test_judgment_pdf_url(self, mock_url_generator, mock_api_client):
        mock_url_generator.return_value = "https://example.com/mock.pdf"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.pdf_url == "https://example.com/mock.pdf"
        mock_url_generator.assert_called_once

    def test_judgment_xml_url(self, mock_api_client):
        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.xml_url == "/xml?judgment_uri=test/1234"

    def test_judgment_assigned_to(self, mock_api_client):
        mock_api_client.get_property.return_value = "testuser"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.assigned_to == "testuser"
        mock_api_client.get_property.assert_called_once_with("test/1234", "assigned-to")

    def test_judgment_content_as_xml(self, mock_api_client):
        mock_api_client.get_judgment_xml.return_value = "<xml></xml>"

        judgment = Judgment("test/1234", mock_api_client)

        assert judgment.content_as_xml() == "<xml></xml>"
        mock_api_client.get_judgment_xml.assert_called_once_with(
            "test/1234", show_unpublished=True
        )

    def test_judgment_is_failure(self, mock_api_client):
        successful_judgment = Judgment("test/1234", mock_api_client)
        failing_judgment = Judgment("failures/test/1234", mock_api_client)

        assert successful_judgment.is_failure is False
        assert failing_judgment.is_failure is True
