from unittest.mock import ANY, patch

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

    @patch("judgments.views.stub.create_rendered_stub", return_value="<xml>")
    def test_judgment_stub_post(self, mock_render_stub):
        superuser = User.objects.create_superuser(username="clark")
        self.client.force_login(superuser)
        _response = self.client.post(
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
        mock_render_stub.assert_called_with(
            {
                "decision_date": "2024-01-01",
                "transform_datetime": ANY,
                "court_code_upper": "UKSC",
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

        # date has a T in the right place and is long enough to have seconds
        transform = mock_render_stub.call_args.args[0]["transform_datetime"]
        assert transform[10] == "T"
        assert len(transform) == 19
