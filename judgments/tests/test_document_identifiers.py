from unittest.mock import patch

from caselawclient.factories import DocumentBodyFactory, JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.identifiers.fclid import FindCaseLawIdentifier
from caselawclient.models.identifiers.neutral_citation import NeutralCitationNumber
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_flag


class TestDocumentIdentifiers(TestCase):
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_document_identifiers_view(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(value="[2025] UKSC 123", deprecated=True),
                FindCaseLawIdentifier(value="tn4t35ts"),
            ],
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        identifiers_uri = reverse("document-identifiers", kwargs={"document_uri": judgment.uri})

        assert identifiers_uri == "/d-a1b2c3/identifiers"

        response = self.client.get(identifiers_uri)

        assert response.status_code == 200

        self.assertContains(response, "Test v Tested", html=True)

        self.assertContains(
            response,
            """<tr>
            <td>Neutral Citation Number</td>
            <td><code>[2025] UKSC 123</code></td>
            <td><code>/uksc/2025/123</code></td>
            <td>True</td>
            </tr>""",
            html=True,
        )

        self.assertContains(
            response,
            """<tr>
            <td>Find Case Law Identifier</td>
            <td><code>tn4t35ts</code></td>
            <td><code>/tna.tn4t35ts</code></td>
            <td>False</td>
            </tr>""",
            html=True,
        )


class TestIdentifierViewDeleteDisablement(TestCase):
    @override_flag("identifier_editing", active=True)
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_identifier_view_delete_disablement_unpublished(self, document_type, document_exists, mock_judgment):
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

        identifiers_uri = reverse("document-identifiers", kwargs={"document_uri": judgment.uri})

        assert identifiers_uri == "/d-a1b2c3/identifiers"

        response = self.client.get(identifiers_uri)

        assert response.status_code == 200

        self.assertContains(response, "Test v Tested", html=True)

        self.assertContains(
            response,
            """<tr>
            <td>Neutral Citation Number</td>
            <td><code>[2025] UKSC 123</code></td>
            <td><code>/uksc/2025/123</code></td>
            <td>False</td>
            <td><a href="/d-a1b2c3/identifiers/id-1234/delete" class="button-danger button-small">Delete</a></td>
            </tr>""",
            html=True,
        )

    @override_flag("identifier_editing", active=True)
    @patch("judgments.utils.view_helpers.get_document_by_uri_or_404")
    @patch("judgments.utils.api_client.document_exists")
    @patch("judgments.utils.api_client.get_document_type_from_uri")
    def test_identifier_view_delete_disablement_published(self, document_type, document_exists, mock_judgment):
        document_type.return_value = Judgment
        document_exists.return_value = None

        judgment = JudgmentFactory.build(
            uri=DocumentURIString("d-a1b2c3"),
            body=DocumentBodyFactory.build(name="Test v Tested"),
            identifiers=[
                NeutralCitationNumber(uuid="id-1234", value="[2025] UKSC 123"),
                FindCaseLawIdentifier(uuid="id-5678", value="tn4t35ts"),
            ],
            has_ever_been_published=True,
        )
        mock_judgment.return_value = judgment

        self.client.force_login(User.objects.get_or_create(username="testuser")[0])

        identifiers_uri = reverse("document-identifiers", kwargs={"document_uri": judgment.uri})

        assert identifiers_uri == "/d-a1b2c3/identifiers"

        response = self.client.get(identifiers_uri)

        assert response.status_code == 200

        self.assertContains(response, "Test v Tested", html=True)

        self.assertContains(
            response,
            """<tr>
            <td>Neutral Citation Number</td>
            <td><code>[2025] UKSC 123</code></td>
            <td><code>/uksc/2025/123</code></td>
            <td>False</td>
            <td><a class="button-danger button-small" disabled aria-disabled="true">Delete</a></td>
            </tr>""",
            html=True,
        )

        self.assertContains(
            response,
            """<tr>
            <td>Find Case Law Identifier</td>
            <td><code>tn4t35ts</code></td>
            <td><code>/tna.tn4t35ts</code></td>
            <td>False</td>
            <td><a class="button-danger button-small" disabled aria-disabled="true">Delete</a></td>
            </tr>""",
            html=True,
        )
