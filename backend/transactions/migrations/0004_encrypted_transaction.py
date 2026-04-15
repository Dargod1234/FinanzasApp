import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def uuid7_or_uuid4():
    uuid7_fn = getattr(uuid, 'uuid7', None)
    if callable(uuid7_fn):
        return uuid7_fn()
    return uuid.uuid4()


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_rename_raw_ocr_response'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EncryptedTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid7_or_uuid4, editable=False, primary_key=True, serialize=False)),
                ('encrypted_data', models.BinaryField()),
                ('nonce', models.BinaryField(max_length=12)),
                ('salt', models.BinaryField(max_length=16)),
                ('crypto_version', models.PositiveSmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='encrypted_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'transactions_encrypted_transaction',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='encryptedtransaction',
            index=models.Index(fields=['user', '-created_at'], name='transactio_user_id_8070f0_idx'),
        ),
    ]
