# Chat e social

Visão geral e legenda *(visto)* / *(cliente)* / *(dedução)* em [multiplayer.md](multiplayer.md).
Cliente: `D:/wartune/decompiled/m2/scripts/chat/`, `managers/IMManager.as`,
`managers/FriendSocketOutManager.as`, `yishi/manager/FriendManager.as`.

## Canais

`chat/datas/ChatChannel.as` *(cliente)*:

| canal | uso |
|---|---|
| 0 | aba "tudo" (só cliente) |
| 1 | corneta grande (item 208002) |
| 2 | anúncio global de sistema, sem remetente |
| 3 | mensagem de sistema para o jogador (já usamos: EXP, "Kazanılan:…") |
| 5 | guilda (exige `consortiaID != 0`) |
| 6 | time / sala / campanha em grupo |
| 7 | alerta (vai no 111, popup) |
| 8 | cena atual ("local") |
| 10 | mundo = corneta pequena (item 208003 ou cota grátis) |
| 11 | alerta de sistema |
| 12 | aviso (aceita URL `http://` no fim) |
| 13 | corneta entre servidores (item 208025) |
| 15 | corneta dourada |
| 20 | privado (só exibição; o envio é pelo IM) |

O jogador escolhe entre 1, 10, 6, 5 e 8 (`chat/view/InputChannelList.as`).

## Envio

| C>S | mensagem | quando |
|---|---|---|
| 15005 | ChatChannelMsg `{channel, encodeMsg, items, stars, powcards, team[]}` | canais 5, 6, 8 |
| 8198 | ChatChannelMsg (`extend2` = id do protocolo) | canal 10 (mundo) |
| 5011 | ChatChannelMsg sem `channel` | canal 1 (corneta grande) |
| 8623 | CrossBigBugleMsg `{content}` | canal 13 |
| 8705 | vazio; resposta 4500 `paraInt1` = cornetas pequenas grátis | ao abrir o chat |
| 15023 | ChatFriendMsg `{fromId, fromNick, toId, encodeMsg}` | privado |
| 15038 | InfoReqMsg `{otherId, from}`; resposta 4256 RelationPlayerMsg (mesmo `from`) | dados de alguém que mandou privado e não é amigo |
| 25024 / 25096 | ChatChannelMsg | batalha/campanha entre servidores; aqui = 15005 local |

`team[]` é a lista de destinatários que o cliente sugere em sala/campanha: o servidor recalcula.

O cliente **não mostra a própria mensagem** ao enviar (`ChatManager.chatNormal` só guarda no
histórico do ↑). Quem envia também recebe o 83. No privado o eco é o 4236.

## Recebimento

- **83** ChatChannelMsg: todos os canais. Para aparecer `[Nick]:` o servidor preenche `otherId`
  (4), `name` (5), `vipGrade` (14) se > 0, `vipType` (26), `consortiaId` (7) e `appellid` (23).
  Canais 2, 3, 11 e 12 não mostram remetente. `job != 0` filtra por classe. `userType` 2 = GM.
- **111**: só popup (canal ignorado).
- **4231** ChatFriendMsg `{fromId, fromNick, encodeMsg, sendDate "YYYY-MM-DD hh:mm:ss"}`: privado
  recebido. Se o remetente não é amigo, o cliente pede 15038 e só mostra depois do 4256.
- **4236** ChatFriendMsg: eco para quem enviou; `result = -1` mostra "o jogador não está online"
  (`friends.im.IMFrame.command02`).
- 4232 ChatStateMsg / 15029: estado do IM (o cliente manda `chatState=7` logo depois do login;
  *(visto)* `login.json #87` 4232 `{userId, chatState:7, result:1}`).

Marcação dentro do `encodeMsg`: `<a t="1" id=".." name=".." …/>` link de jogador, `<a t="2" …
tempid=..>` link de item, `#00`–`#39` emoticons.

## Regras (o servidor revalida)

De `chat/utils/ChatHelper.as` e `chat/view/ChatInputViewII.as` *(cliente)*:

- nível mínimo **6**;
- no máximo **76** caracteres;
- intervalo: canal 8 = 10 s (2 s em sala/batalha), canal 10 = 2 s. O cliente só aplica de verdade
  para GM, então quem garante é o servidor;
- jogador comum tem o HTML escapado; o servidor tira `<…>` do texto para ninguém forjar link de
  jogador/item;
- remetente, VIP, guilda e `userType` vêm sempre do servidor, nunca do cliente.

## Amigos, correio e guilda

Amigos, lista negra, correio, nome e casamento: [social.md](social.md). Guilda: 5130 criar, 5142
convidar, 5143/5134 convites e candidaturas, 5132 expulsar, 8207 membros, 8212 info; respostas
4138/164 info, 4133 membros, 162/163 entrou/saiu (o canal 5 depende dela).

## No servidor

`game/handlers/chat.py`:

- 8198: mundo, para todos online. Gasta primeiro a cota grátis do dia (ConfigInfo
  `SMALL_BUGLE_FREE_COUNT` = 10, zera na virada do dia) e depois uma corneta 208003 (115 e 4500).
- 8705: 4500 `paraInt1` = cornetas grátis restantes.
- 5011: corneta grande (canal 1), gasta o item 208002.
- 8623: corneta entre servidores, gasta 208025 e manda 4541 CrossBigBugleMsg para este servidor
  (sem entre-servidores).
- 25024 / 25096: tratados como o 15005 deste servidor.
- Lista negra: quem me bloqueou não recebe meus 83/4541; no privado eu vejo `result -1`.
- 15005: canal 8 para todos online fora de batalha. Os canais 5 e 6 são recusados até existirem
  guilda e time.
- 15023: privado, com 4231 para o alvo e 4236 para quem enviou (`result -1` se offline).
- 15038: 4256 com nome, nível e classe do jogador pedido.
