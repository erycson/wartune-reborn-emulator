# Cidade externa e mapa-múndi

Opcodes da cidade externa e dos sistemas que o cliente abre a partir dela: grade de exércitos, andar,
voltar ao castelo, ataque extra, mudar o castelo de lugar, gancho (8292, 8293, 8295, 8525), passe de progresso (8636,
8637) e mapa do tesouro (8744, 8745).

Código: `game/outer_city.py` (regras), `game/handlers/outer_city.py`, `game/handlers/hangup.py`,
`game/handlers/singlepass.py`, `game/handlers/treasure.py`. Testes: `tests/game/test_outer_city.py` e
`tests/game/test_mundo_opcodes.py` (todo código tem handler e corpo vazio não derruba a sessão).

Fontes: *(visto)* captura oficial (`captures/transfer_kampi_sistemi.json`, `captures/cevre_altin_madeni_savasi.json`);
*(cliente)* código decompilado (`m2`, `m3`, `m8`); *(dedução)* inferido de cliente e captura.

## O que o servidor tem

O mapa do castelo (100000xxx, modelo 100) é uma instância de cada jogador *(visto)*: replay #706 e cevre #11
trazem as mesmas 4 minas (ids e posições) e os mesmos ids de castelo (765957-765959), mas a instância
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
- Mapas abertos: 1 pede nível 11, 2 nível 21, 3 nível 31, 4 nível 41, 5 nível 51; `-1` fica fechado
  (`WorldMapHelper.chcekMapId`).
- Tamanho do mapa: `MapInfos` `Width` e `Height` em pixels, divididos por 20. O mapa do castelo
  (100000xxx) usa o modelo 100 (Loş Sahil).

## Minas de ouro (missão 60, `game/outer_city.py`)

- **Layout** *(visto)*: as 4 minas vêm das capturas, com os mesmos ids e posições para contas diferentes
  (replay e cevre), então são do mapa modelo 100: 853876 (16,34), 853877 (36,34), 853874 (71,54) e
  853875 (54,64). Cada conta tem a sua cópia (ver *O que o servidor tem*). O nível não é fixo: é sorteado a
  cada refresh (abaixo). Guarda: um soldado, 6504 no nível 8 e 6505 nos níveis 9 e 10. O arquivo
  `maps/100/100.maps` não tem minas.
- **Refresh de 12 h** *(visto)*: `RefreshTime` 43200 s (`MapPhysicsTempInfos`), que sai como 43200000 no 4129
  e no 140 das duas capturas (mapa 100, fixo: na cevre, 35 min depois do `createDate`, ainda é 43200000; só no
  mapa 2 ele vem como contagem regressiva). `createDate` é o começo do ciclo, no fuso do jogo (UTC+3,
  `worldboss.GAME_TZ`): replay 12:19:54 = 09:19:54 UTC, 1 s antes do primeiro pacote; cevre 19:48:57 = 16:48:57
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

## Castelos-robô (missões 100, 411 e 765, `game/outer_city.py` e `handlers/outer_city.py`)

