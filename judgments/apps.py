from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import Warning as CheckWarning
from django.core.checks import register
from django.db import DatabaseError


class JudgmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "judgments"

    def ready(self):
        register(check_editors_group_exists)


def check_editors_group_exists(app_configs, **kwargs):
    Group = apps.get_model("auth", "Group")

    try:
        group_exists = Group.objects.filter(name=settings.EDITORS_GROUP_NAME).exists()
    except DatabaseError:
        # The database isn't ready yet (for example before the first migration), so there is nothing to verify.
        return []

    if group_exists:
        return []

    return [
        CheckWarning(
            f'There is no "{settings.EDITORS_GROUP_NAME}" group, so nobody can perform editing actions.',
            hint=f'Create a group named "{settings.EDITORS_GROUP_NAME}" and add the editing users to it.',
            id="judgments.W001",
        ),
    ]
