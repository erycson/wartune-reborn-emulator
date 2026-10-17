import struct

import pytest

from wartune_server.protocol import (
    DEFAULT_KEY,
    HEADER_SIZE,
    Packet,
    PacketDecoder,
    PacketError,
    StreamCipher,
)

# Primeiros 40 bytes cifrados de dois logins 20001 reais (logs do relay), com a chave padrão.
REAL_LOGIN_PREFIXES = [
    (bytes.fromhex("df137e3b281c5fd55ddd8f60ae4181584b9c684ce8363a6e8a7cb36d41126f7d609b929702f47342"), 72),
    (bytes.fromhex("df137e3a2803bd453ddd8f60ad3d7ca6579458 4ceb39438ffd14ba3c1c1013ba0d7da2e2d945fb99".replace(" ", "")), 73),
]


@pytest.mark.parametrize(("prefix", "length"), REAL_LOGIN_PREFIXES)
def test_decrypts_real_client_login_header(prefix: bytes, length: int) -> None:
    plain = StreamCipher(DEFAULT_KEY).decrypt(prefix)
    magic, size, _check, code, client_id = struct.unpack_from(">hHhhi", plain)
    assert (magic, size, code, client_id) == (29099, length, 20001, 58060894)


def test_encrypt_then_decrypt_keeps_state_across_packets() -> None:
    sender, receiver = StreamCipher(), StreamCipher()
    packets = [Packet(20001, b"\x08\x01" * 30, 7), Packet(8224, b""), Packet(0x8001, b"x" * 300)]
    wire = b"".join(sender.encrypt(p.encode()) for p in packets)

    decoder = PacketDecoder(receiver)
    out = [p for i in range(0, len(wire), 7) for p in decoder.feed(wire[i : i + 7])]
    assert out == packets
    assert sender.key == receiver.key  # as duas pontas avançaram igual


def test_peek_does_not_advance_key() -> None:
    cipher = StreamCipher()
    data = StreamCipher().encrypt(Packet(1).encode())
    cipher.peek(data[:4])
    assert cipher.key == DEFAULT_KEY


def test_packet_roundtrip_and_checksum() -> None:
    raw = Packet(4160, b"\x0a\x03abc", 58060894, 1, -1).encode()
    assert len(raw) == HEADER_SIZE + 5
    assert Packet.decode(raw) == Packet(4160, b"\x0a\x03abc", 58060894, 1, -1)

    tampered = bytearray(raw)
    tampered[-1] ^= 0xFF
    with pytest.raises(PacketError, match="checksum"):
        Packet.decode(bytes(tampered))


def test_high_opcode_is_unsigned_after_decode() -> None:
    assert Packet.decode(Packet(0x8320).encode()).code == 0x8320


def test_decoder_rejects_garbage() -> None:
    with pytest.raises(PacketError):
        PacketDecoder(StreamCipher()).feed(b"\x00" * 20)
