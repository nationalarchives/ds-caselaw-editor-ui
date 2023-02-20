from unittest.mock import patch

from django.test import TestCase

from judgments.models import Judgment


class TestJudgment(TestCase):
    @patch("judgments.models.api_client")
    def test_judgment_neutral_citation(self, mock_api_client):
        mock_api_client.get_judgment_citation.return_value = "2023/test/1234"

        judgment = Judgment("test/1234")

        assert judgment.neutral_citation == "2023/test/1234"
        mock_api_client.get_judgment_citation.assert_called_once_with("test/1234")

    @patch("judgments.models.api_client")
    def test_judgment_name(self, mock_api_client):
        mock_api_client.get_judgment_name.return_value = (
            "Test Judgment v Test Judgement"
        )

        judgment = Judgment("test/1234")

        assert judgment.name == "Test Judgment v Test Judgement"
        mock_api_client.get_judgment_name.assert_called_once_with("test/1234")

    @patch("judgments.models.api_client")
    def test_judgment_court(self, mock_api_client):
        mock_api_client.get_judgment_court.return_value = "Court of Testing"

        judgment = Judgment("test/1234")

        assert judgment.court == "Court of Testing"
        mock_api_client.get_judgment_court.assert_called_once_with("test/1234")

    @patch("judgments.models.api_client")
    def test_judgment_is_published(self, mock_api_client):
        mock_api_client.get_published.return_value = True

        judgment = Judgment("test/1234")

        assert judgment.is_published is True
        mock_api_client.get_published.assert_called_once_with("test/1234")

    @patch("judgments.models.api_client")
    def test_judgment_is_sensitive(self, mock_api_client):
        mock_api_client.get_sensitive.return_value = True

        judgment = Judgment("test/1234")

        assert judgment.is_sensitive is True
        mock_api_client.get_sensitive.assert_called_once_with("test/1234")

    @patch("judgments.models.api_client")
    def test_judgment_is_anonymised(self, mock_api_client):
        mock_api_client.get_anonymised.return_value = True

        judgment = Judgment("test/1234")

        assert judgment.is_anonymised is True
        mock_api_client.get_anonymised.assert_called_once_with("test/1234")

    @patch("judgments.models.api_client")
    def test_judgment_has_supplementary_materials(self, mock_api_client):
        mock_api_client.get_supplemental.return_value = True

        judgment = Judgment("test/1234")

        assert judgment.has_supplementary_materials is True
        mock_api_client.get_supplemental.assert_called_once_with("test/1234")
