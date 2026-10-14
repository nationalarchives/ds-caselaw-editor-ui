from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import Group, User

EDITOR_ONLY_ACTIONS = [
    "/publish",
    "/unpublish",
    "/hold",
    "/unhold",
    "/delete",
    "/upload",
    "/create_stub",
    "/d-a1b2c3/edit",
    "/d-a1b2c3/metadata",
    "/d-a1b2c3/identifiers/add",
    "/d-a1b2c3/identifiers/id-1234/delete",
]

EDITOR_OR_DEVELOPER_ACTIONS = ["/enrich", "/reparse", "/unlock"]


def make_user(kind):
    if kind == "superuser":
        return User.objects.create_superuser(username=kind)
    user = User.objects.create(username=kind)
    if kind != "standard":
        user.groups.add(Group.objects.get_or_create(name=f"{kind.capitalize()}s")[0])
    return user


@pytest.mark.django_db
@pytest.mark.parametrize("action", EDITOR_ONLY_ACTIONS)
@pytest.mark.parametrize("kind", ["standard", "developer", "superuser"])
def test_editor_only_actions_are_forbidden_to_non_editors(client, action, kind):
    client.force_login(make_user(kind))

    with patch("judgments.utils.view_helpers.get_document_by_uri_or_404"):
        response = client.post(action)

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("action", EDITOR_OR_DEVELOPER_ACTIONS)
@pytest.mark.parametrize("kind", ["standard", "superuser"])
def test_enrich_reparse_and_unlock_are_forbidden_to_others(client, action, kind):
    client.force_login(make_user(kind))

    response = client.post(action)

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("action", EDITOR_OR_DEVELOPER_ACTIONS)
def test_enrich_reparse_and_unlock_are_allowed_to_developers(client, action):
    client.force_login(make_user("developer"))

    document = Mock(uri="d-a1b2c3")

    with (
        patch("judgments.views.enrich.get_document_by_uri_or_404", return_value=document),
        patch("judgments.views.document_reparse.get_document_by_uri_or_404", return_value=document),
        patch("judgments.views.unlock.get_document_by_uri_or_404", return_value=document),
        patch("judgments.views.unlock.api_client"),
    ):
        response = client.post(action, {"document_uri": "d-a1b2c3", "judgment_uri": "d-a1b2c3"})

    assert response.status_code == 302
