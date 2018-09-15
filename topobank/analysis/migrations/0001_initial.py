# Generated by Django 2.0.6 on 2018-09-12 16:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Analysis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('args', models.BinaryField()),
                ('kwargs', models.BinaryField()),
                ('task_id', models.CharField(max_length=155, null=True, unique=True)),
                ('task_state', models.CharField(choices=[('pe', 'pending'), ('st', 'started'), ('re', 'retry'), ('fa', 'failure'), ('su', 'success')], max_length=7)),
                ('result', models.BinaryField(default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='AnalysisFunction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='A human-readable name.', max_length=80)),
                ('pyfunc', models.CharField(help_text='Name of Python function in topobank.analysis.functions', max_length=256)),
            ],
        ),
        migrations.AddField(
            model_name='analysis',
            name='function',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analysis.AnalysisFunction'),
        ),
    ]