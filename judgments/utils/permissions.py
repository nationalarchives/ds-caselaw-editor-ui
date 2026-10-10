from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate

from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from judgments.utils.view_helpers import user_can_edit, user_is_developer, user_is_editor_or_developer

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def editors_only_hint() -> str:
    return f"Only members of the {settings.EDITORS_GROUP_NAME} group can do this"


def editors_or_developers_hint() -> str:
    return f"Only members of the {settings.EDITORS_GROUP_NAME} or {settings.DEVELOPERS_GROUP_NAME} groups can do this"


class _GroupRequiredMixin(UserPassesTestMixin):
    raise_exception = True
    request: HttpRequest


class DeveloperRequiredMixin(_GroupRequiredMixin):
    """Restricts every HTTP method to members of the Developers group."""

    def test_func(self) -> bool:
        return bool(user_is_developer(self.request.user))


class EditorRequiredMixin(_GroupRequiredMixin):
    """Restricts mutating HTTP methods to members of the Editors group, leaving pages viewable."""

    def test_func(self) -> bool:
        return self.request.method in SAFE_METHODS or bool(user_can_edit(self.request.user))


def _forbid_unless[**P, R](
    check: Callable[[Any], bool],
    view: Callable[Concatenate[HttpRequest, P], R],
) -> Callable[Concatenate[HttpRequest, P], R]:
    """Wrap a function view so it raises PermissionDenied (403) unless `check(request.user)` passes."""

    @wraps(view)
    def wrapper(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> R:
        if not check(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def editor_required[**P, R](view: Callable[Concatenate[HttpRequest, P], R]) -> Callable[Concatenate[HttpRequest, P], R]:
    """Function-view decorator: only members of the Editors group may call the view."""
    return _forbid_unless(user_can_edit, view)


def editor_or_developer_required[**P, R](
    view: Callable[Concatenate[HttpRequest, P], R],
) -> Callable[Concatenate[HttpRequest, P], R]:
    """Function-view decorator: only members of the Editors or Developers groups may call the view."""
    return _forbid_unless(user_is_editor_or_developer, view)
