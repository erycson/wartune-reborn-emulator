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

*(visto)*:

- `login.json`:
  - #100: 4598.
  - #104: 4595 com o próprio jogador em (72,74).
  - #131: 4597 com 14 jogadores.
  - #152: 4607.
- `gokyuzu_sehrine_teleport_ve_yurume_sistemi.json`:
  - #1: 4606.
  - #3 e #4: 4607.
  - #5 e #6: um 4597 com 3 jogadores, seguido de um 4594 com as 3 posições.
  - Depois disso, outros pares 4597/4594.
- Os 4594 saem em ticks de cerca de 500 ms.
- Não há eco do 4594 para o próprio jogador.
- 4597, 4594 e 4607 continuam chegando com o jogador na cidade externa. O cliente descarta o 4594
  fora da cena SPACE e mantém a lista, então o servidor considera o jogador "no space" enquanto
  ele não está numa campanha.

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
- 5181 → **169** `OutercityArmyUpdatedGridMsg`: exércitos da área.
- 8201 → **4129** `PhysicListUpdateMsg{wildLand[], baseCastle[]}`: castelos e terras. Hoje
  respondemos só com o próprio castelo (`handlers/outer_city.py`).

Atualizações vivas:

- **140** `MapUpdatedMsg` com `updatedType`: 1 terra, 2 castelo, 3 exército. O `state` do exército
  é 0 parado, 1 andando, 2 em combate *(dedução da sequência)*.
- **4167** `PosMoveMsg`: rota de outro exército.
- **4168** `ArmyRemoveMsg`: o exército saiu.

*(visto)* `cevre_altin_madeni_savasi.json` #11: três castelos na cidade externa. Dois são de robôs
(ids 13000027xx), ou seja, o oficial preenche as vagas com robôs.

Clicar num castelo dá estas opções:

| Opção | Pacote |
|---|---|
| Atacar | 5160 `MapPhysicAttackMsg{mapId,posX,posY}` |
| Mover castelo | 5176 |
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
  - 8740: ausente.
  - 8741: sair.
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
- A posição não é gravada: todo login começa em (72,74).
- O `RoomPlayerMsg` leva arma e armadura equipadas (`arm`/`cloth`). Montaria, pet, moda e guilda vão
  vazios até existirem.

**Fica para depois**
- ponytail: broadcast para o space inteiro, sem área de interesse nem tick de 500 ms. Fazer quando
  houver jogadores suficientes para pesar.
