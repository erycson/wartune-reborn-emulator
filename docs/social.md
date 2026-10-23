# Social: amigos, correio, nome e casamento

Legenda *(visto)* / *(cliente)* / *(dedução)* em [multiplayer.md](multiplayer.md). Chat e cornetas em
[chat.md](chat.md). Cliente: `yishi/manager/FriendManager.as`, `managers/FriendSocketOutManager.as`,
`email/` (`EmailManager`, `EmailControler`, `EmailHelp`), `marriage/` (`MarrySender`, `MarryManager`).

Código: `game/social.py` (lista, 160/161, lista negra, buscas), `game/handlers/friends.py`,
`game/mail.py` + `game/handlers/mail.py` + `maillist` em `http/app.py`, `game/handlers/marriage.py`.
Alvo online vem de `OnlinePlayers` (snapshot); offline, do banco (`characters.by_ids`).

## Tabelas (migração 0003)

| tabela | conteúdo |
|---|---|
| `relations` | `(character_id, other_id)` único, `relation` 1 amigo / 2 lista negra / 3 pendente, `group_id` |
| `friend_groups` | grupos criados (`group_id` >= 4; 1 recentes, 2 amigos, 3 lista negra, -1 estranhos e -2 cônjuge são do cliente, `FridendsListView`; 0042 renumerou os antigos) |
| `sns_profiles` | perfil SNS (assinatura, sexo, aniversário, signo, sangue, cidade...) |
| `mails` / `mail_annexes` | correio e até 5 anexos por template (`taken`) ou por item de verdade (`item_id`, migração 0012); anexos caem com o correio |
| `marriages` | uma linha por pessoa do casal: `mate_id`, `state` 1 noivo / 2 noivado cancelado / 3 casado / 4 divorciado, `spec_id`, `married_at` |
| `characters` | + `refuse_friend`, `bugle_free_used`, `bugle_free_day` |
| `relations` (0037) | + `friend_gp` (amizade; sobe 1 dos dois lados a cada rega de árvore de amigo) e `tree_day` (dia em que `character_id` regou a árvore de `other_id`) |

Amizade: 78/165 levam `relationGp` = `friend_gp` e `relationGrade`; o 4156 leva `friendRp`/`friendGrade`. Grau =
1 + `friend_gp` // `friend_grade_step` (game_settings, 10) só para amigo, 0 nos outros *(dedução: ciftlik #85 (só turco: `ciftlik`) tem
grau 4 com 34; a tabela real precisa de captura)*. Fazenda e árvore de amigo em [castelo.md](castelo.md).

Uma relação é de um lado só: "amigo" = as duas linhas com 1. Quem me pede amizade fica 3 (pendente)
no lado dele até eu mandar 15003 relation 1 de volta. Lista negra (2) filtra mundo/cena/cornetas
(`chat._broadcast`), privado (parece offline: 4236 `result -1`) e pedidos (84).

## Amigos

