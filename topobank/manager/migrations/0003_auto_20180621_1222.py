# Generated by Django 2.0.6 on 2018-06-21 10:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('manager', '0002_topography_datafile'),
    ]

    operations = [
        migrations.AddField(
            model_name='topography',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='topography',
            name='user',
            field=models.ForeignKey(default=2, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
