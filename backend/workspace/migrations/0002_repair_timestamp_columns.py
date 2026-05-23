from django.db import migrations


def repair_timestamp_columns(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        ALTER TABLE workspace
        ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone NOT NULL DEFAULT now();

        ALTER TABLE workspace_membership
        ADD COLUMN IF NOT EXISTS created_at timestamp with time zone NOT NULL DEFAULT now();

        ALTER TABLE workspace_membership
        ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone NOT NULL DEFAULT now();
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('workspace', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(repair_timestamp_columns, migrations.RunPython.noop),
    ]
