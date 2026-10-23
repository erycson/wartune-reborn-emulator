# Sequência de login (marco 1)

O caminho vai do portal até a cena do castelo, com o tutorial pulado (`noviceProcess = 19000`).
Fontes: `Loading.as`, `LoginQueue.as`, `MainFigureView.as` e `NewbieSPHelper.as` (módulo Loading),
mais `LoginInitDataAccept` e `BaseManager` (m2). O teste `tests/test_end_to_end.py` percorre esse
caminho inteiro.

## 1. Portal (PHP)

O jogador entra no portal e escolhe o servidor. O `play.php` grava um **ticket** em `play_tickets`,
válido por 5 minutos e só para aquele servidor, e monta as flashvars do `Loading.swf`:

| flashvar | valor |
|---|---|
| `user` | nome da conta |
| `key` | o ticket (a "senha" que o Loading manda no login) |
| `site` | `game_servers.site`; escolhe o `<NODE site=…>` do config.xml |
| `config` | `portal/client-config.php?server=N` |
| `playfb` | `0` |

O relay antigo usava `username`, mas o nome correto é `user`.

## 2. HTTP do Loading.swf

1. `GET config` (portal): o Loading lê `REQUEST_PATH`, `ResourcePath`, `SocktPath` e o `RSAKey` do site.
2. `GET loginselectlist?username=&site=`: retorna `<Item ID Active>` do personagem neste servidor. Na primeira vez não há item.
3. `POST login` com `p = RSA(urlescape(user) | ticket | tempPassword | userId)`:
   * o servidor valida o ticket, cria o personagem **inativo** se ainda não existir e responde `userId`, `Address` e `Port`;
   * guarda uma sessão pendente em memória com `key = md5(tempPassword)`, a mesma chave que o cliente usa daqui em diante.
4. Personagem novo: a tela de criação faz `visualizeregister` com nickname, sex, icon e key.
   O servidor ativa o personagem e cria o herói líder (pelo template) e o castelo.
5. `POST updateplayernovice op=1 noviceprocess=0`: com `skip_tutorial`, o valor salvo nunca fica abaixo de 19000.

## 3. Socket

| # | Cliente → | ← Servidor |
|---|---|---|
| 1 | **20001** `LoginReqMsg{key, ekeys}` | (troca de chave) **3841** vazio, **3** `PlayerMsg`, **150** `ArmyArmyMsg` |
| 2 | — | o primeiro `PlayerMsg` dispara `LOGIN_SUCCESS`; o cliente carrega `StartupResourcesLoader` |
| 3 | **8224** `PlayerDataMsg{castle, army, build, tree, aas, friend, sys, snsReq, …}` | 4233, 4160, 4176, 4154, 4155, 4153, 4452, 4157, 4156, 4245, 4173, 150 |
| 4 | — | `LoginInitDataAccept` conta os 10 pacotes obrigatórios (abaixo) |
| 5 | **8224** `{quest, shop, active, …}` (loginOver) | (ainda sem resposta) |
| 6 | **8224** `{user: true}` | **4598** `SimplePropertyMsg{param1:10000}`, **150**, **6** `LoginStateMsg{playerId, state:0}` |
| 7 | — | `BaseManager.__loginStateHandler` escolhe a cena pelo `noviceProcess` |

Pacotes que o `LoginInitDataAccept` espera:
4153 `BaseCastleMsg`, 4154 `BuildingInfoListMsg`, 4155 `BuildOrderList`, 4156 `FriendRelationList`,
4157 `LoadFarmRsp`, 4160 `SystemPropertyMsg`, 4173 `PlayerAASRefreshMsg`, 4176 `ChallengeCoolTimeMsg`
(o `type 1` não conta), 4233 `VersionMsg` e 4245 `SNSInfoMsg`.

Escolha da cena:

| noviceProcess | Cena |
|---|---|
| ≤ 18500 | o cliente manda 5127 e vai para o tutorial (campanha) |
| < 19000 | OUTER_CITY_SCENE |
| ≤ 35200 (e acima) | CASTLE_SCENE |

## Valores padrão de um personagem novo

Os valores vêm da captura oficial de uma maga de nível 1 e estão em `game/builders/login.py`:
`state 7`, `questSiteLen 200`, `weary 200`, `attackLeftCount 5`, `right 1`, `startFree 1`,
`campaignCount 1`, `reloginCount 1`, `matchRoomCount 15`, `warFieldCount 2`, `trialMaxCount 1`,
`campaignMaxcount 1` e `status -1`. As datas "nunca" são `2000-01-01 00:00:00`.

O 4154 leva os prédios do banco (veja [banco-de-dados.md](banco-de-dados.md#buildings)). Uma lista
vazia não trava a cena, mas a HUD e o tutorial quebram logo depois. Todo `templateId` enviado
precisa existir no `tempinfos.xml`, senão a cena falha com #1009 (`CastleWalkLayer`).

Atributos derivados do herói (ataque, defesa, vida e poder de luta) são calculados pelo servidor.
As fórmulas atuais foram calibradas com essa única amostra (dá 199 de poder de luta na maga nível 1),
por isso estão marcadas com `ponytail:` para serem revistas quando houver mais capturas.

Pacotes extras do login, conferidos com `captures/tutorial_en.json` (conta nova):
- Mandados: 4434 (vazio sem contrato comprado, como o oficial), 83 (devoção, #16), 100 (tropas do castelo, logo
  depois do 150, mesmo vazio: #37-#39), 4544 (destino, vazio no nível 1: #42), 4590 e 514 (super assinatura, `param1`
  2059, com as datas da edição do `game_settings.super_signin`: tutorial_en #110-#111, oficial_encantar #118-#119), 4922 (só com tabuleiro gravado) e as respostas a 8530, 8218, 8209, 8625 e 8322.
- Não mandados, como o oficial: 4224/4372 (alquimia e alma: o 8320/8466 do nível 1 fica sem resposta, #17-#18; o
  cliente pede de novo no nível 14 e no 24), 4905 (cartas, só com carta), 4535 (Senhores, #104-#106) e 4900
  `KingTowerInfoMsg {0, 0}` (#100), que só leva o padrão do protobuf (a torre do rei não existe aqui).
