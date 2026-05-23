import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspace', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NanoBananaImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('picture_url', models.TextField(blank=True, null=True)),
                ('caption', models.TextField(blank=True, null=True)),
                ('platform_captions', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nano_banana_images', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workspace_nano_banana_images', to='workspace.workspace')),
            ],
            options={
                'db_table': 'nano_banana_image',
            },
        ),
    ]
