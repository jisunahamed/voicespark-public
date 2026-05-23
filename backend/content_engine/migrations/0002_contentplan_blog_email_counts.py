from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content_engine', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentplan',
            name='blog_posts_per_week',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='contentplan',
            name='emails_per_week',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
