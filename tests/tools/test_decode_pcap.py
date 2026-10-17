import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from decode_pcap import Flow, decode_flow  # noqa: E402

from wartune_server.protocol.cipher import StreamCipher
from wartune_server.protocol.packet import Packet


def test_recovers_the_key_mid_session_and_after_a_lost_segment() -> None:
    """Captura que começa no meio da sessão (chave desconhecida) e perde um segmento no meio."""
    cipher = StreamCipher(bytes([9, 200, 33, 71, 150, 4, 88, 250]))
    packets = [Packet(100 + n, bytes(range(n * 7 % 50)), client_id=777, extend2=n % 3).encode() for n in range(12)]
    wire = [cipher.encrypt(p) for p in packets]
    flow = Flow(is_client=False)
    seq = 1000
    for n, chunk in enumerate(wire):
        if n not in (0, 5):  # o 0 é antes da captura começar; o 5 se perdeu
            flow.segments[seq] = (chunk, float(n))
        seq += len(chunk)
    got = [raw for _, _, raw in decode_flow(flow)]
    assert got == [p for n, p in enumerate(packets) if n not in (0, 5)]
