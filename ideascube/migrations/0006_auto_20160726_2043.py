# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-07-26 20:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ideascube', '0005_setting'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='country_of_origin_occupation',
            field=models.CharField(blank=True, max_length=100, verbose_name='Occupation in the place of origin'),
        ),
    ]