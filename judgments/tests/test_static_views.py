from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestStaticViews(TestCase):
    def test_labs_view(self):
        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get(reverse("labs"))

        decoded_response = response.content.decode("utf-8")
        self.assertIn("Labs", decoded_response)
        assert response.status_code == 200
