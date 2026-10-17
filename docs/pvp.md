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

**No `battle.py`** (detalhes em [batalha.md](batalha.md)): com `spec["pvp"]` o lado do jogador
perde de verdade, o herói inimigo anuncia a skill no 75 e o dano é simétrico; a batalha só de
pets é automática e manda o 4361 aos 60 s.

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

**Lacunas:** não há tabela de recompensa por posição no tempinfos (o servidor usa
`data/colosseum_rewards.json`), e a regra de troca de posição no ranking não foi observada (o
servidor troca as duas posições).

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
- Hoje o servidor não tem castelo alheio: o 5160 responde só o 140 parado e o 8488 não responde
  ([cidade-externa.md](cidade-externa.md)).

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

Feito: `arenas` (contadores, espera, pontos e formação do torneio, resgates; no snapshot),
`arena_ranks` (posição do coliseu, fora do snapshot) e `challenge_logs` (histórico), migração
0003. Falta o mapa (mina de ouro, castelo).

## O que o servidor faz

Código: `game/arena.py` (regras), `game/handlers/arena.py` (coliseu e torneio),
`handlers/lords.py`, `handlers/warfield.py`, `handlers/battle.py`. Teste: `tests/game/test_pvp.py`.

Fontes: *(visto)* captura e índice; *(cliente)* arquivo do cliente decompilado (`m2/scripts/...`);
*(dedução)* escolha nossa.

### Coliseu

| C>S | O servidor faz / responde | Fonte |
|---|---|---|
| 8256 `{type:0}` | 4169: `curRank`, `challengeCount` (usadas), `lastWinCount`, 4 oponentes, `avater` (arma/armadura), `challengeLog` (10), `leftDay`, `totalCount 10`, `totalBuyCount 10`. Fora do ranking: 4 robôs. No ranking: jogadores acima, espaçados (`rank // 30`); o 1º vê os de baixo; faltando, robôs. A lista fica na sessão: só ela pode ser desafiada. A janela só abre quando o 4169 chega. Com `noviceProcess <= 30000` (tutorial) não responde nada, como o cliente que nem abre a tela. | *(visto)* meydan_okuma #3, #46; *(cliente)* `ColosseumControler.as` |
| 8253 `{tarUserId, payType}` | Recusa (só 4176) se ainda no tutorial (`noviceProcess <= 30000`), fora da lista, em espera, em batalha ou sem tentativas. Da 11ª à 20ª cobra `min((compradas+1)*2, 10)` diamantes (`payType 0` usa o vinculado primeiro, `1` só diamante). Gasta a tentativa e grava **antes** da luta (cair não devolve). 140 `state 2`, 157 `battleType 16, mapTempId 992`, herói inimigo `type 2, userId 0, heroId 1300000000`. No fim: 3, 150, 4103 `{battleScene 7, gpBonus}`, 83 EXP, 140 `state 0`, 4176 `{leftTime 600}` (a espera conta do fim, como na captura). | *(visto)* #6, #26-#29; *(cliente)* `ColosseumModel.buyCountNeedPay` |
| 8265 `PayTypeMsg` | Zera a espera (type 0 coliseu, 1 torneio) por `ceil(s/60)*5` diamantes (`payType 2` aceita vinculado); 3 e 4176. | *(cliente)* `QueueBar.as`, `SocketSendManager.sendCoolColosseun` |
| 8329 | Recompensa da posição, uma por período de `period_days`: ouro e Ruh de `data/colosseum_rewards.json`. 4243 `{isTake false, param1 posição, param2 ouro, param3 Ruh, param4 dias}`. | *(cliente)* `TopToolsBar.as`; tabela *(dedução)* |
| 5021 | `type 1`: tentativa do torneio por `Jion_pet_challenge` de ouro (até 10/dia, *dedução*), 109 e 4176. Outros tipos (2 = chegada dos deuses) não são daqui: registrado. O coliseu compra pelo 8253. | *(cliente)* `PetChallengeController.buyChallengeCount` |
| 8635 `QuestInfo` | Lutar contra a própria cópia é ação de missão com condição 92, que não existe no tempinfos: recusado com log. | *(cliente)* `TaskFrameII.as` |
| 8590 | 4482 `{isTake false}` ("sem direito"): não há arena entre servidores. | *(cliente)* `TopToolsBar.as` |

**Ranking** (`arena_ranks`, por servidor, fora do snapshot porque muda quando outro vence): a
primeira vitória (contra robô ou jogador) entra no fim; vencer alguém acima troca as posições;
perder não muda nada. Leitura, troca e gravação sob uma trava global (`arena.RANK_LOCK`). O
atacado ganha uma linha no histórico (`challenge_logs`) sem que a sessão dele seja tocada.

**Login:** 4176 tipo 0 (usadas, espera) e tipo 1 (restantes) no 8224 `sys`; 4244 (`isTake` =
pode resgatar) com `challReward`; 4613 com `petChallengeReward`; 4481 com `crossScoreReward`.

