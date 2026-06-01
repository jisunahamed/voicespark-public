from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspace', '0003_repair_legacy_joined_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacebookPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_id', models.CharField(max_length=500)),
                ('name', models.CharField(max_length=255)),
                ('access_token', models.TextField()),
                ('category', models.CharField(blank=True, max_length=100, null=True)),
                ('tasks', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='facebook_pages', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workspace_facebook_pages', to='workspace.workspace')),
            ],
            options={'db_table': 'facebook_page'},
        ),
        migrations.CreateModel(
            name='FacebookToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token', models.TextField()),
                ('token_type', models.CharField(default='bearer', max_length=50)),
                ('expires_in', models.IntegerField(blank=True, null=True)),
                ('issued_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='token', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workspace_facebook_token', to='workspace.workspace')),
            ],
            options={'db_table': 'fb_Token'},
        ),
        migrations.CreateModel(
            name='FacebookUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('facebook_id', models.CharField(db_index=True, max_length=100)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('first_name', models.CharField(blank=True, max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('full_name', models.CharField(blank=True, max_length=200)),
                ('picture_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='facebook_profile', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workspace_facebook_profile', to='workspace.workspace')),
            ],
            options={'db_table': 'fb_user'},
        ),
        migrations.CreateModel(
            name='InstagramToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token', models.TextField()),
                ('token_type', models.CharField(default='bearer', max_length=50)),
                ('expires_in', models.IntegerField(blank=True, null=True)),
                ('issued_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='insta_token', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workspace_insta_token', to='workspace.workspace')),
            ],
            options={'db_table': 'insta_Token'},
        ),
        migrations.CreateModel(
            name='InstagramUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instagram_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('first_name', models.CharField(blank=True, max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('full_name', models.CharField(blank=True, max_length=200)),
                ('picture_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='instagram_profile', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workspace_instagram_profile', to='workspace.workspace')),
            ],
            options={'db_table': 'insta_user'},
        ),
    ]
