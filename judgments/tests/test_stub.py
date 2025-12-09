from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase


class TestStubView(TestCase):
    def test_judgment_stub_view(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])
        response = self.client.get("/stub")
        decoded_response = response.content.decode("utf-8")
        assert "I want to create a stub:" in decoded_response
        assert "Case numbers:" in decoded_response
        assert response.status_code == 200

    @patch("judgments.views.stub.messages.success")
    def test_judgment_stub_post(self, mock_success):
        superuser = User.objects.create_superuser(username="clark")
        self.client.force_login(superuser)
        response = self.client.post(
            "/create_stub",
            {
                "decision_date": "2024-01-01",
                "court_code_upper": "UKSC",
                "title": "A title",
                "year": "2024",
                "case_numbers": "ABC123\nDEF123",
                "claimants": "Amy\nBarry",
                "respondants": "Cathy\nDarren",
            },
        )
        mock_success.assert_called_with("ham")
        return response
