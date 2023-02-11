from unittest.mock import patch

from django.test import TestCase

from judgments.models import Judgment


class TestJudgment(TestCase):
    @patch("judgments.models.api_client")
    def test_judgment_name(self, mock_api_client):
        mock_api_client.get_judgment_name.return_value = (
            "Test Judgment v Test Judgement"
        )

        judgment = Judgment("x")

        assert judgment.name == "Test Judgment v Test Judgement"
