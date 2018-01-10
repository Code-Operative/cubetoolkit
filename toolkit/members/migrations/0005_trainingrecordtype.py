# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-09 21:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import toolkit.members.models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0004_member_membership_expires'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingrecord',
            name='training_type',
            field=models.CharField(
                default='R',
                choices=[
                    ('R',
                     'Role Specific Training'),
                    ('G',
                     'General Safety Training')],
                max_length=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='trainingrecord',
            name='role',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='training_records',
                to='diary.Role'),
        ),
    ]
