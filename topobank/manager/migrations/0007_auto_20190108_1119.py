# Generated by Django 2.0.6 on 2019-01-08 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0006_auto_20181221_1548'),
    ]

    operations = [
        migrations.AlterField(
            model_name='topography',
            name='resolution_x',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='topography',
            name='resolution_y',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]