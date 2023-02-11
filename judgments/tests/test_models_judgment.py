from unittest.mock import patch

from django.test import TestCase

from judgments.models import Judgment


class TestJudgment(TestCase):
    @patch("judgments.models.api_client")
    def test_judgment_neutral_citation(self, mock_api_client):
        mock_api_client.get_judgment_citation.return_value = "2023/test/1234"

        judgment = Judgment("x")

        assert judgment.neutral_citation == "2023/test/1234"

    @patch("judgments.models.api_client")
    def test_judgment_name(self, mock_api_client):
        mock_api_client.get_judgment_name.return_value = (
            "Test Judgment v Test Judgement"
        )

        judgment = Judgment("x")

        assert judgment.name == "Test Judgment v Test Judgement"
