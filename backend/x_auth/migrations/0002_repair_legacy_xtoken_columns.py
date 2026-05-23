from django.db import migrations


def repair_legacy_xtoken_columns(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return

    with schema_editor.connection.cursor() as cursor:
        existing = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(x_token)").fetchall()
        }

    columns = {
        'scopes': 'TEXT NULL',
        'x_user_id': 'varchar(255) NULL',
        'username': 'varchar(255) NULL',
    }
    for name, definition in columns.items():
        if name not in existing:
            schema_editor.execute(f'ALTER TABLE x_token ADD COLUMN {name} {definition}')


class Migration(migrations.Migration):

    dependencies = [
        ('x_auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(repair_legacy_xtoken_columns, migrations.RunPython.noop),
    ]
