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
perde de verdade, o herói inimigo anuncia a skill no 75 e o dano é a mesma fórmula dos dois lados; a batalha só de
pets é automática e manda o 4361 aos 60 s.

## Coliseu (desafio por ranking, battleType 16)

*(visto)* só turco: `meydan_okuma.json` (os `#N` desta seção são dela)

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
- #30: drop por vitória (115 e 111/83, "Lvl. 3 Luck Stone").
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

*(visto)* só turco: `peri_turnuvasi.json` (os `#N` desta seção são dela)

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
- #55: "Puan +5" (texto turco; sem versão inglesa).
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

*(visto)* inglesa (`tutorial_en.json`, missão 60). Aqui é contra a guarnição NPC de uma mina sem dono.

**Mina disponível**
- 8201 → #718 **4129**, com `wildLand` (`templateId 200410`/`200409`, `occupyPlayerId:0`, `armyPawn 6505`).

**Ataque e batalha**
- O cliente manda **5160** (#723).
- O exército marcha: 140 `updatedType 3`, #721-#725.
- #726: 140 com a terra em `state:4`.
- #727 a #742: batalha `battleType:1`, fim no 4103 `{battleScene:4}` (#742).

**Depois da vitória**
- #751: **152** `CastleYieldMsg{wildYield}`.
- #752: 140 com a mina `occupyPlayerId` = o jogador.
- A vitória contra NPC não gastou `attackLeftCount` (5 em #14 e #755).

**Template e lacuna**
- Template: `MapPhysicsTempInfo` "Gold Mine" (`SonType=2006`). `Property4` é o rendimento,
  `RefreshTime 43200`.
- Para desistir da mina, o cliente manda 5179 e o servidor responde com o 108.
- O PvP contra o dono não foi capturado. O `WildLandMsg.simpleHeroInfo` é a fonte natural da cópia
  do defensor.

## Ataque a castelo (battleType 4)

**Sem captura de castelo de jogador** *(cliente)*; a inglesa #1648-#1700 tem o ataque ao castelo-robô (5160, 157 `battleType 4`, `mapTempId 993`).

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

### Botão de PvP

| C>S | O servidor faz / responde | Fonte |
|---|---|---|
| 8294 | 4201 `MatchStateMsg{matchState}`: `true` com a janela do PvP aberta agora (`game_settings.pvp_match`: horas no fuso do jogo, padrão 12h, e duração em segundos, padrão 3600), `false` fora dela. O 20008 manda o 4201 sozinho quando a janela abre ou fecha (o primeiro tique só guarda). Sem corpo, nada cobrado | *(visto)* oficial_20261023-153200-1 #2231 (4201 `true` às 12:00, nível 12, sem pedido); *(cliente)* `TopToolsBar.sendMatch`/`showPVP`: o botão só aparece com `grades >= 22` e `isPVPStart`; *(dedução)* a duração de 1 hora (o fechamento não está na captura) |

### Coliseu

| C>S | O servidor faz / responde | Fonte |
|---|---|---|
| 8256 `{type:0}` | 4169: `curRank`, `challengeCount` (usadas), `lastWinCount`, 4 oponentes, `avater` (do líder: arma, armadura e a moda: asa, arma, roupa, chapéu; com a moda escondida, só arma e armadura), `challengeLog` (10), `leftDay`, `totalCount 10`, `totalBuyCount 10`. Fora do ranking: 4 robôs. No ranking: jogadores acima, espaçados (`rank // 30`); o 1º vê os de baixo; faltando, robôs. A lista fica na sessão: só ela pode ser desafiada. A janela só abre quando o 4169 chega. Com `noviceProcess <= 30000` (tutorial) não responde nada, como o cliente que nem abre a tela. | *(visto)* só turco: meydan_okuma #3, #46; *(cliente)* `ColosseumControler.as` |
| 8253 `{tarUserId, payType}` | Recusa (só 4176) se ainda no tutorial (`noviceProcess <= 30000`), fora da lista, em espera, em batalha ou sem tentativas. Da 11ª à 20ª cobra `min((compradas+1)*2, 10)` diamantes (`payType 0` usa o vinculado primeiro, `1` só diamante). Gasta a tentativa e grava **antes** da luta (cair não devolve). 140 `state 2`, 112 das missões "Challenge" (condição 35, Para1 1: 2, 4 e 188), 4152 (leed 19), 157 `battleType 16, mapTempId 992`, herói inimigo `type 2, userId 0, heroId 1300000000`. No fim: 3, 4103 `{battleScene 7, gpBonus}`, 83 EXP, 140 `state 0`, 4176 `{leftTime 600}` (a espera conta do fim), e um item sorteado de `game_settings.arena_challenge_items` (0072: VIP Token x1 no inglês, Lvl. 3 Luck Stone x1 no turco) com 115, 111 e 83 "Received: VIP Token x1". Sem 150. | *(visto)* oficial_20261023-215937-1 #1129-#1133, #1163-#1181; só turco: meydan_okuma #6, #26-#29; *(cliente)* `ColosseumModel.buyCountNeedPay`. TODO(inventado): o resto do conjunto, pesos iguais, só vitória e 1 por dia |
| 8265 `PayTypeMsg` | Zera a espera (type 0 coliseu, 1 torneio) por `ceil(s/60)*5` diamantes (`payType 2` aceita vinculado); 3 e 4176. Com VIP (`vipCoolPrivilege`) é grátis e sai só o 4176: o cliente nem abre o quadro do custo. | *(cliente)* `QueueBar.as`, `SocketSendManager.sendCoolColosseun`, `ColosseumFrame`, `PetChallengeCDView` |
| 8329 | Recompensa da posição, uma por período de `period_days`: ouro e Daru de `data/colosseum_rewards.json`. 4243 `{isTake false, param1 posição, param2 ouro, param3 Daru, param4 dias}`. | *(cliente)* `TopToolsBar.as`; tabela *(dedução)* |
| 5021 | `type 1`: tentativa do torneio por `Jion_pet_challenge` de ouro (até 10/dia, *dedução*), 109 e 4176. Outros tipos (2 = chegada dos deuses) não são daqui: registrado. O coliseu compra pelo 8253. | *(cliente)* `PetChallengeController.buyChallengeCount` |
| 8635 `QuestInfo` | Lutar contra a própria cópia é ação de missão com condição 92, que não existe no tempinfos: recusado com log. | *(cliente)* `TaskFrameII.as` |
| 8590 | 4482 `{isTake false}` ("sem direito"): não há arena entre servidores. | *(cliente)* `TopToolsBar.as` |

**Ranking** (`arena_ranks`, por servidor, fora do snapshot porque muda quando outro vence): a
primeira vitória (contra robô ou jogador) entra no fim; vencer alguém acima troca as posições;
perder não muda nada. Leitura, troca e gravação sob uma trava global (`arena.RANK_LOCK`). O
atacado ganha uma linha no histórico (`challenge_logs`) sem que a sessão dele seja tocada.

**Hero Rankings** (`HeroRankFrame`): o cliente baixa o `challengeorder.xml` do site do jogo (`TEMPLATE_PATH`, zlib).
Com `WARTUNE_RANKING_XML_DIR` o servidor grava ali os 20 primeiros do `arena_ranks` (`game/rankings.py`: `curRank`,
`order` = posição por EXP, guilda e VIP; robôs ficam fora); sem ela, fica o arquivo do oficial do espelho. Os títulos
do `ColosseumSelfView` (o mais forte e o mais forte de cada classe) e a aba 2 do ranking (`SortController`) leem o
`fight.xml`, que o espelho não tem: o servidor grava os 100 de maior `fighting_capacity` (o poder gravado na saída do
jogo) como `<PlayerFight>` com `nikcName`/`fightCapaity` (sic), `job` = template do líder e `<info createDate>`.

**Login:** 4176 tipo 0 (usadas, espera) e tipo 1 (restantes) no 8224 `sys`; 4244 (`isTake` =
pode resgatar) com `challReward`; 4613 com `petChallengeReward`; 4481 com `crossScoreReward`.

**Reset diário:** os contadores (`arenas.day`) zeram no primeiro pedido do dia; com a tela aberta
vai o 4202 com vigor e ataques atuais (o cliente sobrescreve esses campos). No login o dia vira
em silêncio (a 4202 viria antes da 4176 da carga) e só na memória, até o próximo save.

**Robôs:** `Robot(id, nível)`; nome, sexo e herói saem do id (mesmo robô na lista e na luta).
Só há robôs guerreiros nos templates (`GameHeroTemp` HeroType 2: 11001-11030 e 14001-14030),
então acima do nível 30 eles ficam no 30. A captura (só turco: meydan_okuma) tem 2 arqueiros 10202 com o robô, mas lá o
jogador também lutava com soldados; aqui ele não tem, então o robô vai sozinho, com 35% da vida e
15% do ataque do herói do jogador *(dedução, ajustado por simulação: guerreiro e mago ganham 15/15
do nível 11 ao 50; o caçador perde até o ~30 porque o ataque dele ainda sai de PhyAttack)*.

**EXP da luta:** `win_gp_per_grade`/`lose_gp_per_grade` × nível, no mesmo arquivo *(dedução: a
captura turca soma EXP mundial e offline, sem fórmula)*. O drop por vitória (meydan_okuma #30, só turco; VIP Token na oficial_20261023-215937-1 #1168) é o `_prize` (0072).

### Torneio de fadas

| C>S | O servidor faz / responde | Fonte |
|---|---|---|
| 8256 `{type:1}` | 4611: `playerInfo{score, order}` (o cliente monta a própria linha; o jogador não vai em `playerPets`), até 4 jogadores de pontos logo acima, robôs (3 pets nível 50, qualidade 6, ordem 500+) e o histórico. | *(visto)* só turco: peri_turnuvasi #3, #58 |
| 8256 `{type:2}` | 4619 com os 10 de mais pontos. | *(cliente)* `PetChallengeController.openChallengeTopFrame` |
| 8724 `{tarUserId}` | Exige nível `Pet_Challenge_Grade`, formação com pets, oponente da lista, sem espera e tentativas. 157 `battleType 35` só com `pets` (os do jogador com `userId` dele), automática: sem 75, 4361 `{60000, 50}` no quadro 1500. No fim: 4176 `{leftTime 300}`, 4103 `{battleScene 19}`, 83 "Puan  +5". | *(visto)* só turco: peri_turnuvasi #7, #43-#47, #55 |
| 8725 `chaPos` | Só ids de pets do jogador e -1; grava e confirma com 4540 `{chaPos}`. Sem `chaPos` (os Senhores mandam assim) é ignorado. | *(cliente)* `PlayerManager.as` |
| 8726 | Skills do pet no torneio: o pet tem de ser do jogador; responde 4540 com `chaSkillIndexs`. | *(cliente)* `PetData.as` |
| 8727 `{battleId}` | "Encerrar já" (`Battle.finish`): só VIP ativo (`is_vip`: data de fim do VIP no futuro) com nível ≥ `Pet_BattleOver_Grade` (3) e a luta do torneio. VIP vencido não conta, mesmo com nível 3. Senão, recusado sem resposta. | *(cliente)* `BattleUIView.as` (`IsVipAndNoExpirt` e `VipGrade` >= 3, o mesmo valor do template); VIP de `handlers/vip.py` |
| 8728 `{type 1/2}` | Recompensa diária/semanal de `PetChallengeRewards` pela ordem, uma por dia/semana ISO; itens na mochila (115) e 4613 `{status 1, rank}`. | *(cliente)* `PetChallengeReportFrame`; template |

**Pets:** `arena.pets_of(snap)` lê `snap.pets` (tabela `pets`, em [heroi-exercito.md](heroi-exercito.md)).
A formação guarda o espaço de cada pet (`chaPos`, `slot`); do lado do jogador, `pos` = espaço + 1
*(visto)* só turco: peri_turnuvasi #7. O pet do oponente segue a ordem da formação (`pos` = índice + 3, sem captura que diga).
Os dois lados usam os pets gravados: o do oponente vem do snapshot da sessão dele ou, se estiver
offline, do banco (como o coliseu faz com o herói). A batalha usa grau, qualidade e skills do
próprio pet (`change_skills`, formato da peri_turnuvasi #1, só turco, `735101,731001,...`; sem ele, as do template). Sem nenhum pet o cliente nem abre
o torneio ("nopet"), e o servidor recusa formação, skills, desafio e recompensa. Nada no servidor
cria pets ainda: ganhar um é do sistema de pets (item, missão), não deste torneio. Pontos: +5 por
vitória; a perda não foi observada e não tira pontos; os do atacado não mudam *(dedução)*. A vida
e o ataque dos pets são aproximados do que a captura mostra (`pet_hp`, ataque = vida / 14).

### Eventos fechados

| C>S | Resposta | Por quê |
|---|---|---|
| 8711 | 4529 processo 0, sem campeões | Senhores (Warlords) é torneio entre servidores com agenda; sem ela, o cliente recusa a sala ("não aberto") *(cliente)* `WarlordsManager.as` |
| (4538 S>C) | nunca mandado | Aviso do fim da Class Wars a todos: (visto) 183522 #9514 "The Class Wars have ended! Artemis ranked number 27. Their entire server has gained a 7 day blessing!"; (cliente) `WarlordsManager.__getFinalNoticeHandler` lê `PropertyMsg.param4` e mostra no canal 12 com corneta grande. Sem Class Wars aqui (entre servidores, fechada) não há fim nem ranking para anunciar |
| 8714, 8710 | 4530 processo 0 e 4536 (expulsa da sala) | o 8714 repete a cada 5 s até o 4530 |
| 8715, 8716 | 4531 vazio (nada é cobrado) | |
| 8718 / 8721 | 4532 / 4537 vazios | |
| 8717, 8720 | nada (o cliente não espera) | o 8720 só aparece depois de um 4533, nunca mandado |
| 8979, 8975, 8976, 8981 | 4799 `{isOpen false, isSign false, isOver true}` | Senhores de casal; o botão já é escondido no cliente (`MATELORD`) |
| 8633 | mina (abaixo) | mina de ametista (campanha 30000) |

## Campo de batalha (4002, 4005, 4007) — `handlers/warfield.py`, `game/battlefield.py`

Tudo das capturas inglesas 152321 (4005 #9474-#11704, 4007 #14230-#16396), 121453 (4002 #8285-#10568) e 20261101-165308-1 (4003 #3831-#7846, uma partida inteira). Os 11 Campaigns Types 5 "Battleground" (4001 11:00 a 4011 21:00) abrem; os 4 vistos têm os mesmos 28 nós.

- **Entrada (8332)**: 140, 125 (isCross), 21 (com guilda e `teamId`), 127 (28 nós, iguais nos três campos; no 4002 os
  guardiões 13-18 do time 2 vivos, state 1), 4252 a todos, 4175 com o estado de cada um, 150; missão 44. Nasce no
  acampamento do lado: time 1 em 179,75, time 2 em 17,76 (nós 001/002). Pontos pessoais começam em 100. Lado: o de
  menos gente; empatados, sorteio (decisão do usuário: o oficial cruza servidores e as capturas não mostram a regra).
- **4252**: `teamId`, pontos, `order` 0, `geste` = honra total do personagem, abates; `one` = time 1, `two` = time 2
  (gente e pontos do lado); sem `leftTime`. Vai a todos no campo a cada mudança.
- **Pontos do lado**: só sobem com entregas e ganhos no PvP; entrar não soma e perder não desconta.
- **Coleta/entrega**: nós 005-009 (91/2380); a qualidade é sorteada na coleta (`taxas.field_ore_weights`,
  uniforme desde a 0144, decisão do usuário); entrega no "Resource Recovery Officer" do lado (011 time 1, 012 time 2):
  superior 30/3/3, normal 20/2/2, inferior 10/1/1 (pontos/honra/shards). Ordem: 4175, 4252, 4471, 3, 115, 111, 83,
  4252, 4269. A honra entra no geste na hora e no 4471 (honra do dia, `event_state honor_day`; o login e a guerra
  de guildas usam o mesmo contador).
- **PvP (8334)**: o alvo recebe 111 "X is attacking you!" e 83 com o link; perdedor perde `ceil(15%)`, vencedor
  ganha `20 + pontos do perdedor // 20`, 10 de honra e 10 pontos de PvP entre servidores (texto ", Cross-server PvP
  points +10"). O perdedor vai ao acampamento, 4175 state 1 (3 se carrega; o minério fica) por 25 s e renasce
  (4175 state 0/2) na próxima onda de `taxas.field_respawn_period` s desde a abertura (0147: 35 s; na de 01/11 os renascimentos de três exércitos caem numa grade de ~35,3 s, dois mortos em momentos diferentes renascem juntos em #4669/#4413, e o `leftTime` é o tempo até a onda arredondado a 5 s: 30, 15, 5, 25, 20, 0. Por isso uma morte renasce na hora e outra espera quase 30 s). Até lá
  fica na base do lado (x >= 165 no time 1, <= 38 no time 2, os portões): o 5124 morto é cortado no último passo
  dentro dela e o 4104 devolve a posição (decisão do usuário; `bf.in_base`).
  Frases a todos (111 e 83 com link): primeiro sangue, sequência sem morrer (`taxas.field_streaks`: 3 spree,
  4 dominating, 5-6 unstoppable, 7 god, 8+ Grimm Reaper) e "has put a stop to X's domination!" (sequência >=
  `field_streak_stop`). Morto não sai pelos portões 121/122 ("You cannot leave camp when dead!"). Vivo não entra na base inimiga: 5125 na entrada 123/124 (masterType 131, param1 = dono) do outro lado dá 111 "Unable to enter the enemy faction's base." (01/11 #6130, #6921-#6998). Alvo do 8334 dentro da base dele: o mesmo aviso e sem luta (*inventado*, pedido do usuário).
- **Guardiões** (4002): o vivo do outro lado a até `taxas.field_guardian_range` casas (0141/0144: 26; as duas perseguições de 121453, 4105 #10205 com o
  jogador a 24 casas no fim do trecho e #10435 a 26 no começo; a 37 não perseguiu) da posição real (o trecho do
  5124 andado a `taxas.field_move_speed` casas/s, 0142; metade carregando minério, `field_carry_speed` 0143, visto #9958) persegue: 4105, 4494,
  128 nodeState 4, 157 tipo 32; na derrota 4104, 4103, 4122 de volta ao ponto, 4175 morto, 128 nodeState 1, 4494,
  4269 e "You lost: 150 Points." (`taxas.field_guardian_loss`). Vitória (01/11 #6197, #6359: o jogador 102 venceu os dois Morkan Knight): 128 nodeState 8, o guardião some. No 4003 só os Morkan Knight 21/22 (time 1) estavam vivos na entrada.
- **Oficial inimigo** ("Resource Recovery Officer" do outro lado, nós 011/012, heroTempId 24999/25000; o jogador o viu como nível 99 <Battleground Commander>): chegar nele (5125) luta sem 4105, 128 nodeState 4 e 157 tipo 32 (01/11 #4031-#4034); a derrota é a do guardião (4175 morto, 128 nodeState 1, "You lost: 150 Points.", #4099-#4133). Vitória não vista (*inventado*: o oficial fica de pé).
- **Fim** (StopTime): 4248 state 2, 83, 4254 (`oneTeamId` = vencedor, como o cliente lê em
  `PvpSortListView.isVictory`; linhas com `itemCount`/`winGesteCount`), 4248, 22, 4471, 3, 115, 112 (missão 50) e
  "The battle has ended! You received Insignia xN and honor xN!": vencedor 80/90, perdedor 30/30 (visto #11669 e
  121453 #10546). Empate: sem vencedor, todos 30/30. Busca
  (29/10/2026): WebSearch "Wartune battleground tie draw points" e "Wartune battleground guide rules" só trouxeram
  outros jogos e a wiki Wartune (Honor/Insignia: vitória paga mais honra, nada de empate); a página Battleground da
  wiki (breezewiki) recusou o acesso. Sem fonte, fica a regra atual.
- **8337**: 4255 com todos que entraram, na ordem de chegada, nome, abates e a honra do campo.
- **8338**: 200 Star Points (idioma `PvpMapRightView.reset`); cheio: "You already have full HP..." (#15796).
- **Mina**: na abertura 4549 true e 83 "It's Amethyst Double Time!..." (191924 #14217-#14218).

Fora do campo, na mesma captura: "Battleground Treasure Shard x5" vem das missões 758/767 (5014), "Crystaloid x80" do prêmio de 7 dias (8749) e "Circuit Quest"/"Complete Circuit Quests (n/200)" é o anel de missões (`handlers/offer.py`, progresso `CIRCUIT`). "first blood" é a frase do servidor (já feita); "...dy killing, so ?" é conversa de jogador (canal 8).

Ainda inventado: a fase da onda de renascer, o passo do exército (~10 casas/s
de um caso), a perda do guardião (um caso), a vitória contra o guardião, o 4388 `data`, o 4549 no login
dentro da janela, o limite do "stop" (um caso) e a honra/pontos extras de abate (11 e 12 uma vez, 121453 #9800).
cruzados (Senhores).
