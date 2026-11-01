"""Taxas sem fonte no cliente (``game_settings.taxas``, migração 0124). O padrão é o valor da migração, para um banco
sem a linha não quebrar; o banco manda."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

DEFAULTS: dict[str, Any] = {
    "mount_star_bless": 10,
    "mount_star_chance": 5,
    "fate_stone_exp": 1,
    "fate_wheel": {"1": 144, "2": 90, "3": 63, "4": 45, "10": 18},
    "pet_advance_bless_chance": 10,
    "pet_enchant_gain": [1, 10],
    "pet_skill_weights": {},
    "pet_mould_bless_reset": True,
    "offer_quality_weights": [40, 30, 15, 10, 5],
    "star_free_point": True,
    # 0134
    "rune_diamond_multiplier": {"1": 85, "2": 8, "5": 4, "10": 2, "20": 1},
    "vp_reset_days": 3,
    # 0135
    "pet_max_buy": 10,
    "robot_hp": 0.35,
    "robot_attack": 0.15,
    "enemy_cast_ms": 3500,
    # 0138: [Profile da carta, peso] por kit de invocador
    "summoner_kits": {"2131016": [[1, 80], [2, 20]], "2131017": [[2, 80], [3, 20]], "2131018": [[3, 80], [4, 20]]},
    # 0139: EXP que cada carta repetida dá ao ser engolida (9505 op 3)
    "card_burn_gp": 1,
    # 0140: peso de cada qualidade do minério da coleta do campo de batalha
    "field_ore_weights": {"superior": 1, "normal": 1, "inferior": 1},  # 0144: uniforme
    # 0141: guardião do campo: distância (em casas) em que persegue e os pontos perdidos para ele
    "field_guardian_range": 26,
    "field_guardian_loss": 150,
    # 0142: frases de sequência de abates, onda de renascer e passo do exército no campo
    "field_streaks": [[3, "spree"], [4, "dominating"], [5, "unstoppable"], [7, "god"], [8, "reaper"]],
    "field_streak_stop": 4,
    "field_respawn_period": 35,  # 0147: a grade dos renascimentos de 01/11
    "field_move_speed": 10,
    # 0143: fator da velocidade de quem carrega minério
    "field_carry_speed": 0.5,
    # 0149: diferença de placar que encerra o campo antes da hora (ajuda do cliente) e pontos do guardião vencido
    "field_score_gap": 5000,
    "field_guardian_points": 20,
    # 0150: anel (Run Circuit Quest): alvo do "Eliminate", soma por rodada de varredura e os itens do "Fetch"
    "ring_eliminate_targets": [20, 30],
    "ring_eliminate_per_round": 18,
    "ring_fetch_items": [[2, 2013503]],
}


def get(settings: Mapping[str, Any], name: str) -> Any:
    return (settings.get("taxas") or {}).get(name, DEFAULTS.get(name))
