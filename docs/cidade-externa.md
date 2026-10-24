# Cidade externa e mapa-múndi

Opcodes da cidade externa e dos sistemas que o cliente abre a partir dela: grade de exércitos, andar,
voltar ao castelo, ataque extra, mudar o castelo de lugar, gancho (8292, 8293, 8295, 8525), passe de progresso (8636,
8637) e mapa do tesouro (8744, 8745).

Código: `game/outer_city.py` (geometria do mapa e luta contra o guarda), `game/mines.py`, `game/robots.py`,
`game/bosses.py`, `game/handlers/outer_city.py`, `game/handlers/hangup.py`,
`game/handlers/singlepass.py`, `game/handlers/treasure.py`. Testes: `tests/game/test_outer_city.py` e
`tests/game/test_mundo_opcodes.py` (todo código tem handler e corpo vazio não derruba a sessão).

Fontes: *(visto)* captura oficial inglesa (`captures/tutorial_en.json`, "inglesa #N": minas da missão 60 e robô da 100
no mapa 100000042) e turcas (`captures/transfer_kampi_sistemi.json`, `captures/cevre_altin_madeni_savasi.json`, replay),
estas só no que a inglesa não tem;
*(cliente)* código decompilado (`m2`, `m3`, `m8`); *(dedução)* inferido de cliente e captura.

## O que o servidor tem

O mapa do castelo (100000xxx, modelo 100) é uma instância de cada jogador *(visto)*: inglesa #718 e, de outras contas,
replay #706 e cevre #11 (só turco) trazem as mesmas 4 minas (ids e posições) e os mesmos ids de castelo-robô
(765957 e 765958), mas a instância (100000042 na inglesa; 100000313 e 100000714 nas turcas), os 2 robôs, os ids do `armyPawn` das minas e o `createDate` mudam de uma conta para
a outra. Por isso o servidor mostra ali só o castelo e as minas do próprio jogador; ocupação de outro jogador
não aparece nem bloqueia. Nos mapas compartilhados (1 a 5) o 8201 traz os castelos dos outros jogadores nas
grades pedidas. Os 2 castelos-robô da instância existem desde a missão 100 (ver *Castelos-robô*). Não há
exércitos alheios andando. As minas dos mapas 1 a 5 existem (*Minas do mundo*), com a ocupação de todos os jogadores,
e os castelos NPC também (*Castelos NPC do mundo*; os "Köy" do mapa 2 da captura turca são esses). Pedido que depende
disso é recusado ou respondido vazio, do jeito que o cliente espera para não travar.

## Opcodes C>S

