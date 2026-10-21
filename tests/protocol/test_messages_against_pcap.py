"""Valida o ``wartune.proto`` gerado contra corpos reais capturados do servidor oficial.

Para cada amostra com mensagem conhecida: decodifica, exige que não sobrem campos
desconhecidos (sinal de número/tipo errado) e que a re-codificação gere os mesmos bytes.

``pcap_samples.json``: até 3 corpos distintos por (direção, opcode) de ``captures/tutorial_en.json`` (inglesa),
mais as amostras turcas antigas dos opcodes que a inglesa não tem (só turco: c2s 5172, 8574, 10020, 20001;
s2c 102, 4224, 4463, 4922).
"""

import json
from pathlib import Path

import pytest
from google.protobuf.unknown_fields import UnknownFieldSet

from wartune_server.protocol.registry import Direction, MessageRegistry

SAMPLES = json.loads((Path(__file__).parent.parent / "fixtures" / "pcap_samples.json").read_text())
REGISTRY = MessageRegistry.load_default()


def _known(sample: dict[str, str]) -> bool:
    return REGISTRY.message_type(int(sample["code"]), Direction(sample["dir"])) is not None


CASES = [s for s in SAMPLES if _known(s)]


def test_most_captured_opcodes_have_a_message() -> None:
    with_body = [s for s in SAMPLES if s["body"]]
    assert len(CASES) / len(with_body) > 0.8


@pytest.mark.parametrize("sample", CASES, ids=lambda s: f"{s['dir']}-{s['code']}")
def test_decode_reencode_is_byte_exact(sample: dict[str, str]) -> None:
    body = bytes.fromhex(sample["body"])
    msg = REGISTRY.decode(int(sample["code"]), Direction(sample["dir"]), body)
    assert msg is not None
    assert len(UnknownFieldSet(msg)) == 0, f"campos desconhecidos em {type(msg).__name__}"
    assert msg.SerializeToString() == body
