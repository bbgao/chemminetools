# Generated by Django 2.2.6 on 2020-06-10 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compounddb', '0002_auto_20190717_1112'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(fields=('name', 'user'), name='unique_name_user_tag'),
        ),
    ]