| Código | O que o servidor faz | Fonte | Depende de |
|---|---|---|---|
| 5004 | Registra. Sem resposta | *(cliente)* o cliente não lê resposta do 5004 | — (os exércitos da tela chegam pelo 169) |
| 5181 | Sem resposta própria. A grade vem no 169 do 8201 | *(visto)* inglesa #715-#719: sem S>C | — |
| 8201 | Roda o refresh (ver *Minas de ouro*). 4129 com as minas das grades pedidas (mapa modelo 100, ocupadas só pelo próprio jogador), o próprio castelo, os castelos-robô da grade (na instância) e, num mapa compartilhado (1 a 5), os castelos NPC e os de outros jogadores nas grades pedidas (`baseCastle`); depois 169 com o exército próprio se cair numa grade pedida do mesmo mapa | *(visto)* inglesa #716-#719; transfer #14-15 (só turco: no mapa 2 o 4129 traz o castelo de `asiesat` e 20 "Köy"; o 169 traz o exército dele); *(dedução)* castelo de outro jogador com os campos do próprio (a captura não tem um) | exército de outro jogador (o servidor não guarda a posição dele), terras selvagens fora das 4 minas (no mapa 2 há minas tipo 20 e bosses tipo 21) |
| 8254 | Guarda o último ponto andado (pixels // 20). 140 ×2 andando (state 1) no ponto de saída e, na chegada, 140 ×2 parado no destino (0,13 s por tile). Rota vazia, outro exército ou fora do mapa são ignorados | *(visto)* tutorial_en #774-#776 (18 tiles em 2,34 s); *(cliente)* `OuterCitySocketOutManager` | outros exércitos no mapa (4167) |
| 9525 | 4938 com os chefes do mapa pedido e o tempo até o próximo refresh (ver *Chefes do mapa*) | *(visto)* inglesa #525-#526, #709-#710 (instância, sem chefes); transfer #7-10 (só turco: mapa 2 com chefes) | luta contra chefe, monstros do mapa, névoa (4939) e caixas (4940) |
| 5161 | Volta o exército ao castelo, de graça: 98 com a posição | *(cliente)* o botão do exército não checa nada | — |
| 5160 | Roda o refresh. Treasure Cache: luta (ver *Treasure Cache*). Mina livre: luta com o guarda (ver *Minas de ouro*). Castelo-robô (tile de 765958 em (44,22) ou 765957 em (59,56), na instância) ou castelo NPC do mundo: luta com o castelo se há ataque no dia e a diferença de nível é menor que 10; senão 140 parado (ver *Castelos-robô*). Sem alvo ou mina já do jogador: 140 com o exército parado (state 0), sem luta | *(visto)* inglesa #723-#806 (minas) e #1648-#1770 (robô); *(cliente)* `CityInfoFrame.__attackHandler` e `MapPhysicsCastle.attack` mandam o 5160 com a posição do castelo; *(dedução)* parar sem alvo | castelos de jogador e exércitos alheios, terras e tesouros (precisa de captura) |
| 8488 | Registra. Sem resposta (a 157 só vem de batalha) | *(cliente)* PvP contra exército de outro jogador | exército de outro jogador no mapa |
| 8699 | Na pedreira 6001: a luta da coleta (140, 157; fim com Wood x18). Fora dela, registra | *(visto)* inglesa #1928-#2070 | — |
| 9506 | Ataque extra: `ConfigInfos` `AddAttck_Point` diamantes (395 nos templates EN, como o texto EN "Additional attack attempts cost 395 Balens"; vinculado primeiro se `type` 2), até 5 por dia. Responde PlayerMsg com `attackLeftCount`. O ataque ao castelo-robô (5160) gasta um e grava na hora | *(cliente)* `m3/.../AttackAlertFrame.as:130` (`setAddAttackCount`; o cliente só confere 98 de saldo, então abaixo do preço o servidor avisa "You don't have enough Balens!") | — |
| 5176 | Muda o castelo. Outro mapa: 200 de energia e o ponto central do mapa. Mesmo mapa com ponto: 100 de energia. Energia completada com diamantes. Resposta: 140 e 105 (mapa, posição, energia); para outro mapa as minas ocupadas são soltas e vai o 152 (rendimento sem elas) entre o 140 e o 105 (*(visto)* oficial_20261023-153200-1 #184-#187). Recusa: 105 com o castelo como está | *(visto)* transfer #2-5 (só turco: 500 para 300 de energia); *(cliente)* `WorldMapControler`, `MapPhysicsCastle` | sem outros castelos, o ponto de chegada é o centro |
| 8292 | Cancela o gancho: 4200 com `leftWeay` 0 e `isStartHangup` falso, a mesma resposta do 8293. Não cobra | *(cliente)* `HookTimeView` envia o 8292 ao cancelar | sistema de gancho da campanha (ausente) |
| 8293 | Ressincroniza o gancho: 4200 com `leftWeay` 0. Não cobra. No inglês o gancho custa `min(hookleftWeay, 200 − weary) × 10` Balens (teto de fadiga 200; o turco não tinha ×10 e o teto era 235), com `payType` 0/1 pela escolha de vinculados | *(cliente)* `m3/.../HookTimeView.as:279-291` só envia com `hookleftWeay` diferente de zero | sistema de gancho da campanha (ausente) |
| 8295 | Salas do gancho (Altar of Ennoblement, `HookFrame`): 4204 com as 9 campanhas `Types` 3 (7001-7009), `curCount` 0 e `maxCount` = `Capacity` (*dedução*); com a lista vazia o `HookItem` quebrava. É a resposta que termina o pré-carregamento do gancho | *(cliente)* `HookContorler` envia o 8295 sem corpo | ganchos de outros jogadores (ausente) |
| 8525 | Registra (convite de PK, ataque no campo de animais). Sem resposta | *(cliente)* `CampaignSocketOutManager`, `HookMapPKMediator`: o convite não espera resposta | batalha de PK no mapa da campanha (ausente) |
| 8636 | 4552 com área 1 e `maxIndex` 0 | *(cliente)* `SinglePassSocketOutManager`, `SinglePassManager` | progresso das fases (8753, 8755) |
| 8637 | Recusa a recompensa: 4552 atual | *(cliente)* a recompensa exige `maxIndex == área * 10` | progresso das fases |
| 8744 | Op 6: 4633 com a contagem. Op 1: dá um mapa de bronze (2190001) e conta no dia, até `join_tremap_count` (5), só para quem tem o nível do item (`NeedGrades` 55). Ops 2 a 5: 4633 atual | *(cliente)* `TreasureMapSocketOutManager`, `TreasureMapGetFrame`; `join_tremap_count` é a config de `ConfigInfos` que o cliente lê em `TreasureMapModel`; o nível é *(dedução)*, o cliente não tem trava para receber | pontos de tesouro no mapa (refresh, dig, use) e batalha de equipe (dig, reward) |
| 8745 | Registra. Sem resposta | *(cliente)* `TreasureMapSocketOutManager.sendReinforceTreasureMap` | mapa de tesouro de guilda |

S>C usados: 98 (`OutercityRspMsg`), 105 (`CastleReqMsg`), 140 (`MapUpdatedMsg`), 169 (`OutercityArmyUpdatedGridMsg`),
4129 (`PhysicListUpdateMsg`), 4200 (`HangupInfoMsg`), 4202 (`DataResetMsg`), 4204 (`HangupStateListMsg`, vazio), 4552 (`SinglePassMsg`), 4633
(`PlayerTreasureMsg`), 3 (`PlayerMsg`) e 115 (itens, pelo `granted`).

## Regras (`game/outer_city.py`)

- Exército parado: 2 tiles antes do castelo. `PosMoveMsg.routes` vêm em pixels: tile = pixel // 20.
- Grade: `"x_y"`, 50 × 50 tiles. A janela do cliente é de 3 × 2 células.
- Energia de teleporte: 200 para outro mapa, 100 no mesmo mapa. Completar com diamantes custa
  `ceil((máximo - atual) / 5)`, e só quando falta energia para o gasto. *(visto: 500 para 300; só turco: transfer)*
- Virada do dia às 5h (`game/daily.py`, no login e no 20008 que o cliente manda a cada ~60 s): a energia
  de teleporte volta ao máximo (151101 `Property2`, sem regenerar com o tempo), a stamina ganha +100 por
  dia que passou até o máximo (200), e a stamina de poções do dia (`PlayerMsg.wearyLimit`, teto 300 no
  cliente) zera, e a bênção da roda volta a 10% a partir do nível 41 ("Boosts will reset to 10% daily at
  5 a.m.", language `ExtraBufferSeminaryTips`). Quem está online recebe o 4202 com os valores novos e o 3; a energia vai no
  `transEnergy` (prédio -11).
- Mapas abertos: 1 pede nível 11, 2 nível 21, 3 nível 31, 4 nível 41, 5 nível 51; `-1` fica fechado
  (`WorldMapHelper.chcekMapId`).
- Tamanho do mapa: `MapInfos` `Width` e `Height` em pixels, divididos por 20. O mapa do castelo
  (100000xxx) usa o modelo 100 (Twilight Sands).

## Catálogo do mundo (migrações 0027 e 0028, `domain/world.py`)

O que existe em cada mapa fica no banco, não no código: `world_mines` (id, mapa modelo, tile, faixa de
nível, ordem do 4129), `world_mine_guards` (nível -> guarda), `world_robots`, `world_robot_names`,
`world_monster_counts` (mapa, `bossType`, quantos por ciclo) e `world_monster_power` (template ->
`fightCapaity`). A semente é o que as capturas mostram (e dedução onde não há fonte, abaixo); o servidor lê tudo
uma vez ao subir (`persistence/world_store.py`, `Services.world` e `GameContext.world`). Para trocar uma
mina ou mudar quantos monstros um mapa tem, mude as linhas e reinicie. O template de cada nível sai do tempinfos
(`MapPhysicsTempInfos` `SonType` 2006, `Grades` = nível). A mina ocupada grava o nível sorteado e o tile em
`wild_lands` (`template_id`, `pos_x`, `pos_y`): o rendimento sai da linha, então mudar o catálogo não mexe no
que já está ocupado. Ocupação de antes da 0027 ganha o nível no próximo login (`mines.backfill`).

## Minas de ouro (missão 60, `game/mines.py`)

- **Layout** *(visto)*: as 4 minas vêm das capturas, com os mesmos ids e posições para contas diferentes
  (inglesa #718; replay e cevre, só turco), então são do mapa modelo 100: 853876 (16,34), 853877 (36,34), 853874 (71,54) e
  853875 (54,64). Cada conta tem a sua cópia (ver *O que o servidor tem*). O nível não é fixo: é sorteado a
  cada refresh (abaixo). Guarda: um soldado, 6504 no nível 8 e 6505 nos níveis 9 e 10. O arquivo
  `maps/100/100.maps` não tem minas.
- **Refresh de 12 h** *(visto)*: `RefreshTime` 43200 s (`MapPhysicsTempInfos`), que sai como 43200000 no 4129
  e no 140 (inglesa #718, #726; mapa 100, fixo: na cevre, 35 min depois do `createDate`, ainda é 43200000; só no
  mapa 2 ele vem como contagem regressiva, só turco). `createDate` é o começo do ciclo, no fuso do jogo (UTC+3,
  `gameday.GAME_TZ`; só turco): replay 12:19:54 = 09:19:54 UTC, 1 s antes do primeiro pacote; cevre 19:48:57 = 16:48:57
  UTC, 73 s antes do `signDate` 19:50:10 do mesmo `asiesat` (login.json), e o relogin das 17:05 UTC não
  mudou o `createDate`. As duas fases ficam 7 h 29 min distantes, então o ciclo é do jogador
  (`Castle.mines_at`, migração 0018), não do mundo. *(dedução)* o ciclo abre no login; vencido, o seguinte
  abre no primeiro login, 8201 ou 5160 depois do fim (*ponytail*: quem fica online pode ver o oficial renovar
  na hora certa; não há captura de um refresh ao vivo). Castelo de antes da 0018: o ciclo começa na ocupação
  mais velha.
- **Nível sorteado** *(dedução)*: os sorteios vistos deram nível 9 e 10 (inglesa #718: 10, 10, 10
  e 9) e 8 (replay e cevre, só turco). Cada ciclo sorteia o nível com semente `"<jogador>:<id da mina>:<início do ciclo>"`: fica o mesmo até o
  refresh. Os templates são 200408, 200409 e 200410 (`MapPhysicsTempInfos`: `Grades` é o nível, `Property4` o
  ouro por hora). Nível fora de 8 a 10 e guarda diferente não têm captura.
- **Expiração** *(dedução)*: no fim do ciclo toda ocupação vence. Quem vira o ciclo é o `castle.settle`: todo
  acerto de ouro (5015, 8202, 8327, fazenda, caixa por tempo, mina) e o refresh do login, do 8201, do 5160 e do
  fim da luta (`handlers/outer_city.refresh`); não há tarefa periódica. O ouro até o fim do ciclo sai com a
  taxa das minas, o resto só com a dos prédios. A linha da mina fica no banco e só vale se `occupied_at` for do
  ciclo atual; ocupar de novo reaproveita a linha (a unique é `character_id, wild_id`).
- **Guia do tutorial** *(cliente)*: o m8 (`NewbieBaseActionMediator`, alvo 80) procura as minas pelos pixels
  (320,680) e (720,680), e o castelo em (520,920). Sem elas a máscara escura do passo 22500 nunca sai. Por
  isso o castelo novo nasce em (26,46), como no oficial (`GridCastlePlacement`), e a migração 0017 move
  quem ainda estava na grade antiga.
- **Luta** *(visto)* inglesa #723-#754: 140 ×2 do exército lutando, 140 da mina em luta (state 4), 157 (battleType 1,
  mapa 100, as tropas do exército em duas pilhas nas posições 3 e 9, o herói na 4, o guarda na 5; vida da
  pilha = Live × soldados / 100). Fim: 150, 4103 (cena 4), 150, 100, 140 ×2. Vencendo: a mina fica do
  jogador, 112 da missão (condição 7, Para1 2006), 4152 (Leed 9), 109, 152 com o rendimento, 140 da mina
  ocupada e 169. Perdendo: 140 da mina livre (a derrota não tem captura, ver abaixo).
- **Perda de soldados** *(visto)*: nas vitórias contra mina nenhum soldado morre (inglesa #741/#743 e #797:
  `ownPawns` 152 nos dois 150 do fim; cevre #36-39, só turco: 737 antes e depois). Derrota contra mina: *precisa de
  captura*. Na campanha os soldados morrem (replay #1711, turco: battleType 6, mapTempId 1021, pool 900 para 828;
  na inglesa a 1021 de #1187-#1202 fica com 162 antes e depois), mas essa regra
  é de outro sistema e não passa por `outer_city`.
- **Volta** *(visto)* inglesa #758-#759: o primeiro 5035 com state 3 depois da luta recebe o 4382.
- **Ouro** *(visto)*: cada mina ocupada soma `Property4` por hora no 109 (inglesa #802: 280 para 1040, mina
  nível 10 = 760). O 152 lista as minas em `wildYield` e mantém `goldYield` só com os prédios e `goldWildLandYield`
  em 0 (inglesa #751, #804).
- **0017** `wild_lands`: mina ocupada por personagem (`wild_id`, `occupied_at`), carregada em
  `PlayerSnapshot.wild_lands`. Relogar mantém a mina até o refresh.
- **0018** `castles.mines_at`: começo do ciclo de 12 h das minas do jogador.

## Castelos-robô (missões 100, 411 e 765, `game/robots.py` e `handlers/outer_city.py`)

- **Layout** *(visto)*: 765958 em (44,22) e 765957 em (59,56), no mapa da instância (inglesa #718; replay #706 e
  cevre #11, só turco: mesmos ids e tiles). Grau 8 nos dois (inglesa #718; no replay o 765958 tem 7, só turco). O
  dono (`occupyPlayerId` 13000xxxxx) e o nome mudam de uma conta para outra: inglesa Aillendre (765958,
  1300001446) e Addyn (765957, 1300001447). Sem liga e sem tempo de defesa (`defenceLefttime` 0), estado 1, `castleName` = nome.
- **Servidor** *(dedução)*: os ids e tiles são os do oficial; o dono é `ROBOT_USER_BASE + índice` (faixa dos
  robôs); o nome sai da conta (`robot_name`, sorteio com semente `robo:<conta>`; os dois robôs da conta tiram nomes distintos). O banco
  tem os 3 nomes das capturas turcas (`world_robot_names`: ♣Chloe♣, ♫Elizabeth♫, ►Abigail◄; a inglesa traz
  Aillendre e Addyn); com mais robôs que nomes, os nomes se repetem. Sem
  estado: o robô está sempre lá, não muda de dono nem some depois da vitória (não há captura disso).
- **4129** *(visto)* inglesa #718: o robô entra no 4129 da grade dele, junto com o próprio castelo.
  Só na instância do próprio castelo, pela mesma regra das minas (`robots_in` e `robot_at`, com `template_of`): nos mapas 1 a 5 não aparece nem luta.
- **Guia** *(cliente)*: a missão 100 (m8 `NewbieBaseActionMediator`, alvo 80_3) procura o castelo no pixel (880,440),
  o tile (44,22). O robô está nesse tile, então `getPhysicsByXY(880,440)` o acha (`BaseCastle` faz `_x = posX × 20`; `OuterCityModel.as` 367-386). Sem o alvo a tela escurece, como na missão 60.
- **Ataque (5160)** *(cliente)*: o `CityInfoFrame` (`sendAttack`, 28-44) manda o 5160 direto, com a posição do castelo.
  `MapPhysicsCastle.attack` (156-211) recusa com diferença de nível de 10 ou mais (linha 166) e abre o `_attackAlert`; o `attackCount` (`playerInfo`) é lido só depois, em `MapPhysicsCastle.__responseHandler` (213-229, linha 221). O clique no castelo passa também por `OuterCityModel.checkArmy` (`OuterCityModel.as` 477-521): exército existente, em estado parado ou de movimento, e mesmo mapa (ou instância contra o mapa 100). Essa checagem não conta tropas. O clique na mina (`FieldInfoFrame.as` 37) e o `CityInfoFrame` mandam o 5160 sem ela, e nenhum desses caminhos conta tropas.
  O servidor recusa com 140 parado e sem luta nos três casos (sem ataque no dia, diferença de 10 ou mais, luta em andamento).
  Com o ataque aceito, gasta um do dia (*dedução*: o contador é o do 9506, "x/5" no `AttackAlertFrame`) e grava
  logo depois de abrir a luta (junto com a devoção): cair no meio da luta não devolve o ataque.
- **Luta** *(visto)* inglesa #1656-#1657 (`oc.robot_battle`): antes da 157 vai o 140 do robô em luta
  (`updatedType` 2, `state` 4). battleType 4 no mapa 993 ("Plunder City"); as tropas e o herói do jogador como na
  mina; do lado 2 o herói `11000 + grau` (11008 "Warrior (M)": type 2, nome do robô, nível 8, vida 240, skills
  10711/10811 do `SkillScript`) na pos 6 e 2 pilhas de 10102 com 282 de vida nas pos 1 e 7. A vida das pilhas
  é a da captura (robô de grau 8, o único do catálogo).
- **Ataque** *(visto)* inglesa #1648-#1657 e oficial_20261023-171155-1 #740-#749 (`_attack_castle`): 4152 (leed 10),
  140 ×2 do exército lutando, 140 do próprio castelo, 4452 (`defenceLefttime` 0), 3 com o `attackLeftCount` já
  gasto, 140 do robô em luta e 157. Aqui o 83 da devoção vem logo depois do 4152 (no oficial, depois dos 140 do
  exército).
- **Fim** *(visto)* inglesa #1758-#1770: 150, 109, 3, 4103 (`battleScene` 6), 150, 100, 112, 148 (relatório da
  batalha), 140 ×2 do exército, 140 do robô de volta ao `state` 1 e 4382. A captura é uma derrota: `strategyBonus`
  172, as 172 tropas do exército; o PlayerMsg sobe 172 de Daru e o 4382 leva `strategy` 172.
- **Relatório (148)** *(visto: cartas 11554, 11564 e 11569 do `maillist` de oficial_20261023-171155-1)*: "Battle
  Report" de "System Mail", `MailType` 3, lido por `BattleReportHelp.covertToBattleInfo`. XML (`oc.report_contents`):
  `<infos><info type camp result playerName siteName pos mapId time /><me .../><he .../></infos>`, com
  `playerName` = `siteName` = nome do castelo, `result` 1 vitória / 2 derrota, e em `me`/`he` heroId, site1/site2
  vazios (0 mesmo perdendo tropa), `fight` (o nosso poder; o do Aladyr 1760), grade, `gold` (o saque; negativo em
  `he`) e `crystal` (a Kyanite do VIP).
- **Daru de toda luta com tropa** *(visto)*: é o número de soldados perdidos, ganhando ou perdendo (`_casualties`).
  Na inglesa: Wulfgar 88, Karlan 9, Karda 28, o robô 172 = a queda da reserva. Em `oficial_20261023-153200-1`:
  mina 116 (#1620-#1636), tesouro tipo 22 perdido 201 (#1896-#1909), mina 106 (#2004-#2017). Com perda, o 109
  (população) e o 3 saem antes do 4103, e o 4382 da volta ao mapa (5035 state 3) leva o Daru.
  O `failCount` do 4103 é o de derrotas em campanha na sessão (ver `docs/salas-campanha.md`).
- **Missão**: `quest_event(8, vitória ? 1 : 0, 1)`. Para1 0 = qualquer, então 100 e 411 avançam também na derrota
  (*visto* #1765: a 100 com `condition_1` 1 depois de perder); a 765 (Para1 1) só na vitória. A gravação do
  ataque vai em uma só save.
- **Vitória** *(visto)* oficial_20261023-171155-1 #6014-#6027 (Aladyr, grau 12): 150, 109, 3, 4103 (`goldBonus` 0,
  `strategyBonus` 100 = as perdas), 150, 100, **118** (`CastleDefenseRspMsg` x, y, `leftTime` 7200), 112, 148, 140 ×2,
  140 do castelo com `defenceLefttime` 7199, 4382 (`gold` 0). Os 4950 de ouro saqueado não vão em nenhum desses:
  entram no ouro e aparecem no 109 seguinte (#6046) e no relatório. Castelo protegido recusa ataque (o cliente
  avisa com `MapPhysicsCastle.command03`). VIP: + a Kyanite do privilégio 7 ("Bonus Kyanite from Plunder", 500 do
  VIP 4). **TODO(inventado)**: o saque nos outros graus (`npc_castles.loot_per_grade` 412,5 × grau) e a proteção
  só em memória (`Wilds.shields`; `shortcut:`).
- **Níveis** *(cliente + grau 8)*: a diferença menor que 10 deixa atacar até o nível 17. A 411 pede nível 17,
  então só passa no 17. A 765 (nível 12) passa de 12 a 17. Se o grau do oficial for outro, isso muda.
- **Não feito**: PvP contra castelo de jogador (8488 segue sem alvo, porque exército alheio não existe aqui);
  repetir a 765 (o 5012 de missão já existente é recusado, `rules.py:282`; a 765 também exige guilda, `TaskManage.checkConsortia`, 458-465; o cliente re-oferece quando a data da conclusão difere de hoje, `TaskManage.as` 531-542). ~~Gravação só no fim da
  luta~~: o ataque já é gravado ao abrir a luta.

## Chefes do mapa (9525 -> 4938, painel "Current map BOSS info")

- **Relógio** *(visto, só turco: transfer e cevre)*: transfer (mapa 2, 4828 s às 17:39:31 UTC) e cevre (instância
  do castelo, 5775 s às 17:23:44 UTC) apontam para o mesmo instante, 2026-05-21 19:00:00 UTC (22:00 no fuso do
  servidor turco). As horas
  de refresh são as do `ConfigInfos` `WorldMapFreshTime` (0,8,10,...,22) no fuso do jogo
  (`WARTUNE_GAME_TIMEZONE`), como diz o help do cliente ("every 2 hours from 08:00 to 24:00"): de 00:00 a
  08:00 não há refresh, então às 03:00 o painel mostra 5 h. O `leftBossTime` nunca vai 0: com 0 o cliente
  (`OuterCityManager.coolDownBossUpdate`) pede o 9525 de novo, a cada segundo. As duas capturas são da mesma conta.
- **Lista**: os monstros de `bossType` 3 do sorteio do mapa (abaixo). *(visto, só turco: transfer)* o bosslist do
  mapa 2 na transfer tem 5 monstros, todos de `Property1` 3 (210106, 210124, 210129 ×2, 210120), `type` 1, e o 210127
  (`bossType` 2) do 4129 da mesma sessão fica de fora: o painel é a lista dos chefes. x e y em tiles (o radar
  faz `x * 20`; o mapa 2 tem 4000 tiles). A instância do castelo vem sem chefes (inglesa #526, #710): ela não está em
  `world_monster_counts`. O chefe abatido no ciclo fica na lista com `type` 0 e o em luta com 4 (language
  `bossinfo.bossStatus0` "(Killed)", `bossStatus4` "(In battle)").
- **Inglês** *(visto, oficial_20261023-171155-1, mapa 1)*: #284-#839 (ciclo das 12:00, `leftBossTime` 2524 às 13:17:01 =
  14:00) Tauren Grand Master 10, Spirit of Wind 60, Spirit of Dark 80, Deserted Eye 60, Spirit of Fire 70; #1694-#3169
  (ciclo das 14:00, 4222 às 14:49:01 = 16:00) Tauren Grand Master 10 em outro tile, Spirit of Wind 60 **duas vezes**,
  Spirit of Light 70, Spirit of Fire 70. Confirma o sorteio por ciclo: posição e chefe mudam, com repetição de template,
  sempre 5 `type` 1; o refresh a cada 2 h na hora cheia.
- **Contadores** (`count1-3`): abates do dia que contaram, por tipo (`characters.kills_normal`, `kills_elite`,
  `kills_boss`; zeram no `daily.roll` das 5h). O cliente mostra "{0}/{1}" com o `WorldMapKill` (5,3,1).
- **Divine Light** (item 2131055, `SonType` 316, pelo 5006): gasta um e tira a névoa do mapa do castelo para
  todos (help: "anyone" que usar limpa a névoa): 4939 (`MapBossMsg` só com `leftFogTime` 20) a quem vê o mapa,
  e o 4938 do mapa leva o que sobra. Fica só no processo (`monsters.Wilds`): são 20 s. Os 20 s
  só estão na descrição do item ("Can be used to disperse the Wilds’ dark fog for 20 seconds."). O cliente
  tira a névoa com `leftFogTime` > 0 e a põe de volta quando a contagem dele zera (`OuterCityManager`).
- O abate de um chefe deixa o baú como o de qualquer monstro (ver *Monstros dos Wilds*, abaixo).

## Monstros dos Wilds (4129 type 21, `game/monsters.py`)

- **Mensagem** *(visto, só turco: transfer #14)*: 879741, template 210127 em (2268,1932) do mapa 2: `type` 21, `level` 80
  (`Grades`), `refreshTime` 0, `state` 1, `createDate` "2026-05-21 20:00:50" (o ciclo das 20:00 no fuso do
  jogo), `fightCapaity` 746796, `bossType` 2 (`Property1`), `size` 10 (`Property2`; 12 na maioria dos chefes),
  sem `armyPawn`. Vem no meio das terras (type 20), antes dos castelos.
- **Sorteio**: semente (mapa, começo do ciclo), então todo jogador vê os mesmos e um restart não muda nada,
  sem tabela de estado. A cada ciclo de `WorldMapFreshTime` (help: "in random positions") saem
  `world_monster_counts` monstros de cada tipo, com template sorteado entre os `MasterType` 21 daquele
  `Property1` (sem regra de nível por mapa: o mapa 2 da transfer, só turco, tem de nível 20 a 80) e tile a 20 da borda.
  O id é 1000000000 + mapa × 10000 + ordem: estável no ciclo e longe das minas e terras do oficial.
- **Virada com o jogador online**: o cliente guarda os wildLands por tile e só tira um com state 0 ou quando a
  vista sai da grade (`OuterCityModel.updateWildLand`, `removesNSSWildLand`); na virada ele só pede o 9525.
  Então o 20008 (a cada ~60 s) confere o ciclo e, nas grades do último 8201, manda 140 com state 0 dos
  monstros velhos e 140 com os novos (`handlers/outer_city.roll_monsters`).
- **Dedução**: 40 normais, 20 elites e 5 chefes em cada mapa de 1 a 5. Só os 5 chefes do mapa 2 foram vistos;
  o resto segue a proporção de `WorldMapKill` (5,3,1). Nada na Internet sobre isso. `fightCapaity` só do
  210127 (`world_monsters`); os outros vão 0. O tile não checa terreno (o .maps não traz a área andável).
- **Unidade** *(visto no tempinfos, pelo nome)*: o `SonType` é o avatar e não liga a nada; a ligação é o nome
  com o mesmo nível. Normais: `PawnTempInfos` 6992-6999 ("Tauren Gladiator" nível 10 ... "Void Cavalry" 80).
  Elites e chefes: `GameHeroTemp` 2978-2999, na ordem dos templates, com `AddName` "Elite" ou "BOSS· ...". O
  nome sozinho é ambíguo ("Red Claw" nível 20 tem 4 pawns), então o vínculo está em `world_monsters` (0029),
  com um teste que confere nome e nível de cada linha.
- **Luta** (5160 no tile do monstro; `_attack_monster`) *(visto: oficial_20261023-171155-1 #6916-#6960, #7227-#7238,
  #7416-#7422, 13 lutas)*: battleType 3841 (`WORLD_MAP_NPC`) no mapa, **só o herói do jogador** (sem tropa: nada
  de baixa nem Daru; pos 3 com `fightPos` 3) com o livingId seguinte ao dos inimigos; o normal em pilhas de um
  soldado com `Live` / 100 de vida (2 nas pos 2 e 8 até o nível 49, 4 nas 3, 9, 2 e 8 do 50 em diante; a fronteira
  entre o 40 e o 50 vistos é *dedução*), a elite e o chefe como herói NPC na pos 5 com o `Live` do `GameHeroTemp`
  e `fightCapacity` 0. 140 do monstro em state 4 com `curArmyId` a quem vê a grade (no chefe, o 4938 com ele em
  luta antes da 157); recusa (140 parado) se já há luta, se ele já foi abatido no ciclo ou sem unidade no
  catálogo. No 4129 o normal traz um `armyPawn` por pilha; `fightCapaity` dos 15 vistos (migração 0067). Fim:
  150, 4103 (`battleScene` 5), 150, 100, 140 ×2; vencendo,
  o abate vai para `wild_monster_kills` (chave mapa, monstro, começo do ciclo: o id se repete a cada ciclo;
  quem termina depois de outro bate na chave e não conta), o 140 dele vai em state 0 a quem vê e o 4938 sai
  com os contadores. Luta que cruza o refresh não abate: o monstro já é outro (e o 140 dele não sai, para
  não trazer de volta o que o `roll_monsters` tirou). "Em luta" fica em `monsters.Wilds` com o ciclo e só vale
  enquanto a batalha roda: a de uma sessão que caiu se desfaz sozinha. O `countDown` do 156 não limita a luta
  (é o relógio do aumento de dano, `HurtUpMode`). Derrota *(visto #7234)*: o monstro volta a state 1 e o
  exército volta para casa (140 no castelo), sem 4938.
- **Teleporte** (8326) *(visto #7307-#7310, #7469, #7541)*: até a borda do mapa (o oficial foi a 696,3793): 140 do
  exército parado, 4237 sem `mapId` com a energia que sobrou (100 por teleporte; sem energia, 100 diamantes e o
  3) e 111 "Teleportation Complete"; o exército fica no tile novo.
- **Limite e 15 níveis** (help `map.outercity.view.helpFrame.helpContent`): o limite do dia é de prêmio ("kill
  a certain number of monsters every day for rich rewards", reset às 5h), não de ataque; monstro 15 níveis
  abaixo do jogador não dá prêmio nem gasta o limite (`monsters.count_kill`). Elite e BOSS "são para equipe".
- **Morte** (internet): dá para perder. No vídeo https://www.youtube.com/watch?v=Cn6cQpeImEM o grupo de 4
  morre para o Spirit of Dark e revive no mapa ("either you appear next to the boss or ... God knows where");
  na Kongregate "I ... died near the end" (http://web.archive.org/web/20230903070232/https://www.kongregate.com/forums/12-kongregate-multiplayer-games/topics/419195-wartune-wilds-monsters);
  e perder não gasta o limite: "attempts are not used if you fail to beat em... only when you actually win
  rewards" (post #7 de http://web.archive.org/web/20201130235433/https://forum.r2games.com/forum/browser-games/wartune/news-events-aa/93675-guide-the-wilds).
  Então o lado do jogador morre, como em toda luta fora do tutorial (docs/batalha.md). Derrota: o
  monstro volta a state 1, sem abate nem contador. Perda de tropas e espera para voltar: nenhuma fonte.
- **Simulação** (personagem novato com só o nível trocado: herói com 390 de vida no "nível 20" e 990 no "nível
  80", sem equipamento, 150 lanceiros 10101; não é um jogador real): sozinho ele perde para todos de nível 20
  e 80 em 2 a 5 golpes. Sem morte venceria em 1,5 min (normal 20) a mais de 40 min (elite e chefe 80). Vida
  dos templates mantida: elite e BOSS são para grupo de até 4 (o help e o guia da R2: "parties are highly
  recommended"; os vídeos mostram 4 entrando na mesma luta).
- **Baú** (`handlers/wild_boxes.py`): o abate que conta no limite do dia (`count_kill`: dentro do limite e
  não 15 níveis abaixo) deixa um baú no tile do monstro, gravado em `wild_boxes` (sobrevive a restart), e manda
  o 4940. O cliente (m3 `OuterCityManager.onMapBossBox`, `OuterCityMap.onUpdateBox`, `OuterCityBossBoxView`)
  troca a lista inteira, desenha um `BossBoxMc<type>` por `boxId` novo, sem filtrar por mapa nem tirar os que
  saíram da lista, e o clique manda o 9526 e apaga o baú da tela. Então o 4940 leva só os baús do mapa, e vai
  *(visto: oficial_20261023-171155-1 #6969-#6971 e #7379)* na resposta do 8201 entre o 4129 e o 169, quando a
  grade pedida tem um baú (não no abate nem no 9525). "you need to click the chest yourself, the reward won't auto send to your inventory" (internet,
  fórum R2, abaixo). *(dedução)* `type` = `bossType` e o baú não expira.
- **Abrir** (9526): sorteia pela `world_monster_drops` (`monsters.loot`): cada linha do tipo e da faixa de
  nível do monstro sorteada sozinha pela `chance`, quantidade entre `min_count` e `max_count`. Dá os itens e
  moedas (o Kyanite, -600, soma nos cristais) e apaga o baú, sem 4940 *(visto #6974-#6988: 3, 109, 115, 4476,
  111 e 83 com "Wilds Slayer RewardsMystery Stone x1, 10,000 Daru, 10,000 Gold": itens primeiro, moedas do fim da
  tabela para o começo)*. Mochila cheia: o conteúdo
  vai como anexo no correio do jogo (5 por carta, na mesma transação que apaga o baú) e o aviso "Inventory full,
  check your mail!" *(cliente: `VipBoxFrame.command03` do language.txt inglês)*.
- **Tabela de queda** (semente na 0030, coluna `source` em cada linha). Nenhuma fonte publica chance nem
  tabela por nível; as chances são *(dedução)* a partir de "usually"/"can drop"/"very rarely" e dos relatos,
  as quantidades de nível 70-80 vêm dos relatos e as outras faixas (10-29, 30-49, 50-69, 70-80) são
  proporcionais *(dedução)*. Cada membro de um grupo sorteia o seu ("each player gets different rewards").
  *(visto, 0067)* o normal de nível 10 deu duas vezes Mystery Stone x1, 10.000 de Daru e 10.000 de ouro: a faixa
  normal 10-29 é essa (sem Kyanite) e a Mystery x2 a 50% vale do 30 em diante. Elite e chefe: nenhum foi morto
  na captura (só derrotas), seguem a 0030.

  | Tipo | O que cai (chance, quantidade em 70-80) | Fonte |
  |---|---|---|
  | Normal | ouro (sempre, 50-80k), kyanite (80%, 3-6k), daru (30%, 25-40k), Mystery Stone (50%, 2) | wiki: "usually drop only Gold and Kyanite"; fórum: "either 2 or nothing", "2-4 stones out of 5" |
  | Elite | ouro (sempre, 80-120k), daru (50%), Mystery Stone (70%, 2-5), Soul Crystal (50%, 5-10), Energy Core (15%), Divine Light (10%), Fate Stone, Mount Training Whip, Runestone (20%), ouro grande (0,5%, 1-2M) | fórum: "80k gold daru and 8 sc", "5 stones or nothing", "elite and got 2 million"; wiki: "can drop", "very rarely ... 7 million" |
  | BOSS | ouro (sempre, 180-220k), daru (50%), kyanite (sempre, 8-12k), Mystery Stone (sempre, 10-14), Soul Crystal (80%, 20-30), Legendary Stone do nível (sempre, 1-3; 40+), Energy Core, Fate Stone, Whip, Runestone (30%), Divine Light (20%), ouro grande (1%, 2-7M) | fórum: "14 Mystery Stone, 3 Lvl 80 Legend Stone, 10k Kyanite, 200k Gold, 26 Soul Crystal here from lvl 80 Boss", "7million gold from killing lvl 70 boss"; vídeo PaRgg2jSAHE: Spirit of Light 70 com 180 000 de ouro e daru |

  Fontes (internet): https://wartune.fandom.com/wiki/Wilds (e as revisões ?oldid=24193 e 26635: a Divine
  Light está riscada na atual); fórum R2 "What do you think of the wilds events" (94942, páginas 1, 2, 5, 7,
  8 e 9 via Wayback 2024); guia da R2 (130741, p.13: "killed an elite and got 2 million in gold"); vídeos
  https://www.youtube.com/watch?v=PaRgg2jSAHE e https://www.youtube.com/watch?v=KZVo075chg4 (Sawtooth Ant 70
  com ~80 000, Soul Drainer com 100 000). Mahra e "Equipment materials" do post oficial não têm confirmação
  de jogador e ficaram fora. Para mudar uma taxa, basta editar a linha no banco e reiniciar.
- **Níveis 60-80: lidos em vídeo (migração 0032).** Ao pegar o baú, o jogo mostra "Wilds Slayer Rewards:
  ...". O contador "Today's Reward Attempts" confirma o tipo. Foram lidos 35 baús: 18 BOSS (12 Lv80, 4 Lv70,
  2 Lv60), 13 Elite e 5 Normal de nível ~80. A chance é a frequência vista e a quantidade é fixa quando todos
  os baús deram a mesma. Abaixo de 60 continua valendo a 0030. O ouro de milhões (wiki) também continua,
  porque não aparecer nos 35 não o desmente. *(internet)*

  | Tipo | Sempre | Às vezes (frequência vista) |
  |---|---|---|
  | BOSS 60/70/80 | ouro 150k/180k/200k, Mystery Stone x8, Legendary Stone do nível x2/x2/x3 | 2ª pilha de Mystery Stone x5/x6 (40%), daru igual ao ouro (25%), kyanite 6k/8k/10k (30%), Shadow Crystal x7/x8 (30%), Divine Light (50%), Energy Core (30%), Runestone x6/x8/x10 (35%), Whip x7/x8 (25%), Fate Stone x8 (15%), Lvl. 3 Gem Pack x3 (25%), Skeleton Key x4/x5 (10%), Soul Crystal x16 (10%) |
  | Elite 60/70/80 | ouro 70k/80k/100k | Mystery Stone x4/x5 (70%), daru igual ao ouro (40%), kyanite 4 500 (40%), Fate Stone x3/x4 (45%), Soul Crystal x5/x8/x13 (40%), Energy Core (25%), Divine Light (15%), Skeleton Key x3 (15%), Shadow Crystal x6, Runestone x5, Whip x3 (10%) |
  | Normal ~80 | ouro 40-50k | kyanite 3 500 (60%), daru 50k (20%), Shadow Crystal x5 (20%), Mystery Stone x2 (20%) |

  - **Valores *(dedução)*:** os da faixa 60 que não apareceram (Whip, Fate, Soul do BOSS e o Normal).
    O Gem Pack usado é o 2060010 (uma gema), porque o template tem dois "Lvl. 3 Gem Pack".
  - **Vídeos dos baús de BOSS:**
    9TR2vFgoM68, KZVo075chg4, E2mSjZgS4s4, ZQQinb0eCaE, PK9ZQyBjIrA, uHwbw4qh5Mo, z_GJsJHFStk,
    7La5sHVhJVI, WNA3obEGelA, qfWE3Fwnehg, 5qii_QwoyMg, yAwFriADgBA, Cn6cQpeImEM, PaRgg2jSAHE,
    O41F-CZjgX4, Jah1Lt7hVf8, L1PN_S_WOGo, ap2OmPNJfrY.
  - **Vídeos dos baús de Elite e Normal:** KZVo075chg4, E2mSjZgS4s4, PaRgg2jSAHE, M6FNpuuUhGc,
    MkPflW645qU, pct0pNz2IEc, ROf6fZ1I-Wc, L4FT8QhQfqY, MvDYvI72TGM, 7La5sHVhJVI, z_GJsJHFStk.
  - Todos são `https://www.youtube.com/watch?v=<id>`.
  - **O que os vídeos também mostram:**
    - a mochila cheia manda o excedente pelo correio (5qii_QwoyMg: "inventory full, please check your mail!");
    - nenhum baú de nível 10-50 foi lido; os chefes desses níveis são Tauren Grand Master 10, Gale Wolf King 20,
      Poison Jade Lizard 30, Bonecrusher 40 e Purgatory Lord / Water's Heart 50.
- **Não feito**: entrar numa luta já começada (state 4), luta em grupo, as várias barras de vida dos chefes dos
  vídeos ("he's lost one life"), o reviver no mapa, e a regra "+/-15 levels" da wiki (o post oficial e o help
  só falam de 15 abaixo, que é o que está feito).

## Minas do mundo (mapas 1 a 5, `game/mines.py`)

Fonte: oficial_20261023-153200-1 e oficial_20261023-171155-1 (inglês, mapa 1 "Autaric Plains", jogador nível 11-12).

- **Catálogo** *(visto)*: 60 minas do mapa 1 com id e tile do oficial (`world_mines`, migração 0064). Nas 45 grades
  que o cliente pediu nas capturas só existem estas (7 grades sem nenhuma). Nas outras grades e nos mapas 2 a 5
  **TODO(inventado)**: sorteio com semente (mapa, grade) pela contagem das vistas (0:7, 1:23, 2:10, 3:4, 5:1 por
  grade), ids `1_200_000_000 + mapa × 1_000_000 + (gx × 100 + gy) × 10 + n`.
- **Nível e guarda** *(visto)*: template 2004xx sorteado de novo a cada ciclo (806736: 200418 no ciclo das 13:15) na
  faixa do mapa (`MapInfos` MinLevel-MaxLevel: 11-20 no mapa 1). Guardas vistos 11→6506, 12→6509, 13→6511, 14→6513,
  15→6514, 16→6516, 17→6517, 18→6520, 19→6521, 20→6522. **TODO(inventado)**: 21 a 60 (o 1º 65xx de nível >= o da
  mina depois do anterior). A semente é (mapa, mina, ciclo): todo jogador vê o mesmo nível.
- **Ciclo** *(visto)*: o do mundo, createDate 01:15:41 e 13:15:52 (fuso do jogo) em todas as minas, de 12 em 12 h
  (`game_settings.world_mines.anchor`). `refreshTime` = o que falta do ciclo em ms (5109784 às 11:50). Ao entrar
  num mapa do mundo (5176) o `mines_at` do castelo passa a ser o do mundo, e a virada anda de 12 em 12 h
  (`mines.next_cycle`); um castelo que entrou antes é alinhado no próximo refresh.
- **4129** *(visto)* #1503: a mina de outro jogador com `occupyPlayerName`, `occupyLeagueName` (guilda) e o poder dele em
  `fightCapaity`; a livre com o poder do guarda (866 no 6506 ... 1601 no 6522). *(dedução)* os outros guardas:
  `Live` / 100 × 0,6 + ataques + defesas - 6 (dá o visto em 9 de 10). Uma ocupação por mina e ciclo
  (`uq_wild_lands_wild_id_cycle_at`), lida de todos os jogadores (`wild_lands.held_on`).
- **Luta** *(visto)* #3037-#3082: 140 ×2 do exército, 140 da mina em luta (state 4), 157 battleType 1 com `mapTempId`
  = o mapa; vitória: 150, 109, 3, 4103 (battleScene 4), 150, 100, 140 ×2, 109, 152 ("Autaric Plains(2487,2632)",
  `mapId` 1), 140 da mina com o dono, 169 e o 4382 logo em seguida.
- **Recusas** *(cliente)*: até 2 minas (`MapPhysicsField`: `fieldDic` >= 2, "Max number of occupiable resource
  quarries"; `max_held`); mina de alguém da mesma guilda (`AttackConsortiaMember`); a própria; outro lutando por ela.
- **Mina de outro jogador**: o cliente mostra "Attack" (`PhysicsMenu`). **TODO(inventado)**: luta battleType 1 contra
  a cópia do herói dele (`oc.holder_battle`, pvp) no lugar do guarda; vencendo, a mina sai dele (ouro acertado até
  a hora, carta "took ...", 109 e 152 se online) e fica com quem venceu no mesmo nível.
- **Virada com o jogador online** *(visto)* #170-#175: cada mina sai com 109, 152 (com as que faltam) e 148 (carta);
  aqui no 20008 seguinte (*dedução*: até ~60 s depois). No login ou num pedido, só a carta (sem 148).
  **TODO(inventado)**: título e texto da carta (o cliente lê o correio por HTTP).
- **5179 Give Up** *(cliente: `FieldItem`, `OuterCityController.sendGiveUp`)*: `position` "x,y"; o ouro até agora sai
  com a mina, 108 com a posição, 109, 152 e 140 da mina livre para quem vê. *(dedução)* sem captura.
- Baús e monstros não nascem no tile de uma mina nem de um castelo NPC (o 5160 acharia o outro).
- **5176** no mesmo mapa recusa (105 como está) o tile de mina, castelo NPC, robô ou castelo de outro jogador; mudando
  de mapa, o castelo vai para o centro ou, ocupado, para o vizinho livre à direita (*dedução*).

## Castelos NPC do mundo (mapas 1 a 5, `game/npc_castles.py`)

Fonte: oficial_20261023-153200-1 #197/#1524/#1531/#1532 e oficial_20261023-171155-1 #290, #740-#833, #1886-#1993.

- **Vistos** *(visto)*: 5 no mapa 1, iguais nas duas capturas: Alberthim 728858 (2454,2638) grau 14, Aladyr 729056
  (2486,2671) 12, Barbh 732447 (2525,2569) 14, Calena 736544 (2559,2596) 18, Brochesth 745995 (2432,2594) 14, donos
  1300000011-77 (`game_settings.npc_castles`, migração 0065).
- **4129** *(visto)*: `baseCastle` type 1, state 1, sem guilda nem tempo de defesa, `castleName` = o nome; entram
  depois do próprio castelo.
- **Grades não vistas** **TODO(inventado)**: sorteio com semente (mapa, grade) pela contagem das 45 grades vistas
  (40 sem castelo, 5 com um), grau na faixa do `MapInfos`, nome com a metade do começo de um nome visto e a do fim de
  outro, ids `1_250_000_000 + mapa × 1_000_000 + (gx × 100 + gy) × 10 + n` e donos `1_300_100_000 + ...`. Fora dos
  tiles das minas.
- **Ataque e fim** *(visto)*: os do castelo-robô (*Castelos-robô*: leed, 140 do próprio castelo, 4452, 3, 157; no
  fim 100, 118 na vitória, 148 do relatório, 140 ×2, 140 do castelo de volta ao state 1, 4382), com as mesmas recusas
  (ataque do dia, 10 níveis, protegido). Saque, proteção e `fight` em `game_settings.npc_castles` (migração 0066).
- **Luta** *(visto)* #749 e #1893: battleType 4 no 993, herói 11012 "Aladyr" (vida 501 e skills 10711/10811/11011 do
  `GameHeroTemp`), 2 pilhas de 10112 (o lanceiro do grau) com 443 de vida nas pos 1 e 7. **TODO(inventado)**: a vida
  das pilhas nos outros graus (`Live` × 1,05, a razão 443 / 422 do grau 12) e o herói acima do grau 30 (o 11030 com
  a vida × grau / 30).

## Treasure Cache (4129 type 22, `game/caches.py`)

Fonte: oficial_20261023-153200-1 e oficial_20261023-171155-1 (inglês, mapa 1, jogador nível 12).

- **Mensagem** *(visto)*: `templateId` 2201xx ("Treasure Cache", `MapPhysicsTempInfos` MasterType 22, `Description`
  "Rebel", `Grades` = nível 1 a 60, `RefreshTime` 14400 a 51200 s conforme a faixa), `type` 22, `level`, `state` 1,
  `createDate` e `refreshTime` próprios de cada baú: o `refreshTime` é o que falta da vida dele, em ms (18000000 no
  recém-nascido 828569 de #1938, criado às 14:51:53). `armyPawn` com 3 guardas de `ownPawns` 1.
- **Luta** *(visto)* #325-#329 e #570-#574: 140 ×2 do exército lutando, 140 do baú em luta (state 4), 157 com
  `battleType` 3, `mapTempId` = o mapa, 3 guardas nas posições 4, 2 e 8 com a vida de um soldado (`Live` / 100: 840
  no 6011). Guardas vistos: nível 13 → 6011, 14 → 6013, 15 → 6014. *(dedução)* a regra é o 1º `PawnTempInfos` 60xx
  de nível = baú + 2 (bate nos três).
- **Vitória** *(visto)* #645-#670: 150, 109, 3, 115 do item, 4476, 4484 ×9 (títulos: não existem aqui), 111
  "Received: Lvl. 3 Luck Stone x1", 4103 (`battleScene` 0, Daru = tropas perdidas), 150, 100, 140 ×2 do exército,
  140 do baú em state 0, 83 com o mesmo texto, 169 e o 4382 logo em seguida. Prêmios vistos: Lvl. 3 Luck Stone x1
  (baú 13, #661) e Elders Robe x1 (baú 13, mago, #1810).
- **Derrota** *(visto)* #370-#385: 4103 result 2 e o baú volta a state 1.
- **4382 no mapa do mundo** *(visto)*: sai logo no fim de toda luta no mapa 1 (baú #670, #1812; mina #3082, #3162;
  robô #833), sem esperar o 8747. No baú o servidor faz assim; mina e robô seguem como antes (ver *Minas de ouro*).
- **Sorteio** (`caches.on_map`): cada mapa tem `count` vagas (`game_settings.treasure_caches`, migração 0063); cada
  vaga tem nível fixo na faixa do mapa (`MapInfos` MinLevel-MaxLevel: 11-20 no mapa 1 ... 51-60 no 5; vistos 13 a 15)
  e vive o `RefreshTime` do template, com um deslocamento sorteado; a cada vida nasce num tile sorteado
  (semente mapa, vaga, vida), a 20 da borda. Todo jogador vê os mesmos, sem tabela de estado.
- **Aberto**: o primeiro a vencer leva (`treasure_cache_opens`, chave mapa, vaga, nascimento); o baú some para todos
  até a próxima vida. A vida que acaba no meio da luta não dá nada. Mochila cheia: abre sem item (log).
- **Na vista**: o 20008 tira os baús cuja vida acabou (140 state 0) e mostra os que nasceram nas grades do último
  8201 *(dedução: a captura só mostra o 140 do recém-nascido, #1938)*.
- **TODO(inventado)**: quantas vagas por mapa (1000, 640, 250, 160, 90: uma a cada 25 000 tiles; a captura mostra 7
  baús em ~300 × 250 tiles perto do castelo) e o prêmio: Lvl. `ceil(nível/5)` Luck Stone ou um equipamento da
  classe do jogador (`Profile` 2, `NeedGrades` de nível - 5 a nível + 2), por igual.

## Coleta (Resource Harvesting, missões 55, 102, 140, 170, 171, 172): o que as fontes permitem

- **Botão ir** *(cliente)*: `TaskFrameII.as:707-708` pega `worldBossTemplateDict[NeedFightId]` (6001) e
  `WorldBossControler.sendEnterBattle` manda o 8258 com essa campanha. A 6001 é "Resource Quarry", `Types` 2,
  `MinLevel` 1, `Capacity` 10000 (`Campaigns`). `MapInfos` tem a 6001 (2000x2000 px, `Type` 1), mas não tem `CampaignData` nem `MapNodeInfos`. O `.maps`
  existe no CDN local (`D:\xampp\htdocs\wartune-cdn\maps\6001\6001.maps`, fora do repo), mas não está entre os
  13 mapas com nós de campanha da varredura. A captura inglesa tem o 8258 com a 6001 (#1803) e os nós no 127 (#1809):
  a entrada está feita (ver *Resultado*).
- **Coleta no espaço** *(cliente)*: `CollectionAction.sendCollection` manda o 8733 com o id do nó
  (`PropertyMsg.param1`). Os nós "year" são `MasterType` 300 a 315 ou 410 (`SpaceNodeType.isYearNode`), e o 4811
  (`QueryCollectCampaignNodeRspMsg`, `PlayerManager.__receiveYearNodeDataHandler`) diz o recurso de cada nó
  (`sonType`, nome). Os templates têm 20 nós `MasterType` 300 (mapa 10000, "礼物堆" no tempinfos inglês, `SonType` 10031):
  são pacotes de presente, não Wood, Amethyst nem Copper. Nenhuma captura tem 4811 nem 8733.
- **Coleta de campanha** *(cliente)*: `CollectionAction.sendCollection` (`CollectionAction.as` 360-392) manda o 5032 `{mapId, nodeId, cmd 2}` (`SocketSendManager.sendSessionOverToBattle`, 266-273) num nó de campanha de coleta. O servidor só responde o 5032 nos nós do tutorial (`campaign.py`, 281-300). Os `SonType` de coleta são 2350 (som 041), 2351 e 2380 (som 039), 2352 e 2393-2395 (som 040) (`CollectionAction.as` 93-105). O nome do recurso de cada som (Copper, Amethyst, Wood) é dedução.
- **Itens 2100022, 2100023 e 2100024**: nenhum código, drop ou tabela os cria (já visto em `missoes.md`).
- Resultado (2026-10-19): a **pedreira 6001 está feita** pela captura inglesa (#1803-#2123). O 8258 entra, o 5125 numa
  pilha responde 143 COLLECTION, o 5032 colhe Wood (2100022) x2-3 e o 8699 dá Wood x18. O 5025 sai. Os nós vêm da
  captura (127), no banco (`campaign_contents` 6001, migração 0034). Ver [salas-campanha.md](salas-campanha.md).
  A missão 102 fecha pela bolsa. Amethyst (2100023) e Copper (2100024), das missões 140 e 170-172, seguem sem fonte. A
  coleta do espaço (4811 e 8733) é outra rota.

## Tabelas e migrações

- **0012** `arenas.attack_left` (padrão 5): ataques extras do dia. A virada do dia é gravada no login
  (junto com ele) e na 9506. Também conta no `PlayerMsg.attackLeftCount` e no `4202`.
- **0013** `treasure_maps`: uma linha por personagem, com `day`, `join_count` e `reward_count`. Carregada no
  `snapshot` (`PlayerSnapshot.treasure`), como `mystery_shops`.
- **0017** `wild_lands` (minas ocupadas) e **0018** `castles.mines_at` (começo do ciclo de 12 h das minas;
  vazio em castelo antigo). Ver *Minas de ouro*.
- **0063** `treasure_cache_opens` (baú aberto, chave mapa, vaga, nascimento) e `game_settings.treasure_caches`.
  Ver *Treasure Cache*.
- Diamantes passam por `services/ledger.py` (`pay`). Não há tabela de ledger nova.

## Dependências em aberto

1. **Mapa-múndi compartilhado.** Feito: castelos de outros jogadores nos mapas 1 a 5, nas grades pedidas
   (8201), e os 2 castelos-robô da instância (*Castelos-robô*). Falta: exércitos de outros jogadores (o 169 da
   transfer #15, só turco, traz o de `asiesat`, mas a posição de outro jogador só existe na sessão dele; 4167 e 4168 não
   existem aqui) e a resposta do 5160 e do 8488 contra castelo ou exército de jogador (*precisa de captura*). Feito:
   Treasure Cache (*Treasure Cache*), minas do mundo (*Minas do mundo*) e castelos NPC (*Castelos NPC do mundo*).
2. **Gancho da campanha** (8292, 8293, 8295, 8525). Feito: Rest House (`docs/salas-campanha.md#rest-house`).
   Falta o PK no mapa (8525, BattleType 19).
3. **Passe de progresso** (8636, 8637). A área é sempre 1. Falta o progresso das fases (8753, 8755).
4. **Mapa do tesouro.** Falta a tabela de sorteio da qualidade do mapa (o servidor dá o de bronze). Refresh,
   escavação, uso do mapa e recompensa dependem de pontos no mapa do mundo e de batalha de equipe.
5. **Guia do tutorial** (8699, ação a46). Feito: é a luta da pedreira 6001.
6. **Contagem diária do mapa do tesouro.** *(cliente)* "Treasure Map and rewards can both be claimed 5 times per
   day, claim attempts reset daily at 5:00 A.M." (`TreasureMapGetFrame.helpContent`): 5 por dia, vira às 5h, o dia
   do jogo (`A.today`).
7. **Mapa de bronze e nível.** *(dedução)* O item que o oficial dá é sorteado por qualidade; a tabela não está
   nos templates, então vai sempre o de bronze. A trava de nível é o `NeedGrades` do item (55), sem trava
   própria no cliente.
8. **Minas (precisa de captura).** Perda de soldados numa derrota contra a mina; o que acontece no fim do
   ciclo com o jogador online (captura atravessando 12 h depois do `createDate`) e se o ciclo abre no login ou
   na criação da conta (captura de um login mais de 12 h depois do último); guarda e nível fora de 8 a 10. No
   mapa 2 o `refreshTime` vem como contagem regressiva (39799344 ms às 20:39 para `createDate` 19:41:30).
