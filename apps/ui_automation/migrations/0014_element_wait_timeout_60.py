from django.db import migrations, models


def set_element_timeouts_to_60(apps, schema_editor):
    Element = apps.get_model('ui_automation', 'Element')
    Element.objects.all().update(wait_timeout=60)


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0013_step_runtime_actions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='element',
            name='wait_timeout',
            field=models.IntegerField(default=60, verbose_name='等待超时(秒)'),
        ),
        migrations.RunPython(set_element_timeouts_to_60, migrations.RunPython.noop),
    ]
