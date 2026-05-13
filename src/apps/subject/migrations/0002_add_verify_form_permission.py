# Adds Django auth row for custom permission subject.verify_form (Meta on unmanaged Subject).

from django.db import migrations


def add_verify_form_permission(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(app_label="subject", model="subject").first()
    if ct is None:
        return
    Permission.objects.get_or_create(
        content_type=ct,
        codename="verify_form",
        defaults={"name": "Can verify form"},
    )


def remove_verify_form_permission(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(app_label="subject", model="subject").first()
    if ct is None:
        return
    Permission.objects.filter(content_type=ct, codename="verify_form").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("subject", "0001_create_study_eventinstance_file"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(add_verify_form_permission, remove_verify_form_permission),
    ]
