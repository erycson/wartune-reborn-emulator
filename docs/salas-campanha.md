# Salas de campanha, times e pedidos do lote

Estado em memória do processo, como as guildas: `GameContext.rooms` (`game/rooms.py`) e
`GameContext.teams` (`game/teams.py`). Nada disto vai ao banco ainda; a decisão de persistência está na
seção [Persistência](#persistência-decisão). A única migração deste lote é a `0021` (contador de campanha em grupo, 4240).

Os handlers estão em `game/handlers/room.py` (salas), `team.py` (times), `campaign_map.py` (mapa de
campanha), `tower.py`, `dungeon.py` e `tollgate.py`. O 5025 é registrado em `handlers/space.py`, que
primeiro trata a ilha dos pets e só depois consulta a sala.

## Fontes

- **Visto**: captura `exp_kitabi_kullanim_kahraman_sarayi_ve_ek_sahne_giris_ek_sahne_mob.json` (sala
  "Büyük Kristal", #10 a #41); `replay_packets.json` (C>S 5033, 5038, 5039, 5122, 5126, 5180 com as
  respostas; os índices citados abaixo como "replay #N" são desse arquivo); `peri_uyanis.json` (5038 #89 e
  20 #90); `labirent_sandik_toplama_odulu.json` e `yeralti_labirenti_ve_ilk_mob.json` (4205 e 4425);
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
`ChangeMasterRspMsg` na troca de dono.

Dono sair dissolve a sala: cada um dos que estavam nela recebe o 15 com o próprio id.

Tipo de sala (`RoomReqMsg.roomType`): o cliente usa 0 para campanha (PvE), 1 para PvP e 2 para veículo
(`RoomListSocketOutManager.sendCreateRoom`). Aqui só existem as de campanha: 5023 e 5024 de outro tipo são
recusados, e 5026/8465 de outro tipo voltam vazios. Antes, uma sala PvP virava sala PvE.

## Opcodes

| Opcode | Nome | Estado | Fonte | Observação |
|---|---|---|---|---|
| 5023 | ROOM_CREATE | completo | visto | Capacidade do cliente, limitada a 1..4. Senha opcional. Tipo diferente de 0 é recusado. |
| 5024 | ROOM_ENTER | completo | visto (sequência) | Recusa sala cheia, senha errada, tipo diferente de 0 ou quem já está numa sala. |
| 5026 | ROOM_LIST | completo | visto (13 vazio) | Lista as salas de campanha (tipo 0). Outros tipos vêm vazios. |
| 5027 | U_C_CAMPAIGN_INVITE_PLAYER_LIST | só registra | cliente (`FreedomTeamInviteFrame`, aba 2) | Inalcançável: o botão de atualizar só manda o 5027 na aba 2, e a lista tem só as abas 0 e 1. Sem resposta. |
| 8465 | ROOM_FIND | completo na forma | dedução | Filtra por `roomId` e tipo 0. Sem captura do pedido. |
| 5029 | PLACESTATE | completo | dedução (quem pode) | Só o dono abre ou fecha lugar livre, fora do dono. Recusa devolve 17. |
| 5030 | MASTER_CHANGE | completo | cliente (121) | `paraInt1` é o novo dono; só o dono atual pode passar. |
| 5031 | KILLPLAYER | completo | cliente (28) | Só o dono expulsa; o expulso recebe o 28 e sai. |
| 5120 | CAMPAIGN_EXIT | completo para sala | cliente (15) | Sai da sala. Não tira o jogador de um mapa de campanha. |
| 5025 | ROOM_EXIT | completo para sala | cliente (15) | Ilha dos pets primeiro; fora dela, sai da sala. |
| 9504 | MULITY_CAMPAIGN_REQUEST | completo na forma | cliente (`BaseManager.__mulityCampaignRequestHandler`, 4913) | Link de sala no chat: pedido `SimplePropertyMsg` com o roomId. Responde 4913 com `param1` = sala, `param2` = campanha (0 = sem campanha) e `param7` = quem pediu está numa campanha (`s.campaign`, *dedução*; o cliente troca o alerta de entrada com ele). `SwitchPageHelp.isInCampaign` (cena do pedidor) dá a mesma leitura; `WorldBossHelper.getCampaignTips` não serve (só mapas especiais). Leitura alternativa (sala iniciada → False) não se separa, porque salas não iniciam aqui. Sala inexistente: sem resposta (*dedução*). |
| 5033 | CAMPAIGN_CONFIRM | parcial | replay (#1120, #1563); S>C 29 em #1154 | Caixa Pandora. O S>C 29 (`CampaignConfirmMsg`: título "Açma Duyurusu", `mapId` 879, `nodeId` 101107, type 0) abre a caixa, e o cliente devolve `sendFrameCallBack(mapId, nodeId, escolha)` (`CampaignMapController.__callServerSccess`; m3 `MapSocketOuterManager.as`). Então `paraInt1` = mapId, `paraInt2` = nodeId e `paraBool1` = confirmou (true no replay). O 1563 traz 880 e 102107. 879 e 880 não são Id de `MapInfos`, `CampaignData` nem `Campaigns`. O 5125 de chegada (#1119) leva 101107 em `paraInt1`. Depois do 5033 o replay mostra 140, 131, 128 e 157 (não conferidos um a um). O servidor não manda o 29 hoje. Falta: a recompensa da caixa e a resposta do servidor (captura de abrir a caixa). Não muda estado. |
| 5038 | CAMPAIGN_SYSTEM_ARMY | parcial | replay (#923 a #1321), peri_uyanis (#89 e #90) | `paraInt1` é o mapa (cliente: `PreLoadNextCampaign`). Responde 20 `SystemArmyMsg` com a lista do mapa para 1011, 1021 e 2011 (`SYSTEM_ARMY`); mapa fora da tabela: lista vazia. Visto: o 1011 tem o 20 no pacote seguinte (#923 → #924); nem todo 5038 tem (o #1219 não tem). Responder logo a cada 5038 é *dedução*; o cliente remove o listener depois do primeiro 20. A lista de cada mapa deve sair dos nós do `.maps` (*dedução*). |
| 5121 | CAMPAIGN_ARMY | parcial | cliente (`NpcInfoFrame`) | Não muda estado. Único remetente: `NpcInfoFrame`, com `paraInt1=2` fixo e `paraInt2` = id do NPC. Precisa de captura da resposta. |
| 5122 | CAMPAIGN_TAKE_CARD | parcial | replay (#1166, #1651) | Corpo visto: `paraInt1` 58073072 (o id do exército), `paraInt2` 2, `paraBool1` false. 19 e 4105 logo depois são do mapa, não resposta. A carta sai no fim da masmorra (#1221-#1243): 135 (`CampaignCards`, 5 cartas, preço 0), 115, 26 com o `index` escolhido, 83, 134. O sorteio está em `game/drops.py` (lista `Campaigns.Item`, [drops-masmorras.md](drops-masmorras.md)); falta ligar ao fim de masmorra, que não roda aqui. |
| 5126 | CAMPAIGN_FOG_UPDATE | parcial | replay | Névoa não é guardada. O 130 volta só no próximo ENTER. O oficial também manda 19 com névoa própria. |
| 5180 | CAMPAIGN_FINISH | parcial | replay (#1169, #1653) | `paraInt1` = 1. Replay mostra 140, 131, 128 e 157 com o próximo nó. Depende de progresso de campanha. |
| 5039 | CAMPAIGN_ENTER (começar a campanha da sala) | parcial, sem handler | replay (#908) | Corpo `{1: 1, 2: 1001}` (campanha 1001). Respostas: 125 `RoomCreatedMsg` (campaignId 1011), 140 (exército no mapa) e 21 `RoomEnterMsg`. Sem remetente no cliente decompilado. Falta o mapa 1011 (posição inicial e nós). |
| 4240 | U_C_ENTER_COPY_NUM_REFRESH (S>C) | parcial | visto (buyuk_sefer #3), cliente (`PlayerManager.__uPlayerEnterCopyNumHandler`) | Sem C>S. Vem depois do Büyük Sefer com `campaignCount` e `campaignMaxcount` (ver Persistência). Nenhum gasto de entrada visto. |
| 8286 | C_ROOM_REFUSE | completo | cliente (`sendRefuseInvite`, 4194) | Alterna "recusar convites". Responde 4194. O bloqueio do 5142 da guilda é *(dedução)*, ver [guilda.md](guilda.md). Não há convite de sala no servidor. |
| 8297 | TOWER_INFO | parcial | captura (4205) | 4205 com `maxIndex=60`, `campaignId=8001`, 0 entradas feitas e 1 livre de 1 (visto em `labirent_sandik` #17 e `yeralti` #1). `index` ecoa o pedido; `towerIndex` (andar atual) fica 0 sem progresso. `totalGp`, `itemTempIds` e `order` dependem de progresso. |
| 8300 | TOWER_LIVE | parcial | sem captura | Sem efeito. Custo da torre não modelado. |
| 8526 | OPRATE_REPLACEMENTS | parcial | cliente (4424/4423) | Sem efeito. Depende do chefe mundial ([boss-eventos.md](boss-eventos.md)). |
| 8528 | CAMPAIGN_SWEEP | parcial | cliente (4425), captura (4425) | Sem efeito: falta o pedido (`CampaignSweepReq`, sem captura C>S) e o progresso. Respostas vistas: status 1 abre a janela (`sweepType` 1 campanha, 2 labirinto); status 11 é o fim com `result`; status 5 não tem efeito no `MopupManager`. Custo em `ConfigInfos`: campanha `Campaign_Sweep_Gold` 5000 e `Campaign_Sweep_Time` 300 s; labirinto `Tower_Sweep_Gold` 1000 e `Tower_Sweep_Time` 30 s por andar. |
| 8734 | APPLY_INVITE_TEAM | completo | cliente (4620, 4622, 4626) | `param1` é quem convidou, `param7` aceitou. Aceitar cria o time se preciso. |
| 8736 | CHANGE_CAPTAIN | completo | cliente (4627) | Só o capitão troca. |
| 8737 | EDIT_TEAM_FIGHT_POS | completo | dedução (quem pode) | Qualquer membro muda as posições do time (4628). |
| 8738 | INVITE_TEAM | completo | cliente (4620) | Só amigo online (`RelationType.FRIEND`). Até 4 membros. Um convite pendente por vez. |
| 8739 | KICK_TEAM_MEMBER | completo | cliente (4630, 4625) | Só o capitão. Com dois membros sobrando o time acaba (4625). |
| 8740 | C_LEAVE_TEAM_FOR_NOW | completo | dedução (`sendAFK` sem chamador) | Alterna "sair por ora": o jogador fica no time, com `hasLeftForNow` no 4624. Responde 4621 (o cliente só atualiza a tela) e 4624. |
| 8741 | C_QUIT_TEAM | completo | cliente (`FreedomTeamManageFrame`, sair com confirmação) | Sai de vez. Quem sai recebe 4625 (o time acaba) ou 4629 com o próprio id, e o cliente limpa o time. Ver Times. |
| 8742 | BATTLEGUARD_OP | parcial | cliente (4631), captura (login #35) | Operação recusada, responde 4631 vazio. O login oficial manda 4631 com `watchInfo` {gridType 2, gridPos 1, jion1 3120101}; o servidor ainda não manda isso no login. Depende do inventário de gemas. |
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
  `MaxCount - multiCopyCount`); `campaignMaxcount` é o máximo do dia. *(visto)* o login oficial (`login.json`) traz
  1/1 no `PlayerMsg` e nenhuma captura tem 4240 no login. A captura `buyuk_sefer_kullanimi_grup_sahne_yarari_1` tem o
  uso do Büyük Sefer (`ItemTempInfos` 2032101, `Property1` 15, `Property2` 1, "valid for the day used"): 1/1 vira 2/2
  no 4240, com 115, 111 "Grup Ek Sahne yararı 1 kez arttı" e 3. O base é `MultiCampaign_MaxCount` (1). *(dedução)*
  o reset volta ao base no dia seguinte: o item diz que vale no dia do uso, e o reset em si não foi capturado.

## Dependências que faltam

- **Começar a campanha da sala**: o 5039 (visto no replay, corpo `{1: 1, 2: 1001}`) responde 125, 140 e 21.
  Falta o mapa 1011: posição inicial do exército (no 140) e os nós. O `InstanceSelectFrame` não está
  decompilado, então a escolha da campanha antes do 5039 ainda não foi capturada. Até lá a sala fica
  "Savaş seçilmedi".
- **Mapa de nós 1011/2011 e progresso de campanha**: 5180 e a varredura (8528) precisam disso. O 5033 é a caixa Pandora (outra dependência, ver a linha dele). Ver
  [mundo-compartilhado.md](mundo-compartilhado.md).
- **Lista de soldados por mapa (5038)**: só 1011, 1021 e 2011 estão na captura. `PawnTempInfos` confere
  para 2011 ("Otlak Kurdu", nível 5, no mapa 1011 de nível 5 a 7). Os demais mapas precisam de captura do
  5038 de cada um.
- **Varredura (8528)**: falta a captura do pedido C>S. As respostas 4425 estão nas capturas, mas nenhuma
  tem o pedido. Além disso, o progresso de campanha (vitória) não é salvo.
- **Torre**: sem progresso salvo. Os limites vistos (1 de 1, `maxIndex` 60) estão no 8297; a torre real
  ainda não tem o seu `maxIndex`.
- **Gemas da guarda de batalha**: `WorldBossHelper.checkMaze` pede inventário de gemas do labirinto. O
  login oficial manda o 4631 com `watchInfo`; falta captura de jogador sem gema e com gema, e saber o que
  `jion1` (3120101) é.
- **Pedágio**: sem agenda do evento. O template tem a configuração (`tollgate_count` 5 tentativas base,
  `tollgate_attack_count` 10 (desafio com diamantes), `tollgate_add_count` 1000 de limite de compras extras) e as tabelas
  `ScoreRewards` (28), `BossRewards` (370), `AreaRewards` (30) e `LuckyRewards`, que o parser descarta
  (filhos aninhados). Sem a agenda, fica fechado.
- **Contador de campanha multi (4240)**: falta o gasto da entrada. Nenhuma captura mostra o que consome uma entrada
  (entrar numa campanha em grupo, 5039, ou concluir). **precisa de captura**: entrar numa campanha em grupo com 1/1 e
  anotar o S>C seguinte (4240 ou não), depois concluir e anotar de novo. O teto de Büyük Sefer por dia não foi visto
  (`# ponytail:` em `_use_copies`).
- **Protocolo**: o cliente usa `com.road.yishi.proto.simple.PropertyMsg` para 9504 e 4913, que é o
  `SimplePropertyMsg` do `wartune.proto`. `ArmyMsg` não está em `wartune.proto`.

## Testes

- `tests/game/test_rooms_teams.py`: registros de salas e times, sem sessão.
- `tests/game/test_salas_campanha.py`: os 29 opcodes têm handler (e 5025); corpo vazio não derruba a
  sessão; fluxo completo da sala com dois jogadores (criar, entrar, recusar, expulsar, passar o dono,
  sair, dissolver e queda por desconexão); convite sem amizade não chega.
- `tests/game/test_salas_tipos.py`: sala de outro tipo não existe aqui (5023, 5024, 5026, 8465); link de
  sala no chat (9504 com 4913, e sala inexistente sem resposta); pré-carga do mapa (5038 com a lista da
  captura e mapa vazio); info da torre (8297 com 4205).
- `tests/game/test_copias_campanha.py`: o Büyük Sefer soma 1 por uso (115, 4240, 111, 3), o 4240 é salvo e o login volta a 1/1 no dia seguinte.
- `tests/game/test_convites_times_bencao.py`: os 10 opcodes sem corpo do lote (registro e corpo vazio);
  sair de vez com dois e três jogadores; sair por ora; recusa de convite de time e de guilda; recusas e
  bênção voltam no login; bênção do seminário; gancho, PvP e transporte.
