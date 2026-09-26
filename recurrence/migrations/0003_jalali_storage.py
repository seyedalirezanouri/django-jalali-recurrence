from django.db import migrations, models


def reject_legacy_rows(apps, schema_editor):
    """Do not silently reinterpret Gregorian rows as Jalali values."""
    for name in ("Recurrence", "Rule", "Date"):
        model = apps.get_model("recurrence", name)
        if model.objects.exists():
            raise RuntimeError(
                "django-jalali-recurrence 2.0 is Jalali-only; existing recurrence "
                f"rows were found in {name}. Start with an empty database."
            )


class Migration(migrations.Migration):
    dependencies = [("recurrence", "0002_alter_date_id_alter_param_id_alter_recurrence_id_and_more")]

    operations = [
        migrations.RunPython(reject_legacy_rows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="recurrence", name="dtstart",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="recurrence", name="dtend",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="rule", name="until",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="rule", name="skip",
            field=models.CharField(default="OMIT", max_length=8),
        ),
        migrations.AlterField(
            model_name="date", name="dt",
            field=models.TextField(),
        ),
    ]
