"""Par RSA do login HTTP (``POST /login`` envia ``p`` cifrado pelo cliente).

O ``Loading.swf`` lê ``RSAKey@PublicKeyModulus``/``publicExponent`` do ``config.xml``
(Base64, big-endian) e cifra ``user|key|tempPassword|userId`` com
``com.hurlant.crypto.rsa.RSAKey.encrypt`` (PKCS#1 v1.5 tipo 2) e Base64.

Detalhes do Hurlant que importam:
* ``BigInteger(bytes)`` é com sinal: o módulo precisa de um ``0x00`` na frente
  quando o bit mais alto é 1 (o config oficial começa com ``AI...``).
* ``BigInteger.toArray`` omite zeros à esquerda: um bloco cifrado pode vir com
  menos bytes que o módulo. Por isso a chave tem 2048 bits (cabe tudo em um
  bloco) e o bloco é completado à esquerda antes de decifrar.
"""

from __future__ import annotations

import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class RSAError(ValueError):
    pass


class LoginKeyPair:
    def __init__(self, private_key: rsa.RSAPrivateKey) -> None:
        self._key = private_key
        numbers = private_key.public_key().public_numbers()
        self._modulus, self._exponent = numbers.n, numbers.e
        self._block = (self._modulus.bit_length() + 7) // 8

    @classmethod
    def generate(cls, bits: int = 2048) -> LoginKeyPair:
        return cls(rsa.generate_private_key(public_exponent=65537, key_size=bits))

    @classmethod
    def load_or_create(cls, path: Path) -> LoginKeyPair:
        if path.exists():
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            if not isinstance(key, rsa.RSAPrivateKey):
                raise RSAError(f"{path} não é uma chave RSA")
            return cls(key)
        pair = cls.generate()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            pair._key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        return pair

    @property
    def modulus_b64(self) -> str:
        return base64.b64encode(_signed_bytes(self._modulus)).decode()

    @property
    def exponent_b64(self) -> str:
        return base64.b64encode(_signed_bytes(self._exponent)).decode()

    def decrypt_b64(self, payload: str) -> bytes:
        try:
            data = base64.b64decode(payload.replace(" ", "+"), validate=True)
        except ValueError as exc:
            raise RSAError("payload RSA não é Base64") from exc
        if not data or len(data) > self._block:
            raise RSAError(f"bloco RSA com {len(data)} bytes (esperado até {self._block})")
        try:
            return self._key.decrypt(data.rjust(self._block, b"\x00"), padding.PKCS1v15())
        except ValueError as exc:
            raise RSAError("falha ao decifrar o payload RSA") from exc

    def encrypt_b64(self, plain: bytes) -> str:
        """Faz o papel do cliente (usado em testes e no cliente de teste)."""
        return base64.b64encode(self._key.public_key().encrypt(plain, padding.PKCS1v15())).decode()


def _signed_bytes(value: int) -> bytes:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return b"\x00" + raw if raw[0] & 0x80 else raw
