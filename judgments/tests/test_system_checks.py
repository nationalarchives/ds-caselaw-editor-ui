import pytest
from django.contrib.auth.models import Group

from judgments.apps import check_editors_group_exists


@pytest.mark.django_db
def test_editors_group_missing_is_an_error():
    assert [error.id for error in check_editors_group_exists(None)] == ["judgments.E001"]


@pytest.mark.django_db
def test_editors_group_present_passes():
    Group.objects.create(name="Editors")

    assert check_editors_group_exists(None) == []
