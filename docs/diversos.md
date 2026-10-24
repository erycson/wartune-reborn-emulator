# Diversos: veículos, conta e segurança, pacotes do login

Cidade do céu e ilha dos pets estão em [mundo-compartilhado.md](mundo-compartilhado.md).

Como ler a coluna "Fonte":
- *(visto)*: a captura e o índice do pacote.
- *(cliente)*: o arquivo `.as` do cliente inglês. Os caminhos são relativos a `D:\xampp\htdocs\wartune\decomp\2\scripts`,
  salvo quando indicado (`m3/...`, `m9/...`).
- *(dedução)*: não há prova direta.

Código: `game/handlers/vehicle.py`, `game/handlers/account.py`.

## Veículos (Daimon Trial / Tank Trials)

**Onde está no cliente inglês.** As janelas `vehicle.DaimonFrame`, `DaimonTrialFrame` e `VehicleRoomFrame` estão em
`m9/vehicle`. A cena VEHICLE (campanha 3001, `com.map.vehicle`) está em `m17/com/map/vehicle`. Código:
`game/handlers/vehicle.py` (pacotes, fila, prêmio) e `game/vehicles.py` (a partida, sem I/O). O mapa 3001 sai do
`maps/3001/3001.titles` da CDN para `data/vehicle_map_3001.json` (`tools/extract_vehicle_map.py`).

**Estado gravado** (colunas em `characters`):
- `vehicle_exp`, `vehicle_score`, `vehicle_default`: o perfil que vai no 4515.
- `vehicles`: os templateIds possuídos, separados por vírgula. Começa com `"1"`, o padrão do cliente em
  `SimplePlayerInfo._vehicleTempId`.

Fila, partidas e quem já ganhou o prêmio de cada janela ficam só em memória (`GameContext.vehicles`).

| C>S | O que o servidor faz | Fonte |
|---|---|---|
| login (depois do tutorial) | 4512 `matchState` = janela aberta agora, 4515 perfil, 4516 garagem, 4501 `param1` = `game_settings.vehicle_tech` (tecnologia). A conta nova da captura inglesa não recebe esses pacotes (nenhum na captura inteira). | *(visto)* `login.json` #83, #110-112 (só turco: `login`); *(cliente)* `BaseManager.__vehicleStartHandler` |
| 20008 relógio | 4512 de novo quando a janela abre ou fecha | *(dedução)*: o botão da barra e a fila dependem do 4512 (`TopToolsBar.as`) |
| 8608 entrada solo | Recusa com alerta: janela fechada ("Tanks are not open yet!"), menos de 5 min para o fim ("Tank Trial is about to close, cannot enter."), nível < 35, em luta/mapa/fila/sala. Senão 4525 `param1` 1 (o relógio "procurando" do `DaimonTrialBottomView`) e a fila. | *(cliente)* `RoomListSocketOutManager.as:80`, `VehicleRoomFrame.checkCanEnter`, `CampaignInfo` 3001 `MinLevel` |
| 8609 cancelar | Tira o jogador sozinho da fila; o cliente não espera resposta | *(cliente)* `RoomListSocketOutManager.as:86` |
| 5023/5024 tipo 2 | Sala de veículo (campanha 3001), a mesma das PvE; as listas e o convite vão pelo tipo | *(cliente)* `RoomListSocketOutManager.sendCreateRoom`, `VehicleRoomFrame` |
| 5039 (sala de veículo) | Só o dono, com todos prontos e cada um passando as travas do 8608: a sala inteira entra na fila, no mesmo time, e todos recebem o 25 `roomState` 2 (o relógio da sala) | *(cliente)* `VehicleRoomFrame.__startClickHandler` (`sendStartCampaignScene(0,0)`), `__updateRoomInfoHanlder` |
| 5037 `state` 1 (sala de veículo) | Cancel do dono procurando: a sala sai da fila e todos recebem o 25. Alguém sair da sala também a tira da fila. | *(cliente)* `VehicleRoomFrame.__cancelClickHandler` |
| (partida montada) | Sala: 25 `roomState` 3 e a sala some (o 125 descarta o `RoomManager`). Cada um: 125 `createdType` 1 com `room.campaignId` 3001, 4474 nós, 4517 todos os tanques (o próprio com `templateId` e `hp`) e a vida do chefe sem `playerId`, 4518 placar e relógio; os outros recebem o 4513 do novo. Nasce num ponto marcado do mapa com o buff 4 (Invincible, 10 s). | *(cliente)* `BaseManager.__createCampaignHandler`, `VehicleSceneController`, `VehicleModel.__initPlayerListHandler`, vehicle.helpTxt01 |
| 8615 andar | Tiles andáveis do 3001 (`VehicleModel.getWalkable`), até 10 pontos; a posição vira `path[0]`, os outros recebem o 4519. Tira a proteção. | *(cliente)* `VehicleSocketOutManager.as`, `AvatarPathWalkAi` |
| 8616 skill | Refaz as travas do cliente (vivo, sem atordoar, skill que ele tem, recarga, usos da caixa, alcance em px, inimigo vivo e sem proteção). Alvo único, área (calculada aqui), armadilha e em si mesmo. 4520 para todos, 4513 com a vida e 4518 com o placar. | *(cliente)* `VehicleCharacterController.keyDownHandler`, `CastAction` |
| 8617 pegar caixa | A skill da caixa vai para a tecla Q (4521; a antiga sai com `state` 1) e a caixa some (4474 `state` 1) | *(cliente)* `PickupAction`, `VehicleSkillbag.updateSkill` |
| 8610 voltar | Sai da partida: 4523 para todos; se um lado esvaziou, a partida acaba | *(cliente)* `VehicleSocketOutManager.sendReturnCampaignRoom`, `__playerExitHandler` |
| 8611 escolher veículo `paraInt1` | Só aceita veículo que o jogador já tem. Grava `vehicle_default` e responde 4515. | *(cliente)* `PlayerManager.as:1407`, `:1108` |
| 8619 ativar `param1` | Valida o veículo, cobra e grava; detalhes abaixo da tabela | *(cliente)* `VehicleDaimonController.as:84`, `m9/vehicle/daimon/view/DaimonRightView.as:207-251` |
| 25111 sair do nó | Responde 4175 `PlayerStateListMsg` com estado 0 (diferente de 6/7/8). O cliente solta o jogador do nó (`CampaignArmy.exitNode`). | *(cliente)* `m3/.../MapSocketOuterManager.as:172`, `CampaignSocketManger.as:1032` |
| 25112 ataque de veículo | Ecoa um 4520 sem dano (`attackTyep=1`), para a animação tocar | *(cliente)* `m3/.../MapVehicleCastAction.as:481`, `CampaignSocketManger.as:337` |

