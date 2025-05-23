# Generated by Django 4.2.20 on 2025-05-08 17:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('blockchain', '0002_invitationcode'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockchainNode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=64, unique=True)),
                ('is_validator', models.BooleanField(default=False)),
                ('public_key', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_hash', models.CharField(max_length=64, unique=True)),
                ('from_address', models.CharField(max_length=64)),
                ('to_address', models.CharField(max_length=64)),
                ('data', models.TextField()),
                ('signature', models.TextField()),
                ('gas_used', models.IntegerField(default=0)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SmartContract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contract_address', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('version', models.CharField(max_length=20)),
                ('bytecode', models.TextField()),
                ('abi', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RealisticBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('block_number', models.IntegerField(unique=True)),
                ('block_hash', models.CharField(max_length=64, unique=True)),
                ('previous_hash', models.CharField(max_length=64)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('merkle_root', models.CharField(max_length=64)),
                ('difficulty', models.IntegerField(default=2)),
                ('nonce', models.IntegerField(default=0)),
                ('miner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='blockchain.blockchainnode')),
                ('transactions', models.ManyToManyField(to='blockchain.transaction')),
            ],
            options={
                'ordering': ['-block_number'],
            },
        ),
        migrations.CreateModel(
            name='StudentRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_id', models.CharField(db_index=True, max_length=20)),
                ('encrypted_data', models.BinaryField()),
                ('status', models.CharField(choices=[('active', 'Active'), ('superseded', 'Superseded'), ('invalid', 'Invalid')], default='active', max_length=10)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('previous_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='blockchain.studentrecord')),
            ],
            options={
                'indexes': [models.Index(fields=['student_id', 'status'], name='blockchain__student_e15c3a_idx')],
            },
        ),
    ]
