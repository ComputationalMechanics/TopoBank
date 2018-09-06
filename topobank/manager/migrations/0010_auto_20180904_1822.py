# Generated by Django 2.0.6 on 2018-09-04 16:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('manager', '0009_auto_20180904_1754'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='topography',
            name='user',
        ),
        migrations.AddField(
            model_name='surface',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