**Reset diário:** os contadores (`arenas.day`) zeram no primeiro pedido do dia; com a tela aberta
vai o 4202 com vigor e ataques atuais (o cliente sobrescreve esses campos). No login o dia vira
em silêncio (a 4202 viria antes da 4176 da carga) e só na memória, até o próximo save.

**Robôs:** `Robot(id, nível)`; nome, sexo e herói saem do id (mesmo robô na lista e na luta).
Só há robôs guerreiros nos templates (`GameHeroTemp` HeroType 2: 11001-11030 e 14001-14030),
então acima do nível 30 eles ficam no 30. A captura tem 2 arqueiros 10202 com o robô, mas lá o
jogador também lutava com soldados; aqui ele não tem, então o robô vai sozinho, com 35% da vida e
15% do ataque do herói do jogador *(dedução, ajustado por simulação: guerreiro e mago ganham 15/15
do nível 11 ao 50; o caçador perde até o ~30 porque o ataque dele ainda sai de PhyAttack)*.

**EXP da luta:** `win_gp_per_grade`/`lose_gp_per_grade` × nível, no mesmo arquivo *(dedução: a
captura soma EXP mundial e offline, sem fórmula)*. O drop por vitória (#30) não foi reproduzido.

### Torneio de fadas

| C>S | O servidor faz / responde | Fonte |
|---|---|---|
| 8256 `{type:1}` | 4611: `playerInfo{score, order}` (o cliente monta a própria linha; o jogador não vai em `playerPets`), até 4 jogadores de pontos logo acima, robôs (3 pets nível 50, qualidade 6, ordem 500+) e o histórico. | *(visto)* peri_turnuvasi #3, #58 |
| 8256 `{type:2}` | 4619 com os 10 de mais pontos. | *(cliente)* `PetChallengeController.openChallengeTopFrame` |
| 8724 `{tarUserId}` | Exige nível `Pet_Challenge_Grade`, formação com pets, oponente da lista, sem espera e tentativas. 157 `battleType 35` só com `pets` (os do jogador com `userId` dele), automática: sem 75, 4361 `{60000, 50}` no quadro 1500. No fim: 4176 `{leftTime 300}`, 4103 `{battleScene 19}`, 83 "Puan  +5". | *(visto)* #7, #43-#47, #55 |
| 8725 `chaPos` | Só ids de pets do jogador e -1; grava e confirma com 4540 `{chaPos}`. Sem `chaPos` (os Senhores mandam assim) é ignorado. | *(cliente)* `PlayerManager.as` |
| 8726 | Skills do pet no torneio: o pet tem de ser do jogador; responde 4540 com `chaSkillIndexs`. | *(cliente)* `PetData.as` |
| 8727 | "Encerrar já" (`Battle.finish`): só para VIP ≥ `Pet_BattleOver_Grade`; sem VIP no servidor, recusado. | *(cliente)* `BattleUIView.as` |
| 8728 `{type 1/2}` | Recompensa diária/semanal de `PetChallengeRewards` pela ordem, uma por dia/semana ISO; itens na mochila (115) e 4613 `{status 1, rank}`. | *(cliente)* `PetChallengeReportFrame`; template |

**Depende do sistema de pets:** `arena.pets_of(snap)` devolve `[]` enquanto não houver pets no
servidor. Sem pets o cliente nem abre o torneio ("nopet"), e o servidor recusa formação, skills,
desafio e recompensa. O teste cobre a batalha simulando um pet. Pontos: +5 por vitória; a perda
não foi observada e não tira pontos; os do atacado não mudam *(dedução)*. A vida e o ataque dos
pets são aproximados do que a captura mostra.

### Eventos fechados

| C>S | Resposta | Por quê |
|---|---|---|
| 8711 | 4529 processo 0, sem campeões | Senhores (Warlords) é torneio entre servidores com agenda; sem ela, o cliente recusa a sala ("não aberto") *(cliente)* `WarlordsManager.as` |
| 8714, 8710 | 4530 processo 0 e 4536 (expulsa da sala) | o 8714 repete a cada 5 s até o 4530 |
| 8715, 8716 | 4531 vazio (nada é cobrado) | |
| 8718 / 8721 | 4532 / 4537 vazios | |
| 8717, 8720 | nada (o cliente não espera) | o 8720 só aparece depois de um 4533, nunca mandado |
| 8979, 8975, 8976, 8981 | 4799 `{isOpen false, isSign false, isOver true}` | Senhores de casal; o botão já é escondido no cliente (`MATELORD`) |
| 8337 | 4255 vazio | classificação do campo de batalha |
| 8332, 8334, 8338 | nada | campo de batalha (campanhas 4001-4013, mapa com times): sem 125 o cliente não troca de cena |
| 8633 | nada | mina de ametista (campanha 30000): o botão só aparece com 4549/4422, nunca mandados |

No login (8224 `sys`): 4776 com a agenda dos Senhores no passado e 4535 processo 0; **4248 com
`state 1` para 4001-4013** (o padrão do cliente é 0 = aberto, e o botão apareceria no nível 30).
Abrir de verdade depende do mapa de campanha compartilhado (campo e mina) e de agenda/servidores
cruzados (Senhores).
