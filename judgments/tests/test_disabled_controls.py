from unittest.mock import patch

import pytest
from caselawclient.factories import JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from caselawclient.models.judgments import Judgment
from django.contrib.auth.models import User
from factories import make_editor

from judgments.utils.permissions import editors_only_hint

ACTION_PAGES = [
    "/pubtest/4321/123/publish",
    "/pubtest/4321/123/unpublish",
    "/pubtest/4321/123/hold",
    "/pubtest/4321/123/unhold",
    "/pubtest/4321/123/delete",
    "/pubtest/4321/123/upload",
    "/pubtest/4321/123/identifiers/add",
    "/pubtest/4321/123/metadata",
    "/stub",
]


@pytest.fixture
def document_pages():
    judgment = JudgmentFactory.build(uri=DocumentURIString("pubtest/4321/123"))
    with (
        patch("judgments.utils.view_helpers.get_document_by_uri_or_404", return_value=judgment),
        patch("judgments.utils.api_client.document_exists", return_value=None),
        patch("judgments.utils.api_client.get_document_type_from_uri", return_value=Judgment),
        patch("caselawclient.models.documents.are_unpublished_assets_clean", return_value=True),
    ):
        yield


@pytest.mark.django_db
@pytest.mark.usefixtures("document_pages")
@pytest.mark.parametrize("page", ACTION_PAGES)
def test_action_pages_are_viewable_but_disabled_for_non_editors(client, page):
    client.force_login(User.objects.create(username="standard"))

    response = client.get(page)

    assert response.status_code == 200
    assert f'title="{editors_only_hint()}"' in response.content.decode()


@pytest.mark.django_db
@pytest.mark.usefixtures("document_pages")
@pytest.mark.parametrize("page", ACTION_PAGES)
def test_action_pages_are_not_disabled_for_editors(client, page):
    client.force_login(make_editor())

    response = client.get(page)

    assert response.status_code == 200
    assert f'title="{editors_only_hint()}"' not in response.content.decode()
