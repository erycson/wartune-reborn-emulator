# Cidade externa e mapa-múndi

Opcodes da cidade externa e dos sistemas que o cliente abre a partir dela: grade de exércitos, andar,
voltar ao castelo, ataque extra, mudar o castelo de lugar, gancho (8292, 8293, 8295, 8525), passe de progresso (8636,
8637) e mapa do tesouro (8744, 8745).

Código: `game/outer_city.py` (geometria do mapa e luta contra o guarda), `game/mines.py`, `game/robots.py`,
`game/bosses.py`, `game/handlers/outer_city.py`, `game/handlers/hangup.py`,
`game/handlers/singlepass.py`, `game/handlers/treasure.py`. Testes: `tests/game/test_outer_city.py` e
`tests/game/test_mundo_opcodes.py` (todo código tem handler e corpo vazio não derruba a sessão).

Fontes: *(visto)* captura oficial (`captures/transfer_kampi_sistemi.json`, `captures/cevre_altin_madeni_savasi.json`);
*(cliente)* código decompilado (`m2`, `m3`, `m8`); *(dedução)* inferido de cliente e captura.

## O que o servidor tem

O mapa do castelo (100000xxx, modelo 100) é uma instância de cada jogador *(visto)*: replay #706 e cevre #11
trazem as mesmas 4 minas (ids e posições) e os mesmos ids de castelo-robô (765957 e 765958), mas a instância
(100000313 e 100000714), os 2 robôs, os ids do `armyPawn` das minas e o `createDate` mudam de uma conta para
a outra. Por isso o servidor mostra ali só o castelo e as minas do próprio jogador; ocupação de outro jogador
não aparece nem bloqueia. Nos mapas compartilhados (1 a 5) o 8201 traz os castelos dos outros jogadores nas
grades pedidas. Os 2 castelos-robô da instância existem desde a missão 100 (ver *Castelos-robô*). Não há
exércitos alheios andando, terras selvagens fora das 4 minas nem os castelos "Köy" do mapa 2. Pedido que depende
disso é recusado ou respondido vazio, do jeito que o cliente espera para não travar.

## Opcodes C>S

