from django.contrib.auth.models import User
from django.test import TestCase


class TestStyleGuide(TestCase):
    def test_style_guide_view(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get("/style-guide")

        assert response.status_code == 200
        decoded_response = response.content.decode("utf-8")
        assert "style guide" in decoded_response
        assert "Components" in decoded_response
        assert "Buttons" in decoded_response
        assert "Note" in decoded_response
        assert "Notification messaging" in decoded_response
        assert "Summary panels" in decoded_response
        assert "Tabs" in decoded_response
        assert "Spacing" in decoded_response
        assert "Typography" in decoded_response
        assert "Font family" in decoded_response
        assert "Font sizes" in decoded_response
        assert "Font weights" in decoded_response
        assert "Line heights" in decoded_response
