from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestStats(TestCase):
    def test_stats_view(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(reverse("stats"))

        decoded_response = response.content.decode("utf-8")
        assert "Stats" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.stats.api_client")
    def test_combined_csv_download(self, mock_api_client):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        mock_api_client.get_combined_stats_table.return_value = [
            ["Column 1", "Column 2", "Column 3", "Column 4"],
            ["Value 1", "Value 2", None, 7],
        ]

        response = self.client.get(reverse("stats_combined_csv"))

        decoded_response = response.content.decode("utf-8")

        assert response.status_code == 200
        assert decoded_response == "Column 1,Column 2,Column 3,Column 4\r\nValue 1,Value 2,,7\r\n"
