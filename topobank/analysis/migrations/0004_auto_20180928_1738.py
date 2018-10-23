# Generated by Django 2.0.6 on 2018-09-28 15:38

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0003_auto_20180913_1613'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysis',
            name='end_time',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='analysis',
            name='start_time',
            field=models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0)),
            preserve_default=False,
        ),
    ]