# Mundo compartilhado

Visão geral e legenda em [multiplayer.md](multiplayer.md). O cliente tem três sistemas de presença
separados: (A) cidade do céu, (B) cidade externa e mapa-múndi, (C) salas de campanha em grupo.

## A. Cidade do céu ("Space", mapa 10000)

Cliente: `m2/scripts/map/space/manager/SpaceSocketManager.as`, `SpaceManager.as`,
`m3/scripts/map/space/mediator/hero/SpacePlayerWalkMediator.as`.

| op | dir | mensagem | papel |
|---|---|---|---|
| 4598 | S>C | SimplePropertyMsg `{param1:10000}` | mapa do space no login (já mandamos) |
| 4595 | S>C | RoomEnterMsg, `player[0]` = o próprio | cria a cena SPACE; logo depois do 6 no login |
| 4606 | S>C | RoomEnterMsg (próprio) | volta para o space (fim de campanha, teleporte) |
| 4597 | S>C | RoomEnterMsg com N `player` | outros jogadores presentes ou que chegaram |
| 4594 | S>C | SpacePlayerMoveMsg `{players{playerId, path[x,y em tiles]}}` | movimento dos outros |
| 4607 | S>C | SpacePlayerMoveMsg `{players{playerId}}` | alguém saiu ou ficou fora de vista |
| 8690 | C>S | SpacePlayerMoveMsg (o próprio, caminho em tiles) | o cliente andou |
| 8688 | C>S | SimplePropertyMsg | entrar no space |
| 149 | S>C | HeroEquUpdatedMsg | outro jogador trocou o visual |
| 8689 | C>S | SimplePropertyMsg | sair do space (`leaveSpace`, sem chamador no cliente) |
| 8692 | C>S | SimplePropertyMsg `{param1: nodeId}` | clicou num nó do mapa (`MapNodeInfos`) |
| 4601 | S>C | SimplePropertyMsg `{param1: nodeId}` | abre a janela do nó (`SpaceSceneController.__selectNodeHandler`) |
| 4126 | S>C | StandPosMsg `{id: playerId, posX, posY}` | teleporte sem andar |
| 8700 | C>S | vazio | `resetSpacePosition` (sem chamador) |
| 8701 | C>S | SpacePlayerArmyInfoReqMsg `{userList}` | dados de jogadores (sem chamador; não há mensagem de resposta própria) |
| 8733 | C>S | SimplePropertyMsg `{param1: nodeId}` | fim de uma coleta iniciada por 143 "COLLECTION" |
| 8694 | C>S | CampaignReqMsg `{paraInt1: mapa}` | ilha dos pets por opção de diálogo tipo 6 (nenhum nó usa hoje) |

*(visto)*:

- inglesa:
  - #7: 4595 com o próprio jogador em (76,76).
  - #91: 4598.
  - #2126: 4597 com 12 jogadores (na volta da pedreira 6001).
  - #2147 e #2148: um 4597 com 1 jogador, seguido de um 4594 com a posição dele.
- só turco: `login.json` #152: 4607.
- só turco: `gokyuzu_sehrine_teleport_ve_yurume_sistemi.json`:
  - #1: 4606.
  - #3 e #4: 4607.
  - #5 e #6: um 4597 com 3 jogadores, seguido de um 4594 com as 3 posições.
  - Depois disso, outros pares 4597/4594.
- Os 4594 saem em ticks de cerca de 500 ms.
- Não há eco do 4594 para o próprio jogador.
- 4597, 4594 e 4607 continuam chegando com o jogador na cidade externa. O cliente descarta o 4594
  fora da cena SPACE e mantém a lista, então o servidor considera o jogador "no space" enquanto
  ele não está numa campanha.
- 20261101-165308-1 #9364-#10019 (anel na cidade do céu): enquanto o jogador anda, chegam pares 4597 (um jogador,
  `currentRoomIndex` 0/1/2) + 4594 (a posição) e 4607 de outros; 8692 de NPC sempre com o 4601 do mesmo nó. A
  regra de quem entra e sai da tela (raio? limite de N?) não fecha com as posições vistas (Tankie sai a ~11 tiles):
  o servidor segue mostrando todos (TODO: AOI sem regra; `currentRoomIndex` sem uso no cliente conhecido).

Movimento *(cliente)*:

- O cliente acumula passos e manda 8690 a cada **7 tiles** ou ao parar.
- Passos colineares viram um só.
- O servidor repassa o mesmo `path` para os outros jogadores no 4594.

Campos de `RoomPlayerMsg` que o cliente usa para desenhar (`SpaceManager.readMember`):

