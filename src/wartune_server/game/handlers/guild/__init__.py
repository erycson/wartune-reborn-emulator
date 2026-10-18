"""Guilda (consortia): criar, entrar, sair, cargos, textos, listas, contribuição, melhorias,
habilidades, mercado, bênção do altar, baú e eleição. Estado em ``game/guild.py``; fluxo e fontes
em docs/guilda.md. As atividades (altar do demônio, terra secreta, guerra) ficam em
``handlers/guild_events.py``.
"""

from . import altar, box, election, info, members, upgrades  # noqa: F401  (registram os handlers)
from .box import add_to_box
from .common import CREATE_GOLD, R_FAIL, R_GUILD, R_LIMIT, R_NO_PLAYER, R_OK
from .upgrades import shop_buy

__all__ = ["CREATE_GOLD", "R_FAIL", "R_GUILD", "R_LIMIT", "R_NO_PLAYER", "R_OK", "add_to_box", "shop_buy"]
