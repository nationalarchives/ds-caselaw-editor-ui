import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from django.views import View

from judgments.utils.permissions import (
    DeveloperRequiredMixin,
    EditorRequiredMixin,
    editor_or_developer_required,
    editor_required,
)


class DeveloperView(DeveloperRequiredMixin, View):
    def get(self, request):
        return HttpResponse("ok")


class EditorView(EditorRequiredMixin, View):
    def get(self, request):
        return HttpResponse("ok")

    def post(self, request):
        return HttpResponse("ok")


@editor_required
def editor_function_view(request):
    return HttpResponse("ok")


@editor_or_developer_required
def editor_or_developer_function_view(request):
    return HttpResponse("ok")


def request_as(method, user):
    request = getattr(RequestFactory(), method)("/")
    request.user = user
    return request


@pytest.fixture
def standard_user(db):
    return User.objects.create(username="alice")


@pytest.fixture
def editor_user(db):
    user = User.objects.create(username="ed")
    user.groups.add(Group.objects.get_or_create(name="Editors")[0])
    return user


@pytest.fixture
def developer_user(db):
    user = User.objects.create(username="dev")
    user.groups.add(Group.objects.get_or_create(name="Developers")[0])
    return user


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="clark")


def test_developer_mixin_allows_developer(developer_user):
    assert DeveloperView.as_view()(request_as("get", developer_user)).status_code == 200


@pytest.mark.parametrize("user_fixture", ["standard_user", "editor_user", "superuser"])
def test_developer_mixin_denies_non_developers(user_fixture, request):
    with pytest.raises(PermissionDenied):
        DeveloperView.as_view()(request_as("get", request.getfixturevalue(user_fixture)))


def test_editor_mixin_allows_editor_to_post(editor_user):
    assert EditorView.as_view()(request_as("post", editor_user)).status_code == 200


@pytest.mark.parametrize("user_fixture", ["standard_user", "developer_user", "superuser"])
def test_editor_mixin_denies_non_editors_posting(user_fixture, request):
    with pytest.raises(PermissionDenied):
        EditorView.as_view()(request_as("post", request.getfixturevalue(user_fixture)))


def test_editor_mixin_allows_anyone_to_get(standard_user):
    assert EditorView.as_view()(request_as("get", standard_user)).status_code == 200


def test_editor_required_allows_editor(editor_user):
    assert editor_function_view(request_as("post", editor_user)).status_code == 200


@pytest.mark.parametrize("user_fixture", ["standard_user", "developer_user", "superuser"])
def test_editor_required_denies_non_editors(user_fixture, request):
    with pytest.raises(PermissionDenied):
        editor_function_view(request_as("post", request.getfixturevalue(user_fixture)))


@pytest.mark.parametrize("user_fixture", ["editor_user", "developer_user"])
def test_editor_or_developer_required_allows_editors_and_developers(user_fixture, request):
    response = editor_or_developer_function_view(request_as("post", request.getfixturevalue(user_fixture)))
    assert response.status_code == 200


@pytest.mark.parametrize("user_fixture", ["standard_user", "superuser"])
def test_editor_or_developer_required_denies_others(user_fixture, request):
    with pytest.raises(PermissionDenied):
        editor_or_developer_function_view(request_as("post", request.getfixturevalue(user_fixture)))
