from django.db import migrations


def create_metadata_aside_judges_flag(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="metadata_aside_judges",
        defaults={
            "everyone": False,
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": "Allow editors to add and remove judges from the judgment metadata aside.",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("judgments", "0004_bulkreparserunlog_detail"),
        ("waffle", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_metadata_aside_judges_flag, migrations.RunPython.noop),
    ]
