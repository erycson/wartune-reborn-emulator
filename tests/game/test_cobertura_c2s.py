"""Todo opcode que o cliente manda (opcodes.json: mensagem C>S ou ``client_sends``) tem handler."""

import json
from importlib import resources

from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.game.router import router


def test_every_client_opcode_has_a_handler() -> None:
    raw = resources.files("wartune_server.protocol.data").joinpath("opcodes.json").read_text(encoding="utf-8")
    sent = sorted(int(code) for code, op in json.loads(raw).items() if op.get("c2s") or op.get("client_sends"))
    assert len(sent) > 400  # o arquivo regenerado não pode perder códigos sem ninguém ver
    assert [c for c in sent if router.get(c) is None] == []
