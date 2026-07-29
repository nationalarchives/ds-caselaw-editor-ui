from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class TestToolsViews(TestCase):
    def setUp(self):
        developer_group = Group.objects.create(name="Developers")
        self.developer_user = User.objects.create(username="dev")
        self.developer_user.groups.add(developer_group)
        self.standard_user = User.objects.create(username="alice")

    def test_tools_index_ok_for_developer(self):
        self.client.force_login(self.developer_user)

        response = self.client.get(reverse("tools"))

        assert response.status_code == 200
        assert "Tools" in response.content.decode("utf-8")
        assert "Published documents missing FCLID" in response.content.decode("utf-8")

    def test_tools_index_forbidden_for_non_developer(self):
        self.client.force_login(self.standard_user)

        response = self.client.get(reverse("tools"))

        assert response.status_code == 403

    def test_tools_index_redirects_unauthenticated(self):
        response = self.client.get(reverse("tools"))

        assert response.status_code == 302
        assert "/accounts/login" in response["Location"]

    def test_missing_fclid_forbidden_for_non_developer(self):
        self.client.force_login(self.standard_user)

        response = self.client.get(reverse("tools_missing_fclid"))

        assert response.status_code == 403

    @patch("judgments.views.tools.api_client")
    def test_missing_fclid_ok_for_developer(self, mock_api_client):
        self.client.force_login(self.developer_user)
        mock_api_client.get_missing_fclid.return_value = ["/ewhc/kb/2025/1.xml"]

        response = self.client.get(reverse("tools_missing_fclid"))

        decoded_response = response.content.decode("utf-8")
        assert response.status_code == 200
        assert "Published documents missing FCLID" in decoded_response
        assert "ewhc/kb/2025/1" in decoded_response
        mock_api_client.get_missing_fclid.assert_called_once_with(maximum_records=200)
