from unittest.mock import Mock, patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from editing import editing_order, record, tracking_editing_session


class TestDocumentDelete(TestCase):
    def setUp(self):
        editor_group = Group(name="Editors")
        editor_group.save()
        self.editor_user = User.objects.get_or_create(username="ed")[0]
        self.editor_user.groups.add(editor_group)
        self.editor_user.save()
        self.standard_user = User.objects.get_or_create(username="alice")[0]
        self.super_user = User.objects.create_superuser(username="clark")

    @patch("judgments.views.delete.invalidate_caches")
    @patch("judgments.views.delete.get_document_by_uri_or_404")
    def test_document_delete_flow_if_safe(self, mock_document, mock_invalidate_caches):
        order = editing_order()
        document = Mock()
        document.safe_to_delete = True
        document.uri = "d-a1b2c3"
        document.editing_session = tracking_editing_session(order)
        document.delete.side_effect = record(order, "delete")
        mock_document.return_value = document

        self.client.force_login(self.editor_user)

        response = self.client.post(
            reverse("delete"),
            data={
                "judgment_uri": document.uri,
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse("home")

        assert order == ["editing_session", "delete", "editing_session_end"]
        mock_invalidate_caches.assert_called_once()

    @patch("judgments.views.delete.invalidate_caches")
    @patch("judgments.views.delete.get_document_by_uri_or_404")
    def test_document_delete_flow_if_not_editor(
        self,
        mock_document,
        mock_invalidate_caches,
    ):
        document = Mock()
        mock_document.return_value = document

        self.client.force_login(self.standard_user)

        response = self.client.post(
            reverse("delete"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 403
        mock_document.return_value.delete.assert_not_called()
        mock_invalidate_caches.assert_not_called()

    @patch("judgments.views.delete.invalidate_caches")
    @patch("judgments.views.delete.get_document_by_uri_or_404")
    def test_document_delete_flow_if_not_safe(
        self,
        mock_document,
        mock_invalidate_caches,
    ):
        order = editing_order()
        document = Mock()
        document.safe_to_delete = False
        document.editing_session = tracking_editing_session(order)
        mock_document.return_value = document

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.post(
            reverse("delete"),
            data={
                "document_uri": document.uri,
            },
        )

        assert response.status_code == 403
        assert order == []
        mock_document.return_value.delete.assert_not_called()
        mock_invalidate_caches.assert_not_called()
