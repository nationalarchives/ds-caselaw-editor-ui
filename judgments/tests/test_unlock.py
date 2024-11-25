from unittest.mock import ANY, patch

import pytest
from caselawclient.factories import JudgmentFactory
from caselawclient.models.documents import DocumentURIString
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_break_lock_confirm_page():
    client = Client()
    client.force_login(User.objects.get_or_create(username="testuser")[0])

    response = client.get("/unlock?judgment_uri=my_uri")
    decoded_response = response.content.decode("utf-8")
    assert '<input type="hidden" name="judgment_uri" value="my_uri" />' in decoded_response
    assert response.status_code == 200


@pytest.mark.django_db
@patch("judgments.views.unlock.get_document_by_uri_or_404")
@patch("judgments.views.unlock.api_client.break_checkout")
@patch("judgments.views.unlock.messages")
def test_break_lock_post(messages, break_checkout, mock_judgment):
    judgment = JudgmentFactory.build(
        uri=DocumentURIString("ewca/civ/2023/1"),
    )
    mock_judgment.return_value = judgment

    client = Client()
    client.force_login(User.objects.get_or_create(username="testuser")[0])

    response = client.post("/unlock", data={"judgment_uri": "/ewca/civ/2023/1"})
    break_checkout.assert_called_with("ewca/civ/2023/1")
    messages.success.assert_called_with(ANY, "Document unlocked.")
    assert response.status_code == 302
    assert response.url == reverse(  # type: ignore # noqa: PGH003
        "edit-document",
        kwargs={"document_uri": "ewca/civ/2023/1"},
    )