- **Identidade:** playerId, heroId, armyId, nickName, grades, templateId (classe/sexo).
- **Posição e estado:** curPosX/curPosY em tiles, campaignId 10000, armyState, onlineState.
- **Equipamento e visual:** arm, cloth, wing, hat, fashionArm, fashionCloth, hide.
- **Montaria, pet e transformação:** mountTempId, petTemplateId, changeShapeId.
- **Status e guilda:** isVip, vipType, appellid, consortiaId e consortiaName.

## B. Cidade externa e mapa-múndi

O cliente pede por grade de 50 tiles; a janela visível é de 3×2 células
(`m3/scripts/map/outercity/manager/OuterCitySocketOutManager.as`):

- 5004 `OutercityReqMsg{mapId, position:"43_38,…"}`.
- 5181: sem resposta própria. A captura não tem S>C para ele; a grade chega no 169 do 8201.
- 8201 → **4129** `PhysicListUpdateMsg{wildLand[], baseCastle[]}` e depois **169**
  `OutercityArmyUpdatedGridMsg` (exércitos da grade). Hoje o 4129 leva o próprio castelo, as minas da
  instância (só o próprio jogador ocupa: o mapa 100000xxx é de cada conta) e, nos mapas 1 a 5, os castelos de
  outros jogadores nas grades pedidas; o 169 só traz o próprio exército (`handlers/outer_city.py`). Detalhes e
  o restante dos opcodes em [cidade-externa.md](cidade-externa.md).

Atualizações vivas:

- **140** `MapUpdatedMsg` com `updatedType`: 1 terra, 2 castelo, 3 exército. O `state` do exército
  é 0 parado, 1 andando, 2 em combate *(dedução da sequência)*.
- **4167** `PosMoveMsg`: rota de outro exército.
- **4168** `ArmyRemoveMsg`: o exército saiu.

*(visto)* inglesa #718: três castelos na cidade externa. Dois são de robôs
(ids 13000014xx), ou seja, o oficial preenche as vagas com robôs.

Clicar num castelo dá estas opções:

| Opção | Pacote |
|---|---|
| Atacar | 5160 `MapPhysicAttackMsg{mapId,posX,posY}` (mina livre luta; o resto só para o exército) |
| Mover castelo | 5176 ([cidade-externa.md](cidade-externa.md)) |
| Amigo | — |
| Correio | — |
| PvP contra um exército | 8488 `{tarUserId}` |

## C. Times e salas

**Time livre** (`m2/scripts/managers/FreedomTeamManager.as`) *(cliente, sem captura)*:

- Pedidos do cliente:
  - 8738: convida (só amigos).
  - 8734: aceita.
  - 8736: líder.
  - 8739: expulsar.
  - 8740: sair por ora (alterna `hasLeftForNow`; sem chamador no cliente).
  - 8741: sair de vez (sem chamador no cliente; mesma regra da desconexão).
  - 8737: posições.
- Respostas do servidor:
  - 4620: convite.
  - 4622: criado.
  - 4626: membro novo.
  - 4624: sincroniza membros.
  - 4625: desfeito.
  - 4627, 4629, 4630: líder, saída, expulsão.

**Sala de campanha em grupo** (ek sahne, `m3/scripts/map/campaign/CampaignSocketManger.as`):

- Pedidos do cliente:
  - 5023: criar.
  - 5026: listar.
  - 5024: entrar.
  - 5025: sair.
  - 5028: convidar.
  - 5033: iniciar.
- Respostas do servidor:
  - 13: lista.
  - 120: membros.
  - 125: sala criada.
  - **21**: RoomEnterMsg com todos os membros.
- Dentro da campanha:
  - 5124 (rota em px) é repassado aos outros como **4185** `PosMoveMsg`.
  - 124 e 123: membro online e offline.
  - 4183: HP compartilhado.
- Hoje `CampaignMap` é por sessão (`s.campaign`). Nenhuma captura tem 2 jogadores na mesma sala.

## No servidor

Fatia 1 (cidade do céu), feita em `game/space.py` e `game/handlers/space.py`:

**Escopo**
- Só depois do tutorial (`noviceProcess` ≥ 19000). O 4595 troca a cena do cliente.

**Login**
1. Espera a sessão anterior terminar (`OnlinePlayers.kick`) antes de carregar o snapshot. Se não
   terminar a tempo, recusa o login. Assim o relogin não duplica item nem é sobrescrito.
2. Depois do 6, manda 4595 com o próprio jogador.
3. Manda 4597 e 4594 com quem já está no space.
4. Avisa os outros com 4597 e 4594.

