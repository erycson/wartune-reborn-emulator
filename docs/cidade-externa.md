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

O mapa é compartilhado só no que o servidor guarda: o castelo de cada jogador (no mesmo mapa e nas grades
pedidas, pelo 8201) e as minas de ouro do mapa 100 ocupadas por quem já jogou (ver *Minas de ouro*). Não há
exércitos alheios andando, terras selvagens fora das 4 minas nem castelos de robôs. Pedido que depende disso
é recusado ou respondido vazio, do jeito que o cliente espera para não travar.

## Opcodes C>S

| Código | O que o servidor faz | Fonte | Depende de |
|---|---|---|---|
| 5004 | Registra. Sem resposta | *(cliente)* o cliente não lê resposta do 5004 | — (os exércitos da tela chegam pelo 169) |
| 5181 | Sem resposta própria. A grade vem no 169 do 8201 | *(visto)* transfer #12-15, cevre #11-12: sem S>C | — |
| 8201 | Roda o refresh (ver *Minas de ouro*). 4129 com as minas das grades pedidas (mapa modelo 100; o dono é o do ciclo atual, com nome e poder), o próprio castelo e os castelos de outros jogadores do mesmo mapa nas grades pedidas (`baseCastle`); depois 169 com o exército próprio se cair numa grade pedida do mesmo mapa | *(visto)* transfer #15 (no mapa 2 o 4129 traz o castelo de `asiesat` com `occupyPlayerName` e `occupyLeagueName`, e o 169 traz o exército dele); replay #706 | exército de outro jogador (o servidor não guarda a posição dele), terras selvagens fora das 4 minas (no mapa 2 há minas tipo 20 e bosses tipo 21) e castelos "Köy" sem dono (NPC, *(dedução)*) |
| 8254 | Guarda o último ponto andado (pixels // 20). 140 ×2 andando (state 1) no ponto de saída e, na chegada, 140 ×2 parado no destino (0,134 s por tile). Rota vazia, outro exército ou fora do mapa são ignorados | *(visto)* replay #761-#767 (18 tiles em 2,43 s); *(cliente)* `OuterCitySocketOutManager` | outros exércitos no mapa (4167) |
| 5161 | Volta o exército ao castelo, de graça: 98 com a posição | *(cliente)* o botão do exército não checa nada | — |
| 5160 | Mina livre: luta com o guarda (ver *Minas de ouro*). Sem alvo, mina já do jogador ou mina de outro jogador: 140 com o exército parado (state 0), sem luta | *(visto)* replay #713-#795; *(dedução)* parar sem alvo e na mina alheia | luta contra o dono de mina alheia, castelos e exércitos alheios, terras e tesouros (precisa de captura) |
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
  853875 (54,64). O nível não é fixo: é sorteado a cada refresh (abaixo). Guarda: um soldado, 6504 no nível 8
  e 6505 nos níveis 9 e 10. O arquivo `maps/100/100.maps` não tem minas.
- **Refresh de 12 h** *(visto)*: `RefreshTime` 43200 s (`MapPhysicsTempInfos`), que sai como 43200000 no 4129
  e no 140 das duas capturas (mapa 100); `createDate` é o começo do ciclo. *(dedução)* os ciclos começam a
  cada 12 h a partir de 2026-05-21 12:19:54 UTC (`createDate` do replay). A fase é do mundo: *ponytail*, a
  cevre abriu em outra hora; mundo novo pode ter outra fase.
- **Nível sorteado** *(dedução)*: os 8 sorteios vistos nas duas capturas (replay e cevre) deram nível 8, 9 e
  10. Cada ciclo sorteia o nível com semente `"<id da mina>:<início do ciclo>"`, então todo jogador vê o mesmo sorteio. Os
  templates são 200408, 200409 e 200410 (`MapPhysicsTempInfos`: `Grades` é o nível, `Property4` o ouro por
  hora). Nível fora de 8 a 10 e guarda diferente não têm captura.
- **Expiração** *(dedução)*: ocupação com `occupied_at` antes do começo do ciclo vence. Quem roda o refresh é o
  login, o 8201 e o 5160 (`handlers/outer_city.refresh`); não há tarefa periódica, então quem fica online só vê
  a mina cair no próximo pedido. Antes de sair, o ouro até o refresh sai na taxa antiga (`castle.expire_mines`
  chama `settle`), e as linhas vencidas saem com `delete=` (a unique é `character_id, wild_id`). *(ponytail)*
  ouro cobrado depois do começo do ciclo por handler que não passa pelo refresh (5015, 8202, 8327, farm) ainda
  paga a taxa da mina até o próximo 8201, 5160 ou login; subir: refresh antes de cada `settle`. Duas sessões
  que vencem a mesma mina no mesmo instante passam juntas na checagem de dono (sem trava por mina).
- **Dono de outro jogador**: o castelo alheio no 4129 leva `occupyPlayerId`, `occupyPlayerName` e
  `occupyLeagueName` *(visto)* transfer #15 (`asiesat`, mapa 2). Para a mina, *(dedução)* o 4129 leva o dono
  pelo mesmo campo e o poder em `fightCapaity`; nas capturas as minas do mapa 2 vêm com `occupyPlayerId` 0.
  Mina ocupada por outro: o 5160 só para o exército, sem luta (*ponytail*). *(precisa de captura)* a luta contra
  o dono e a regra oficial para isso.
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
  `PlayerSnapshot.wild_lands`. Relogar mantém a mina até o refresh. Leitura de todos os jogadores:
  `SqlWildLandRepository.occupied(ids, início do ciclo)`.

## Tabelas e migrações

- **0012** `arenas.attack_left` (padrão 5): ataques extras do dia. A virada do dia é gravada no login
  (junto com ele) e na 9506. Também conta no `PlayerMsg.attackLeftCount` e no `4202`.
- **0013** `treasure_maps`: uma linha por personagem, com `day`, `join_count` e `reward_count`. Carregada no
  `snapshot` (`PlayerSnapshot.treasure`), como `mystery_shops`.
- Diamantes passam por `services/ledger.py` (`pay`). Não há tabela de ledger nova.

## Dependências em aberto

1. **Mapa-múndi compartilhado.** Feito: castelos de outros jogadores no mesmo mapa e nas grades (8201) e minas
   ocupadas por outros, com nome e poder do dono (8201, 5160). Falta: exércitos de outros jogadores (o 169 da
   transfer #15 traz o de `asiesat`, mas a posição de outro jogador só existe na sessão dele; 4167 e 4168
   não existem aqui), terras selvagens fora das 4 minas, castelos NPC "Köy", e a resposta do 5160 e do 8488
   contra castelo ou exército alheio (*precisa de captura*). A luta contra o dono de uma mina alheia também *precisa de captura*.
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
8. **Minas (precisa de captura).** Perda de soldados numa derrota contra a mina; luta contra o dono de mina
   ocupada por outro; fase do refresh em outro mundo; guarda e nível fora de 8 a 10; e se o `RefreshTime` muda
   em outro mapa (no mapa 2 o `refreshTime` vem como contagem regressiva: 39799344 ms às 20:38 para `createDate`
   19:41:30).
