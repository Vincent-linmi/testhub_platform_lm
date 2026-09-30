from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0006_alter_testcasestep_action_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='testcase',
            name='global_wait_enabled',
            field=models.BooleanField(default=False, verbose_name='启用步骤间全局等待'),
        ),
        migrations.AddField(
            model_name='testcase',
            name='global_wait_time',
            field=models.PositiveIntegerField(
                default=1000,
                validators=[MinValueValidator(100), MaxValueValidator(60000)],
                verbose_name='步骤间全局等待时间(毫秒)',
            ),
        ),
    ]
