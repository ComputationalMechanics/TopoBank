# Generated by Django 2.2.13 on 2020-07-20 14:25

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('manager', '0018_auto_20200720_1625'),
    ]

    operations = [
        migrations.CreateModel(
            name='Publication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('version', models.PositiveIntegerField(default=1)),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('license', models.CharField(choices=[('cc0-1.0', 'CC0 (Public Domain Dedication)'), ('ccby-4.0', 'CC BY 4.0'), ('ccbysa-4.0', 'CC BY-SA 4.0')], default='', max_length=12)),
                ('surface', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='manager.Surface')),
            ],
        ),
    ]