**A partida.** O que vem do cliente inglês:
- janela: `MatchOfVehicleTime` (`10:00,10:25|16:00,16:25`) nos dias `Vehicle_Day`, no fuso do jogo
  (`VehicleModel.initStartEndDate`); a partida vai até o fim da janela;
- vida máxima `Hp + (nível do tanque - 1) × 100` (`PlayerVehicleInfo.totalHp`), nível pelo `UpGradeTempInfos` tipo 24;
- 4 por time (`CampaignInfo` 3001 `Capacity`); diferença de 10.000 pontos acaba antes (vehicle.helpTxt01);
- chefe Derleth (2191) aos 300 s, caixas a cada 180 s, revive geral a cada `revivalTime` (30 s), e o morto recebe o
  `rebornTime` no 4513 (`VehicleBossDownTimeView`);
- `remainsTiem` do 4518 = fim da janela - início da partida (o cliente conta dali o chefe, as caixas e o revive);
- buffs pelo `VehicleBuffTempInfos` (`EffectType`): imunes barram atordoar e lentidão, escudo absorve
  `EffectValue`, sangramento e restauração pelo `Interval` (4522 estado 2), cura instantânea com `Duration` 0;
- fim: 4514 para todos com o vencedor (3 = empate) e, para quem ainda não ganhou nesta janela, baú (Victory/Failure
  Chest) e o pacote da posição (`VehicleAccountBottomView.getRunking`: 1º-5º um Runestone Pack; 6º em diante ou menos
  de 200 pontos a Small Runestone). O prêmio vai pelo correio; EXP e pontos do tanque vão no 4515.
- `isFirst` do 4515 = ainda tem o prêmio desta janela: false faz o `DaimonTrialBottomView` avisar "Tank Trails
  attempts have run out. You will gain no rewards if you enter." (`room.view.pve.RoomRightView.tip`).

