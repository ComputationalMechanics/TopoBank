# Generated by Django 2.1.7 on 2019-05-08 12:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0005_auto_20190507_1410'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='topography',
            unique_together={('surface', 'name')},
        ),
    ]