# Generated by Django 3.1.12 on 2021-08-07 02:39

import ckeditor_uploader.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='question',
            name='figure',
        ),
        migrations.AlterField(
            model_name='question',
            name='content',
            field=ckeditor_uploader.fields.RichTextUploadingField(),
        ),
    ]
