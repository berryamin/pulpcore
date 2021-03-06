# Generated by Django 2.2.7 on 2019-11-12 20:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_auto_20191112_1426'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basedistribution',
            name='base_path',
            field=models.TextField(unique=True),
        ),
        migrations.AlterField(
            model_name='basedistribution',
            name='name',
            field=models.TextField(db_index=True, unique=True),
        ),
        migrations.AlterField(
            model_name='contentappstatus',
            name='name',
            field=models.TextField(db_index=True, unique=True),
        ),
        migrations.AlterField(
            model_name='contentguard',
            name='name',
            field=models.TextField(db_index=True, unique=True),
        ),
        migrations.AlterField(
            model_name='filesystemexporter',
            name='name',
            field=models.TextField(db_index=True, unique=True),
        ),
        migrations.AlterField(
            model_name='remote',
            name='name',
            field=models.TextField(db_index=True, unique=True),
        ),
        migrations.AlterField(
            model_name='repository',
            name='name',
            field=models.TextField(db_index=True, unique=True),
        ),
        migrations.AlterField(
            model_name='reservedresource',
            name='resource',
            field=models.TextField(unique=True),
        ),
        migrations.AlterField(
            model_name='reservedresourcerecord',
            name='resource',
            field=models.TextField(unique=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='name',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='worker',
            name='name',
            field=models.TextField(db_index=True, unique=True),
        ),
    ]
