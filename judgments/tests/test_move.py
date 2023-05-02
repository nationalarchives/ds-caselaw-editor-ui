from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.http import Http404
from factories import JudgmentFactory


def get_mock_judgment(uri):
    if not uri:
        raise Http404("empty uri")
    if "bad" in uri or "666" in uri:
        raise Http404("deliberate test failure")
    if "good" in uri or "888" in uri:
        return JudgmentFactory.build(uri=uri)


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
def test_get_move(mock_judgment, client):
    "We can get a /move page for a judgment that exists"
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.get("/good/2099/888/move")
    assert response.status_code == 200
    assert b"New Neutral Citation" in response.content


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
def test_perform_move_invalid_target(mock_judgment, client):
    "There is an error if the neutral citation is invalid"
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.post("/good/2099/888/move", {"neutral_citation": "jam"})
    assert response.status_code == 200
    assert b"Unable to parse" in response.content


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
@patch("judgments.views.judgment_move.api_client")
@patch("judgments.views.judgment_move.update_judgment_uri")
def test_perform_move_present_target(
    mock_update, mock_api_client, mock_judgment, client
):
    "Given an existing target, we should redirect to overwrite"
    mock_api_client.judgment_exists.return_value = True
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.post("/good/2099/1/move", {"neutral_citation": "[2099] EAT 888"})
    mock_api_client.set_judgment_citation.assert_not_called()
    mock_update.assert_not_called()
    assert response.status_code == 302
    assert response.url == "/good/2099/1/overwrite?target=%5B2099%5D+EAT+888"
    overwrite_response = client.get(response.url)
    assert (
        b'<input type="hidden" name="neutral_citation" value="[2099] EAT 888" id="id_neutral_citation">'
        in overwrite_response.content
    )


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
@patch("judgments.views.judgment_move.api_client")
@patch("judgments.views.judgment_move.update_judgment_uri")
def test_perform_move_absent_target(
    mock_update, mock_api_client, mock_judgment, client
):
    "Given an absent target, we should move the judgment to the new location"
    mock_api_client.judgment_exists.return_value = False
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.post("/good/2099/1/move", {"neutral_citation": "[2099] EAT 888"})
    mock_update.assert_called_with("good/2099/1", "[2099] EAT 888")
    mock_api_client.set_judgment_citation.assert_called_with(
        "/eat/2099/888", "[2099] EAT 888"
    )
    assert response.status_code == 302
    assert response.url == "/eat/2099/888"


########################################


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
def test_get_overwrite(mock_judgment, client):
    "We can get an overwrite page if there's a target"
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.get("/good/2099/888/overwrite?target=[2023]+EWCA+Civ+888")
    assert response.status_code == 200
    assert (
        b'<input type="hidden" name="neutral_citation" value="[2023] EWCA Civ 888"'
        in response.content
    )


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
def test_get_overwrite_no_such_target(mock_judgment, client):
    "We do not get an overwrite page if there's no such target"
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.get("/good/2099/888/overwrite?target=[2023]+EWCA+Civ+666")
    assert response.status_code == 404


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
def test_get_overwrite_no_such_source(mock_judgment, client):
    "We do not get an overwrite page if there's no such source"
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.get("/good/2099/666/overwrite?target=[2023]+EWCA+Civ+888")
    assert response.status_code == 404


@pytest.mark.django_db
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
def test_post_overwrite_invalid(mock_judgment, client):
    mock_judgment.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.post(
        "/good/2099/888/overwrite?target=[2023]+EWCA+Civ+888",
        {"neutral_citation": "jam"},
    )
    assert response.status_code == 200
    assert b"Unable to parse" in response.content


@pytest.mark.django_db
@patch("judgments.utils.get_judgment_by_uri")
@patch("judgments.views.judgment_move.get_judgment_by_uri_or_404")
@patch("judgments.views.judgment_move.api_client")
@patch("judgments.views.judgment_move.overwrite_judgment")
def test_perform_overwrite_present_target(
    mock_overwrite, mock_api_client, mock_judgment_or_404, mock_judgment_by_uri, client
):
    "Given an existing target, we should overwrite it"
    mock_overwrite.return_value = "/eat/2099/888"
    mock_api_client.judgment_exists.return_value = True
    mock_judgment_or_404.side_effect = get_mock_judgment
    client.force_login(User.objects.get_or_create(username="testuser")[0])
    response = client.post(
        "/good/2099/1/overwrite", {"neutral_citation": "[2099] EAT 888"}
    )
    mock_overwrite.assert_called_with("good/2099/1", "[2099] EAT 888")
    mock_api_client.set_judgment_citation.assert_called_with(
        "/eat/2099/888", "[2099] EAT 888"
    )

    assert response.status_code == 302
    assert response.url == "/eat/2099/888"
