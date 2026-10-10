import pytest
from django.contrib.auth.models import Group

from judgments.apps import check_editors_group_exists


@pytest.mark.django_db
def test_editors_group_missing_is_a_warning():
    assert [warning.id for warning in check_editors_group_exists(None)] == ["judgments.W001"]


@pytest.mark.django_db
def test_editors_group_present_passes():
    Group.objects.create(name="Editors")

    assert check_editors_group_exists(None) == []
