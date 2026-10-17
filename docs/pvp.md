# Lutas entre jogadores

Visão geral e legenda em [multiplayer.md](multiplayer.md).

## O que todos os modos têm em comum

**Mesmo fluxo de batalha do PvE** ([batalha.md](batalha.md)):

1. 157
2. o cliente manda 10007
3. 156
4. 153/75
5. 154
6. 4103

**O oponente nunca joga ao vivo.** O servidor monta uma cópia do oponente (jogador offline ou
robô), e a IA dele age. Os robôs de iniciante têm `userId 13000xxxxx`.

**Na batalha, o herói do oponente vai como NPC:**
- `type:2`
- `userId:0`
- `heroId` alto
- nome e skills do jogador copiado

**O que falta no `battle.py` atual:**
- o lado do jogador perder de verdade (hoje o dano nunca leva o jogador abaixo de 1 de vida);
- herói e pet inimigos montados a partir de um snapshot;
- 75 também para a IA inimiga;
- batalha só de pets, automática;
- limite de tempo com o 4361.

## Coliseu (desafio por ranking, battleType 16)

*(visto)* `meydan_okuma.json`

**Lista de oponentes**
- O cliente manda **8256** `{type:0}` e recebe **4169** `ChallengeInfoMsg` (#3) com:
  - `lastWinCount`
  - `challengeCount` (usados)
  - `curRank` (0 = fora do ranking)
  - `leftDay`
  - `totalCount 10`
  - `totalBuyCount`
  - 4 `simplePlayer` (robôs nível 13)

**Desafio**
- O cliente manda **8253** `{tarUserId, payType}`. Ele mesmo trava 5 s.

**Batalha**
- #6 **157** `battleType:16, mapTempId:992`. O lado 2 é o herói do oponente como NPC
  (`tempId 14010, grade 10, skills 10711/10811/11011`) mais 2 soldados.
- #8 a #12: **75** também para o herói inimigo.

**Resultado e depois da luta**
- #26: **4103** `{battleResult:1, battleScene:7}` com a EXP.
- #29: **4176** `{leftTime:600, challengeCount:1, totalCount:10, type:0}`, ou seja, 10 min de
  espera.
- #30: drop por vitória (115 e 111/83, "Şans Taşı Lv.3").
- #46: **4169** de novo, agora com `curRank:1693` (a primeira vitória coloca o jogador no ranking)
  e 4 oponentes melhores no ranking, com `avater[]`.

**Outros pedidos** *(cliente, `mvc/controler/ColosseumControler.as`)*
- **Desafio extra:** custa `min((compradas+1)*2, 10)` diamantes.
- **Recompensa de rank:**
  - o cliente manda 8329;
  - o servidor responde com o 4243;
  - no login vai o 4244.
- **Zerar a espera:** 8265 `PayTypeMsg`.
- **Reset diário:** 4202 `DataResetMsg`.
- **Histórico:** `ChallengeInfoMsg.challengeLog[]`.

**Lacunas:** não há tabela de recompensa por posição no tempinfos, e a regra de troca de posição
no ranking não foi observada.

## Torneio de fadas (battleType 35)

*(visto)* `peri_turnuvasi.json`

**Entrada e lista**
- #1: 4540, a formação.
- #2: **4176** `{challengeCount:10, type:1}`. Aqui o número é o que **resta**.
- 8256 `{type:1}` → #3 **4611** `PetChallengeInfoMsg{playerInfo{score, order}, playerPets[]}`.

**Desafio**
- O cliente manda **8724** `{tarUserId}`.

**Batalha**
- #7 **157** só com `pets`, sem heróis.
- Do #10 ao #44: só 153. A luta é 100% automática: o cliente não manda 10008 e o servidor não
  manda 75.
- #43: **4361** `{countDown:60000, damageImprove:50}`. Depois de 60 s o dano sobe 50%.
- #46: **4176** com 5 min de espera.
- #47: **4103** `{battleScene:19}`.
- #55: "Puan +5".
- #58: 4611 com o novo score e o `challengeLog`.

**Templates e outros pedidos**
- Templates:
  - `PetChallengeReward`: tipo 1 diário e tipo 2 temporada, por faixa de ranking.
  - `ConfigInfo`:
    - `Pet_Challenge_Grade=55`
    - `Pet_Challenge_Count=10`
    - `Jion_pet_challenge=50000` de ouro por tentativa extra
    - `Pet_Challenge_Default_Score_Line`
- Pedidos do cliente:
  - 8725: formação.
  - 8726: skills.
  - 5021: comprar tentativa.
  - 8728: recompensa (o servidor responde com o 4613).
  - 8727: terminar já.

## Mina de ouro (battleType 1)

*(visto)* `cevre_altin_madeni_savasi.json`. Aqui é contra a guarnição NPC de uma mina sem dono.

**Mina disponível**
- 8201 → #11 **4129**, com `wildLand` (`templateId 200409`, `occupyPlayerId:0`, `armyPawn 6505`).

**Ataque e batalha**
- O cliente manda **5160**.
- O exército marcha: 140 `updatedType 3`, de #13 a #18.
- #19: 140 com a terra em `state:4`.
- #20 a #26: batalha `battleType:1`.

**Depois da vitória**
- #32: **152** `CastleYieldMsg{wildYield}`.
- #33: 140 com a mina `occupyPlayerId` = o jogador.
- #36: 4103 `{battleScene:4}`.
- A vitória contra NPC não gastou `attackLeftCount`.

**Template e lacuna**
- Template: `MapPhysicsTempInfo` "Altın Madeni" (`SonType=2006`). `Property4` é o rendimento,
  `RefreshTime 43200`.
- Para desistir da mina, o cliente manda 5179 e o servidor responde com o 108.
- O PvP contra o dono não foi capturado. O `WildLandMsg.simpleHeroInfo` é a fonte natural da cópia
  do defensor.

## Ataque a castelo (battleType 4)

**Sem captura nenhuma** *(cliente)*.

- O ataque é o **5160** contra a posição do castelo. O cliente bloqueia o botão se
  `PlayerMsg.attackLeftCount` for 0.
- Proteção depois de ser atacado: 118 `CastleDefenseRspMsg`.
- Saque: 4382 `FightOverMoiveMsg{gp, gold, strategy}`.
- PvP contra um exército no mapa: 8488.

**Não se sabe:**
- como o defensor real vai no 157;
- a fórmula do saque;
- a honra (`geste`).

Fica por último, ou capturar antes.

## Persistência que o PvP vai pedir

- **Cópia de combate de cada jogador:** herói, skills, atributos e formação. Os snapshots do banco
  já têm quase tudo.
- **Rankings:** posição única no coliseu; score e ordem no torneio.
- **Contadores diários:**
  - usados e comprados;
  - espera de 600 s no coliseu e 300 s no torneio;
  - `attackLeftCount`;
  - reset pelo 4202.
- **Recompensas:** flags de já resgatada.
- **Mapa:** dono da mina, proteção do castelo.
