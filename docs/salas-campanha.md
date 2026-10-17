# Salas de campanha, times e pedidos do lote

Estado em memória do processo, como as guildas: `GameContext.rooms` (`game/rooms.py`) e
`GameContext.teams` (`game/teams.py`). Nada disto vai ao banco, então reiniciar o servidor esvazia as
salas e os times. Não há migração nova neste lote.

Os handlers estão em `game/handlers/room.py` (salas), `team.py` (times), `campaign_map.py` (mapa de
campanha), `tower.py`, `dungeon.py` e `tollgate.py`. O 5025 é registrado em `handlers/space.py`, que
primeiro trata a ilha dos pets e só depois consulta a sala.

## Fontes

- **Visto**: captura `exp_kitabi_kullanim_kahraman_sarayi_ve_ek_sahne_giris_ek_sahne_mob.json` (sala
  "Büyük Kristal", #10 a #41) e `replay_packets.json` (C>S 5033, 5038, 5122, 5126, 5180 com as respostas).
- **Cliente**: `RoomManager.as` (listeners 15, 17, 28, 32, 120, 121), `FreedomTeamManager.as`
  (convite só a amigo, limite de 4 em `:527`), `MopupManager.as`, `WorldBossHelper.checkMaze`.
- **Dedução**: marcada na coluna "Fonte". Vale até uma captura confirmar.

## Salas PvE (roomType 0)

Um jogador está em no máximo uma sala. A sala tem 4 lugares: o do dono (0) e os demais. Lugar
fechado vale `-1`, lugar aberto `0`, ocupado tem o `userId` (`PlaceStateRspMsg`).

Respostas: 12 `RoomMsg` ao criar ou entrar; 17 `PlaceStateRspMsg`; 32 `EditRoomRspMsg`; 120
`RoomPlayerListMsg` para quem está na sala; 13 `RoomListRspMsg` para listas; 15 `RoomExitRspMsg` a cada
saída (o cliente volta à lista quando recebe o próprio id); 28 `KillPlayerRspMsg` na expulsão; 121
`ChangeMasterRspMsg` na troca de dono.

Dono sair dissolve a sala: cada um dos que estavam nela recebe o 15 com o próprio id.

## Opcodes

| Opcode | Nome | Estado | Fonte | Observação |
|---|---|---|---|---|
| 5023 | ROOM_CREATE | completo | visto | Capacidade do cliente, limitada a 1..4. Senha opcional. |
| 5024 | ROOM_ENTER | completo | visto (sequência) | Recusa sala cheia, senha errada ou quem já está numa sala. |
| 5026 | ROOM_LIST | completo | visto (13 vazio) | Lista todas as salas. |
| 5027 | U_C_CAMPAIGN_INVITE_PLAYER_LIST | só registra | dedução (`sendRefreshInviteHall` sem chamador) | Inalcançável no cliente: a aba de convite da sala não existe. Sem resposta. |
| 8465 | ROOM_FIND | completo na forma | dedução | Filtra por `roomId`. Sem captura do pedido. |
| 5029 | PLACESTATE | completo | dedução (quem pode) | Só o dono abre ou fecha lugar livre, fora do dono. Recusa devolve 17. |
| 5030 | MASTER_CHANGE | completo | cliente (121) | `paraInt1` é o novo dono; só o dono atual pode passar. |
| 5031 | KILLPLAYER | completo | cliente (28) | Só o dono expulsa; o expulso recebe o 28 e sai. |
| 5120 | CAMPAIGN_EXIT | completo para sala | cliente (15) | Sai da sala. Não tira o jogador de um mapa de campanha. |
| 5025 | ROOM_EXIT | completo para sala | cliente (15) | Ilha dos pets primeiro; fora dela, sai da sala. |
| 9504 | MULITY_CAMPAIGN_REQUEST | parcial | cliente (4913) | Sem resposta. O formato do pedido não foi identificado. |
| 5033 | CAMPAIGN_CONFIRM | parcial | replay | Replay mostra 140, 131, 128 e 157. Depende do mapa de nós 1011/2011. |
| 5038 | CAMPAIGN_SYSTEM_ARMY | parcial | replay | Responde 20 `SystemArmyMsg` vazio. Origem de `soldierTemplated` não resolvida. |
| 5121 | CAMPAIGN_ARMY | parcial | sem captura | Não muda estado. `paraInt1` conflita com `NpcInfoFrame` (`paraInt1=2`). |
| 5122 | CAMPAIGN_TAKE_CARD | parcial | replay | Não muda estado. Depende da tabela de cartas. |
| 5126 | CAMPAIGN_FOG_UPDATE | parcial | replay | Névoa não é guardada. O 130 volta só no próximo ENTER. |
| 5180 | CAMPAIGN_FINISH | parcial | replay | Replay mostra 140, 131, 128 e 157. Depende de progresso de campanha. |
| 8286 | C_ROOM_REFUSE | completo | cliente (`sendRefuseInvite`, 4194) | Alterna "recusar convites". O 5142 da guilda não chega ao alvo que recusa ([guilda.md](guilda.md)). Não há convite de sala no servidor. |
| 8297 | TOWER_INFO | parcial | cliente (4205) | 4205 com `maxIndex=60` (visto no labirinto 8001) e entradas zeradas. Sem progresso. |
| 8300 | TOWER_LIVE | parcial | sem captura | Sem efeito. Custo da torre não modelado. |
| 8526 | OPRATE_REPLACEMENTS | parcial | cliente (4424/4423) | Sem efeito. Depende do chefe mundial ([boss-eventos.md](boss-eventos.md)). |
| 8528 | CAMPAIGN_SWEEP | parcial | cliente (4425) | Sem efeito. Depende do progresso. A UI não espera resposta: o 4425 só abre a janela (status 1) ou mostra aviso (status 2, 3, 4); os textos dos avisos não foram identificados, então não há recusa a mandar. |
| 8734 | APPLY_INVITE_TEAM | completo | cliente (4620, 4622, 4626) | `param1` é quem convidou, `param7` aceitou. Aceitar cria o time se preciso. |
| 8736 | CHANGE_CAPTAIN | completo | cliente (4627) | Só o capitão troca. |
| 8737 | EDIT_TEAM_FIGHT_POS | completo | dedução (quem pode) | Qualquer membro muda as posições do time (4628). |
| 8738 | INVITE_TEAM | completo | cliente (4620) | Só amigo online (`RelationType.FRIEND`). Até 4 membros. Um convite pendente por vez. |
| 8739 | KICK_TEAM_MEMBER | completo | cliente (4630, 4625) | Só o capitão. Com dois membros sobrando o time acaba (4625). |
| 8740 | C_LEAVE_TEAM_FOR_NOW | completo | dedução (`sendAFK` sem chamador) | Alterna "sair por ora": o jogador fica no time, com `hasLeftForNow` no 4624. Responde 4621 com o id e 4624. |
| 8741 | C_QUIT_TEAM | completo | dedução (`sendQuik` sem chamador) | Sai de vez. Mesma regra da desconexão (ver Times). |
| 8742 | BATTLEGUARD_OP | parcial | cliente (4631) | Operação recusada, responde 4631 vazio. Depende do inventário de gemas. |
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
4629 com o próprio id. Sair por ora (8740) não tira o jogador do time: alterna `hasLeftForNow`, que vem no
`memberDetail` do 4624, e responde 4621 com o id. Os dois pedidos não têm remetente no cliente decompilado
(`sendQuik` e `sendAFK` não são chamados), então o efeito é dedução do campo e da resposta.

## Dependências que faltam

- **Escolher campanha da sala e começar**: o pedido que escolhe a campanha (`startCampaignId`, 32) e o
  que começa a campanha da sala (125 e 21) não foram identificados. `InstanceSelectFrame` não está
  decompilado. Até lá a sala fica "Savaş seçilmedi".
- **5039**: não tem remetente `PackageOut` no cliente decompilado, só `ProtocolType` e a captura.
  Fica como dependência, fora da lista.
- **Mapa de nós 1011/2011 e progresso de campanha**: 5033, 5038, 5180 e a varredura (8528) precisam
  disso. Ver [mundo-compartilhado.md](mundo-compartilhado.md).
- **Origem de `soldierTemplated 2011`**: a tabela `PawnTempInfos` ainda não foi conferida.
- **Torre**: sem progresso salvo e sem tabela de limites. O 8001 tem `maxIndex=60`; a torre real
  ainda não tem o seu.
- **Gemas da guarda de batalha**: `WorldBossHelper.checkMaze` pede inventário de gemas do labirinto.
- **Pedágio**: sem agenda do evento; `TollgateReward.ScoreRewards` está descartado no parser.
- **Protocolo**: `PropertyMsg` (4913) e `ArmyMsg` não estão em `wartune.proto`. O 4913 aparece no
  `opcodes.json` com `SimplePropertyMsg`.

## Testes

- `tests/game/test_rooms_teams.py`: registros de salas e times, sem sessão.
- `tests/game/test_salas_campanha.py`: os 29 opcodes têm handler (e 5025); corpo vazio não derruba a
  sessão; fluxo completo da sala com dois jogadores (criar, entrar, recusar, expulsar, passar o dono,
  sair, dissolver e queda por desconexão); convite sem amizade não chega.
- `tests/game/test_convites_times_bencao.py`: os 10 opcodes sem corpo do lote (registro e corpo vazio);
  sair de vez com dois e três jogadores; sair por ora; recusa de convite de time e de guilda; recusas e
  bênção voltam no login; bênção do seminário; gancho, PvP e transporte.
