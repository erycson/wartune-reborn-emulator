"""anúncios agendados (Sylph Atoll) e chances dos sorteios no banco

``scheduled_announcements``: um 83 para todos os online em cada horário (hora do jogo). Vem com o Defend Sylph Atoll:
os dois 83 canal 12 da captura do oficial inglês (#3029/#3030, nessa ordem) 5 min antes de cada ataque, e o início e
o fim com os textos do ``language.txt`` inglês. Os horários são escolha do dono (configuráveis): o padrão segue o
help do cliente ("Every day from 01:00, the Sylph Atoll attacks every 3 hours") e a captura (#3029 às 18:55, entre os
4234 de 18:55:01 e 18:56:02, antes do ataque das 19:00). Duração de 30 min: escolha nossa.

``vip_wheel_prizes.weight``: peso de cada prêmio da roleta VIP (padrão 1 = uniforme, como antes). ``game_settings``
ganha os pesos que eram constantes inventadas no código: estrelas (``star_weights``, ``star_open_next``) e labirinto
de gemas (``gem_maze_reward_weights``). Como editar: ``docs/configuracao.md``.

Revision ID: 0036
Revises: 0034
Create Date: 2026-10-19 12:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0036"
# ponytail: aponta para a 0034 enquanto a 0035 (outro trabalho em paralelo) não entra; trocar para "0035" no merge
down_revision = "0034"
branch_labels = None
depends_on = None

CAPTURE = "(visto) captura do oficial inglês tutorial_en"
LANG = "(cliente) language.txt inglês (res134)"
HELP = f"{LANG} PetBossInfoView.boss.helpContent: 'from 01:00, the Sylph Atoll attacks every 3 hours'"
OWNER = "horário: escolha do dono, configurável"
ATTACKS = range(1, 24, 3)  # 01:00, 04:00, ..., 22:00


def _at(minute_offset: int) -> str:
    """Os 8 horários do dia, ``minute_offset`` minutos depois de cada ataque (negativo = antes)."""
    return ",".join(f"{(h * 60 + minute_offset) // 60 % 24:02d}:{(h * 60 + minute_offset) % 60:02d}" for h in ATTACKS)


SYLPH = "sylph_atoll"
# (nome, horários, canal, userType, isCenterTip, texto, fonte)
ANNOUNCEMENTS = [
    # #3029: aspas curvas e 36 espaços no fim, como o oficial mandou
    (SYLPH, _at(-5), 12, 1, True, "Sylph Atoll echoes, “Humans, how foolish you are!”" + " " * 36,
     f"{CAPTURE} #3029 (83 canal 12, otherId -1, userType 1, isCenterTip); {OWNER} ({HELP}; #3029 às 18:55)"),
    (SYLPH, _at(-5), 12, 1, False, "Defend Sylph Atoll event is starting soon. Sylphs here have hidden themselves.",
     f"{CAPTURE} #3030 (logo depois do #3029, isCenterTip falso); {OWNER}"),
    (SYLPH, _at(0), 12, 1, False, "Defend Sylph Atoll event has started.",
     f"{LANG} yishi.manager.BaseManager.PetBossIsOpen; canal e flags (dedução) como o #3030; {OWNER} ({HELP})"),
    (SYLPH, _at(30), 12, 1, False, "Defend Sylph Atoll event has ended",
     f"{LANG} 1ª linha de yishi.manager.BaseManager.petBoss.reportStr (o resto é o relatório do time); "
     f"{OWNER}: 30 min de evento (dedução)"),
]  # fmt: skip
OURS = "(dedução) escolha nossa, configurável"
SETTINGS = [
    (
        "star_weights",
        {"1": [40] * 5, "2": [35, 33, 30, 27, 24], "3": [18, 21, 24, 27, 30], "4": [5, 8, 11, 14, 17],
         "5": [0, 2, 4, 6, 8], "7": [0, 0, 0, 0, 1], "6": [2] * 5},
        f"{OURS}: peso por Profile da starTempInfos (chave) e cristal 0..4 (posição), a olho da kader_sistemi.json",
    ),
    ("star_open_next", 0.3, f"{OURS}: chance (0 a 1) de o sorteio acender o cristal seguinte"),
    (
        "gem_maze_reward_weights",
        [1, 1, 1],
        f"{OURS}: peso de cada prêmio do labirinto de gemas, na ordem 2060008 x1, 208027 x1, 208014 x2 (os vistos)",
    ),
]  # fmt: skip


def upgrade() -> None:
    with op.batch_alter_table("vip_wheel_prizes") as batch:
        batch.add_column(sa.Column("weight", sa.Float(), server_default="1", nullable=False))
    table = op.create_table(
        "scheduled_announcements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), server_default="", nullable=False),
        sa.Column("times", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("weekdays", sa.String(length=32), server_default="", nullable=False),
        sa.Column("channel", sa.Integer(), server_default="12", nullable=False),
        sa.Column("user_type", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_center_tip", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("text", sa.Text(), server_default="", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("source", sa.String(length=1000), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_announcements")),
    )
    keys = ("name", "times", "channel", "user_type", "is_center_tip", "text", "source")
    op.bulk_insert(table, [dict(zip(keys, row, strict=True)) for row in ANNOUNCEMENTS])
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": k, "value": json.dumps(v), "source": s} for k, v, s in SETTINGS])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([k for k, _, _ in SETTINGS])))
    op.drop_table("scheduled_announcements")
    with op.batch_alter_table("vip_wheel_prizes") as batch:
        batch.drop_column("weight")