O que só o servidor oficial sabia (não há captura de uma partida; tudo `ponytail` em `game/vehicles.py`): partida
com 1 de cada lado, 12 caixas com as skills 2-7 e 9-13 (uma por caixa sem `Maximum`), dano `ataque × Power% -
defesa/2`, pontos (1 a cada 10 de dano, 100 por abate, 1000 pelo chefe), o chefe parado no meio batendo a cada 5 s
num tanque ao alcance (aviso 4524 2 s antes), armadilha até 10 tiles, o significado dos números -1/-2/-3, quantos
Small Runestone (3), a EXP do fim (100 vencendo, 50 perdendo, mais 1 a cada 10 pontos), o texto do correio e a
velocidade (não é conferida).

**8619 em detalhe.**
- Valida:
  - o veículo existe em `VehicleObjectTempInfos` com `Type=1` (a garagem);
  - o jogador ainda não o tem;
  - tecnologia de tanque (o `param1` do 4501) `>= NeedGrades`. Texto do cliente: "Requires {0} Tank Tech Level.";
  - `NeedDiamond` Balens. O cliente abre o alerta "Do you want to consume {0} Balens to activate {1}?" com a opção
    de usar vinculados. `param2` 0 = vinculados primeiro, 1 = só Balens (`sendOpenVehicle`).
- Cobra pelo ledger (`reason="vehicle"`) e grava tudo numa transação.
- Responde 4516, 4515 e, se cobrou, 3.

**Dependências e limites:**
- **Mapas de guerra com veículos e torres (25111/25112).** São os `CampaignInfo` de Types 9, GvG e cross.
  Dependem do sistema de guerra de guilda (dono: [pvp.md](pvp.md) / guilda).
- **Tecnologia de tanque**: `game_settings.vehicle_tech`, padrão 218 *(visto: inglês, fora do login; o turco manda
  18218 no login)*. O cliente só a lê do 4501 e não tem tela nem regra para evoluí-la. Com 218, Nightwolf (365) e o 4
  (915) ficam bloqueados no próprio cliente.
- **Veículos sem `NeedDiamond`** não mandam 8619: o cliente só compara `autoOpenGrade`, que os templates não têm.
- **Um processo só**: fila e partidas não passam entre servidores (a batalha entre servidores não existe aqui).

## Anti-vício (AAS)

No login, o 4173 vai com `isCloseAAS=true` e `sysSwitch=false`. Isso desliga o sistema inteiro no cliente
(`LoginInitDataAccept.as:336`): o formulário e o timer não aparecem.

| C>S | O que o servidor faz | Fonte |
|---|---|---|
| 8260 cadastro (`cardName`, `cardId`) | Responde 4172 `PlayerAASRspMsg`. `result=true` exige nome não vazio e um documento chinês válido de 18 posições; `age` sai da data de nascimento do documento. O documento não é gravado. | *(cliente)* `mainBar/view/IndulgeFrame.as:157-205` |
| 8261 tempo online | Registra no log (debug) e não responde | *(cliente)* `ui/resourcebar/view/IndulgeView.as:88,177` |
| 8620 desligar (Kaixin) | Responde 4172 com `result=true` e `age=18`. O cliente só manda depois que a plataforma confirmou a identidade. | *(cliente)* `BaseManager.as:953-973` |

## Senha secundária (8806 / 4696)

**Como a senha é guardada.**
- Coluna `characters.vice_password`, com o sha256 de `id:senha`. Vazio quer dizer sem senha.
- Coluna `vice_reset_at`: a hora em que o reset foi pedido.
- O PlayerMsg do login leva `hasVicePassword` e `isDuringToResetTime`. Com isso o cliente sabe quando
  pedir a senha antes de trancar um item (`ArmyFrameII.as:405`).

**Regra da senha** (`VicePasswordUtil`): 6 dígitos, sem repetir o mesmo dígito em todas as posições e sem sequência.

| opType | Pedido | Resposta `result=1` quando |
|---|---|---|
| 1 | verificar `inputPass` | a senha confere; marca `s.vice_confirmed` na sessão |
| 2 | definir `inputPass`=`newPass` | o jogador ainda não tem senha e ela é válida |
| 3 | trocar: `prePass` é a antiga, `inputPass`=`newPass` é a nova | a antiga confere e a nova é válida; cancela um reset pendente |
| 4 | pedir reset | tem senha e não há reset pendente; grava `vice_reset_at` |

**Respostas e prazos.**
- Recusa: `result=0`. O cliente ignora e a janela continua aberta.
- O reset apaga a senha `VP_RESET_DAYS` (3) dias depois do pedido. Isso é conferido no login e no 8806.
  *(dedução)*: o prazo real não está no cliente nem nas capturas.

