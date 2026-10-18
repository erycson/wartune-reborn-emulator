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
| 5033 | CAMPAIGN_CONFIRM | feito (masmorra) | replay (#1120, #1563); S>C 29 em #1154 e #1622 | Caixa Pandora da masmorra. O S>C 29 (`CampaignConfirmMsg`: título "Açma Duyurusu", `mapId` 879 ou 880, `nodeId` 101107 ou 102107, type 0) abre a caixa, e o cliente devolve `paraInt1` = mapId, `paraInt2` = nodeId e `paraBool1` = confirmou. O servidor só age se houver um 29 pendente e os três campos baterem. Responde 4126 (posição do nó + 2, visto nas duas caixas), 4165 com o buff da captura (1301 no 1011, 1701 no 1021), 150, 150, 128 DONE, 111 e 83 com o alerta (#1155-#1161, #1623-#1630). No tutorial não há caixa. Falta: recompensa além do buff (a captura traz `itemTempId` 0). |
| 5038 | CAMPAIGN_SYSTEM_ARMY | parcial | replay (#923 a #1321), peri_uyanis (#89 e #90) | `paraInt1` é o mapa (cliente: `PreLoadNextCampaign`). Responde 20 `SystemArmyMsg` com a lista do mapa para 1011, 1021 e 2011 (`SYSTEM_ARMY`); mapa fora da tabela: lista vazia. Visto: um 20 para cada 5038 na masmorra (#923 → #924 ... #1650 → #1718; o relay não guarda a ordem entre C>S e S>C: o S>C chega uns 30 pacotes atrasado (o 10007 da luta 4c4d40c7 no #1153 vem antes do 157 dela no #1186; o 5033 do #1120 antes do 29 do #1154)). O 20 do meio do fim do 1011 (#1218) é a resposta do 5038 #1165, não parte do fim. Responder logo a cada 5038 é *dedução*; o cliente remove o listener depois do primeiro 20. A lista de cada mapa deve sair dos nós do `.maps` (*dedução*). |
| 5121 | CAMPAIGN_ARMY | parcial | cliente (`NpcInfoFrame`) | Não muda estado. Único remetente: `NpcInfoFrame`, com `paraInt1=2` fixo e `paraInt2` = id do NPC. Precisa de captura da resposta. |
| 5122 | CAMPAIGN_TAKE_CARD | feito (masmorra) | replay (#1166 -> #1227-#1243, #1651 -> #1730-#1747); cliente (`ChestFrame`) | Corpo visto: `paraInt1` 58073072 (o id do exército), `paraInt2` 2 (o `index` da carta), `paraBool1` false (`isPay`; true no `autoChest`, quando o tempo do quadro acaba). (cliente) só sai do clique numa carta do 135, então vem depois do fim; no relay aparece antes porque o relay não guarda a ordem entre C>S e S>C: o S>C chega uns 30 pacotes atrasado (o 10007 da luta 4c4d40c7 no #1153 vem antes do 157 dela no #1186; o 5033 do #1120 antes do 29 do #1154). Com o mapa vencido e nenhuma carta virada, sorteia em `drops.card` (`Campaigns.Item`), grava o item num save e responde 115, 26 com o `index`, 83 e 134 (mochila cheia: só o 134). Antes do fim, `index` fora de 0..`cardCount`-1 ou segunda carta: sem efeito. Falta: chance de cada item e cartas pagas ([drops-masmorras.md](drops-masmorras.md)). |
| 5126 | CAMPAIGN_FOG_UPDATE | feito (masmorra) | replay (#950 -> #953) | Na masmorra devolve 19 com os mesmos `index` e `fogByte` enviados. A névoa não é guardada: o 130 volta com a névoa da captura no próximo ENTER. No tutorial, sem efeito. |
| 5180 | CAMPAIGN_FINISH | parcial | replay (#1169, #1653); cliente (`ChestFrame`) | `paraInt1` 1 = o quadro das cartas fechou (`dispose`, 8 s depois do 26), 2 = jogar de novo (`campaignAgain`). Sem efeito: a resposta não dá para separar no relay. (O revisor tirou a leitura "5180 solta a última luta": o 157 do #1186 é da chegada #1148, o relay não guarda a ordem entre C>S e S>C: o S>C chega uns 30 pacotes atrasado (o 10007 da luta 4c4d40c7 no #1153 vem antes do 157 dela no #1186; o 5033 do #1120 antes do 29 do #1154).) Depois do #1169 o cliente manda 5035 state 0 e 8747 (volta ao castelo) e o 5039 #1212 leva ao 1021. |
| 5039 | CAMPAIGN_ENTER (começar a campanha da sala) | feito (masmorra) | replay (#908, #1212) | Corpo `{1: 1, 2: 1001}` (campanha 1001). Não há tipo C>S para o 5039 no `opcodes.json`: o handler recebe `None` e ignora o corpo. Entra no 1011: 125 (`RoomCreatedMsg`, campaignId 1011), 140, 21, 127 (10 nós), 130 (névoa 24 x 19), 143 e 138 (diálogo de entrada, `{nick}`). Com o 1011 vencido, o mesmo 5039 leva ao 1021, sem diálogo. Cada mapa gasta 20 de Beden (`weary`, 200 → 180 → 160) e manda 3 e 83 "[Kurt İni] haritasına girildi, 20 can kullanıldı." (#917-#918, #1319-#1320), gravado num save; com menos de 20 não entra e não responde (a recusa do oficial precisa de captura). Sair para a cidade do céu (8688) entre os mapas zera `s.campaign` e o próximo 5039 volta ao 1011 (*dedução*). (dedução) vencido o 1021, o 5039 recomeça no 1011: a captura não mostra. |
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

## Masmorra Kurt İni (campanha 1001)

Mapas 1011 e 1021, nós, névoa, lutas, Pandora, baús e fim vêm de `content/dungeon_1001.json`, extraído da captura por `tools/extract_dungeon.py` (mesmo padrão do tutorial, sem nada do jogador). A sessão guarda o mapa em `CampaignMap` com `dungeon=True`: sem Tina e sem a tabela de retomada do tutorial.

- **Chegada (5125)**: nó com luta no `battles` começa a luta (inclusive o 101109 e o chefe 102109). Pandora (`param3` com buffs) manda o 29. Baú de ouro (101108 e 102108 com 500 e 126, 102104 com 111 "Kazanılan:Altın 500") dá o ouro num save só: 109, 126 ou 111, 128, 83 (#1020-#1023, #1475-#1477). Nó travado (`CampaignMap.locked`: o chefe 102109 só libera com o grupo caído) não reage.
- **Grupo de lobos**: a vitória só fecha o grupo (`param3`) quando todos caem. O `param4` do último lobo esconde (action 0, DISAPPEARD) ou mostra (action 1, FLICKER) outro nó; no 1021 vem o aviso (126) antes.
- **Fim**: vencer o último nó (101109 no 1011, chefe 102109 no 1021) manda 137, 4151, 83, 135, 4165, 150, 150, 140 (#1722-#1729); com a 70 aberta, o 112 dela sai entre o 135 e o 4165 (#1215-#1226). A carta sai quando o jogador clica (5122): `drops.card` (`Campaigns.Item`) com 115, 26, 83, 134 e o item gravado. Uma carta por mapa. O buff da Pandora zera no fim; a "Ruh" do chefe (`strategyBonus` 72) entra no personagem.
- **Ordem do relay**: o relay não guarda a ordem entre C>S e S>C: o S>C chega uns 30 pacotes atrasado (o 10007 da luta 4c4d40c7 no #1153 vem antes do 157 dela no #1186; o 5033 do #1120 antes do 29 do #1154). Só a ordem S>C entre si vale; o extrator não usa mais a ordem C>S.
- **Loot das lutas**: `content/dungeon_1001.json` (campo `drops`, por nó) dá o item de cada luta vencida: 102102 Kurt Dişi x2 e Şans Taşı Lv.1 x1, 102103 Kurt Dişi x2, 102105 e 102106 Kurt Dişi x3 cada (visto: replay #1355-#1592). Os Kurt Dişi formam uma pilha só (pos 6: 2, 4, 7 e 10). O Şans Taşı sai direto no 115 da luta; o oficial usa um baú (desvio). Os lobos do 1011 e o chefe não dão item. Sem chance (ver [drops-masmorras.md](drops-masmorras.md)).
- **Missões da 1001**: o fim de cada mapa (`campaign._map_finished`) vale a condição 14 (campanha 1001) e a 31 (cena solo, capacidade 1). A 26 (chefe 102109 morto, `Para1` 1011) é contada na batalha do chefe. A 27 (Kurt Dişi na bolsa) é lida e paga na entrega (5014): a pilha inteira sai, com o 115 vazio antes do 112 de conclusão (#1609-#1611). Fecham com a 1001: 70, 80 e 90 (ver [missoes.md](missoes.md)).
- **Diferenças de captura**: a EXP do fim (630, no texto do 83) é constante copiada: o `BaseGp` do 1001 é 600 e não explica o número. O diálogo de entrada é só o do 1011.

## Dependências que faltam

- **Começar a campanha da sala**: o 5039 entra no 1011 (seção da masmorra). Falta a escolha da campanha antes do 5039: o `InstanceSelectFrame` não está decompilado, então ainda não foi capturada. Até lá a sala fica "Savaş seçilmedi".
- **Progresso de campanha e mapa 2011**: o estado dos nós da masmorra não é salvo (só a carta e o progresso das missões 14, 26, 27 e 31 da 1001). O mapa 2011 não tem nós, e a varredura (8528) precisa do progresso. Ver [mundo-compartilhado.md](mundo-compartilhado.md).
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
- `tests/game/test_masmorra_1001.py`: masmorra Kurt İni: entrada (125, 140, 21, 127, 130, 143, 138); luta do lobo (157, 4103, 128, 4382); último lobo começa no 5125; Pandora (29, mapa errado sem efeito, depois 4126, 4165, 150, 150, 128, 111, 83, segunda caixa nada); baú de 500 uma vez e gravado (109, 126, 128, 83; 102104 com 111); chefe travado (`CampaignMap.locked`); 5122 antes do fim sem efeito; mapa 1011 inteiro, fim sem carta, 5122 fora das 5 cartas sem efeito, 5122 com 115, 26, 83, 134, carta gravada e uma só; grupo do 1021 (126, 143, 143, 128) e fim com o chefe e a carta dele; 5126 (19); missões 70, 80 e 90 fecham jogando a 1001 do começo ao fim (`test_missoes_70_80_90_fecham_jogando_a_1001_do_comeco_ao_fim`); pilha única do Kurt Dişi (2, 4, 7, 10), Ruh da 90 no PlayerMsg e o guia depois da 70 (`test_guia_depois_da_70_aprende_a_skill_e_avanca_o_novice`).
- `tests/game/test_missoes_masmorra.py`: condições 14, 25, 26, 27 e 31 contra a masmorra (casam o id e não somam, Para1 em lista, chefe pelo template, bolsa com entrega de todas as unidades, cena solo, fim de mapa com o grupo caído e sem `param4`) e os drops por nó.
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
