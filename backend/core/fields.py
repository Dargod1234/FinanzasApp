from django.db import models
from .encryption import FieldEncryptor


class EncryptedCharField(models.CharField):
    """Campo que se encripta automáticamente al guardar y desencripta al leer."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 512)
        super().__init__(*args, **kwargs)
        self._encryptor = None

    @property
    def encryptor(self):
        if self._encryptor is None:
            self._encryptor = FieldEncryptor()
        return self._encryptor

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encryptor.encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return self.encryptor.decrypt(value)
        except Exception:
            return value  # Fallback para datos migrados sin encriptar