**Recompensa da primeira senha** (`ConfigInfos.vice_password_reward`: 5000 de ouro, Lvl. 1-3 Gem Pack, 2000 de Daru,
20 Mount Training Whip; o `SetVPView` mostra o mesmo):
- Login: 4696 `opType=6 result=1` logo antes do 4598 enquanto a recompensa não saiu (`event_states` `vice_reward`), só
  depois do tutorial. *(visto)* oficial_encantar #95; o mesmo personagem, depois de criar a senha, não recebe mais
  (153200, 171155, 215937, 231733); o tutorial_en (personagem novo) não tem *(dedução: só depois do tutorial)*.
- Quem já tem senha não recebe o aviso (sem como resgatar). O primeiro opType 2 aceito dá a recompensa: 109, 3, 115, 4476, os 4484, 111 "Congrats! You earned: Lvl. 1-3 Gem Pack
  x1, Mount Training Whip x20, 5,000 Gold, 2,000 Daru", 4696 6/0, 4696 2/1 e o mesmo texto no 83 *(visto)*
  oficial_encantar #256-#273. Uma senha nova depois do reset não dá de novo.

**Fontes.** *(cliente)* `mainBar/vicePassword/VicePasswordUtil.as:28`, `PlayerManager.as:211-292`, `SetVPView.as:93-131`;
*(visto)* oficial_encantar #95, #256-#273; só turco: `login.json` #99.

**Fica para depois.**
- Trancar e destrancar item (8809) é do dono da mochila e deve exigir `s.vice_confirmed`.

## Verificações, anti-trapaça e outros

