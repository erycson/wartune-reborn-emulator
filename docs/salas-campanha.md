# Salas de campanha, times e pedidos do lote

Estado em memória do processo, como as guildas: `GameContext.rooms` (`game/rooms.py`) e
`GameContext.teams` (`game/teams.py`). Nada disto vai ao banco ainda; a decisão de persistência está na
seção [Persistência](#persistência-decisão). A única migração deste lote é a `0021` (contador de campanha em grupo, 4240).

Os handlers estão em `game/handlers/room.py` (salas), `team.py` (times), `campaign_map.py` (mapa de
campanha), `tower.py`, `dungeon.py` e `tollgate.py`. O 5025 é registrado em `handlers/space.py`, que
primeiro trata a ilha dos pets e só depois consulta a sala.

## Fontes

- **Visto**: captura inglesa `captures/tutorial_en.json` ("inglesa #N": masmorras 1001/1002, 5033, 5038, 5039,
  5122, 5126, 5180). Só turco: `exp_kitabi_kullanim_kahraman_sarayi_ve_ek_sahne_giris_ek_sahne_mob.json` (sala
  "Claristun", #10 a #41); `replay_packets.json` ("replay #N"); `peri_uyanis.json` (5038 #89 e
  20 #90); `labirent_sandik_toplama_odulu` e `yeralti_labirenti_ve_ilk_mob` (apagadas; labirinto inteiro);
  `savasa_baskin_ve_elmas_ile_hizlandirma.json` (4425 da varredura); `buyuk_sefer_kullanimi_grup_sahne_yarari_1.json`
  (4240 e aviso 111); `login.json` (4631 com `watchInfo` #35).
- **Cliente**: `RoomManager.as` (listeners 15, 17, 28, 32, 120, 121), `RoomListSocketOutManager.as` (5023,
  5024, 5026, 8465, 9504), `BaseManager.as` (`__mulityCampaignRequestHandler`, 4913), `PreLoadNextCampaign.as`
  (5038), `CampaignSocketOutManager.as` (5122, 5126, 5180), `MapSocketOuterManager.as` (m3; 5121, 5033) e `MineralDialogFrame.as` (m3, chama o 5033),
  `FreedomTeamManager.as` (convite só a amigo, limite de 4 em `:527`), `MopupManager.as` (status da
  varredura), `WorldBossHelper.checkMaze`.
- **Templates**: `ConfigInfos` (`MultiCampaign_MaxCount`, `tollgate_*`, `Campaign_Sweep_*`, `Tower_Sweep_*`),
  `PawnTempInfos` (2011), `MapInfos` (1011, 1021, 2011), `ItemTempInfos` (2032101).
- **Dedução**: marcada na coluna "Fonte". Vale até uma captura confirmar.

## Salas PvE (roomType 0)

Um jogador está em no máximo uma sala. A sala tem 4 lugares: o do dono (0) e os demais. Lugar
fechado vale `-1`, lugar aberto `0`, ocupado tem o `userId` (`PlaceStateRspMsg`).

Respostas: 12 `RoomMsg` ao criar ou entrar; 17 `PlaceStateRspMsg`; 32 `EditRoomRspMsg`; 120
`RoomPlayerListMsg` para quem está na sala; 13 `RoomListRspMsg` para listas; 15 `RoomExitRspMsg` a cada
saída (o cliente volta à lista quando recebe o próprio id); 28 `KillPlayerRspMsg` na expulsão; 121
`ChangeMasterRspMsg` na troca de dono; 24 `PlayerReadyRspMsg` no "pronto"; 25 `RoomStateRspMsg` no estado da
sala; 16 `RoomInviteMsg` para o convidado.

`playerState` do 120 (e `readyState` do 24): 2 o dono (só turco, #20), 1 pronto, 0 sem "pronto" (o
`RoomRightView` mostra o botão Ready para 0 e Cancel para os outros; o `PVPRoomPlayerFigure` desenha 0 e 1).
Antes todos iam com 2, e quem entrava via o Cancel sem ter apertado nada. Sair da sala ou virar dono limpa o
"pronto".

Dono sair dissolve a sala: cada um dos que estavam nela recebe o 15 com o próprio id.

Tipo de sala (`RoomReqMsg.roomType`): o cliente usa 0 para campanha (PvE), 1 para PvP e 2 para veículo
(`RoomListSocketOutManager.sendCreateRoom`). Aqui existem as de campanha e as de veículo (campanha 3001, começa no
5039 e cancela no 5037: [diversos.md](diversos.md)); 5023 PvP é recusado, 5024 só entra na sala do tipo pedido, e
5026/8465 listam só o tipo pedido. Antes, uma sala PvP virava sala PvE.

## Opcodes

| Opcode | Nome | Estado | Fonte | Observação |
|---|---|---|---|---|
| 5023 | ROOM_CREATE | completo | visto | Capacidade do cliente, limitada a 1..4. Senha opcional. Tipo 0 (campanha) e 2 (veículo, campanha 3001); PvP é recusado. |
| 5024 | ROOM_ENTER | completo | visto (sequência) | Recusa sala cheia, senha errada, tipo diferente do da sala ou quem já está numa sala. |
| 5026 | ROOM_LIST | completo | visto (13 vazio); *(cliente)* `RoomListSocketOutManager.requestRoomList` | Lista as salas do tipo pedido, filtradas pela campanha do `nameKey` ("0" = todas). Outros tipos vêm vazios. Cada sala vai com `roomState` 1 ("em uso", `RoomState.STATE_USEING`): o `PVERoomItem` só deixa entrar com 1 e, com 0, mostra "This room is not being used". |
| 5027 | U_C_CAMPAIGN_INVITE_PLAYER_LIST | feito | *(cliente)* `RoomInviteFrame` (aba Hall, aberto pelo convite da sala PvE/PvP/veículo); `FreedomTeamInviteFrame` (times, aba 2 inexistente) | Responde 4161 `RoomPlayerListMsg` com quem está online e fora de uma sala, menos quem pediu (*dedução*, sem captura): `playerState` 1 (o cliente só lista com estado diferente de 0, `SimplePlayerInfo.isOnline`), nível, nome, sexo, guilda e poder. Antes era dado como inalcançável porque só o quadro dos times tinha sido lido. |
| 8465 | ROOM_FIND | feito | *(cliente)* `PVERoomItem`, `PVERoomSearchFrame`, `PVERoomListControler.__searchRoomHandler` | Clicar na sala ou procurar pelo número: 4370 `RoomMsg` da sala, e o cliente manda o 5024 ou abre a senha. `roomId` 0 (entrada rápida do PvP) = a primeira com lugar (*dedução*). Sala inexistente fica sem resposta (precisa captura). |
| 5029 | PLACESTATE | completo | dedução (quem pode) | Só o dono abre ou fecha lugar livre, fora do dono. Recusa devolve 17. |
| 5030 | MASTER_CHANGE | completo | cliente (121) | `paraInt1` é o novo dono; só o dono atual pode passar. |
| 5031 | KILLPLAYER | completo | cliente (28) | Só o dono expulsa; o expulso recebe o 28 e sai. |
| 5120 | CAMPAIGN_EXIT | completo para sala | cliente (15) | Sai da sala. Não tira o jogador de um mapa de campanha. |
| 5025 | ROOM_EXIT | completo para sala | cliente (15) | Ilha dos pets primeiro; fora dela, sai da sala. |
| 9504 | MULITY_CAMPAIGN_REQUEST | completo na forma | cliente (`BaseManager.__mulityCampaignRequestHandler`, 4913) | Link de sala no chat: pedido `SimplePropertyMsg` com o roomId. Responde 4913 com `param1` = sala, `param2` = campanha (0 = sem campanha) e `param7` = quem pediu está numa campanha (`s.campaign`, *dedução*; o cliente troca o alerta de entrada com ele). `SwitchPageHelp.isInCampaign` (cena do pedidor) dá a mesma leitura; `WorldBossHelper.getCampaignTips` não serve (só mapas especiais). Leitura alternativa (sala iniciada → False) não se separa, porque salas não iniciam aqui. Sala inexistente: sem resposta (*dedução*). |
| 5033 | CAMPAIGN_CONFIRM | feito (masmorra) | só turco: replay (#1120, #1563); S>C 29 em #1154 e #1622. A inglesa (#1428-#1438) difere: ver "Resposta ao 29" | Caixa Pandora da masmorra. O S>C 29 (`CampaignConfirmMsg`: título "Hints" (inglesa #1428), `mapId` 879 ou 880, `nodeId` 101107 ou 102107, type 0) abre a caixa, e o cliente devolve `paraInt1` = mapId, `paraInt2` = nodeId e `paraBool1` = confirmou. O servidor só age se houver um 29 pendente e os três campos baterem. Responde 4126 (posição do nó + 2, visto nas duas caixas), 4165 com o buff da captura (1301 no 1011, 1701 no 1021), 150, 150, 128 DONE, 111 e 83 com o alerta (replay #1155-#1161, #1623-#1630). No tutorial não há caixa. Falta: recompensa além do buff (a captura traz `itemTempId` 0). |
| 5038 | CAMPAIGN_SYSTEM_ARMY | parcial | inglesa (#874 a #3154), peri_uyanis (só turco: #89 e #90) | `paraInt1` é o mapa (cliente: `PreLoadNextCampaign`). Responde 20 `SystemArmyMsg` com a lista do mapa para 1011, 1021 e 2011 (`SYSTEM_ARMY`); mapa fora da tabela: lista vazia. Visto: um 20 para cada 5038 na masmorra (inglesa #874 → #876, #922 → #924 ...). O 20 do meio do fim do 1011 (inglesa #1101) é a resposta do 5038 #1095, não parte do fim. Responder logo a cada 5038 é *dedução*; o cliente remove o listener depois do primeiro 20. A lista de cada mapa deve sair dos nós do `.maps` (*dedução*). |
| 5121 | CAMPAIGN_ARMY | parcial | cliente (`NpcInfoFrame`) | Não muda estado. Único remetente: `NpcInfoFrame`, com `paraInt1=2` fixo e `paraInt2` = id do NPC. Precisa de captura da resposta. |
| 5122 | CAMPAIGN_TAKE_CARD | feito (masmorra) | inglesa (#1110 -> #1111-#1123, #1532, #2715, #3169); cliente (`ChestFrame`) | Corpo visto: `paraInt1` 58073072 (o id do exército), `paraInt2` 2 (o `index` da carta), `paraBool1` false (`isPay`; true no `autoChest`, quando o tempo do quadro acaba) (só turco: replay #1166; a inglesa traz 6837/0/true no #1110 e 6837/1/false no #1532). (cliente) só sai do clique numa carta do 135, então vem depois do fim (inglesa: 135 no #1107, 5122 no #1110). Com o mapa vencido e nenhuma carta virada, sorteia em `drops.card` (`Campaigns.Item`), grava o item num save e responde 115, 26 com o `index`, 83 e 134 (mochila cheia: só o 134). Antes do fim, `index` fora de 0..`cardCount`-1 ou segunda carta: sem efeito. Falta: chance de cada item e cartas pagas ([drops-masmorras.md](drops-masmorras.md)). |
| 5126 | CAMPAIGN_FOG_UPDATE | feito (masmorra) | inglesa (#881 -> #883) | Na masmorra devolve 19 com os mesmos `index` e `fogByte` enviados. A névoa não é guardada: o 130 volta com a névoa da captura no próximo ENTER. No tutorial, sem efeito. |
| 5180 | CAMPAIGN_FINISH | parcial | só turco: replay (#1169, #1653); a inglesa (#1124 → 134 no #1126, #1546, #2730, #3183) responde 134, ver "Carta (5122)"; cliente (`ChestFrame`) | `paraInt1` 1 = o quadro das cartas fechou (`dispose`, 8 s depois do 26), 2 = jogar de novo (`campaignAgain`). Sem efeito: a resposta não dá para separar no relay. (O revisor tirou a leitura "5180 solta a última luta": o 157 do #1186 é da chegada #1148, o relay não guarda a ordem entre C>S e S>C: o S>C chega uns 30 pacotes atrasado (o 10007 da luta 4c4d40c7 no #1153 vem antes do 157 dela no #1186; o 5033 do #1120 antes do 29 do #1154).) Depois do replay #1169 o cliente manda 5035 state 0 e 8747 (volta ao castelo) e o 5039 (replay #1212) leva ao 1021. |
| 5034 | CAMPAIGN_ROOM_EDIT | feito | *(cliente)* `InstanceSelectFrame` → `RoomSocketOuterManager.updateRoomInfo`; `RoomManager.__updateRoomInfoHandler` | `RoomReqMsg {roomId, dungeonId, campaignId}`: só o dono, campanha do `Campaigns`. Todos da sala recebem o 32 `EditRoomRspMsg` com `startCampaignId`. Recusa sem resposta (dedução, sem captura). |
| 8344 | C_ROOM_PWDCHANGE | feito | *(cliente)* `RoomRightView` (cadeado) → `RoomPasswordFrame` (`maxChars` 6, `restrict` "0-9") | `RoomEditMsg {roomId, roomPwd}`: só o dono; até 6 dígitos, vazio tira a senha. Todos recebem o 32 com o `passWord`. Recusa sem resposta (dedução). |
| 5036 | U_C_PLAYER_READY_STATE | feito | *(cliente)* `RoomRightView.sendPlayerReady`/`_cancelClick`; `RoomManager.__updateReaderStateHandler` | `RoomReqMsg {state 1 pronto / 0 cancelar, isGet}`: quem não é o dono. Todos recebem o 24 com o estado de cada membro. O `isGet` leva o `isNoGet` do cliente (`!_incomeBtn.selected`): true = entra sem prêmio e sem gastar a entrada, como o `paraBool1` do 5039 (visto 191924 #4525 "1/1", gpBonus 0; #6870 "0/1"). |
| 5037 | U_C_ROOM_STATE | feito na forma | *(cliente)* `PVPRoomRightView`, `VehicleRoomFrame` (mandam 1 ao começar); `RoomManager.__updateRoomStateHandler` | `RoomReqMsg {state}`: só o dono; todos recebem o 25 `RoomStateRspMsg {roomState}` e o estado vai no `RoomMsg` da lista (`RoomState`: 0 sem uso, 1 em uso, 2 competindo, 3 jogando). Na sala de veículo o 1 é o Cancel do dono procurando: a sala sai da fila (PvP não existe aqui). |
| 5028 | U_C_CAMPAIGN_ROOM_INVITE | feito | *(cliente)* `InviteItem`/`InviteItemButton` → `sendRoomInvite(userId)`; `BaseManager.__roomInviteHandler`, `InviteFrame` | `RoomReqMsg {userId}`. O convidado recebe o 16 `RoomInviteMsg {roomId, playerId, nickName, name, signStr, roomType (o da sala), tempId, position 0}`: `signStr` é a senha, que o aceite devolve no 5024 com `isInvite`; `name` a campanha escolhida (vazio: o cliente põe o texto padrão); `tempId` a campanha (aviso de estamina). Não recebe quem está offline, já numa sala ou recusa convites (8286). Recusa sem resposta (dedução). |
| 5039 | CAMPAIGN_ENTER (começar a campanha da sala) | feito (masmorras) | inglesa (#843, #1151, #2310, #2788) | `CampaignReqMsg {paraInt1: 1, paraInt2: <campanha>}`. Entra na etapa da vez da campanha pedida (`campaign_stage:<id>`): 125, 140, 21, 127, 130, 143, [138], 3, 83 "Entered [Worg Lair] and deducted 20 stamina.". 20 de estamina por etapa; sem estamina não entra e não responde (a recusa do oficial precisa de captura). Ver a seção das masmorras. Na sala de veículo (`VehicleRoomFrame`, `paraInt` 0/0) é o começar da fila ([diversos.md](diversos.md)). |
| 4240 | U_C_ENTER_COPY_NUM_REFRESH (S>C) | parcial | visto (só turco: buyuk_sefer #3), cliente (`PlayerManager.__uPlayerEnterCopyNumHandler`) | Sem C>S. Vem depois do The Empire Crusade com `campaignCount` e `campaignMaxcount` (ver Persistência). Nenhum gasto de entrada visto. |
| 8286 | C_ROOM_REFUSE | completo | cliente (`sendRefuseInvite`, 4194) | Alterna "recusar convites". Responde 4194. O bloqueio do 5142 da guilda é *(dedução)*, ver [guilda.md](guilda.md). Também barra o convite de sala (5028). |
| 8297 | TOWER_INFO | feito | captura (4205, só turco) | `game/maze.py` `info`: 4205 com `campaignId=8001`, `towerIndex` (andar da corrida), `maxIndex` (recorde), `totalGp` (EXP da corrida), `itemTempIds` ("id,n\|..."), entradas feitas e livres do dia (`game_settings.maze` `free_enter`/`max_enter`, 1 de 1 visto em `labirent_sandik` #17 e `yeralti` #1; zera no dia novo). `index` ecoa o pedido. `order` 0 (shortcut: o ranking do labirinto não existe). |
| 8299 | C_TOWER_RESET | feito | *(cliente)* `MazeFrame` (botão Reset, com `towerIndex` > 0, depois da confirmação); `PlayerManager.__towerInfoHandler` | `TowerInfoReqMsg {index}`. Fora de campanha, a corrida volta ao andar 0 (EXP, itens e dobrado zerados; o recorde fica) e responde o 4205. |
| 8296 | C_ENTER_TOWER | feito | captura (só turco: `yeralti` #26-#39), *(cliente)* `MazeFrame` | `EnterTowerInfoMsg {campaignId, chooseIndex 1 começar / 0 continuar, isDouble 2 lucro dobrado}`. Start gasta uma entrada do dia e começa no andar 1; o dobrado gasta a Crypt Key (208008). Continue volta ao andar da corrida. Resposta: 4205, 4165, 150, 150, 125, 140, 21, 3, 150 (4902 das cartas), 4903, 127, 4205, o 83 da poção de vida e o 4152 do leed 23. Andares (`game/maze.py`): mapa 8000+k, monstro 7000+k (a cada 5 o GameHeroTemp do chefe com 2 pawns), nós `mapa*100` + 1 início, 2 monstro, 3 baú, 4 portal. Vitória: o totalGp soma a EXP, o recorde sobe e o 4373 sai antes do 131. Portal: o 4205 com o andar novo depois do 21. Baú do chefe: 128, 115, 4476/4426, 4484, 111, 4205 com os itens e o 83 (só turco: `labirent_sandik`). |
| 8300 | TOWER_LIVE | feito | *(cliente)* `MazeRiverView` (25 Balens) | Dentro do labirinto, cobra 25 (`payType` 0 aceita os vinculados) e enche a vida do herói (3 e o 83). **TODO(inventado)**: a resposta, sem captura. |
| 8526 | OPRATE_REPLACEMENTS | parcial | cliente (4424/4423) | Sem efeito. Depende do chefe mundial ([boss-eventos.md](boss-eventos.md)). |
| 8528 | CAMPAIGN_SWEEP | feito (campanha e labirinto) | cliente (`MopupManager`, `CampaignMopupPrepareFrame`/`IngFrame`, `CampaignInfoView`), captura (4425, só turco) | `game/sweep.py`. op 1 começa: precisa da masmorra vencida (`campaign_rank`, o 4151 que mostra o botão), nível 20, 1..99 rodadas, estamina 20 × rodadas (status 6) e ouro 5000 × rodadas (status 3; grátis com o contrato 5 Free Blitz); já varrendo = 2. Resposta status 1 com `result` [type 2, `time` = rodadas × 300]. Cada rodada (`Campaign_Sweep_Time` 300 s) cobra 20 de estamina e `Campaign_Sweep_Gold` 5000 na hora em que acontece ("deducted gradually"), dá a EXP do fim (`total_gp(BaseGp)` + VIP type 6; 0 acima do `MaxLevel` da campanha, só turco: a 1007 no nível 56), o ouro de `game_settings.campaign_sweep.round_gold` (item -100; só turco: 6000 na 1007, **TODO(inventado)** as outras sem ouro) e uma carta (`drops.card`); sem estamina ou ouro a varredura para (status 15). op 3 pergunta: as rodadas novas em type 1 (`finishCount`, `gp`, `items`, `time` que falta) e um type 2 se ainda varre; status 5 (visto), 11 no fim. op 2 acelera: `ceil(segundos/60)` Balens (`payType` 1 = só Balens), grátis com o contrato 5; faz todas as rodadas e responde 11. op 4 fecha ou cancela: acerta o que venceu e apaga, sem resposta. Login: varredura aberta acerta o que venceu offline e manda status 10 com todas as rodadas, `totalGp` e `dropItems`. Baú de prata (ouro) e caixa misteriosa (Skeleton Key 208005): uma carta a mais cada, **TODO(inventado)** o ouro (2000) e o prêmio. Mochila cheia: rodada sem item (**TODO(inventado)**: `mailIn`). Labirinto (`sweepType` 2, `MazeMopupPrepareFrame`, só turco `yeralti` #2-#26): do `towerIndex` (1 sem corrida) até `eIndex`, abaixo do recorde e com recorde ≥ 10 (status 14 senão); 30 s (`Tower_Sweep_Time`) e 1000 de ouro (`Tower_Sweep_Gold`) por andar; começo: 109, 140 e o 4425 status 1 sem `result` nem `campaignId`; cada andar dá a EXP com o bônus de mundo e descansada (o 83 "Received N EXP" depois do 4425), o totalGp sobe só a base e o `towerIndex` vai ao seguinte; resultado type 1 com `cIndex`/`eIndex`; aceleração 5× (grátis com o contrato 4). |
| 8734 | APPLY_INVITE_TEAM | completo | cliente (4620, 4622, 4626) | `param1` é quem convidou, `param7` aceitou. Aceitar cria o time se preciso. |
| 8736 | CHANGE_CAPTAIN | completo | cliente (4627) | Só o capitão troca. |
| 8737 | EDIT_TEAM_FIGHT_POS | completo | dedução (quem pode) | Qualquer membro muda as posições do time (4628). |
| 8738 | INVITE_TEAM | completo | cliente (4620) | Só amigo online (`RelationType.FRIEND`). Até 4 membros. Um convite pendente por vez. |
| 8739 | KICK_TEAM_MEMBER | completo | cliente (4630, 4625) | Só o capitão. Com dois membros sobrando o time acaba (4625). |
| 8740 | C_LEAVE_TEAM_FOR_NOW | completo | dedução (`sendAFK` sem chamador) | Alterna "sair por ora": o jogador fica no time, com `hasLeftForNow` no 4624. Responde 4621 (o cliente só atualiza a tela) e 4624. |
| 8741 | C_QUIT_TEAM | completo | cliente (`FreedomTeamManageFrame`, sair com confirmação) | Sai de vez. Quem sai recebe 4625 (o time acaba) ou 4629 com o próprio id, e o cliente limpa o time. Ver Times. |
| 8742 | BATTLEGUARD_OP | parcial | cliente (4631), captura (só turco: login.json #35; a inglesa não tem 4631 no login) | Op 1 abre o encaixe (UpGradeTempInfos tipo 28: nível, Kingdom Mark nos entalhes 3-5, o 6 nunca abre, Willpower com 300 de resistência somada com a do mascote), op 2 encaixa gema SonType 312 da mochila (100 na Willpower, 101..106 nos entalhes, uma de cada por encaixe; a do lugar volta), op 3 tira (mochila ou correio). Responde 115, 4631 inteiro e 150 (ordem inventada); o login manda o estado gravado como o turco ({gridType 2, gridPos 1, jion1 3120101}). |
| 8746 | C_TEAM_REFUSE | completo | cliente (`sendRefuseTeamInvite`, 4635) | Alterna "recusar convites de time". Com ele ligado, o 8738 não chega ao alvo. Responde 4635. |
| 8752 | TOLLGATE_GET_REWARD | parcial | cliente (4645) | Responde evento fechado. Não há agenda do evento. |
| 8753 | TOLLGATE_REQUEST | parcial | cliente (4645) | Idem. |
| 8754 | TOLLGATE_SCORE | parcial | cliente (4645) | Idem. `TollgateReward.ScoreRewards` é descartado pelo parser. |
| 8755 | TOLLGATE_REQUEST_ATTACK | parcial | cliente (4645) | Idem. |

## Times

Só amigos entram: o cliente oferece convite só para quem tem `relation == 1`, e o servidor confere de
novo. O convite só chega se o alvo estiver online.

Quem sai avisa os demais com 4629, com o id de quem saiu. Com dois membros, o time acaba e os demais
recebem 4625. Se era o capitão, o novo capitão é enviado (4627). Na desconexão, quem caiu não recebe nada.

Sair de vez (8741) segue a mesma regra, e quem pediu recebe a própria resposta: 4625 se o time acaba, ou
4629 com o próprio id, que o cliente trata como saída (`FreedomTeamManager`). Sair por ora (8740) não tira o
jogador do time: alterna `hasLeftForNow`, que vem no `memberDetail` do 4624, e responde 4621, que o cliente
só usa para atualizar a tela. O cliente não envia o 8740 (`sendAFK` não tem chamador), então esse efeito é
dedução do campo.

## Persistência (decisão)

Hoje nada de salas e times vai ao banco. A decisão abaixo segue o oficial; onde falta captura, diz o que
capturar.

- **Salas: não persistem.** Lugares, dono e campanha ficam presos às sessões vivas. O oficial manda o
  estado ao vivo (12, 17, 32, 120) e dissolve a sala quando o dono sai (15 para todos). Nenhuma captura
  mostra sala restaurada no login.
- **Times: não persistem por enquanto.** Nenhuma captura tem 4620 a 4630 no login, então não dá para
  provar que o oficial restaura o time depois de relogar. Para decidir: formar um time com dois amigos,
  desconectar, logar de novo e gravar o login. Se o 4624 voltar no login, persistir membros, capitão,
  posições de combate (`fight_pos`) e `hasLeftForNow` numa tabela nova (migração).
- **Recusas de convite (8286, 8746): persistem** no personagem (`refuse_invite`, `refuse_team_invite`) e
  voltam no login (visto).
- **Contador de campanha multi (4240, `campaignCount` e `campaignMaxcount`): persiste** (migração `0021`:
  `multi_copy_count`, `multi_copy_max`, `multi_copy_day`; `Character.multi_copies`). `campaignCount` são as entradas
  que sobram (o cliente só entra com `multiCopyCount >= 1`, `InviteFrame` e `BaseManager`; `DayGuideManager` calcula
  `MaxCount - multiCopyCount`); `campaignMaxcount` é o máximo do dia. *(visto)* o login oficial (inglesa #14) traz
  1/1 no `PlayerMsg` e nenhuma captura tem 4240 no login. A captura `buyuk_sefer_kullanimi_grup_sahne_yarari_1` (só turco) tem o
  uso do The Empire Crusade (`ItemTempInfos` 2032101, `Property1` 15, `Property2` 1, "valid for the day used"): 1/1 vira 2/2
  no 4240, com 115, 111 "Grup Ek Sahne yararı 1 kez arttı" (texto turco da captura; o servidor manda "Multi-player Dungeon attempts increased by 1", deduzido) e 3. O base é `MultiCampaign_MaxCount` (1). *(dedução)*
  o reset volta ao base no dia seguinte: o item diz que vale no dia do uso, e o reset em si não foi capturado.

## Masmorras 1001 e 1002 e a pedreira 6001

O conteúdo vem do banco: tabela `campaign_contents`, um JSON por campanha, gravado pela migração 0034 a partir de
`persistence/migrations/versions/0034_campanhas.json`. O JSON sai da captura inglesa com
`tools/extract_dungeon.py captures/tutorial_en.json --campaign N`. Ele traz os mapas (nós, névoa, ponto de partida,
exército do 5038, diálogo de entrada e o 135), as lutas por nó, os diálogos de chegada, os baús, as perguntas (29)
com o desfecho, as moedas das caixas, os drops com chance, os avisos, os portais e a coleta. O `World` carrega
tudo uma vez (`world.campaigns` e `world.campaign_cards`). As fontes são as linhas `#N` de `captures/tutorial_en.txt`.

**Etapas.** As etapas são: 1001 = [1011], [1021]; 1002 = [1131 → 1132], [1141 → 1142]; 1003 = [1031 → 1032] (migração
0058, `oficial_20261023-153200-1`); 1004 = [1051], [1061] (migrações 0069 e 0071, `oficial_20261023-171155-1` e `oficial_20261023-215937-1`); 1005 = [1071 → 1072 → 1073], [1081 → 1082 → 1083] e 1006 = [1151], [1161] (migração
0075, `oficial_20261023-231733-1`); 1007 = [1171 → 1172] (migração 0090, `oficial_20261024-191924-1` #2345-#3706; a 2ª
etapa, 1181 → 1182 no `MapInfos`, não foi jogada e fica de fora); 6001 = [6001].

**Entrada (5039).** O 5039 manda `CampaignReqMsg {paraInt1: 1, paraInt2: <campanha>}` (o corpo `08 01 10 e9 07` é
a 1001). A etapa sai do estado do personagem: o `EventState` `campaign_stage:<id>` avança no fim de cada etapa. A
captura mostra o mesmo 5039 levando ao 1011 e depois ao 1021 (#843, #1151), e ao 1131 e depois ao 1141 (#2310,
#2788). *(dedução)* Depois da última etapa, volta à primeira.

A entrada custa 20 de estamina e manda, nesta ordem: 125 tipo 1, 140, 21, 127, 130, 143, 138 (se o mapa tem
diálogo), 3 e o 83 "Entered [Worg Lair] and deducted 20 stamina." (#844-#853). Sem estamina, o servidor fica calado.

**Portal.** O nó do portal (masterType 62: 113106, 114106) responde 4208, 125 tipo 3, 127, 130, 21 e 131
(#2503-#2508). A etapa (`StageRun`) passa para o mapa novo, então o tempo do 137 conta desde o 125 do 1131.

**Chegada (5125).** O que acontece depende do nó:

| Nó | Resposta |
|---|---|
| Com diálogo (Karlan 113205) | 138, um a cada 5125 (#2666-#2667). A luta vem no 5032 do fim do diálogo. |
| Caixa ou tumba (61, com pergunta) | 29 e 4126 na posição do nó + 2 (#1428-#1429, #2397-#2398). |
| Monstro ou chefe com luta | A luta começa. |
| Baú de ouro | 109, depois 126 ou 111, depois 128 e 83 "Received: 500 Gold" (#945-#948). |

A Pandora do 1011 nunca foi aberta na captura. *(dedução)* Ela usa o 29 da Pandora de mesmo `sonType` (102107),
com o nó trocado.

**Resposta ao 29 (5033).** O desfecho depende do conteúdo do nó:

| Nó | Resposta |
|---|---|
| Pandora | 4165 com o buff, 150, 150, 111, 128 DONE, 83 "Received: Rage Boost" (#1433-#1438). O buff é sorteado entre os do `param3` (*visto*: a mesma 102107 deu 1701 Rage Boost no tutorial e 1301 "Lvl. 1 PDEF Boost" no gravador, `oficial_encantar` #629-#635, onde o 128 veio antes do 111: a ordem entre os dois varia no oficial), e o texto é o `CampaignBufferTemps.TemplateName`. |
| Tumba com sentinela (113105) | 126 "You've startled a sentinel... begin battle!", 128 com `visitUserIds`, depois a luta (#2400-#2404). |
| Caixa do caçador (113203, 114203) | A luta. Na vitória (Daru; a 114203 sorteia Daru ou Lvl. 3 Luck Stone, que vem como 115, 4476, 126 sem o 3, oficial_encantar #1436-#1457): 3, 126 "Received: 10,000 Daru", 128 DONE para cada nó do `param4` da caixa (a caixa e os reforços 113207/113208) e 83 (#2630-#2644). |
| Tumba com Daru (114105) | 3, 126 "Received: 5,000 Daru", 128 state 1 visitado, 83 (#2874-#2877). |
| Caixa com chave (Mystery Box 103108) | O 29 traz `itemTempId` 208005 (Skeleton Key): sem a chave o 5033 não faz nada (log "5033 sem a chave"). Com ela, gasta a chave: 115 da chave, 109 (ouro), 128 DONE, 111 e 83 "Received: 5,000 Gold" (oficial_20261023-153200-1 #914-#918) ou 115, 128, 115 do item, 111 e 83 "Received: Lvl. 2 Luck Stone x2" (oficial_20261023-171155-1 #2538-#2552). |

O desfecho é sorteado (`_roll`): o `param5` do nó traz `tipo,item,n,peso|...` (-300 item, -200 Daru, -500 luta;
ex. tumba "-200,0,5000,50|-500,0,0,50", caixa "-300,2040103,1,50|-200,0,10000,50") e sai pelo peso; sem
`param5`, uma das listas de `pick` do conteúdo por igual, ou `drops`. Nó com `wins` (caixa do caçador) sempre luta, e
o sorteio vale para o prêmio da vitória. *(visto)* oficial_20261023-171155-1: a mina 103105 deu 10.000 Daru numa volta
e Lvl. 3 Luck Stone na outra. Nó sem luta própria (tumba 114105) usa a de um nó do mesmo `sonType`
(`CampaignMap.battle_like`, *dedução*).

**Drops de missão.** Item de missão de coleta (`QuestCondictionInfos` tipo 27 com `Para3` = a campanha, ex. Worg
Tooth da 90 na 1001, Perene Bone da 190 na 1003) só cai com a missão aberta (`rules.quest_goods_wanted`). *(visto)*
oficial_20261023-171155-1: nenhum Perene Bone na 1ª volta; na 2ª, com a 190 aberta (#2949), 2 no 103102 (#3296) e
1 em cada nó que a mina 103105 fecha (#3514, #3540, #3560, numa luta só; o relay atrasa os avisos); nenhum nas lutas
depois da entrega (#3558: 103103, 103104, 103106). *(dedução)* para na entrega: o 5º veio antes dela, e a captura
não separa "missão fechada" de "já tem os 5". Nó que fecha outros
(`param4` de um nó com `wins`) solta o drop de cada um.

**Grupo de monstros.** O `param4` do monstro diz o que muda quando o grupo cai:

- `id,0`: o nó some (DISAPPEARD).
- `id,1`: o nó aparece com FLICKER (o chefe do 1021).
- só `id`, sem ação (1002): o nó aparece só com o 128, como o portal do 1131 (#2470-#2471).

O 1021 manda o aviso 126 "Defeat all the worgs to remove the obstacle." antes.

**Alavanca (1003).** O Temple Hub 103204 (61, `param4` `103205,0|103207,1`) não tem luta: o 5125 manda 126
"Successfully open the outer temple." (delay 25), 142 no 103205, 143 DISAPPEARD, 142 no 103207 (75), 128 da
alavanca DONE, 143 FLICKER, 142 (0, 0) e o 128 do chefe aparecendo (`oficial_20261023-153200-1` #1117-#1126). O
extrator grava como `switches` o nó com 126 sem drop; `_switch` em `handlers/campaign.py`.

Há um desvio de ordem. No oficial (#1408-#1422), o aviso e os filmes saem antes do 128 do lobo, e o 128 do chefe
sai depois do 4382. Aqui eles saem depois do 128 e do 83 do drop.

**Daru e derrota.** O Daru de cada luta (`strategyBonus`, o 3 e o 4382) são os soldados perdidos, ganhando ou
perdendo: inglesa #1509 (88 = a reserva 738 -> 650), oficial_20261023-153200-1 #892-#1205 (127, 98, 115, 121) e
as derrotas #778 (53), #1324 e #1449 (202, o exército inteiro). Sem tropa, 0. Na derrota o `failCount` sobe: 1, 2
e 3 nas três derrotas da 1003. As lutas da cidade externa repetem o valor sem somar (#1623, #1899). *(dedução)* A
conta é da sessão.

**Luta.** Fora da masmorra (tutorial_en #906-#914) o fim da luta manda: 3, 4103, 83 "Received 35 EXP " (com o espaço
no fim), 150, 100, 140, 131. Na masmorra vale a ordem das capturas novas *(visto: oficial_20261023-171155-1 #5318-#5325,
#5532-#5543 na 1004, #2096-#2106 na 1003)*: 109 (população depois das baixas), 3, o 83 "Used HP pack to restore HP." se
a reserva curou, outro 3 se houve EXP, 4103, 150, 100, 140, 115 e 111 do drop, 112, 131, 128 DONE, o 83 da EXP e o 83
do drop; na derrota o 83 da poção vem logo depois do 4103 (oficial_20261023-153200-1 #1446-#1457). A última luta
(o chefe que fecha a masmorra) leva `gpBonus` 0 e `petGpBonus` -1 (tutorial_en #1509, #2692, #3146; #5783). O 4382 só sai quando o cliente volta ao
mapa, no 5035 state 4 (#1094-#1096). Ele leva o `strategy` do chefe (Daru: 88 no Wulfgar, 9 no Karlan, 28 na
Karda).

**Fim da etapa.** O mapa acaba com o chefe (masterType 41) ou com o grupo todo caído sem `param4`; caixas e tumbas
não acabam o mapa. O fim só sai no último mapa da etapa e vai junto do 4382: 3, 137, 4151, 83 "Received 630 EXP ",
135, 112 (missões do fim), 4165, 150, 150, 140 (#1096-#1107, #2703-#2714). O 20 no meio é a resposta do 5038.

**Carta (5122).** O 5122 responde 115, 26 e 83 "Received: Banshee Plume x1". O 5180 responde 134 e tira o jogador
do mapa (#1124-#1126). Depois do tutorial (noviceProcess > 30000) vem também o 4595 da cidade do céu *(visto,
oficial_20261023-171155-1 #2936-#2937, oficial_20261023-215937-1 #728-#729; até 28500 só o 134)*.

**Relatório 137.** O cálculo está em `game/campaign.py` (`report`, `grades`, `total_gp`):

| Campo | Cálculo |
|---|---|
| `time` | Segundos inteiros desde o 125 da etapa. *(visto)* 143, 151, 189, 177. |
| `woundValue` | Dano que o lado do jogador causou na etapa (`Battle.wound`). |
| `hurtValue` | Dano que o lado do jogador sofreu na etapa. A soma da captura não fechou com os 153, então vale a nossa simulação. |
| `failedCount` | Lutas perdidas. |
| `batter` | Maior 8282 recebido na etapa. O 8282 da última luta chega depois do 137 (#2698 → #2705), e o 7 mostrado é o maior anterior. |
| `woundAppraisal` | `1 + quantos de (0,7; 0,8; 0,9; 1,0)` a razão dano causado / `StandardDamage` alcança (0,62 ainda é D: `oficial_encantar` #689). |
| `hurtAppraisal` | `5 − quantos de (0,2; 0,4; 0,6; 0,8)` a razão dano sofrido / `StandardHurt` passa. |
| `failedAppraisal` | `max(1, 5 − derrotas)`. |
| `totalAppraisal` | Média das três notas, arredondada. |
| `totalGp` | `int(float32(BaseGp) × 1.05f)`: 600 → 630 e 800 → 839, como na captura (#1100, #2707). **Falta**: com o personagem no nível 10 e a Worg Lair (MinLevel 5, MaxLevel 7) repetida, o oficial deu 252 no fim (×0,4), 21 por lobo em vez de 35 e 52 de Daru no chefe em vez de 88 (×0,6) (`oficial_encantar` #449-#691). **É por nível**: no mesmo nível 10, a Baylon Plains (9-11) repetida deu tudo cheio (63 por luta, 441, 839 no fim; oficial_encantar #831-#1550, iguais à inglesa #2358-#2705). Falta a curva: com um ponto só (3 acima do `MaxLevel`: lutas e Daru ×0,6, fim ×0,4) não dá para deduzir; o servidor dá o valor cheio. Precisa de amostras com 1, 2 e 4+ níveis acima. |

As notas vão de 1 = D a 5 = S. *(dedução)* Os limites das notas foram deduzidos. As seis amostras (inglesa #1098,
#1521, #2705, #3157; só turco: replay #1215, #1722) dão 1, 5, 5, 4 e fecham com esses degraus. A internet não trouxe a
fórmula. O `StandSecond` não entra em nota nenhuma: o 137 não tem nota de tempo. O 4151 lista a melhor nota total
de cada campanha (`campaign_rank:<id>`), em ordem de id.

**Pedreira 6001.** O 8258 `{param1: 6001}` entra; é o botão "ir" da missão 102 (TaskFrameII.as:707). A entrada
manda 125, 140, 140, 21 e 127, sem névoa (#1805-#1809). A coleta funciona assim:

- 5125 numa pilha (masterType 91) responde 143 COLLECTION com o `nodeId`.
- Cada 5032 dá 2 ou 3 Wood (115, 111, 83 "Received: Wood x2"). A pilha nunca fecha.
- *(ponytail)* Não há limite de colheita.

O 8699 começa a luta da coleta (140, 157; herói Affudda 11005, mapTempId 1). O fim manda 115, 111 "Received: Wood
x18", 140, 4103, 150, 100, 83 e 4382 (#2050-#2070). A luta da captura foi perdida e a madeira veio mesmo assim. O
5025 sai: 4165, 150, 150, 140, 22 e a cidade do céu (4595) (#2118-#2123). A missão 102 (tipo 32, Wood 2100022) lê
a bolsa.

**Não feito.** Ficaram de fora:

- a fala no meio da luta (171);
- os movimentos de câmera (142);
- o `RejectType` da Karda (1023, "19,100,38,39"): só registrado.

**Tutorial e ilha dos pets.** Os dois continuam em `content/*.json`. `CampaignMap.enter`, o 127 da ilha e os
testes do tutorial leem esses arquivos sem banco, de forma síncrona. Levar para o banco é mudar esse caminho todo,
e o custo é alto para conteúdo que não muda.

**Correlações.**

| Missão | Liga com |
|---|---|
| 70 | Passar a 1001 (tipo 14). |
| 80 | Wulfgar (GameHeroTemp 1011), o chefe 102109. |
| 90 | 8 Worg Tooth (2100001), dos lobos do 1021. |
| 120 | Passar a 1002 (tipo 14) (#2710). |
| 130 | Os irmãos tauren, Karlan (1022) e Karda (1023). |
| 102 | Wood 2100022 (tipo 32), da pedreira 6001. |

## Rest House

Altar of Ennoblement (`handlers/hangup.py`): campanhas 7001-7009 (`Types` 3, mapa `7001`), nível 21
(`OpenGradesII.HOOK`). Sem captura; tudo do cliente (`HookMapMediator`, `HookTimeView`, `HookAlertFrame`,
`CampaignMapController`) e dos arquivos do mapa.

- Entrada (8258 `param1`): 4199 `leftWeay` antes da view, 125, 21, 127 (4 estátuas), 130, 4206 e o leed 22.
- Estátuas: nó `types` 111, `resource` 2, sonType 7001 (o `mapmaterial/build/7001.swf` é vazio: a estátua está na
  arte). **dedução**: as quatro `guajifang/shenxiang01-04` do `7001.maps` e os tiles valor 3 do `.titles` ao pé
  delas; o estado do 4206 é o índice da estátua (a CDN só tem `images/hook/1.png` a `4.png`). Entrada no bloco de
  tiles valor 4 (36,22).
- Chegar na estátua (5125) manda o 29 `type` 7, que abre o "Divine Statue"; o 5033 `paraBool1` começa (4200
  `isStartHangup`, 4206 para a sala). Cada 120 s: 4235 `addWeay` 1 e +1 de estamina (gravada).
- 8292 cancela (paga os tiques vencidos), 8293 acelera `min(resta, limite - estamina)` × `HangupFastPoint` (10)
  Balens, grátis com o contrato 4 (Lord of Time). Sem meditação, os dois devolvem o 4200 parado.
- Teto diário: `game_settings.rest_house.daily` (0096: 60 = RecoverInfos SonType 6 OneDayMax; Recuperar EXP 3 × 20).
- **dedução**: a meditação para ao sair (5025) ou desconectar; o oficial pode seguir offline (sem fonte).
- Falta: PK no mapa (8525 / 4421, BattleType 19).

## Dependências que faltam

- **Campanha da sala** (feito, `campaign._group_start`): o Start manda 5039 com `paraBool1` (usar a entrada do dia; `RoomSocketOuterManager.sendStartCampaignScene`); cada um entra com 125 da sala inteira (roomState 3). Só a 9001 tem conteúdo (0084); falta o mapa 2012 e a luta compartilhada entre os da sala (cada um joga o seu mapa).
- **Progresso de campanha e mapa 2011**: o estado dos nós da masmorra não é salvo (só a etapa da vez, a melhor nota, a carta e as missões). A varredura (8528) precisa do progresso. Ver [mundo-compartilhado.md](mundo-compartilhado.md).
- **Lista de soldados por mapa (5038)**: as campanhas no banco levam a sua (`maps[mapa].army`, inglesa
  #924, #1524, #2513); fora delas só o 2011 (só turco: peri_uyanis). Os demais mapas precisam de captura do 5038 de cada um.
- **Labirinto**: o Necropolis (8101, segunda aba) não tem andares (shortcut). Os andares 1 a 25 estão vistos nas capturas de 24 a 27/10 (`content/maze_floors.json`: nós, monstro, força, baú dos 5, 10, 15 e 20). Do 26 em diante é dedução: o sonType e a força são chutes (**TODO(inventado)**), o baú do 25 não foi visto, e o drop de monstro: nenhum nos andares 1 a 15 (o 4103 dá só EXP); o 21 e o 22 têm loot que não dá para atribuir a um monstro. A varredura não entrega o baú dos andares 5, 10, 15 e 20 que a captura de 25/10 mostrou (#9650), e o 4207 "Respawn Note" não é enviado pelo servidor. As capturas param no 25: o 30 que se fala ainda não tem prova. Os baús têm uma gema de nível 1 que varia (2050101, 2050501, 2050701 nos vistos), e a da varredura não foi confirmada.
- **Gemas da guarda de batalha**: modeladas pelo cliente (`BattleGuardView`, `PlayerManager.sendAddBattleGem`);
  `jion1` 3120101 é a Lvl. 1 Fire Resistance Crystal. Falta captura do 8742 (ordem da resposta, vínculo da gema
  devolvida: **TODO(inventado)**). Na batalha o golpe de elemento (mascote, PetType) cai pela resistência do alvo menos o ReduceResi do autor (attle.resist_factor, fórmula **TODO(inventado)**: o cliente não calcula dano).
- **Pedágio**: sem agenda do evento. O template tem a configuração (`tollgate_count` 5 tentativas base,
  `tollgate_attack_count` 10 (desafio com diamantes), `tollgate_add_count` 1000 de limite de compras extras) e as tabelas
  `ScoreRewards` (28), `BossRewards` (370), `AreaRewards` (30) e `LuckyRewards`, que o parser descarta
  (filhos aninhados). Sem a agenda, fica fechado.
- **Contador de campanha multi (4240)**: a entrada gasta uma ao começar com `isGet` (só turco: exp_kitabi #40, "1/2" depois da entrada; o PlayerMsg leva o `campaignCount` novo). Sem 4240 na entrada (a captura não tem). O teto de The Empire Crusade por dia não foi visto (`# ponytail:` em `_use_copies`).
- **Protocolo**: o cliente usa `com.road.yishi.proto.simple.PropertyMsg` para 9504 e 4913, que é o
  `SimplePropertyMsg` do `wartune.proto`. `ArmyMsg` não está em `wartune.proto`.

## Testes

- `tests/game/test_rooms_teams.py`: registros de salas e times, sem sessão.
- `tests/game/test_masmorra_1001.py`: 1001 pela captura inglesa: entrada (125, 140, 21, 127, 130, 143, 138, 3, 83 em inglês), campanha inexistente e a pedreira não entram pelo 5039, estamina, luta do lobo (4382 só no 5035 state 4), Pandora (29 e 4126 na chegada; 4165, 150, 150, 111, 128, 83), baú de 500, chefe travado, 5122/5180 fora do fim, fim do 1011 (137 com `totalGp` 630, 4151, carta 115, 26, 83; 134 no 5180; etapa avança), 1021 (aviso, DISAPPEARD, FLICKER, chefe, Daru 88, etapa volta a 0), 5126, 5038 do banco, missões 70, 80 e 90 jogando a 1001 inteira e o guia depois da 70.
- `tests/game/test_masmorra_1005_1006.py`: as duas etapas de cada uma, as cartas (Regalian Robe, VIP Token) e a luta
  inventada do elite 115116.
- `tests/game/test_masmorra_1007.py`: 1ª etapa da 1007: entrada no 1171, o portal 117105 fechado até o grupo de
  117103/117104 cair, a passagem para o 1172 e o Viscount Remus (117204), que fala no 5125 e luta no 5032.
- `tests/game/test_masmorra_1004.py`: entrada na 1004 (sala 1051), cartas com a Skeleton Key, baú de prata pago com ouro (ordem, texto, `param1` -100) e a recusa sem ouro.
- `tests/game/test_masmorra_1003.py`: entrada na 1003, portal para o 1032, alavanca (ordem, textos, `extend2`, estados) e o diálogo do chefe; Perene Bone só com a missão 190; Mystery Box com e sem a chave.
- `tests/game/test_masmorra_1002_pedreira.py`: `total_gp` (630, 839), notas das amostras (1, 5, 5, 4) e uma etapa com derrotas, `param4` com e sem ação, portal e fim de mapa; 1002 jogada (tumba com sentinela, portal 125 tipo 3, caixa do caçador com Daru e os nós que fecham, Karlan pelo 5032, fim com 839 e o 4151, 2ª etapa no 1141, tumba com Daru); pedreira (8258, COLLECTION, colheita, 8699 com Wood x18, 5025).
- `tests/game/test_missoes_masmorra.py`: condições 14, 25, 26, 27 e 31 contra a masmorra (casam o id e não somam, Para1 em lista, chefe pelo template, bolsa com entrega de todas as unidades, cena solo, fim de mapa com o grupo caído e sem `param4`) e os drops por nó (com chance).
- `tests/game/test_salas_campanha.py`: os 29 opcodes têm handler (e 5025); corpo vazio não derruba a
  sessão; fluxo completo da sala com dois jogadores (criar, entrar, recusar, expulsar, passar o dono,
  sair, dissolver e queda por desconexão); convite sem amizade não chega.
- `tests/game/test_salas_tipos.py`: sala de outro tipo não existe aqui (5023, 5024, 5026, 8465); link de
  sala no chat (9504 com 4913, e sala inexistente sem resposta); pré-carga do mapa (5038 com a lista da
  captura e mapa vazio); info da torre (8297 com 4205).
- `tests/game/test_copias_campanha.py`: o The Empire Crusade soma 1 por uso (115, 4240, 111, 3), o 4240 é salvo e o login volta a 1/1 no dia seguinte.
- `tests/game/test_convites_times_bencao.py`: os 10 opcodes sem corpo do lote (registro e corpo vazio);
  sair de vez com dois e três jogadores; sair por ora; recusa de convite de time e de guilda; recusas e
  bênção voltam no login; bênção do seminário; gancho, PvP e transporte.

## Captura que falta (revisão do m9 inglês)

Recusa do 8465 (sala inexistente) e do 5039 (sem estamina), campanha em grupo com 2 jogadores, mapa do gancho,
PvP em equipe, formato oficial do convite rápido 8353 e a sala de casamento. Na 1001: a resposta do 5180 (1 sair,
2 de novo), as cartas pagas (`isPay`, `payCardCount`), a recusa sem Beden, as missões (112, 4476/4484), o progresso
salvo (sair recomeça no 1011), a recompensa da Pandora além do buff, o 5121 e a chance de cada carta. O exército do
sistema (5038) só tem lista para 1011, 1021 e 2011.
