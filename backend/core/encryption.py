import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FieldEncryptor:
    """
    Encripta/desencripta campos individuales usando AES-256-GCM.
    La clave se almacena en variable de entorno, NUNCA en código.
    """

    def __init__(self):
        key_str = os.environ.get('FIELD_ENCRYPTION_KEY', '').strip()
        if not key_str:
            raise ValueError("FIELD_ENCRYPTION_KEY no está configurada")
        
        # Corregir padding si falta para evitar "Invalid base64-encoded string"
        missing_padding = len(key_str) % 4
        if missing_padding:
            key_str += '=' * (4 - missing_padding)
            
        try:
            self.key = base64.urlsafe_b64decode(key_str)
        except Exception:
            # Reintentar con b64decode estándar si urlsafe falla
            self.key = base64.b64decode(key_str)

        if len(self.key) != 32:
            raise ValueError(f"La clave debe tener 32 bytes tras decodificar (tiene {len(self.key)})")

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
