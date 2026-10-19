"""Decifra uma captura do Wireshark (``.pcapng``) do jogo oficial para o formato ``replay_packets.json``.

Remonta cada fluxo TCP da porta do jogo pelo número de sequência e decifra pacote a pacote. A
captura costuma começar no meio da sessão, sem o 20001 que traz a chave, então a chave é recuperada
pelo próprio cabeçalho: cada byte da chave só evolui com o texto cifrado (``StreamCipher``), e o
cabeçalho tem bytes conhecidos (magic, tamanho, ``extend1`` quase sempre 0). Uma chave candidata só
vale se o checksum de vários pacotes seguidos bater; se um segmento faltar, ressincroniza.

Uso::

    uv run python tools/decode_pcap.py "D:/wartune/server-relay/all pcaps/teknoloji upgrade.pcapng" -o captures/
    uv run python tools/dump_capture.py captures/teknoloji_upgrade.json
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from wartune_server.protocol.cipher import DEFAULT_KEY, StreamCipher
from wartune_server.protocol.packet import HEADER_SIZE, MAGIC, checksum

GAME_PORT = 5000
CONFIRM = 3  # pacotes seguidos com checksum certo para aceitar uma chave recuperada


@dataclass
class Flow:
    is_client: bool
    segments: dict[int, tuple[bytes, float]] = field(default_factory=dict)  # seq -> (dados, tempo)

    def stream(self) -> tuple[bytes, dict[int, float]]:
        """Bytes em ordem e o tempo de cada começo de segmento (onde dá para ressincronizar)."""
        # ponytail: ignora a volta do número de sequência (captura > 4 GB por fluxo)
        data, starts, expected = bytearray(), {}, None
        for seq in sorted(self.segments):
            chunk, ts = self.segments[seq]
            end = seq + len(chunk)
            if expected is not None and end <= expected:
                continue  # retransmissão
            if expected is not None and seq < expected:
                chunk = chunk[expected - seq :]
            starts[len(data)] = ts
            data += chunk
            expected = end
        return bytes(data), starts


def read_pcapng(path: Path) -> Iterator[tuple[float, int, bytes]]:
    """(tempo, linktype, quadro) de cada pacote."""
    data = path.read_bytes()
    pos, endian, links, tsres = 0, "<", [], []
    while pos + 12 <= len(data):
        btype = struct.unpack_from(endian + "I", data, pos)[0]
        if btype == 0x0A0D0D0A:
            endian = "<" if data[pos + 8 : pos + 12] == b"\x4d\x3c\x2b\x1a" else ">"
            links, tsres = [], []
        blen = struct.unpack_from(endian + "I", data, pos + 4)[0]
        body = data[pos + 8 : pos + blen - 4]
        if btype == 1:  # IDB
            links.append(struct.unpack_from(endian + "H", body, 0)[0])
            res = 6
            opt = 8
            while opt + 4 <= len(body):
                code, olen = struct.unpack_from(endian + "HH", body, opt)
                if code == 0:
                    break
                if code == 9:
                    res = body[opt + 4]
                opt += 4 + (olen + 3) // 4 * 4
            tsres.append(res)
        elif btype == 6:  # EPB
            iface, hi, lo, caplen = struct.unpack_from(endian + "IIII", body, 0)
            res = tsres[iface]
            div = 10**res if res < 128 else 2 ** (res & 0x7F)
            yield ((hi << 32) | lo) / div, links[iface], body[20 : 20 + caplen]
        elif btype == 3:  # SPB
            yield 0.0, links[0], body[4:]
        pos += blen


def tcp_payload(link: int, frame: bytes) -> tuple[str, int, str, int, int, bytes] | None:
    if link == 1:  # Ethernet
        off, etype = 14, struct.unpack_from(">H", frame, 12)[0]
        while etype == 0x8100:
            etype, off = struct.unpack_from(">H", frame, off + 2)[0], off + 4
        if etype not in (0x0800, 0x86DD):
            return None
    elif link == 0:  # loopback BSD
        off = 4
    elif link in (101, 228, 229):  # IP cru
        off = 0
    else:
        return None
    ip = frame[off:]
    if len(ip) >= 20 and ip[0] >> 4 == 4 and ip[9] == 6:
        ihl, total = (ip[0] & 15) * 4, struct.unpack_from(">H", ip, 2)[0]
        tcp, src, dst = ip[ihl:total], ".".join(map(str, ip[12:16])), ".".join(map(str, ip[16:20]))
    elif len(ip) >= 40 and ip[0] >> 4 == 6 and ip[6] == 6:  # IPv6 (oficial na Cloudflare), sem extensões
        tcp, src, dst = ip[40 : 40 + struct.unpack_from(">H", ip, 4)[0]], ip[8:24].hex(), ip[24:40].hex()
    else:
        return None
    sport, dport, seq = struct.unpack_from(">HHI", tcp, 0)
    payload = tcp[(tcp[12] >> 4) * 4 :]
    return src, sport, dst, dport, seq, bytes(payload)


def flows(path: Path, port: int) -> list[Flow]:
    found: dict[tuple[str, int, str, int], Flow] = {}
    for ts, link, frame in read_pcapng(path):
        parsed = tcp_payload(link, frame)
        if parsed is None or not parsed[5] or port not in (parsed[1], parsed[3]):
            continue
        src, sport, dst, dport, seq, payload = parsed
        flow = found.setdefault((src, sport, dst, dport), Flow(is_client=dport == port))
        old = flow.segments.get(seq)
        if old is None or len(old[0]) < len(payload):
            flow.segments[seq] = (payload, ts)
    return list(found.values())


def _valid(raw: bytes) -> bool:
    return struct.unpack_from(">hH", raw)[0:2] == (MAGIC, len(raw)) and struct.unpack_from(">H", raw, 4)[0] == checksum(
        raw
    )


def _length(enc: bytes, key: bytes) -> int | None:
    magic, length = struct.unpack(">hH", StreamCipher(key).peek(enc[:4]))
    return length if magic == MAGIC and length >= HEADER_SIZE else None


def _confirms(data: bytes, pos: int, key: bytes) -> bool:
    cipher = StreamCipher(key)
    for _ in range(CONFIRM):
        if pos + HEADER_SIZE > len(data):
            return pos == len(data)
        length = _length(data[pos:], cipher.key)
        if length is None or pos + length > len(data) or not _valid(cipher.decrypt(data[pos : pos + length])):
            return False
        pos += length
    return True


def recover_key(enc: bytes) -> bytes | None:
    """Chave que faz ``enc`` começar com magic e ``extend1 == 0``. Os bytes 2 e 3 (tamanho) ficam
    para ``_key_for_length``; quem confirma é o checksum."""
    known = {0: MAGIC >> 8, 1: MAGIC & 0xFF, 12: 0, 13: 0, 14: 0, 15: 0}  # magic, extend1
    if len(enc) < 16:
        return None
    key = bytearray(8)
    for k in (0, 1, 4, 5, 6, 7):
        p = k if k < 2 else k + 8
        found = next((g for g in range(256) if _plain_at(enc, k, g, p) == known[p]), None)
        if found is None:
            return None
        key[k] = found
    return bytes(key)


def _plain_at(enc: bytes, k: int, value: int, p: int) -> int:
    """Byte ``p`` decifrado se o byte ``k`` da chave começa valendo ``value`` (p ≡ k mod 8)."""
    if p == 0:
        return enc[0] ^ value
    for i in range(k if k else 8, p + 1, 8):
        value = ((value + enc[i - 1]) ^ i) & 0xFF
    return ((enc[p] - enc[p - 1]) & 0xFF) ^ value


def _key_for_length(enc: bytes, base: bytes, length: int) -> bytes:
    """Ajusta os bytes 2 e 3 da chave para o cabeçalho dizer ``length``."""
    key = bytearray(base)
    for k, want in ((2, length >> 8), (3, length & 0xFF)):
        key[k] = next(g for g in range(256) if _plain_at(enc, k, g, k) == want)
    return bytes(key)


def decode_flow(flow: Flow) -> Iterator[tuple[int, float, bytes]]:
    """(posição, tempo, pacote decifrado). Sem chave (começo, troca no 20001, segmento perdido),
    recupera pelo cabeçalho no próximo começo de segmento."""
    data, times = flow.stream()
    starts = sorted(times)
    pos = 0
    cipher: StreamCipher | None = StreamCipher(DEFAULT_KEY) if _confirms(data, 0, DEFAULT_KEY) else None
    while pos < len(data):
        if cipher is None:
            cipher, pos = _resync(data, pos, starts)
            if cipher is None:
                return
        length = _length(data[pos:], cipher.key)
        raw = cipher.decrypt(data[pos : pos + length]) if length and pos + length <= len(data) else b""
        if not raw or not _valid(raw):
            cipher = None  # ressincroniza a partir daqui (o pacote pode começar o segmento depois da falha)
            continue
        yield pos, times[max(s for s in starts if s <= pos)], raw
        pos += length


def _resync(data: bytes, pos: int, starts: list[int]) -> tuple[StreamCipher | None, int]:
    for start in (s for s in starts if s >= pos):
        enc = data[start:]
        base = recover_key(enc)
        if base is None:
            continue
        # tenta os tamanhos possíveis até o fim do fluxo, do menor para o maior
        for length in range(HEADER_SIZE, min(len(enc), 0xFFFF) + 1):
            key = _key_for_length(enc, base, length)
            if _confirms(data, start, key):
                return StreamCipher(key), start
    return None, len(data)


def decode(path: Path, port: int = GAME_PORT) -> list[dict[str, object]]:
    out: list[tuple[float, bool, int, bytes]] = []
    for flow in flows(path, port):
        for pos, ts, raw in decode_flow(flow):
            out.append((ts, flow.is_client, pos, raw))
    out.sort(key=lambda r: (r[0], not r[1], r[2]))
    packets = []
    for index, (ts, is_client, _, raw) in enumerate(out, 1):
        _, length, _, code, client_id, ext1, ext2 = struct.unpack_from(">hHhhiii", raw)
        packets.append(
            {
                "index": index,
                "isClient": is_client,
                "code": code & 0xFFFF if code < 0 else code,
                "size": length,
                "clientId": client_id,
                "extend1": ext1,
                "extend2": ext2,
                "bodyHex": raw[HEADER_SIZE:].hex(),
                "time": ts,
            }
        )
    return packets


def slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name.replace("ı", "i")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcaps", type=Path, nargs="+")
    parser.add_argument("-o", "--out", type=Path, default=Path("captures"))
    parser.add_argument("--port", type=int, default=GAME_PORT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for pcap in args.pcaps:
        packets = decode(pcap, args.port)
        target = args.out / f"{slug(pcap.stem)}.json"
        target.write_text(json.dumps(packets, ensure_ascii=False, indent=0), encoding="utf-8")
        client = sum(1 for p in packets if p["isClient"])
        print(f"{pcap.name}: {len(packets)} pacotes ({client} do cliente) -> {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
