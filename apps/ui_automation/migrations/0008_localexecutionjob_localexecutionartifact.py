# Generated manually for the on-demand local Playwright runner.

import apps.ui_automation.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ui_automation', '0007_testcase_global_wait'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocalExecutionJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('attempt_id', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('status', models.CharField(choices=[('waiting_runner', '等待本机执行器'), ('claimed', '已领取'), ('running', '执行中'), ('passed', '通过'), ('failed', '失败'), ('cancelled', '已取消'), ('expired', '已过期')], db_index=True, default='waiting_runner', max_length=30, verbose_name='状态')),
                ('launch_code_hash', models.CharField(max_length=64, unique=True, verbose_name='一次性领取码摘要')),
                ('upload_token_hash', models.CharField(blank=True, max_length=64, verbose_name='任务令牌摘要')),
                ('payload', models.JSONField(default=dict, verbose_name='执行快照')),
                ('expires_at', models.DateTimeField(verbose_name='领取截止时间')),
                ('claimed_at', models.DateTimeField(blank=True, null=True, verbose_name='领取时间')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ui_local_execution_jobs', to=settings.AUTH_USER_MODEL, verbose_name='发起人')),
                ('execution', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='local_job', to='ui_automation.testcaseexecution', verbose_name='执行记录')),
            ],
            options={
                'db_table': 'ui_local_execution_jobs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LocalExecutionArtifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('artifact_type', models.CharField(max_length=30, verbose_name='附件类型')),
                ('file', models.FileField(max_length=500, upload_to=apps.ui_automation.models.local_execution_artifact_path, verbose_name='文件')),
                ('original_name', models.CharField(max_length=255, verbose_name='原始文件名')),
                ('content_type', models.CharField(blank=True, max_length=150, verbose_name='MIME类型')),
                ('file_size', models.BigIntegerField(default=0, verbose_name='文件大小')),
                ('sha256', models.CharField(max_length=64, verbose_name='SHA256')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='ui_automation.localexecutionjob', verbose_name='本机执行任务')),
            ],
            options={
                'db_table': 'ui_local_execution_artifacts',
                'ordering': ['created_at'],
            },
        ),
    ]
