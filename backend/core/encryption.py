import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FieldEncryptor:
    """
    Encripta/desencripta campos individuales usando AES-256-GCM.
    La clave se almacena en variable de entorno, NUNCA en código.
    """

    def __init__(self):
        key_b64 = os.environ.get('FIELD_ENCRYPTION_KEY')
        if not key_b64:
            raise ValueError("FIELD_ENCRYPTION_KEY no está configurada")
        self.key = base64.b64decode(key_b64)
        if len(self.key) != 32:
            raise ValueError("La clave debe tener exactamente 32 bytes (256 bits)")

    def encrypt(self, plaintext: str) -> str:
        """Encripta un string y devuelve base64(nonce + ciphertext)."""
        nonce = os.urandom(12)
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt(self, encrypted_b64: str) -> str:
        """Desencripta un string previamente encriptado."""
        raw = base64.b64decode(encrypted_b64)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self.key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