| C>S | mensagem | S>C | situação |
|---|---|---|---|
| 15003 | FriendRelationMsg `{nickName, relation}` | 78 FriendInfoMsg (relation 3 pendente, com `consortiaId`/`consortiaName` do alvo) + 111 **canal 111** "Added successfully, awaiting the other player's response." + 83 canal 3 "You added a new friend: {link}."; 84 para o alvo; quando vira amizade, o outro lado recebe 165 e 83 "{link} has added you to his/her friends list." | pronto *(visto)* oficial_encantar #1776-#1779 e #1792-#1793 (o link leva o `consortiaId` da guilda) |
| 15012 | FriendRelationMsg | como 15003 relation 1 | pronto; sem chamador no cliente *(dedução)* |
| 15004 | `{otherId}` | 79 `{otherId, result}`; o outro lado volta a pendente (165) | pronto *(cliente)* |
| 8285 | vazio | 4193 RefuseFriendRspMsg | pronto: alterna "recusar pedidos" *(cliente)* |
| 8286 | vazio | 4194 RefuseFriendRspMsg | pronto: alterna "recusar convites" *(cliente)* `sendRefuseInvite`; no cliente inglês o `refuseInvite` (SettingFrame, C_ROOM_REFUSE) cobre pesca, estrada e caça-níquel; o bloqueio do convite de guilda (5142) é *(dedução)*, ver [guilda.md](guilda.md) |
| 8746 | vazio | 4635 RefuseFriendRspMsg | pronto: alterna "recusar convites de time"; o 8738 não chega ao alvo que recusa *(cliente)* `sendRefuseTeamInvite` |
| 15013 | vazio | 85 RecommendListMsg | pronto: até 10 online fora da lista *(cliente)* |
| 15025 / 15026 / 15027 | FriendGroupMsg | 4227 / 4228 / 4229 | pronto: apagar devolve os amigos ao grupo 2 *(cliente)*; até 3 grupos do jogador (o `groupDic` tem no máximo 4 com o 2: "Max Group number has been reached."), nome até 12 e sem `,` `|` `%` ("Group name contains invalid characters") *(cliente inglês `FridendsListView`)* |
| 15028 | MoveFriendReqMsg | 4230 | pronto *(cliente)* |
| 15029 | ChatStateMsg | 4232 para mim e para quem me tem na lista | pronto *(visto)* inglesa #75 |
| 15043 | RecentContractsStateReqMsg | 4272 estados | pronto *(cliente)* |
| 15033 / 15036 | SNSInfoMsg / vazio | 4239 SNSUpdatedMsg | pronto: só campos presentes (`HasField`) / reset *(cliente)* |
| 15042 | FriendSearchConditionReqMsg | 4273 | pronto: 10 por página, `pageIndex` a partir de 1 *(cliente)* |
| 8200 | InfoReqMsg | 4128 | pronto *(cliente)* |
| 8257 | SimplePlayerSearchReqMsg | 4170 (sem `info` = não existe) | pronto *(cliente)* |
| — (login) | | 4156 FriendRelationList | pronto: uma página (`maxPage=1`, 0 sem relações nem grupos) com grupos; a lista negra vai com `groupId` 3 (com -1 o cliente a mostraria também entre os estranhos) *(visto em 2 páginas, só turco: `login`; dedução: uma basta)*; lista vazia: inglesa #61 `{maxPage: 0, curPage: 0}` |
| — | | 160 / 161 | pronto: no login e no `on_disconnect` (sem nova sessão), para quem tem linha apontando para mim |

