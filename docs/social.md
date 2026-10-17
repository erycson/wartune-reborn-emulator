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
| `friend_groups` | grupos criados (`group_id` >= 3; 1 recentes e 2 amigos são fixos do cliente) |
| `sns_profiles` | perfil SNS (assinatura, sexo, aniversário, signo, sangue, cidade...) |
| `mails` / `mail_annexes` | correio e até 5 anexos por template (`taken`) ou por item de verdade (`item_id`, migração 0012); anexos caem com o correio |
| `marriages` | uma linha por pessoa do casal: `mate_id`, `state` 1 noivo / 2 noivado cancelado / 3 casado / 4 divorciado, `spec_id`, `married_at` |
| `characters` | + `refuse_friend`, `bugle_free_used`, `bugle_free_day` |

Uma relação é de um lado só: "amigo" = as duas linhas com 1. Quem me pede amizade fica 3 (pendente)
no lado dele até eu mandar 15003 relation 1 de volta. Lista negra (2) filtra mundo/cena/cornetas
(`chat._broadcast`), privado (parece offline: 4236 `result -1`) e pedidos (84).

## Amigos

| C>S | mensagem | S>C | situação |
|---|---|---|---|
| 15003 | FriendRelationMsg `{nickName, relation}` | 78 FriendInfoMsg (relation 3 pendente) + 111 "Eklendi,yanıtını bekleyin." + 83 canal 3 "Yeni arkadaşı eklediniz" + link; 84 para o alvo; 165 para o outro lado quando vira amizade | pronto *(visto)* `arkadas_istegi_gonderme.json` |
| 15012 | FriendRelationMsg | como 15003 relation 1 | pronto; sem chamador no cliente *(dedução)* |
| 15004 | `{otherId}` | 79 `{otherId, result}`; o outro lado volta a pendente (165) | pronto *(cliente)* |
| 8285 | vazio | 4193 RefuseFriendRspMsg | pronto: alterna "recusar pedidos" *(cliente)* |
| 8286 | vazio | 4194 RefuseFriendRspMsg | pronto: alterna "recusar convites" *(cliente)* `sendRefuseInvite`; o bloqueio do convite de guilda (5142) é *(dedução)*, ver [guilda.md](guilda.md) |
| 8746 | vazio | 4635 RefuseFriendRspMsg | pronto: alterna "recusar convites de time"; o 8738 não chega ao alvo que recusa *(cliente)* `sendRefuseTeamInvite` |
| 15013 | vazio | 85 RecommendListMsg | pronto: até 10 online fora da lista *(cliente)* |
| 15025 / 15026 / 15027 | FriendGroupMsg | 4227 / 4228 / 4229 | pronto: apagar devolve os amigos ao grupo 2 *(cliente)*; até 10 grupos, nome até 12 *(dedução)* |
| 15028 | MoveFriendReqMsg | 4230 | pronto *(cliente)* |
| 15029 | ChatStateMsg | 4232 para mim e para quem me tem na lista | pronto *(visto)* `login.json #87` |
| 15043 | RecentContractsStateReqMsg | 4272 estados | pronto *(cliente)* |
| 15033 / 15036 | SNSInfoMsg / vazio | 4239 SNSUpdatedMsg | pronto: só campos presentes (`HasField`) / reset *(cliente)* |
| 15042 | FriendSearchConditionReqMsg | 4273 | pronto: 10 por página, `pageIndex` a partir de 1 *(cliente)* |
| 8200 | InfoReqMsg | 4128 | pronto *(cliente)* |
| 8257 | SimplePlayerSearchReqMsg | 4170 (sem `info` = não existe) | pronto *(cliente)* |
| — (login) | | 4156 FriendRelationList | pronto: uma página (`maxPage=1`) com grupos *(visto em 2 páginas; dedução: uma basta)* |
| — | | 160 / 161 | pronto: no login e no `on_disconnect` (sem nova sessão), para quem tem linha apontando para mim |

Limites: 200 amigos (pendentes contam), 50 na lista negra, nível 6 para pedir *(cliente)*.

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

`MarrySender` *(cliente)* dá os `opType`; a UI do casamento não está decompilada, então o fluxo é
*(dedução)*. Pedidos, ofertas e pedidos de divórcio ficam em memória (ponytail: somem no restart).
Preços dos ConfigInfos: `divorce_need` 3999, `cancel_engage_need` 500,
`marriage_deal_divorce_point` 1799. `payType` 1 = diamante (`point`), outro = `gift_token`.

| C>S | op | S>C | situação |
|---|---|---|---|
| 8759 | 1 pedir (`property1` alvo, `property3` texto) | 4656 EngageMsg para o alvo | pronto: sexos diferentes, nível 36, os dois solteiros e online |
| 8759 | 3 responder (`property1`, `property5`) | 4657 MarriageMsg para os dois | pronto: noivos |
| 15049 | 4 escolher casamento (`property1` MarrySpecTempInfo, `payType`) | 4658 MarriageProMsg para o cônjuge | pronto: `Points` com `Discount`% nas primeiras `DiscountTime` h |
| 8759 | 5 aceitar a escolha | 4657 para os dois + correio com `Rewards` | parcial: cobra e já casa; sem cerimônia (sala/carro dependem da cena de campanha) |
| 8759 | 8 divórcio pago / 14 cancelar noivado / 15 divórcio grátis (cônjuge offline ≥ 5 dias) | 4657 | pronto |
| 8759 | 16 pedir divórcio consensual / 17 aceitar | 358 para o cônjuge / 4657 | pronto (17 custa 1799) |
| 8759 | 9 dados do pretendente | 4659 | pronto |
| 8759 | 10 salas / 20 procurar par | 4662 vazio / 359 RecommendListMsg | 10 vazio; 20 pronto |
| 8759 | 6, 7, 12, 13, 18 (sala, carro, anel, entrar, ajudar árvore) | — | só log: dependem de cena/árvore/anel |
| 8760 | cerimônia (presentes, senha, convidados) | — | só log: cena de campanha |
| 8773 | árvore do casal | — | só log: sistema de árvore/fazenda |
| 8774 | missões do casal (2001 pegar) | 4675 vazio | parcial |
| 8802 | jogo do coração | — | só log: perguntas fora dos templates |
| 9611 | loja do altar (Guerra de Vênus) | 365 AltarShopListMsg do ConfigInfo `Mate_Shop`, `altarScore` 0 | parcial: compra recusada (sem pontos de altar) |

No login vai 4657 depois do LoginState 6 para quem tem linha em `marriages`.

## Depende de outros sistemas

- Guilda: correio de guilda (8205 sendType 2), canal 5.
- Time/sala: canal 6, convite de amigo para time.
- Cena de campanha: cerimônia do casamento (8760, op 6/7/13), sala de casamento.
- SMTP: 9591.
- VIP: cota maior de cornetas grátis.
- Entre-servidores: 8623, 25024, 25096, 25097 tratados como este servidor.
