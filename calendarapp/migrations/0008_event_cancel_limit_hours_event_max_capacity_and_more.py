# Generated by Django 4.2.20 on 2025-03-22 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendarapp', '0007_attendance_delete_eventregistration'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='cancel_limit_hours',
            field=models.PositiveIntegerField(default=24),
        ),
        migrations.AddField(
            model_name='event',
            name='max_capacity',
            field=models.PositiveIntegerField(default=10),
        ),
        migrations.AddField(
            model_name='event',
            name='signup_limit_hours',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
