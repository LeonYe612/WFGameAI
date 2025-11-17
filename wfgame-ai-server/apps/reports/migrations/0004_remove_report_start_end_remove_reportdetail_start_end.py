from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0003_alter_report_end_time_alter_reportdetail_end_time'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='report',
            name='start_time',
        ),
        migrations.RemoveField(
            model_name='report',
            name='end_time',
        ),
        migrations.RemoveField(
            model_name='reportdetail',
            name='start_time',
        ),
        migrations.RemoveField(
            model_name='reportdetail',
            name='end_time',
        ),
    ]