Limites: 200 amigos (pendentes contam) + 50 com VIP, 50 na lista negra, nível 6 para pedir *(cliente)*. O +50 é o
do cliente (`VIPModel.vipFriendPrivilege`): procura `VipPrerogativeTempInfos` com `para2` 6 (não `type`) no nível VIP
e dá 50 fixos se `para1` != 0; com os templates de hoje isso vale para todo VIP, embora o `type` 4 ("Increased Friend
Limit") diga +0 no VIP 1-2. O servidor segue o cliente (`vip.friend_bonus`).

## Correio

A lista é HTTP: `POST maillist {userId, key, mailId, reqType}` responde XML em zlib
`<Result value="true"><Info Id=".." Title=".." ReadDate=".." Annex1=".." .../></Result>`; cada
atributo vira o campo de mesmo nome de `EmailInfo` (`XmlCoder.decode`) *(cliente)*. `ReadDate` ano
2999 = não lido; `reqType=1` marca como lido. `AnnexN` vai **negativo** porque o cliente só pede
`itemlist` para `AnnexN > 0`; `AnnexNName` = TemplateId e `AnnexNCount` = quantidade *(dedução)*.
A `key` precisa ser a da sessão HTTP do próprio `userId`.

| C>S | mensagem | S>C | situação |
|---|---|---|---|
| 8205 | MailSendReqMsg `{sendType, receiverUserId[], title, contents}` | 148 MailMsg para o destinatário | pronto: jogador→jogador, 1 destinatário, assunto ≤ 15, texto ≤ 300, 100 de ouro, nível 6. Correio de guilda (sendType 2) recusado *(cliente)* |
| 8206 | MailDelReqMsg `{delList}` | 4132 com os ids apagados | pronto; não apaga correio com item de verdade ainda não retirado (ele fica até o 5022) |
| 5022 | MailMsg `{mailsIdArray, position}` (0 = todos) | 114 MailPickupRspMsg, 4131 ReceiveMailMsg, 115, 109/3 | pronto: atômico por correio; sem espaço = `result false`. Item de verdade (leilão, lance devolvido) vai para a mochila; diamante do anexo entra no `cash_ledger` (`reason` `mail`) |
| 9591 | MailCheckMsg | 337 `state 0` | parcial: verificação de e-mail precisa de SMTP; nunca dá `mail_rewards` |
| — | | 148 | correio novo (online) |

`game.mail.send_system_mail(ctx, receiver_id, título, texto, [(templateId, n), ...])` é o correio
do servidor (SendType 2, ícone de GM): recompensas que não cabem na mochila, presentes do casamento.
Moedas como anexo usam os templates negativos de `CURRENCIES` (ex.: -100 ouro).

## Nome

| C>S | mensagem | S>C | situação |
|---|---|---|---|
| (HTTP) `nicknamecheck` | `{nickname}` | `xml_result` true = livre | pronto (RenameView chama antes do 8345) |
| 8345 | PlayerRenameReqMsg `{type, pos, nickName}` | 4271, 3, 150, 115 | pronto: type 1 gasta a carta SonType 289 (208018) em `pos`; type 2 grátis só se o nome tem "!" (fusão de servidores). Troca personagem, herói líder e castelo; corrida pelo nome = desfaz |
| 8223 | CheckNickMsg `{nickName}` | 4148 `playerId` (-1 = não existe) | pronto: presente da loja *(cliente)* |
| 25097 | DetailReqMsg `{otherId}` | 4464 HeroInfo | pronto: sem entre-servidores = este servidor |

## Casamento

`MarrySender` e `MarryManager` *(cliente)* dão os `opType` e as respostas; as telas estão no cliente inglês
(`m9/scripts/marry/{propose,quality,room,income}`, `2/scripts/marry/view`, `m3/.../MarryUIMediator.as`,
`m7/scripts/farm/marrytree`). Pedidos, ofertas e pedidos de divórcio ficam em memória (ponytail: somem no restart).
Preços dos ConfigInfos: `divorce_need` 3999, `cancel_engage_need` 500, `marriage_deal_divorce_point` 1799. Toda
cobrança passa pelo ledger; `payType` 1 = só Balens, 0 = vinculados primeiro.

**Fluxo do cliente inglês** (`MarryRingView`, `helpContent02`, `SpaceDialogFrame`): o líder de um time de 2 pede com o
Engagement Ring 208033; o alvo aceita e os dois ficam noivos (state 1) por até 20 dias; o líder reserva a cerimônia na
NPC Andrew (15049 → 4658 → op 5); a sala abre e a troca de alianças casa o casal (state 3, `marTime`). Nas 72 h depois do
casamento o botão "Wedding Ceremony" da TopToolsBar reserva outra cerimônia com desconto. O servidor pula a sala: o op 5
já casa.

| C>S | op | S>C | situação |
|---|---|---|---|
| 8759 | 1 pedir (`property1` alvo, `property3` texto até 100) | 4656 para o alvo: `property1` true (pedido novo), `property3` nível, `property4` guilda, `property5` texto, `property6` cabeça (`pics`) | pronto: sexos diferentes, nível 36 (`MarryQuestFrame`), os dois solteiros e online, anel 208033 na mochila. Alvo não solteiro: 111 "Cannot propose because your teammate is married"; sem anel: 111 "You don't have an Engagement Ring." |
| 8759 | 3 responder (`property1`, `property5`) | 4656 `property1` falso ao alvo (sai da lista); aceito: 4657 aos dois e 4656 `property7` 1 a quem pediu (abre o QUALITY_SELECT) | pronto: noivos; o anel sai de quem pediu *(dedução: quando ele é gasto)*; os outros pedidos ao noivo caem |
| 15049 | 4 escolher casamento (`property1` MarrySpecTempInfo, `payType`) | 4658 MarriageProMsg para o cônjuge | pronto, noivo ou casado. Preço de `MarryModel.getMarryQualityCosts`: `Points` cheio; `ceil(Points × Discount / 100)` nas 72 h depois de `marTime` (noivo não tem data, paga cheio) |
| 8759 | 5 aceitar a escolha | 4657 para os dois + correio com `Rewards` | parcial: cobra e já casa; sem a sala. O `MarryConfirmFrame` manda true e, ao fechar, false: vale o primeiro |
| 8759 | 8 divórcio pago / 15 divórcio grátis (cônjuge offline ≥ 5 dias, desde a saída gravada) | 4657 | pronto |
| 8759 | 14 cancelar noivado | 4657 | pronto, mas sem chamador na interface inglesa (`MarryManager.checkTime` não é chamado). O prazo de 20 dias é do servidor: qualquer pedido de casamento e o login cancelam o noivado vencido, sem custo |
| 8759 | 16 pedir divórcio consensual / 17 aceitar | 358 para o cônjuge / 4657 | pronto (17 custa 1799 a quem aceita). Cônjuge offline no 16 ou recusa no 17: 111 a quem pediu (texto nosso, o language_en não tem) |
| 8759 | 9 dados do pretendente | 4659: `property1` solteiro, `property3` nível, `property4` guilda, `property6` cabeça | pronto (`MarryQuestFrame.refreshView`) |
| 8759 | 10 salas / 20 procurar par | 4662 vazio / 359 RecommendListMsg (5 linhas, `attack` = poder) | 10 vazio; 20 pronto, sem chamador no inglês |
| 8759 | 6, 7, 13 (sala, carro, entrar), 12 (aliança), 18 (`helpMateTrain`, ajuda de satisfação, sem chamador) | — | só log |
| 8760 | sala: 101 alianças, 102-109 bolo/champanhe/doces/buquê/fogos, 104/112 presentes, 105 senha, 106 expulsar, 110/111 convidar | — | só log: a sala não existe |
| 8773 | árvore do casal (1001-1005), resposta 4678 e `FarmInfoRspMsg.marriageTree` | — | só log |
| 8774 | missões do casal (2001 pegar, 2004 usar o mapa, 2005 falar) | 4675 vazio para casado | parcial |
| 8802 | jogo do coração (3001-3005, perguntas em `HeartTempInfos`), respostas 4690/4691 | — | só log |
| 9611 | loja do altar (Guerra de Vênus) | 365 AltarShopListMsg do ConfigInfo `Mate_Shop`, `altarScore` 0 | parcial: compra recusada (sem pontos de altar) |

**4657** (`MarryManager.__marryInfoHandler`): cônjuge, `state`, `templateId` (cerimônia), `speTemplateId` 0 (≠ 0 é
"reservada e alianças por trocar"; aqui casar já troca), `marTime` em `YYYY-MM-DD hh:mm:ss` (`MarryInfo.marriageTime`,
vazio para noivo) e `logoutDays` pela saída gravada. Faltam `happy`, `ringGrade`/`ringGp`, `questCount`, `answerNum` e o 357
`MarriageDataMsg` (satisfação, aliança, árvore).

No login vai 4662 vazio antes do 4686, como o oficial (tutorial_en #43), e 4657 depois do LoginState 6 para quem tem linha
em `marriages`.

## Depende de outros sistemas

- Guilda: correio de guilda (8205 sendType 2), canal 5.
- Time/sala: canal 6, convite de amigo para time.
- Sala de casamento: cerimônia (8760, op 6/7/13, 4662/4673/4674/4672).
- SMTP: 9591.
- Entre-servidores: 8623, 25024, 25096, 25097 tratados como este servidor.