- **Layout** *(visto)*: 765958 em (44,22) e 765957 em (59,56), no mapa da instância, nas duas capturas
  (replay #706 e cevre #11, mesmos ids e tiles). Grau 8 em 3 dos 4 (o quarto, replay 765958, tem 7). O dono
  (`occupyPlayerId` 13000xxxxx) e o nome mudam de uma conta para outra: replay ♣Chloe♣ e ♫Elizabeth♫; cevre
  ♫Elizabeth♫ e ►Abigail◄. Sem liga e sem tempo de defesa (`defenceLefttime` 0), estado 1, `castleName` = nome.
- **Servidor** *(dedução)*: os ids e tiles são os do oficial; o dono é `ROBOT_USER_BASE + índice` (faixa dos
  robôs); o nome sai da conta e do castelo (`robot_name`, sorteio com semente `robo:<conta>:<índice>`). A captura
  tem 3 nomes, então o sorteio usa só esses (*ponytail*: ampliar `ROBOT_NAMES` se houver mais nomes). Sem
  estado: o robô está sempre lá, não muda de dono nem some depois da vitória (não há captura disso).
- **4129** *(visto)* cevre #11, replay #706: o robô entra no 4129 da grade dele, junto com o próprio castelo.
  Só no mapa da própria instância (`robots_in`); nos mapas 1 a 5 não aparece.
- **Guia** *(cliente)*: a missão 100 (m8 `NewbieBaseActionMediator`, alvo 80_3) procura o castelo no pixel (880,440),
  o tile (44,22). Sem o robô a tela escurece, como na missão 60; com ele a máscara sai no ataque.
- **Ataque (5160)** *(cliente)*: `CityInfoFrame.__attackHandler` manda o 5160 com a posição do castelo.
  `MapPhysicsCastle.attack` recusa sem ataque no dia (`attackCount` 0) e com diferença de nível de 10 ou mais.
  O servidor faz as mesmas duas recusas e uma terceira (luta em andamento), todas com 140 parado e sem luta.
  Com o ataque aceito, gasta um do dia (*dedução*: o contador é o do 9506, "x/5" no `AttackAlertFrame`).
- **Luta** *(dedução)*: a spec da mina (`guard_battle`: battleType 1, mapa 100, cena 4) com o guarda 6504
  (grau 8). Não há captura de luta com castelo. Fim na ordem da mina: 150, 4103, 150, 100, 140 ×2.
- **Vitória** *(dedução)*: `quest_event(8, 1, 1)`, em que Para1 1 = vitória. As missões 100 e 411 (Para1 0)
  e a 765 (Para1 1) avançam; sai o 112 e a gravação do ataque vai em uma só save.
- **Ouro saqueado: sem fonte.** A captura não tem castelo atacado, nem o `4103` com ouro de saque. O
  `U_C_ARMY_ATTACK_CASTLE` (97) não tem listener no cliente decompilado (só a constante). Então o relatório sai
  com `goldBonus` 0 e nenhum ouro é creditado.
- **Níveis** *(cliente + grau 8)*: a diferença menor que 10 deixa atacar até o nível 17. A 411 pede nível 17,
  então só passa no 17. A 765 (nível 12) passa de 12 a 17. Se o grau do oficial for outro, isso muda.
- **Não feito**: PvP contra castelo de jogador (8488 segue sem alvo, porque exército alheio não existe aqui);
  repetir a 765 (o 5012 de missão já existente é recusado, `rules.py`); e a gravação no fim da luta: um corte no
  meio da luta não cobra o ataque.

## Coleta (Kaynak Topla, missões 55, 102, 140, 170, 171, 172): o que as fontes permitem

- **Botão ir** *(cliente)*: `TaskFrameII.as:707-708` pega `worldBossTemplateDict[NeedFightId]` (6001) e
  `WorldBossControler.sendEnterBattle` manda o 8258 com essa campanha. A 6001 é "Maden Ocağı", `Types` 2,
  `MinLevel` 1, `Capacity` 10000 (`Campaigns`). Não tem `CampaignData` nem `maps/6001` (o repo tem só os
  `.maps` 100, 10001 e 10002), e nenhuma captura tem 8258 nem 6001. Sem layout nem fonte, a entrada não é
  implementada. Hoje o 8258 é recusado com o aviso de indisponível (antes dizia "inválido").
- **Coleta no espaço** *(cliente)*: `CollectionAction.sendCollection` manda o 8733 com o id do nó
  (`PropertyMsg.param1`). Os nós "year" são `MasterType` 300 a 315 ou 410 (`SpaceNodeType.isYearNode`), e o 4811
  (`QueryCollectCampaignNodeRspMsg`, `PlayerManager.__receiveYearNodeDataHandler`) diz o recurso de cada nó
  (`sonType`, nome). Os templates têm 20 nós `MasterType` 300 (mapa 10000, "Hediye Yığını", `SonType` 10031):
  são pacotes de presente, não Kereste, Ametist nem Bakır. Nenhuma captura tem 4811 nem 8733.
- **Itens 2100022, 2100023 e 2100024**: nenhum código, drop ou tabela os cria (já visto em `missoes.md`).
- Resultado: coleta **não implementada**. Faltam: o layout da 6001 (`.maps` ou `CampaignData`), ou os nós de
  coleta com recurso (4811 de captura), e uma fonte dos três itens.

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
