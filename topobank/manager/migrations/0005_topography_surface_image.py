# Generated by Django 2.0.6 on 2018-07-16 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0004_topography_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='topography',
            name='surface_image',
            field=models.ImageField(default='topographies/not_available.png', upload_to=''),
        ),
    ]
