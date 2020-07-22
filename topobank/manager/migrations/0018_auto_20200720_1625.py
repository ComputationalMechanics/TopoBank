# Generated by Django 2.2.13 on 2020-07-20 14:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0017_auto_20200713_1459'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='surface',
            name='license',
        ),
        migrations.RemoveField(
            model_name='surface',
            name='publication_datetime',
        ),
        migrations.AddField(
            model_name='surface',
            name='parent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='manager.Surface'),
        ),
    ]
