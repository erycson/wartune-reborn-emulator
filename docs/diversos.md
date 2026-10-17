# Diversos: veículos, conta e segurança, pacotes do login

Cidade do céu e ilha dos pets estão em [mundo-compartilhado.md](mundo-compartilhado.md).

Como ler a coluna "Fonte":
- *(visto)*: a captura e o índice do pacote.
- *(cliente)*: o arquivo `.as`. Os caminhos são relativos a `D:/wartune/decompiled/m2/scripts`, salvo quando indicado.
- *(dedução)*: não há prova direta.

Código: `game/handlers/vehicle.py`, `game/handlers/account.py`.

## Veículos (Daimon Trial)

**O que falta no cliente.** A cena VEHICLE (campanha 3001) é carregada por reflexão
(`com.map.vehicle.net.VehicleSocketManager`). As janelas `vehicle.DaimonFrame`, `DaimonTrialFrame` e
`VehicleRoomFrame` também não estão no cliente decompilado. Sem elas não sabemos o formato de 4513, 4514, 4518, 4519 e 4521 a 4524,
nem os pedidos de movimento e ataque dentro da cena.

**Como contornamos.** O servidor manda 4512 `matchState=false`, como o oficial fora do horário. Assim o botão
da barra não abre a fila (`TopToolsBar.as`).

**Estado gravado** (colunas em `characters`):
- `vehicle_exp`, `vehicle_score`, `vehicle_default`: o perfil que vai no 4515.
- `vehicles`: os templateIds possuídos, separados por vírgula. Começa com `"1"`, o padrão do cliente em
  `SimplePlayerInfo._vehicleTempId`.

| C>S | O que o servidor faz | Fonte |
|---|---|---|
| login (depois do tutorial) | 4512 `matchState=false`, 4515 perfil, 4516 garagem, 4501 `param1=0` (tecnologia). A conta nova do replay não recebe esses pacotes. | *(visto)* `login.json` #83, #110-112 |
| 8608 fila rápida | Registra no log e não responde. Sem a cena, não há sala para criar (o oficial responderia com 125 `campaignId=3001`). | *(cliente)* `RoomListSocketOutManager.as:80`, `BaseManager.as:1469` |
| 8609 cancelar fila | Nada; o cliente não espera resposta | *(cliente)* `RoomListSocketOutManager.as:86` |
| 8611 escolher veículo `paraInt1` | Só aceita veículo que o jogador já tem. Grava `vehicle_default` e responde 4515. | *(cliente)* `PlayerManager.as:1407`, `:1108` |
| 8619 ativar `param1` | Valida o veículo, cobra e grava; detalhes abaixo da tabela | *(cliente)* `VehicleDaimonController.as:84`, `DaimonModel.as` |
| 25111 sair do nó | Responde 4175 `PlayerStateListMsg` com estado 0 (diferente de 6/7/8). O cliente solta o jogador do nó (`CampaignArmy.exitNode`). | *(cliente)* `m3/.../MapSocketOuterManager.as:172`, `CampaignSocketManger.as:1032` |
| 25112 ataque de veículo | Ecoa um 4520 sem dano (`attackTyep=1`), para a animação tocar | *(cliente)* `m3/.../MapVehicleCastAction.as:481`, `CampaignSocketManger.as:337` |

**8619 em detalhe.**
- Valida:
  - o veículo existe em `VehicleObjectTempInfos` com `Type=1` (a garagem);
  - o jogador ainda não o tem;
  - `vehicle_exp >= NeedGrades`;
  - `point >= NeedDiamond`.
- Desconta o diamante e grava tudo numa transação.
- Responde 4516, 4515 e, se cobrou, 3.

**Dependências e limites:**
- **Batalha de veículos (campanha 3001).** Depende do módulo de cena que falta no cliente.
- **Mapas de guerra com veículos e torres (25111/25112).** São os `CampaignInfo` de Types 9, GvG e cross.
  Dependem do sistema de guerra de guilda (dono: [pvp.md](pvp.md) / guilda).
- **`NeedGrades`** é comparado com a EXP de veículo *(dedução)*: os valores 365 e 915 não cabem em nível.
- **`param2` do 8619** vale 0 ou 1 conforme uma flag do frame que falta. É ignorado: o servidor sempre cobra em `point`.
- **`isFirst`** vai sempre `true`, como na captura; o significado não é conhecido.

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

**Fontes.** *(cliente)* `mainBar/vicePassword/VicePasswordUtil.as:28`, `PlayerManager.as:211-286`; *(visto)* `login.json` #99.

