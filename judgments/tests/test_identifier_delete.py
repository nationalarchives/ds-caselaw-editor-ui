from unittest.mock import patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase


class TestDeleteIdentifierView(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_delete_identifier_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(uuid="id-1234", value="[2025] UKSC 123"),
            ],
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get("/d-a1b2c3/identifiers/id-1234/delete")

        assert response.status_code == 200

        self.assertContains(response, "Test v Tested", html=True)

        self.assertContains(
            response,
            "You're about to delete a <b>Neutral Citation Number</b> with value <b>[2025] UKSC 123</b>.",
            html=True,
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_delete_identifier_view_when_document_previously_published(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(uuid="id-1234", value="[2025] UKSC 123"),
            ],
            has_ever_been_published=True,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get("/d-a1b2c3/identifiers/id-1234/delete")

        self.assertContains(
            response,
            "Document d-a1b2c3 has previously been published; identifiers cannot be deleted.",
            html=True,
            status_code=403,
        )

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_delete_identifier_view_when_identifier_not_in_document(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(uuid="id-1234", value="[2025] UKSC 123"),
            ],
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        response = self.client.get("/d-a1b2c3/identifiers/id-5678/delete")

        assert response.status_code == 404


class TestDeleteIdentifierForm(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_delete_identifier_form(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(uuid="id-1234", value="[2025] UKSC 123"),
            ],
        )

        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        with patch.object(judgment, "save_identifiers") as patched_save:
            self.client.post("/d-a1b2c3/identifiers/id-1234/delete", data={})

            assert judgment.identifiers == {}
            patched_save.assert_called()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_delete_identifier_form_when_document_previously_published(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(uuid="id-1234", value="[2025] UKSC 123"),
            ],
            has_ever_been_published=True,
        )

        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        with patch.object(judgment, "save_identifiers") as patched_save:
            response = self.client.post("/d-a1b2c3/identifiers/id-1234/delete", data={})

            assert response.status_code == 403
            patched_save.assert_not_called()

    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_delete_identifier_form_when_identifier_not_in_document(
        self,
        document_type,
        document_exists,
        mock_judgment,
    ):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(uuid="id-1234", value="[2025] UKSC 123"),
            ],
        )

        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        with patch.object(judgment, "save_identifiers") as patched_save:
            response = self.client.post("/d-a1b2c3/identifiers/id-5678/delete", data={})

            assert response.status_code == 404
            patched_save.assert_not_called()
