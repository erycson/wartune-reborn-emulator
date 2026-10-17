from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.game.router import router

# todos os C>S de eventos/atividades/recompensas/VIP/minigames (docs/eventos.md)
CODES = [8586, 8266, 8496, 8749, 8234, 8235, 8322, 8518]
CODES += [8288, 8289, 8290, 8291, 8298, 8729, 8730, 8731, 8732, 8574, 8634, 8866, 9602, 8751, 8703]
CODES += [8722, 8723, 8540, 9523, 8994, 8629, 8630, 8534, 9645]
CODES += [8505, 8513, 8519, 8521, 8756, 8582]
CODES += [8320, 8321, 8466, 8467, 8748, 8750, 9500, 9501, 9502, 9503, 9507, 9508, 9509, 9510, 9513]
CODES += [9515, 9516, 9517, 9520, 9521, 9522, 9610, 8638, 8639, 8640, 9638, 8604, 9550]


def test_every_event_opcode_has_a_handler() -> None:
    assert [c for c in CODES if router.get(c) is None] == []