**Movimento**
- No 8690, guarda o último ponto e repassa 4594 aos outros.

**Saída**
- Quando a sessão termina ou entra numa campanha, manda 4607 aos outros.
- No relogin a sessão anterior já terminou antes da nova entrar (passo 1 do login), então os outros
  recebem o 4607 e depois o 4597, nessa ordem.
- A posição é gravada ao sair (fatia 2).
- O `RoomPlayerMsg` leva arma e armadura equipadas (`arm`/`cloth`). Montaria, pet, moda e guilda vão
  vazios até existirem.

**Fica para depois**
- ponytail: broadcast para o space inteiro, sem área de interesse nem tick de 500 ms. Nenhum pedido do
  cliente manda raio ou área de visão; ele só limita a criação a 1 view por 500 ms (`SpaceWalkLayer.as`).
  A filtragem, quando vier, é do servidor: escolher quem vai no 4597/4594 e tirar com 4607.

Fatia 2 (nós, posição, visual, ilha dos pets), em `game/space.py` e `game/handlers/space.py`:

**Posição**
- Fica nas colunas `characters.space_x` e `space_y` (padrão 76,76: o personagem novo do oficial inglês nasce aí, tutorial_en #7; migração 0044).
- O 8690 muda só a memória. A sessão grava o personagem quando termina, se o jogador já passou do tutorial.
- No login, o jogador entra onde parou.

**Visual (149)**
- `space.refresh_look(s)` manda `HeroEquUpdatedMsg{playerId, armStr, clothStr}` aos outros do space.
- O 5005 (mochila <-> herói) chama essa função. Quem implementar moda chama a mesma `refresh_look`.
- Asa, chapéu e moda vão vazios até existirem.
- Fontes: *(visto)* só turco: `exp_kitabi_...json` #22; *(cliente)* `SpaceSocketManager.as:186`.

**Nós (8692)**
- Vêm de `MapNodeInfos` do tempinfos.xml com `MapId=10000` (70 nós).
- O servidor confere que o nó existe e que o jogador está a até `HandlerRange+5` tiles. É a mesma conta do
  cliente (`SpaceArmyViewHelper.selfArmyToEnd`).
- Por MasterType:
  - 1 (NPC que anda): o cliente resolve sozinho; o servidor ignora.
  - 171 (teleporte, `Param3` = nível mínimo): o nó 5 leva à ilha dos pets. O nó 15 (mina de ametista, 30000)
    fica sem resposta: depende do sistema de minas.
  - Os demais (61 NPC com janela, 191 mapa do tesouro, 300 pilhas de presente): ecoa 4601 com o nodeId e o
    cliente abre a janela (`Param3` = "frameType,título,nível").

**Ilha dos pets (20001)**
- Entra pelo nó 5 ou pelo 8694, com a sequência da captura `peri_adasi_tp.json` #3-8 (só turco):
  1. 140
  2. 125 `{createdType 1, campaignId 20001}`
  3. 21, com o jogador em (141,171)
  4. 127 com os 121 nós, guardados em `content/petisland.json`
- Enquanto está na ilha, o jogador some do space dos outros (4607).
- Quando a cena termina de carregar (5035 `state=4`), o servidor repete o 21, como a captura (#6-7).
- Para sair, o cliente manda 5025 `RoomExitMsg` pelo botão de sair: no pet land o `MainToolBar` não pede
  confirmação. O servidor responde 4606 e o jogador reaparece para os outros. O 8688 também traz de volta.
  - ponytail: o 5025 só é tratado na ilha dos pets; o 5025 das salas em grupo é do sistema de salas (C).
- O 8694 também confere a distância até o nó de teleporte.
- No login vai 4686 `PetIslandDefendStateMsg` zerado, ou seja, sem invasão do chefe (inglesa #44).
- ponytail: mapa por sessão, sem outros jogadores. Pets selvagens (masterType 91), coleta (1003), loja
  (888) e o chefe dependem do sistema de pets/campanha.

**Outros pedidos**
- 8689: some da tela dos outros (4607).
- 8700: 4126 com o último tile conhecido.
- 8701: 4597 com os jogadores pedidos que estão no space (até 50).
- 8733: só registra no log. A coleta só existe depois de um 143 "COLLECTION", que ainda não mandamos.
- 9526 (baú dos monstros dos Wilds, 4940): saiu daqui; está em `handlers/wild_boxes.py`
  ([cidade-externa.md](cidade-externa.md)). No cliente o proto real é `army.BoxMsg`, com as mesmas tags do
  `ArmyBoxMsg`.
