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

O mundo do servidor tem o castelo do próprio jogador e as 4 minas de ouro do mapa 100 (ver *Minas de ouro*).
Não há outros exércitos, outras terras selvagens nem castelos alheios. Pedido que depende de outro jogador ou de terra é recusado ou respondido vazio, do jeito que o
cliente espera para não travar.

## Opcodes C>S

| Código | O que o servidor faz | Fonte | Depende de |
|---|---|---|---|
| 5004 | Registra. Sem resposta | *(cliente)* o cliente não lê resposta do 5004 | — (os exércitos da tela chegam pelo 169) |
| 5181 | Sem resposta própria. A grade vem no 169 do 8201 | *(visto)* transfer #12-15, cevre #11-12: sem S>C | — |
| 8201 | 4129 com as minas das grades pedidas (mapa modelo 100) e o próprio castelo, depois 169 com o exército próprio se cair numa grade pedida do mesmo mapa | *(visto)* transfer #15, replay #706 | outras terras selvagens e castelos vizinhos |
| 8254 | Guarda o último ponto andado (pixels // 20). 140 ×2 andando (state 1) no ponto de saída e, na chegada, 140 ×2 parado no destino (0,134 s por tile). Rota vazia, outro exército ou fora do mapa são ignorados | *(visto)* replay #761-#767 (18 tiles em 2,43 s); *(cliente)* `OuterCitySocketOutManager` | outros exércitos no mapa (4167) |
| 5161 | Volta o exército ao castelo, de graça: 98 com a posição | *(cliente)* o botão do exército não checa nada | — |
| 5160 | Mina livre: luta com o guarda (ver *Minas de ouro*). Sem alvo, ou mina já do jogador: 140 com o exército parado (state 0) | *(visto)* replay #713-#795; *(dedução)* parar sem alvo | outras terras, tesouros e castelos alheios |
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
  (replay e cevre), então são do mapa modelo 100: 853876 (16,34) nível 9, 853877 (36,34) nível 10,
  853874 (71,54) nível 8, 853875 (54,64) nível 10. Guarda: um soldado 6505 (6504 na de nível 8). O arquivo
  `maps/100/100.maps` não tem minas.
- **Guia do tutorial** *(cliente)*: o m8 (`NewbieBaseActionMediator`, alvo 80) procura as minas pelos pixels
  (320,680) e (720,680), e o castelo em (520,920). Sem elas a máscara escura do passo 22500 nunca sai. Por
  isso o castelo novo nasce em (26,46), como no oficial (`GridCastlePlacement`), e a migração 0017 move
  quem ainda estava na grade antiga.
- **Luta** *(visto)* #713-#744: 140 ×2 do exército lutando, 140 da mina em luta (state 4), 157 (battleType 1,
  mapa 100, as tropas do exército em duas pilhas nas posições 3 e 9, o herói na 4, o guarda na 5; vida da
  pilha = Live × soldados / 100). Fim: 150, 4103 (cena 4), 150, 100, 140 ×2. Vencendo: a mina fica do
  jogador, 112 da missão (condição 7, Para1 2006), 4152 (Leed 9), 109, 152 com o rendimento, 140 da mina
  ocupada e 169. Perdendo: 140 da mina livre. Os soldados não morrem, como no replay (150 antes e depois).
- **Volta** *(visto)* #750: o primeiro 5035 com state 3 depois da luta recebe o 4382.
- **Ouro** *(visto)*: cada mina ocupada soma `Property4` por hora no 109 (280 para 960). O 152 lista as minas
  em `wildYield` e mantém `goldYield` só com os prédios e `goldWildLandYield` em 0, como no replay.
- **0017** `wild_lands`: mina ocupada por personagem (`wild_id`, `occupied_at`), carregada em
  `PlayerSnapshot.wild_lands`. Relogar mantém a mina.

## Tabelas e migrações

- **0012** `arenas.attack_left` (padrão 5): ataques extras do dia. A virada do dia é gravada no login
  (junto com ele) e na 9506. Também conta no `PlayerMsg.attackLeftCount` e no `4202`.
- **0013** `treasure_maps`: uma linha por personagem, com `day`, `join_count` e `reward_count`. Carregada no
  `snapshot` (`PlayerSnapshot.treasure`), como `mystery_shops`.
- Diamantes passam por `services/ledger.py` (`pay`). Não há tabela de ledger nova.

## Dependências em aberto

1. **Mapa-múndi compartilhado.** Outras terras selvagens, castelos de outros jogadores e de robôs. Com isso:
   o 8201 completo (outros `baseCastle`), o 5160 contra castelos e o 8488. As minas do mapa 100 existem, mas
   cada jogador vê só a própria ocupação; o refresh de 12 h (nível sorteado de novo, ocupação que vence) não
   existe.
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
