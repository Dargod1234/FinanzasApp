import { Buffer } from 'buffer';

export class CryptoService {
  static decodeBase64(input: string): Uint8Array {
    return Uint8Array.from(Buffer.from(input, 'base64'));
  }

  private static async deriveKey(mnemonic: string, salt: ArrayBuffer) {
    const keyMaterial = await window.crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(mnemonic.trim()),
      { name: 'PBKDF2' },
      false,
      ['deriveKey']
    );

    return window.crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt,
        iterations: 250000,
        hash: 'SHA-256',
      },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt']
    );
  }

  static async encrypt(data: object, mnemonic: string) {
    const text = JSON.stringify(data);
    const encoder = new TextEncoder();
    const encodedData = encoder.encode(text);

    const salt = window.crypto.getRandomValues(new Uint8Array(16));
    const cryptoKey = await this.deriveKey(mnemonic, salt.buffer as ArrayBuffer);

    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const encrypted = await window.crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      cryptoKey,
      encodedData
    );

    return {
      ciphertext: Buffer.from(encrypted).toString('base64'),
      iv: Buffer.from(iv).toString('base64'),
      salt: Buffer.from(salt).toString('base64'),
      crypto_version: 1,
    };
  }
}