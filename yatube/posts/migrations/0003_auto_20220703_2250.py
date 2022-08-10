# Generated by Django 2.2.19 on 2022-07-03 19:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_auto_20220703_2215'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groups',
            name='slug',
            field=models.SlugField(unique=True),
        ),
        migrations.AlterField(
            model_name='groups',
            name='title',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='post',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='posts.Groups'),
        ),
    ]