**Fica para depois.**
- 4696 `opType=6` no login (*(visto)* #99, `result=1`) mostra o bloco de recompensa por definir a senha.
  Não mandamos, porque essa recompensa não existe aqui.
- Trancar e destrancar item (8809) é do dono da mochila e deve exigir `s.vice_confirmed`.

## Verificações, anti-trapaça e outros

| C>S | O que o servidor faz | Fonte |
|---|---|---|
| 8516 "tem captcha?" | Nada. O oficial só responde (4402) quando aplica captcha. | *(visto)* `replay_packets.json` #126 sem resposta; *(cliente)* `MainToolBar.as:970` |
| 8514 resposta do captcha | Registra no log; nenhum captcha pendente | *(cliente)* `managers/SocketSecurityCodeMessageManager.as:17` |
| 8524 "já informou o telefone?" | 4420 `CheckSend{canSend=-1}`: telefone não informado (o SMS é por HTTP e não existe aqui) | *(cliente)* `managers/TaskSocketManager.as:49`, `m15/.../TaskMobilePhoneView.as:259` |
| 8352 código do SMS | Registra no log e recusa; vínculo de celular não existe | *(cliente)* `m15/.../TaskSocketSendManager.as:18` |
| 20010 batida do relógio | Sem resposta, como o oficial. Se chegar antes de 80% de 60 s depois da anterior, registra `possível speed-hack` no log | *(visto)* `replay_packets.json`: 12 pacotes a cada ~60 s, sem resposta; *(cliente)* `PlayerModel.as:286` |
| 20009 acelerador detectado | Registra aviso no log. Não tem chamador no cliente decompilado. | *(cliente)* `PlayerManager.as:1357` |
| 5041 dados do launcher | Ignora. Leva usuário, senha e token da plataforma, por isso **não vai para o log**. | *(cliente)* `PlayerManager.as:900` |
| 5020 estado de login | Nada: `SocketSendManager.loginState()` não tem chamador; o estado vai no 6 | *(cliente)* `SocketSendManager.as:73` |
| 8598 resposta de integridade | Registra no log. É a resposta ao desafio 4490, que não mandamos. | *(cliente)* `BaseManager.as:1697`, `farm/FarmManager.as:365` |
| 8301 saiu do nó de teleporte | Ecoa 4208 `PlayerNodeStateMsg` para quem está na campanha. O `opcodes.json` foi corrigido de `?Message` para `PlayerNodeStateMsg`; o `scan_opcodes.py` desfaz isso se for rodado de novo. | *(cliente)* `m3/.../TranseferWaitMediator.as:65`, `CampaignMapController.as:494` |
| 8302 guia de QTE concluído | Grava `characters.qte_guide=1`, que volta no PlayerMsg `qteGuide`. É o único guia que o cliente informa por pacote; o tutorial geral vai pelo `noviceProcess` (5017). | *(cliente)* `yishi/view/guild/QteSkillGuide.as:62`, `PlayerManager.as:828` |
| 8353 convite rápido do capitão | Registra no log. Depende das salas PvE compartilhadas (dono: [mundo-compartilhado.md](mundo-compartilhado.md) C) | *(cliente)* `SocketSendManager.as:373` |

## Pacotes do login oficial que o servidor não manda

Comparação de `captures/login.json` (conta nível 56) e do início de `server-relay/replay_packets.json`
(conta nova) com `handlers/login.py`:

- Desta fatia, passamos a mandar: 4512, 4515, 4516, 4501 (veículos) e 4686 (chefe da ilha dos pets, tudo zerado).
- 4173 já era mandado.

O conjunto comparado são os pacotes que `socket_login`, `login_load`, `_login_state`, `space.enter` e
`vehicle.login` mandam. Ficam fora:
- as respostas a pedidos do cliente (por exemplo 109 do 5015);
- o tutorial do replay (1, 21, 125, 127, 130, 140, 143), que vem dos handlers da campanha.

Os pacotes abaixo continuam faltando. O cliente aguenta sem eles: cada um preenche o próprio painel quando chega.

| Pacotes | Sistema | Dono provável |
|---|---|---|
| 4426, 4427 | montaria | montaria |
| 4540, 4555, 4544 | pets, dragão, destino | pets / destino |
| 4902, 4903, 4905 | cartas de poder | cartas |
| 4631, 4495, 4178, 4180 | guarda de batalha, runas, estrelas | herói |
| 4542, 4484 | moda e títulos | moda / títulos |
| 4224, 4372, 4360, 4912, 4247 | sorte, refino de alma, recompensas, recuperação, taxa | castelo / atividades |
| 4152, 4150 | guia de tarefas (leed) | missões |
| 4614, 4616, 4198, 4393, 4638, 4640 | recompensas repetidas, ações diárias, 7 dias, primeiro depósito | atividades |
| 4461, 4463, 4475, 4476, 4251, 363, 364, 4901, 4428 | atividades e promoções | atividades ([boss-eventos.md](boss-eventos.md)) |
| 4238, 4145, 4184 | loja e ferreiro | loja |
| 4410, 4392, 4725 | VIP, atendimento, tokens | VIP |
| 4133, 4135, 4137, 4138, 4451, 4683, 4685, 4741 | guilda, guerra de guilda | guilda |
| 4182, 4248, 4776, 4201, 190, 414, 4590 | estado de boss, war field, PvP, mina, cadeiras, barra do topo | [boss-eventos.md](boss-eventos.md) / [pvp.md](pvp.md) |
| 4151, 4244, 4481, 4373, 4900, 4633, 4922 | ranking, torre, rei, mapa do tesouro, labirinto | ranking / masmorras |
| 85, 4232, 4497 | recomendação de amigos, estado do chat, garrafa | amigos / [chat.md](chat.md) |
| 152, 110, 4438, 4434, 4529, 4662 | segurança do castelo, efeito, prosperidade, contrato, lordes, casamento | castelo / eventos |
| 11 | lista de espera da campanha | [mundo-compartilhado.md](mundo-compartilhado.md) C |
| 100 | `ArmyPawnUpdatedMsg` das tropas, sem pedido (#6, #29) | exército / tropas |
| 109 | `CastleYieldMsg` empurrado no fim (#133); hoje só vai em resposta ao 5015 | castelo |
| 83, 111 | mensagens de sistema e o alerta de recompensa do guia de tarefas (#2, #148, #150) | [chat.md](chat.md) / missões (leed) |
| 4696 `opType=6` | bloco de recompensa da senha secundária (ver acima) | senha secundária (esta fatia), quando houver a recompensa |
| 462 | sem nome no `opcodes.json` (corpo `3800`) | desconhecido |
