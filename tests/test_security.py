import base64

import pytest

from wartune_server.security.rsa_keys import LoginKeyPair, RSAError


@pytest.fixture(scope="module")
def keys() -> LoginKeyPair:
    return LoginKeyPair.generate()


def test_modulus_is_positive_for_hurlant(keys: LoginKeyPair) -> None:
    raw = base64.b64decode(keys.modulus_b64)
    assert raw[0] == 0 and raw[1] & 0x80  # 0x00 + byte alto: BigInteger com sinal fica positivo
    assert keys.exponent_b64 == "AQAB"


def test_decrypts_client_payload(keys: LoginKeyPair) -> None:
    plain = b"jo%C3%A3o|ticket-abc|1234567|0"
    assert keys.decrypt_b64(keys.encrypt_b64(plain)) == plain


def test_accepts_block_without_leading_zero(keys: LoginKeyPair) -> None:
    # Hurlant omite zeros à esquerda; gera blocos até achar um que comece com 0x00
    for _ in range(2000):
        ct = base64.b64decode(keys.encrypt_b64(b"x"))
        if ct[0] == 0:
            assert keys.decrypt_b64(base64.b64encode(ct[1:]).decode()) == b"x"
            return
    pytest.skip("nenhum bloco com zero à esquerda gerado")


def test_rejects_garbage(keys: LoginKeyPair) -> None:
    with pytest.raises(RSAError):
        keys.decrypt_b64("não é base64!")
    with pytest.raises(RSAError):
        keys.decrypt_b64(base64.b64encode(b"\x01" * 300).decode())
    # Padding inválido NÃO levanta: OpenSSL 3.2+ faz "implicit rejection" (anti-Marvin) e devolve
    # bytes aleatórios. Quem valida é o LoginService, pelo formato "user|key|temp|id".
    assert isinstance(keys.decrypt_b64(base64.b64encode(b"\x01" * 256).decode()), bytes)


def test_load_or_create_persists(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "k.pem"
    first = LoginKeyPair.load_or_create(path)
    assert LoginKeyPair.load_or_create(path).modulus_b64 == first.modulus_b64