| Código | O que o servidor faz | Fonte | Depende de |
|---|---|---|---|
| 5004 | Registra. Sem resposta | *(cliente)* o cliente não lê resposta do 5004 | — (os exércitos da tela chegam pelo 169) |
| 5181 | Sem resposta própria. A grade vem no 169 do 8201 | *(visto)* transfer #12-15, cevre #11-12: sem S>C | — |
| 8201 | Roda o refresh (ver *Minas de ouro*). 4129 com as minas das grades pedidas (mapa modelo 100, ocupadas só pelo próprio jogador), o próprio castelo, os castelos-robô da grade (na instância) e, num mapa compartilhado (1 a 5), os castelos de outros jogadores nas grades pedidas (`baseCastle`); depois 169 com o exército próprio se cair numa grade pedida do mesmo mapa | *(visto)* replay #706, cevre #11, transfer #14-15 (no mapa 2 o 4129 traz o castelo de `asiesat` e 20 "Köy"; o 169 traz o exército dele); *(dedução)* castelo de outro jogador com os campos do próprio (a captura não tem um) | exército de outro jogador (o servidor não guarda a posição dele), terras selvagens fora das 4 minas (no mapa 2 há minas tipo 20 e bosses tipo 21) e castelos "Köy" sem dono |
| 8254 | Guarda o último ponto andado (pixels // 20). 140 ×2 andando (state 1) no ponto de saída e, na chegada, 140 ×2 parado no destino (0,134 s por tile). Rota vazia, outro exército ou fora do mapa são ignorados | *(visto)* replay #761-#767 (18 tiles em 2,43 s); *(cliente)* `OuterCitySocketOutManager` | outros exércitos no mapa (4167) |
| 9525 | 4938 com os chefes do mapa pedido e o tempo até o próximo refresh (ver *Chefes do mapa*) | *(visto)* transfer #7-10, cevre #3, #9, #43, #44 | luta contra chefe, monstros do mapa, névoa (4939) e caixas (4940) |
| 5161 | Volta o exército ao castelo, de graça: 98 com a posição | *(cliente)* o botão do exército não checa nada | — |
| 5160 | Roda o refresh. Mina livre: luta com o guarda (ver *Minas de ouro*). Castelo-robô (tile de 765958 em (44,22) ou 765957 em (59,56), na instância): luta com o guarda de grau 8 se há ataque no dia e a diferença de nível é menor que 10; senão 140 parado (ver *Castelos-robô*). Sem alvo ou mina já do jogador: 140 com o exército parado (state 0), sem luta | *(visto)* replay #713-#795; *(cliente)* `CityInfoFrame.__attackHandler` e `MapPhysicsCastle.attack` mandam o 5160 com a posição do castelo; *(dedução)* parar sem alvo e a luta do castelo-robô | castelos de jogador e exércitos alheios, terras e tesouros (precisa de captura) |
| 8488 | Registra. Sem resposta (a 157 só vem de batalha) | *(cliente)* PvP contra exército de outro jogador | exército de outro jogador no mapa |
| 8699 | Registra. Sem resposta | *(cliente)* ação a46 do guia do tutorial (m8) | nó de coleta que o passo abre (ausente nas capturas) |
| 9506 | Ataque extra: 100 diamantes (vinculado primeiro se `type` 2), até 5 por dia. Responde PlayerMsg com `attackLeftCount` | *(cliente)* `AttackAlertFrame` (`setAddAttackCount`); preço em `ConfigInfos` `AddAttck_Point` | — |
| 5176 | Muda o castelo. Outro mapa: 200 de energia e o ponto central do mapa. Mesmo mapa com ponto: 100 de energia. Energia completada com diamantes. Resposta: 140 e 105 (mapa, posição, energia). Recusa: 105 com o castelo como está | *(visto)* transfer #2-5 (500 para 300 de energia); *(cliente)* `WorldMapControler`, `MapPhysicsCastle` | sem outros castelos, o ponto de chegada é o centro |
| 8292 | Cancela o gancho: 4200 com `leftWeay` 0 e `isStartHangup` falso, a mesma resposta do 8293. Não cobra | *(cliente)* `HookTimeView` envia o 8292 ao cancelar | sistema de gancho da campanha (ausente) |
| 8293 | Ressincroniza o gancho: 4200 com `leftWeay` 0. Não cobra | *(cliente)* `HookTimeView` só envia com `hookleftWeay` diferente de zero | sistema de gancho da campanha (ausente) |
| 8295 | Estado dos ganchos da sala: 4204 vazio. É a resposta que termina o pré-carregamento do gancho | *(cliente)* `HookContorler` envia o 8295 sem corpo | ganchos de outros jogadores (ausente) |
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
  `ceil((máximo - atual) / 5)`, e só quando falta energia para o gasto. *(visto: 500 para 300)*
- Virada do dia às 5h (`game/daily.py`, no login e no 20008 que o cliente manda a cada ~60 s): a energia
  de teleporte volta ao máximo (151101 `Property2`, sem regenerar com o tempo), a stamina ganha +100 por
  dia que passou até o máximo (200), e a stamina de poções do dia (`PlayerMsg.wearyLimit`, teto 300 no
  cliente) zera, e a bênção da roda volta a 10% a partir do nível 41 ("Boosts will reset to 10% daily at
  5 a.m.", language `ExtraBufferSeminaryTips`). Quem está online recebe o 4202 com os valores novos e o 3; a energia vai no
  `transEnergy` (prédio -11).
- Mapas abertos: 1 pede nível 11, 2 nível 21, 3 nível 31, 4 nível 41, 5 nível 51; `-1` fica fechado
  (`WorldMapHelper.chcekMapId`).
- Tamanho do mapa: `MapInfos` `Width` e `Height` em pixels, divididos por 20. O mapa do castelo
  (100000xxx) usa o modelo 100 (Loş Sahil).

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
  (replay e cevre), então são do mapa modelo 100: 853876 (16,34), 853877 (36,34), 853874 (71,54) e
  853875 (54,64). Cada conta tem a sua cópia (ver *O que o servidor tem*). O nível não é fixo: é sorteado a
  cada refresh (abaixo). Guarda: um soldado, 6504 no nível 8 e 6505 nos níveis 9 e 10. O arquivo
  `maps/100/100.maps` não tem minas.
- **Refresh de 12 h** *(visto)*: `RefreshTime` 43200 s (`MapPhysicsTempInfos`), que sai como 43200000 no 4129
  e no 140 das duas capturas (mapa 100, fixo: na cevre, 35 min depois do `createDate`, ainda é 43200000; só no
  mapa 2 ele vem como contagem regressiva). `createDate` é o começo do ciclo, no fuso do jogo (UTC+3,
  `gameday.GAME_TZ`): replay 12:19:54 = 09:19:54 UTC, 1 s antes do primeiro pacote; cevre 19:48:57 = 16:48:57
  UTC, 73 s antes do `signDate` 19:50:10 do mesmo `asiesat` (login.json), e o relogin das 17:05 UTC não
  mudou o `createDate`. As duas fases ficam 7 h 29 min distantes, então o ciclo é do jogador
  (`Castle.mines_at`, migração 0018), não do mundo. *(dedução)* o ciclo abre no login; vencido, o seguinte
  abre no primeiro login, 8201 ou 5160 depois do fim (*ponytail*: quem fica online pode ver o oficial renovar
  na hora certa; não há captura de um refresh ao vivo). Castelo de antes da 0018: o ciclo começa na ocupação
  mais velha.
- **Nível sorteado** *(dedução)*: os 8 sorteios vistos nas duas capturas (replay e cevre) deram nível 8, 9 e
  10. Cada ciclo sorteia o nível com semente `"<jogador>:<id da mina>:<início do ciclo>"`: fica o mesmo até o
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
- **Luta** *(visto)* #713-#744: 140 ×2 do exército lutando, 140 da mina em luta (state 4), 157 (battleType 1,
  mapa 100, as tropas do exército em duas pilhas nas posições 3 e 9, o herói na 4, o guarda na 5; vida da
  pilha = Live × soldados / 100). Fim: 150, 4103 (cena 4), 150, 100, 140 ×2. Vencendo: a mina fica do
  jogador, 112 da missão (condição 7, Para1 2006), 4152 (Leed 9), 109, 152 com o rendimento, 140 da mina
  ocupada e 169. Perdendo: 140 da mina livre (a derrota não tem captura, ver abaixo).
- **Perda de soldados** *(visto)*: nas 3 vitórias contra mina nenhum soldado morre (cevre #36-39: `ownPawns`
  737 antes e depois; replay #735 e #787: 150 antes e depois). Derrota contra mina: *precisa de captura*. Na
  campanha os soldados morrem (replay #1711, battleType 6, mapTempId 1021, pool 900 para 828), mas essa regra
  é de outro sistema e não passa por `outer_city`.
- **Volta** *(visto)* #750: o primeiro 5035 com state 3 depois da luta recebe o 4382.
- **Ouro** *(visto)*: cada mina ocupada soma `Property4` por hora no 109 (280 para 960). O 152 lista as minas
  em `wildYield` e mantém `goldYield` só com os prédios e `goldWildLandYield` em 0, como no replay.
- **0017** `wild_lands`: mina ocupada por personagem (`wild_id`, `occupied_at`), carregada em
  `PlayerSnapshot.wild_lands`. Relogar mantém a mina até o refresh.
- **0018** `castles.mines_at`: começo do ciclo de 12 h das minas do jogador.

## Castelos-robô (missões 100, 411 e 765, `game/robots.py` e `handlers/outer_city.py`)

- **Layout** *(visto)*: 765958 em (44,22) e 765957 em (59,56), no mapa da instância, nas duas capturas
  (replay #706 e cevre #11, mesmos ids e tiles). Grau 8 em 3 dos 4 (o quarto, replay 765958, tem 7). O dono
  (`occupyPlayerId` 13000xxxxx) e o nome mudam de uma conta para outra: replay ♣Chloe♣ e ♫Elizabeth♫; cevre
  ♫Elizabeth♫ e ►Abigail◄. Sem liga e sem tempo de defesa (`defenceLefttime` 0), estado 1, `castleName` = nome.
- **Servidor** *(dedução)*: os ids e tiles são os do oficial; o dono é `ROBOT_USER_BASE + índice` (faixa dos
  robôs); o nome sai da conta (`robot_name`, sorteio com semente `robo:<conta>`; os dois robôs da conta tiram nomes distintos). A captura
  tem 3 nomes (`world_robot_names`); com mais robôs que nomes, os nomes se repetem. Sem
  estado: o robô está sempre lá, não muda de dono nem some depois da vitória (não há captura disso).
- **4129** *(visto)* cevre #11, replay #706: o robô entra no 4129 da grade dele, junto com o próprio castelo.
  Só na instância do próprio castelo, pela mesma regra das minas (`robots_in` e `robot_at`, com `template_of`): nos mapas 1 a 5 não aparece nem luta.
- **Guia** *(cliente)*: a missão 100 (m8 `NewbieBaseActionMediator`, alvo 80_3) procura o castelo no pixel (880,440),
  o tile (44,22). O robô está nesse tile, então `getPhysicsByXY(880,440)` o acha (`BaseCastle` faz `_x = posX × 20`; `OuterCityModel.as` 367-386). Sem o alvo a tela escurece, como na missão 60.
- **Ataque (5160)** *(cliente)*: o `CityInfoFrame` (`sendAttack`, 28-44) manda o 5160 direto, com a posição do castelo.
  `MapPhysicsCastle.attack` (156-211) recusa com diferença de nível de 10 ou mais (linha 166) e abre o `_attackAlert`; o `attackCount` (`playerInfo`) é lido só depois, em `MapPhysicsCastle.__responseHandler` (213-229, linha 221). O clique no castelo passa também por `OuterCityModel.checkArmy` (`OuterCityModel.as` 477-521): exército existente, em estado parado ou de movimento, e mesmo mapa (ou instância contra o mapa 100). Essa checagem não conta tropas. O clique na mina (`FieldInfoFrame.as` 37) e o `CityInfoFrame` mandam o 5160 sem ela, e nenhum desses caminhos conta tropas.
  O servidor recusa com 140 parado e sem luta nos três casos (sem ataque no dia, diferença de 10 ou mais, luta em andamento).
  Com o ataque aceito, gasta um do dia (*dedução*: o contador é o do 9506, "x/5" no `AttackAlertFrame`).
- **Luta** *(dedução)*: a spec da mina (`guard_battle`: battleType 1, mapa 100, cena 4) com o guarda da mina
  do mesmo grau (`world_mine_guards`: 6504 no grau 8). Não há captura de luta com castelo. Fim na ordem da mina: 150, 4103, 150, 100, 140 ×2.
- **Vitória** *(dedução)*: `quest_event(8, 1, 1)`, em que Para1 1 = vitória. As missões 100 e 411 (Para1 0)
  e a 765 (Para1 1) avançam; sai o 112 e a gravação do ataque vai em uma só save.
- **Ouro saqueado: sem fonte.** A captura não tem castelo atacado, nem o `4103` com ouro de saque. O
  `U_C_ARMY_ATTACK_CASTLE` (97) não tem listener no cliente decompilado (só a constante). Então o relatório sai
  com `goldBonus` 0 e nenhum ouro é creditado.
- **Níveis** *(cliente + grau 8)*: a diferença menor que 10 deixa atacar até o nível 17. A 411 pede nível 17,
  então só passa no 17. A 765 (nível 12) passa de 12 a 17. Se o grau do oficial for outro, isso muda.
- **Não feito**: PvP contra castelo de jogador (8488 segue sem alvo, porque exército alheio não existe aqui);
  repetir a 765 (o 5012 de missão já existente é recusado, `rules.py:282`; a 765 também exige guilda, `TaskManage.checkConsortia`, 458-465; o cliente re-oferece quando a data da conclusão difere de hoje, `TaskManage.as` 531-542); e a gravação no fim da luta: um corte no
  meio da luta não cobra o ataque.

## Chefes do mapa (9525 -> 4938, painel "Current map BOSS info")

- **Relógio** *(visto)*: transfer (mapa 2, 4828 s às 17:39:31 UTC) e cevre (instância do castelo, 5775 s às
  17:23:44 UTC) apontam para o mesmo instante, 2026-05-21 19:00:00 UTC (22:00 no fuso do turco). As horas
  de refresh são as do `ConfigInfos` `WorldMapFreshTime` (0,8,10,...,22) no fuso do jogo
  (`WARTUNE_GAME_TIMEZONE`), como diz o help do cliente ("every 2 hours from 08:00 to 24:00"): de 00:00 a
  08:00 não há refresh, então às 03:00 o painel mostra 5 h. O `leftBossTime` nunca vai 0: com 0 o cliente
  (`OuterCityManager.coolDownBossUpdate`) pede o 9525 de novo, a cada segundo. As duas capturas são da mesma conta.
- **Lista**: os monstros de `bossType` 3 do sorteio do mapa (abaixo). *(visto)* o bosslist do mapa 2 na
  transfer tem 5 monstros, todos de `Property1` 3 (210106, 210124, 210129 ×2, 210120), `type` 1, e o 210127
  (`bossType` 2) do 4129 da mesma sessão fica de fora: o painel é a lista dos chefes. x e y em tiles (o radar
  faz `x * 20`; o mapa 2 tem 4000 tiles). A instância do castelo vem sem chefes (cevre): ela não está em
  `world_monster_counts`.
- **Divine Light** (item 2131055, `SonType` 316, pelo 5006): gasta um e manda o 4939 (`MapBossMsg` só com
  `leftFogTime` 20); o 4938 do mapa do castelo leva o que sobra (`characters.fog_map` e `fog_until`). Os 20 s
  só estão na descrição do item ("Can be used to disperse the Wilds’ dark fog for 20 seconds."). O cliente
  tira a névoa com `leftFogTime` > 0 e a põe de volta quando a contagem dele zera (`OuterCityManager`).
- **Não feito**: a luta com monstro e chefe (5160 num monstro segue parado; ver abaixo), então `count1` a
  `count3` (abates do dia; o máximo é `WorldMapKill` 5,3,1) ficam 0, e as caixas (4940/9526).

## Monstros dos Wilds (4129 type 21, `game/monsters.py`)

- **Mensagem** *(visto, transfer #14)*: 879741, template 210127 em (2268,1932) do mapa 2: `type` 21, `level` 80
  (`Grades`), `refreshTime` 0, `state` 1, `createDate` "2026-05-21 20:00:50" (o ciclo das 20:00 no fuso do
  jogo), `fightCapaity` 746796, `bossType` 2 (`Property1`), `size` 10 (`Property2`; 12 na maioria dos chefes),
  sem `armyPawn`. Vem no meio das terras (type 20), antes dos castelos.
- **Sorteio**: semente (mapa, começo do ciclo), então todo jogador vê os mesmos e um restart não muda nada,
  sem tabela de estado. A cada ciclo de `WorldMapFreshTime` (help: "in random positions") saem
  `world_monster_counts` monstros de cada tipo, com template sorteado entre os `MasterType` 21 daquele
  `Property1` (sem regra de nível por mapa: o mapa 2 da transfer tem de nível 20 a 80) e tile a 20 da borda.
  O id é 1000000000 + mapa × 10000 + ordem: estável no ciclo e longe das minas e terras do oficial.
- **Virada com o jogador online**: o cliente guarda os wildLands por tile e só tira um com state 0 ou quando a
  vista sai da grade (`OuterCityModel.updateWildLand`, `removesNSSWildLand`); na virada ele só pede o 9525.
  Então o 20008 (a cada ~60 s) confere o ciclo e, nas grades do último 8201, manda 140 com state 0 dos
  monstros velhos e 140 com os novos (`handlers/outer_city.roll_monsters`).
- **Dedução**: 40 normais, 20 elites e 5 chefes em cada mapa de 1 a 5. Só os 5 chefes do mapa 2 foram vistos;
  o resto segue a proporção de `WorldMapKill` (5,3,1). Nada na Internet sobre isso. `fightCapaity` só do
  210127 (`world_monster_power`); os outros vão 0. O tile não checa terreno (o .maps não traz a área andável).
- **Luta** *(parado)*: o `SonType` do template é o avatar do cliente (2108, 2179...), não unidade de batalha:
  só 2401, 2143, 2151, 2402 e 2124 batem com um `PawnTempInfos` (`MasterType` 101), e com outro nome
  ("Lanetli Mızrak" para o "Boğa Başlılar Reisi"). Não há HP nem tropas do monstro em nenhuma fonte, então a
  157 não sai sem inventar a unidade. Precisa de captura de uma luta com monstro do mapa (battleType 2,
  `NPC_WILDLAND_BATTLE`); com ela vêm o abate (state 4/0 no 140, `count1-3`), a regra dos 15 níveis e o baú.
- Internet: não achei fonte sobre os chefes do mapa externo (horário ou regra). O fuso do oficial inglês é o
  do Pacífico (internet) https://wartunereborn.wan.com/article/read?aid=8721.html.

## Coleta (Kaynak Topla, missões 55, 102, 140, 170, 171, 172): o que as fontes permitem

- **Botão ir** *(cliente)*: `TaskFrameII.as:707-708` pega `worldBossTemplateDict[NeedFightId]` (6001) e
  `WorldBossControler.sendEnterBattle` manda o 8258 com essa campanha. A 6001 é "Maden Ocağı", `Types` 2,
  `MinLevel` 1, `Capacity` 10000 (`Campaigns`). `MapInfos` tem a 6001 (2000x2000 px, `Type` 1), mas não tem `CampaignData` nem `MapNodeInfos`. O `.maps`
  existe no CDN local (`D:\xampp\htdocs\wartune-cdn\maps\6001\6001.maps`, fora do repo), mas não está entre os
  13 mapas com nós de campanha da varredura. Nenhuma captura tem 8258 nem 6001. Sem layout nem captura, a entrada não é
  implementada. Hoje o 8258 é recusado com o aviso de indisponível (antes dizia "inválido").
- **Coleta no espaço** *(cliente)*: `CollectionAction.sendCollection` manda o 8733 com o id do nó
  (`PropertyMsg.param1`). Os nós "year" são `MasterType` 300 a 315 ou 410 (`SpaceNodeType.isYearNode`), e o 4811
  (`QueryCollectCampaignNodeRspMsg`, `PlayerManager.__receiveYearNodeDataHandler`) diz o recurso de cada nó
  (`sonType`, nome). Os templates têm 20 nós `MasterType` 300 (mapa 10000, "Hediye Yığını", `SonType` 10031):
  são pacotes de presente, não Kereste, Ametist nem Bakır. Nenhuma captura tem 4811 nem 8733.
- **Coleta de campanha** *(cliente)*: `CollectionAction.sendCollection` (`CollectionAction.as` 360-392) manda o 5032 `{mapId, nodeId, cmd 2}` (`SocketSendManager.sendSessionOverToBattle`, 266-273) num nó de campanha de coleta. O servidor só responde o 5032 nos nós do tutorial (`campaign.py`, 281-300). Os `SonType` de coleta são 2350 (som 041), 2351 e 2380 (som 039), 2352 e 2393-2395 (som 040) (`CollectionAction.as` 93-105). O nome do recurso de cada som (Bakır, Ametist, Kereste) é dedução.
- **Itens 2100022, 2100023 e 2100024**: nenhum código, drop ou tabela os cria (já visto em `missoes.md`).
- Resultado: coleta **não implementada**. Faltam: a 6001 como campanha (`CampaignData` e nós de coleta, que não existem nos dados); uma captura do 8258 com a
  6001 e do 5032 num nó de coleta (quantidade por coleta); e uma fonte dos três itens. A coleta do espaço (4811 e 8733) é outra rota.

## Tabelas e migrações

- **0012** `arenas.attack_left` (padrão 5): ataques extras do dia. A virada do dia é gravada no login
  (junto com ele) e na 9506. Também conta no `PlayerMsg.attackLeftCount` e no `4202`.
- **0013** `treasure_maps`: uma linha por personagem, com `day`, `join_count` e `reward_count`. Carregada no
  `snapshot` (`PlayerSnapshot.treasure`), como `mystery_shops`.
- **0017** `wild_lands` (minas ocupadas) e **0018** `castles.mines_at` (começo do ciclo de 12 h das minas;
  vazio em castelo antigo). Ver *Minas de ouro*.
- Diamantes passam por `services/ledger.py` (`pay`). Não há tabela de ledger nova.

## Dependências em aberto

1. **Mapa-múndi compartilhado.** Feito: castelos de outros jogadores nos mapas 1 a 5, nas grades pedidas
   (8201), e os 2 castelos-robô da instância (*Castelos-robô*). Falta: exércitos de outros jogadores (o 169 da
   transfer #15 traz o de `asiesat`, mas a posição de outro jogador só existe na sessão dele; 4167 e 4168 não
   existem aqui), terras selvagens fora das 4 minas, castelos NPC "Köy", e a resposta do 5160 e do 8488 contra
   castelo ou exército de jogador (*precisa de captura*).
2. **Gancho da campanha** (8292, 8293, 8295, 8525). O servidor responde o gancho zerado (4200) e a lista
   de ganchos vazia (4204); o cancelar (8292) não muda nada. O ganho de tempo offline da campanha precisa do
   sistema de gancho, e os ganchos de outros jogadores não existem.
3. **Passe de progresso** (8636, 8637). A área é sempre 1. Falta o progresso das fases (8753, 8755).
4. **Mapa do tesouro.** Falta a tabela de sorteio da qualidade do mapa (o servidor dá o de bronze). Refresh,
   escavação, uso do mapa e recompensa dependem de pontos no mapa do mundo e de batalha de equipe.
5. **Guia do tutorial** (8699, ação a46). Abre um nó de coleta que nenhuma captura tem.
6. **Contagem diária do mapa do tesouro.** *(dedução)* A config `join_tremap_count` não diz o período, e o
   cliente não mostra data. Assumimos o dia, como o coliseu e o ataque extra.
7. **Mapa de bronze e nível.** *(dedução)* O item que o oficial dá é sorteado por qualidade; a tabela não está
   nos templates, então vai sempre o de bronze. A trava de nível é o `NeedGrades` do item (55), sem trava
   própria no cliente.
8. **Minas (precisa de captura).** Perda de soldados numa derrota contra a mina; o que acontece no fim do
   ciclo com o jogador online (captura atravessando 12 h depois do `createDate`) e se o ciclo abre no login ou
   na criação da conta (captura de um login mais de 12 h depois do último); guarda e nível fora de 8 a 10. No
   mapa 2 o `refreshTime` vem como contagem regressiva (39799344 ms às 20:39 para `createDate` 19:41:30).