| C>S | O que o servidor faz | Fonte |
|---|---|---|
| 8516 "tem captcha?" | Nada. O oficial só responde (4402) quando aplica captcha. | *(visto)* inglesa #125 sem resposta; *(cliente)* `MainToolBar.as:970` |
| 8514 resposta do captcha | Registra no log; nenhum captcha pendente | *(cliente)* `managers/SocketSecurityCodeMessageManager.as:17` |
| 8524 "já informou o telefone?" | 4420 `CheckSend{canSend=-1}`: telefone não informado (o SMS é por HTTP e não existe aqui) | *(cliente)* `managers/TaskSocketManager.as:49`, `m15/.../TaskMobilePhoneView.as:259` |
| 8352 código do SMS | Registra no log e recusa; vínculo de celular não existe | *(cliente)* `m15/.../TaskSocketSendManager.as:18` |
| 20010 batida do relógio | Sem resposta, como o oficial. Se chegar antes de 80% de 60 s depois da anterior, registra `possível speed-hack` no log | *(visto)* inglesa (#130, #192, ...): 33 pacotes a cada ~62 s, sem resposta; *(cliente)* `PlayerModel.as:286` |
| 20009 acelerador detectado | Registra aviso no log. Não tem chamador no cliente decompilado. | *(cliente)* `PlayerManager.as:1357` |
| 5041 dados do launcher | Ignora. Leva usuário, senha e token da plataforma, por isso **não vai para o log**. | *(cliente)* `PlayerManager.as:900` |
| 5020 estado de login | Nada: `SocketSendManager.loginState()` não tem chamador; o estado vai no 6 | *(cliente)* `SocketSendManager.as:73` |
| 8598 resposta de integridade | Registra no log. É a resposta ao desafio 4490, que não mandamos. | *(cliente)* `BaseManager.as:1697`, `farm/FarmManager.as:365` |
| 8301 saiu do nó de teleporte | Ecoa 4208 `PlayerNodeStateMsg` para quem está na campanha. O `opcodes.json` foi corrigido de `?Message` para `PlayerNodeStateMsg`; o `scan_opcodes.py` desfaz isso se for rodado de novo. | *(cliente)* `m3/.../TranseferWaitMediator.as:65`, `CampaignMapController.as:494` |
| 8302 guia de QTE concluído | Grava `characters.qte_guide=1`, que volta no PlayerMsg `qteGuide`. É o único guia que o cliente informa por pacote; o tutorial geral vai pelo `noviceProcess` (5017). | *(cliente)* `yishi/view/guild/QteSkillGuide.as:62`, `PlayerManager.as:828` |
| 8353 convite rápido ("Fast Invite") | `chat.py` ([chat.md](chat.md)): de quem está numa sala PvE com lugar livre. Gasta 1 Bullhorn (Small) 208003, com a cota grátis do 8198 antes (4500), e sai no canal mundo (83, canal 10) com `type` 4: a mensagem é uma tag `<room id campaignId roomType position name/>` (`position` 0 = trancada) e o texto inteiro (as linhas do `inviteContent` juntas) é o `name`, o link. O clique manda o 9504. Tipo 1 (casamento) é recusado: a sala de casamento não existe. Formato montado do cliente, sem captura | *(cliente)* `QuickInviteFrame.as:200-266`, `ChatFormat.as:73-77,411-437`, `SocketSendManager.as:373` |

## Pacotes do login oficial que o servidor não manda

Comparação de `login.json` (conta nível 56; só turco: `login`) e do início de `server-relay/replay_packets.json`
(conta nova; só turco: replay) com `handlers/login.py`. O login da conta nova inglesa (#1–#115) já está conferido em
[sequencia-login.md](sequencia-login.md):

- Desta fatia, passamos a mandar: 4512, 4515, 4516, 4501 (veículos) e 4686 (chefe da ilha dos pets, tudo zerado).
- 4173 já era mandado.

O conjunto comparado são os pacotes que `socket_login`, `login_load`, `_login_state`, `space.enter` e
`vehicle.login` mandam. Ficam fora:
- as respostas a pedidos do cliente (por exemplo 109 do 5015);
- o tutorial (inglesa #116–#122: 125, 140, 21, 127, 130, 143; o 1 vem depois, #165), que vem dos handlers da campanha.

Todos os pacotes de `login.json` saem hoje (conferido pacote a pacote; a captura foi apagada depois). Os últimos:
110 tipo 104 da tecnologia de ouro com a bênção (#20, 330), 4631/4633/4555 depois do 4544 (#35-#37; guarda e mapas
a partir do nível 55, dragão do 40), 4495 depois do 4686 (#40; runas do `OpenRuneGrade` 35), 4696 `opType=6` antes do
4598 (#99) e a ordem do baú de atividade 8235 (#134-#150, a mesma do inglês tutorial_en #1561-#1565). Diferenças que ficam:

| Pacote | Diferença | Por quê |
|---|---|---|
| 4631 | vai sem `watchInfo` (o turco tinha uma gema, 3120101) | shortcut: as gemas da guarda (8742) não são modeladas |
| 4501 | `param1` de `game_settings.vehicle_tech` (218, o do inglês); o turco manda 18218 | a regra da tecnologia de tanque não está no cliente |
| 109 do fim (#133) | resposta ao 5015 do cliente, como no inglês (#123→#124) | o pedido não aparece (a captura turca só tem S>C) |
| 462 | corpo `3800`, igual ao oficial | sem nome no `opcodes.json` |

## Visto no oficial e ainda sem regra (oficial_encantar #1833-#2892)

Horários da captura no relógio da máquina (UTC-3); o oficial segue o Pacífico (UTC-7).

| Pacote | O que o oficial fez | Por que não foi feito |
|---|---|---|
| 4686 ilha dos pets | login 11:39 com invasão aberta (`mapId` 20002, `bossId` 5102, `leftTime` 1242307 ms: fim 12:00); 12:00:16 tudo zerado; 14:00:16 abre `mapId` 20004, `bossId` 5104, `leftTime` 3584000 (1 h). Janelas de 1 h, mapa e chefe mudando | **feito**: janela pelo `ConfigInfos` e 4686 no login e no 20008 ([eventos.md](eventos.md#defend-sylph-atoll-a-janela-gamepet_defendpy-handlerspet_defendpy)) |
| 4512 veículos | `matchState` true às 14:00:25 e false às 14:25:28 (10:00-10:25 no Pacífico) | já igual: `MatchOfVehicleTime` 10:00,10:25 no fuso do jogo (`WARTUNE_GAME_TIMEZONE`) |
| 4501 tecnologia de tanque | `param1` 218 às 14:30:29, 5 min depois da janela, sem o jogador ter jogado | não se sabe de onde vem o 218 (o turco manda 18218); o servidor manda `game_settings.vehicle_tech`, padrão 218 |
| 11 lista de espera do PvE | 124 empurrões (65 entradas, 58 saídas, `playerState` 7) de outros jogadores, o dia todo. O cliente põe em `PlayerManager.watingList`, lido pela lista de jogadores do `PVERoomListFrame` | a captura não mostra o critério de quem entra na lista (o cliente não manda nada ao abrir a tela) |
| 5019 baú de tempo online | além de 115, 111, 4250, 4, 83 ×2, também 4476 (SumActive) e nove 4484 (títulos) | feito: os dois saem de `events.items_gained` |
