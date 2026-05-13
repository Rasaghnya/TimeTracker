# Generated migration for adding face recognition fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracktimeapp', '0003_alter_duration_exittime_alter_duration_timespent'),
    ]

    operations = [
        migrations.AddField(
            model_name='members',
            name='face_encoding',
            field=models.BinaryField(blank=True, help_text='128-dimensional face encoding stored as binary', null=True),
        ),
        migrations.AddField(
            model_name='members',
            name='face_registered',
            field=models.BooleanField(default=False, help_text='Whether the student has registered their face'),
        ),
    ]
