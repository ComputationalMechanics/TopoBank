# Generated by Django 2.2.13 on 2020-06-26 09:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0013_topography_datafile_format'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='topography',
            options={'ordering': ['name']},
        ),
    ]