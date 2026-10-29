# Mercado entre jogadores: anunciar, lances, preço fixo e busca

Handlers em `game/handlers/mall.py`; encerramento dos anúncios vencidos (na hora do pedido e agendado) e cartas
do sistema em `game/mall.py`; correio com item em `game/mail.py` e `game/handlers/mail.py` (5022, 8206).
Legenda: *(cliente)* = constante, campo ou texto do cliente inglês; *(dedução)* = coerente com o resto, sem prova direta.

**Fontes.** Nenhuma captura (inglesa ou turca) tem pacote do mercado (8448–8457 ou 4352–4359). As regras vêm do
cliente inglês decompilado: telas em `D:\xampp\htdocs\wartune\decomp\m7\scripts\auction` (`AuctionFrame`,
`buy/AuctionSearchControl`, `buy/AuctionBuyResultPane`, `sell/AuctionSellSubmitPane`, `sell/AuctionSellResultPane`,
`record/AuctionRecordResultPane`, `common/AuctionChecker`), envio em `2/scripts/mediator/AuctionMessageSender.as`.
Os textos entre aspas são do `language.txt` inglês (`Auction.*`, `auction.view.AuctionHelp.helpContent`, 8 itens,
citada como *(ajuda item N)*).

## Telas do cliente inglês

| aba | pedido | o que a tela faz |
|---|---|---|
| Buy | 8457 (`AuctionSearchControl`) | busca com nome, nível, qualidade, classe, tipo, `usable`, página, `orderBy`/`orderType`; 7 linhas (`AuctionBuyResultPane`). Lance pelo `AuctionInputFrame`: valor igual ao atual só sai se ainda não há lance; ≥ fixo vira compra (8453) depois de confirmar; o próprio anúncio é barrado (`AuctionChecker`, "You cannot bid in your own auction!") |
| Sell Items | 8449 (1, 9, 1) e 8448 | meus anúncios (9 por página, ordenados na própria tela) e o painel de venda (`AuctionSellSubmitPane`) |
| Sell Sylphs | 8449 e 8448 com `sellType` 2 | abre no nível 50 ("Unlocks at Lvl. 50"); ajuda `AuctionFrame.helpPet`: só mascote não vinculado, entregue pelo correio, recusado com o plantel cheio (ver [Sylph no leilão](#sylph-no-leilão)) |
| Record | 8452 (página, 9, 1, `orderBy`, `orderType`) | meus lances, ordenáveis pelos títulos |

O 8450 (`sendPlayerAuctionListReq`) não tem chamador no cliente inglês; o servidor responde para quem mandar.

## Opcodes

| C>S | o que faz | S>C |
|---|---|---|
| 8448 SellItemReqMsg | anuncia uma pilha da mochila (`itemId`, `itemPos`, `count`, `point`, `fixPoint`, `hour`, `sellType`) e cobra a taxa em ouro | 115 (a mochila muda), 4352 SellItemRspMsg `{result, item}`, 109 (ouro) |
| 8449 MallItemViewReqMsg | meus anúncios abertos, do mais novo para o mais antigo (`page`, `count`) | 4353 AuctionItemsMsg `{pageIdx, pageCount, sellItem[]}` |
| 8450 MallItemViewReqMsg | anúncios abertos do servidor, na aba `from` (1 só itens, 2 só Sylphs, outro os dois; *dedução*) | 4354 AuctionItemsMsg |
| 8451 AuctionItemReqMsg | lance em `id` por `point` | 4355 AuctionItemRspMsg `{result, itemBuy}` |
| 8452 MallItemViewReqMsg | meus lances em anúncios abertos (`itemBuy` com o meu `bidupPoint`), na ordem pedida | 4356 AuctionItemsMsg `{pageIdx, pageCount, itemBuy[]}` |
| 8453 AuctionItemReqMsg | compra pelo preço fixo: `point` tem que ser o `fixPoint` | 4357 FixAuctionItemRspMsg `{result, mallItemId}`; o item vai pelo correio (148), sem 115 |
| 8454 AuctionItemReqMsg | cancela o meu anúncio (`id`) sem lance | 115 (o item volta à mochila) e 4358 CanceltemRspMsg `{result, id}` |
| 8457 SearchItemReqMsg | busca nos anúncios abertos, na ordem pedida | 4359 AuctionItemsMsg (7 por página) |

**Ordem** (8452 e 8457): `orderBy` 1 nível (`NeedGrades`), 2 tempo restante (`ends_at`), 3 preço atual, 4 preço fixo;
`orderType` 2 decrescente, 1 crescente (`AuctionSearchControl`/`AuctionRecordResultPane.__onTitleClick`: o primeiro
clique pede 2). Sem `orderBy`, o mais novo primeiro.

Todo handler responde mesmo com corpo vazio ou mínimo (`tests/game/test_mall.py`). Pedido vazio cai na
recusa do próprio handler: 8448 com `sellType` 0 dá `NOT_AUCTION`; 8451, 8453 e 8454 com `id` 0 dão `GONE`.

### Códigos de resultado

`SellResultType` (`yishi/datas/consant/SellResultType.as`) dá o código; o texto é `Auction.ResultAlert<valor absoluto>`.

| código | nome no servidor | quando | texto do cliente |
|---|---|---|---|
| 0 | `OK` | deu certo | "Success!" |
| −2 | `GONE` | anúncio inexistente, ou cancelar de quem não é o dono | "Item does not exist!" |
| −3 | `COUNT` | quantidade fora de 1..`count` da pilha | "Invalid quantity!" |
| −4 | `PRICE` | lance abaixo do mínimo, lance ≥ preço fixo, ou compra com `point` diferente do `fixPoint` | "Bid must be higher than the current price, please re-enter!" |
| −5 | `FIX_PRICE` | `fixPoint` 0 ou não maior que o inicial (`SubmitAlert3`/`SubmitAlert4`) | "Invalid Buy-It-Now Price" |
| −6 | `HOUR` | `hour` fora de 8, 24, 48 | "Invalid Time" |
| −7 | `BLOCKED` | item vinculado, ou travado (8809) | "Item is bound!" |
| −8 | `NO_ITEM` | a posição não tem o item de `itemId` | "Item does not exist!" |
| −10 | `NO_GOLD` | ouro menor que a taxa | "Inadequate gold reserves." |
| −11 | `NO_POINT` | Balens insuficientes | "You don't have enough Balens!" |
| −12 | `NOT_AUCTION` | `sellType` diferente de 1 e 2, template com `StartingPrice` 0, ou Sylph abaixo do nível 50 | "You cannot auction this item!" |
| −14 | `FIX_FAIL` | anúncio sem preço fixo (anúncio antigo; o 8448 não aceita mais) | "Unable to purchase item!" |
| −15 | `CANCEL_FAIL` | cancelar com lance feito, ou mochila sem espaço para devolver | "Unable to delete item." |
| −16 | `OWN_FIX` | comprar ou dar lance no próprio anúncio (o cliente já barra) | "You can't buy an item from yourself!" |
| −17 | `OWN_BID` | o líder cobrir o próprio lance | "Bid failed:you are already the high bidder." |
| −18 | `SELL_MAX_COUNT` | mais de 9 unidades num anúncio | "Number of items sold cannot exceed 9!" |
| −19 | `START_PRICE` | inicial abaixo de 2 ou de `StartingPrice × count` | "Starting Price cannot be less than the default price." |
| −52 | `DAILY_LIMIT` | lance ou compra que passa do limite diário; só com `game_settings.mall_daily_limit` | sem texto no cliente inglês (alerta genérico) |

Não usados: −1 (falha genérica), −9 ("Item is being sold!"), −13 ("Item Auction Failed!").

## Anunciar (8448)

Regras do `AuctionSellSubmitPane` *(cliente)*, conferidas também no servidor:

- Item da mochila (bolsa 1) com `sellType` 1 e template com `StartingPrice` > 0 em `ItemTempInfos`; ou Sylph com
  `sellType` 2 (ver abaixo).
- Inicial: no mínimo 2 (`onSellBtnClick`; `SubmitAlert2` "Starting price may not be zero…") e `StartingPrice × count`
  (−19, "…less than the default price"; o produto pela quantidade é *(dedução)*).
- Preço fixo obrigatório e maior que o inicial (`SubmitAlert3` "Did you forget to enter the buy-it-now price?",
  `SubmitAlert4` "Buy-it-now price must be higher than the starting price!").
- Duração 8, 24 ou 48 h (`getSelectTime`, `Auction.SubmitHour1..3`); o 8448 leva as horas. `ends_at = started_at + hour`
  (`AuctionListItemData.timeLeft` = `hour × 3600000 − (agora − startTime)`).
- Taxa de 250 × horas de ouro (`updateCarryingCost`; *ajuda item 4*: "A small auction fee of gold is required and will
  be automatically deducted when selling items"). Sai na transação do anúncio; o 109 atualiza a barra. *ponytail*:
  cancelar não devolve a taxa (o cliente não diz).
- Quantidade: 1 a 9 por anúncio (`Auction.ResultAlert18`).
- Pilha parcial: a quantidade anunciada vira uma linha nova na bolsa 11 (AUCTION, posição 0) e a mochila fica com o
  resto na mesma linha. Não volta a empilhar na pilha original ao cancelar.
- Anúncio inteiro: a linha do item muda para a bolsa 11 e sai da mochila na mesma gravação que cria o
  `mall_listings`. Um item nunca está nos dois lugares.

## Lances, compra e encerramento

- **Lance (8451)**: o primeiro lance é ≥ o inicial (`AuctionBuyResultPane.inputPriceCallback` manda o valor atual
  quando `auctioned` é falso); os seguintes são > o último. Lance ≥ `fixPoint` é recusado: o cliente troca pelo 8453.
  O líder não cobre o próprio lance (−17). Os Balens saem agora (`ledger.pay`, `reason` `mall`, só Balens). O lance
  superado volta pelo correio ("Bid Refund", anexo −400 com o valor). O `mall_bids` guarda um registro por jogador e
  por anúncio.
- **Compra (8453)**: paga `fixPoint` (ou a diferença, se já é o líder). O item vai ao comprador pelo correio
  ("Purchased Item") *(ajuda item 3: "Purchased items will be sent via the in-game mail system")*, então mochila cheia
  não recusa a compra. Os Balens do vendedor vão pelo correio ("Sale Income"); o lance superado volta pelo correio;
  os lances e o anúncio são apagados.
- **Imposto da venda**: o vendedor recebe 80% (`game/mall.py` `income`) *(ajuda item 7: "a procedure fee (20% of the
  closing price) will be charged from the seller")*, na compra pelo fixo e no vencido com lance. *ponytail*:
  arredondado para baixo.
- **Cancelar (8454)**: só o dono e só sem lance *(ajuda item 5: "Auctions for items that have winning bids cannot be
  cancelled")*. O item volta à mochila na primeira posição livre.
- **Limite diário de compra**: a ajuda inglesa não tem; padrão sem limite. `game_settings.mall_daily_limit` (JSON
  `{"bands": [[nível abaixo de, limite], ...], "top": limite}`) liga, ex. o do turco
  `{"bands": [[60, 500], [70, 1000]], "top": 1500}`. Conta os Balens pagos (`characters.mall_spent` / `mall_day`,
  migração `0018`); passou: −52, recusado antes de cobrar; o lance devolvido não volta para a cota.
- **Encerramento**: dois caminhos, na mesma transação e sob `MALL_LOCK`:
  - **agendado**: `game/mall.py` `run`, iniciado em `app.py` (`serve`) e cancelado ao desligar. Roda já na subida e
    depois dorme até o menor `ends_at` (no máximo 60 s, `SWEEP_SECONDS`). Uma rodada que falha é registrada (`log.exception`) e a próxima tenta de
    novo.
  - **no pedido**: antes de cada pedido do mercado, `_transact` roda `settle`, então um pedido nunca vê um anúncio
    vencido aberto.

  `settle` encerra os anúncios com `ends_at <= agora`:
  - com lance: o item vai ao vencedor pelo correio ("Won Item") e os Balens, menos 20%, ao vendedor ("Sale Income");
  - sem lance: o item volta ao vendedor pelo correio ("Returned Item") *(ajuda item 6)*.

  Os lances do anúncio são apagados. Vale também para vendedor fora do jogo: a carta fica no banco até ele entrar e
  pegar no 5022. O 148 sai depois do commit, só para quem está online.

### Como o correio entrega item

- `game/mail.py` `stage(uow, mail, goods, items)` põe a carta e os anexos na transação de quem chama
  (sem commit). Item de verdade vira `MailAnnex` com `item_id`, e a linha do item passa para a bolsa
  10 (MAIL) do destinatário, posição 0, objeto 0. Diamante e ouro continuam como anexo por template.
- `notify` manda o 148 ao destinatário online, depois do commit.
- 5022 pega o item (linha lida do banco por `item_id`, `character_id` já do destinatário) e o põe na
  mochila na primeira posição livre; diamante vai pelo `cash_ledger` com `reason` `mail`.
- 8206 não apaga carta com item de verdade ainda não retirado: ele fica até o 5022.

## Anti-duplicação e concorrência

- O item sai de uma bolsa e entra na outra na mesma gravação que o anúncio, o lance ou a compra.
- Itens das bolsas 10 e 11 não entram no snapshot do login (`services/characters.py`, `snapshot`):
  o que está à venda ou em trânsito não aparece na mochila nem fica em memória.
- Transferência de item é só atualização da linha no banco. Quem não está na sessão do pedido recebe
  pelo correio, e o snapshot dele não é mexido daqui. O agendador também não mexe em snapshot: só banco e correio.
- `MALL_LOCK` (asyncio, em `game/mall.py`) serializa as gravações do mercado, o agendador incluído. Um servidor por
  processo. ponytail: lock global, por anúncio se a fila pesar.
- Único caminho que apaga carta é o 8206, e ele recusa carta com item não retirado. Apagar personagem
  ou conta leva a carta e o item juntos (cascata em `characters`). Nenhum código do servidor nem o portal
  PHP apaga carta por validade. Quem criar essa purga tem que pular as cartas com `item_id` não retirado.

## Tabelas

Migrações `0015_mercado_entre_jogadores_e_itens_no_` e `0018_limite_diario_de_compra_no_mercado` (`persistence/migrations/versions/`):

| tabela | conteúdo |
|---|---|
| `mall_listings` | um anúncio: `server_id`, `seller_id`, `item_id` (único; cascata do item), `seller_nick`, `point` (lance atual ou inicial), `fix_point`, `hour`, `started_at`, `ends_at` (índice), `bidder_id` (0 = sem lance) |
| `mall_bids` | `listing_id`, `bidder_id`, `price`, `bid_at`; único por `(listing_id, bidder_id)`; cascata do anúncio |
| `mail_annexes.item_id` | id do item de verdade no anexo (0 = anexo por template); `server_default` 0 |
| `characters.mall_spent`, `mall_day` | diamante pago no mercado no dia `mall_day` (limite diário, −52); outro dia zera |

Bolsas novas: 10 (MAIL, correio) e 11 (AUCTION, leilão), ambas com posição 0 (ver [itens.md](itens.md)).

## Sylph no leilão

O cliente trata o Sylph como o item −900 (`PetData.convertToGoods`: MasterType 4, SonType 309, `StartingPrice` 10,
quantidade 1) e lê o pet do `itemInfo.property1` (`GoodsInfo.property1` → `PetData.createWidthString`). O servidor
faz igual (migração 0049):

| Passo | Regra | Resposta |
|---|---|---|
| 8448 `sellType` 2 | `itemPos` = id do pet (`AuctionSellSubmitPane`). Nível 50 (`AuctionFrame`), pet livre, fora de batalha, fora da equipe do Sylph Arena e sem equipamento (`PetSellView` só lista esses; recusa −7), quantidade 1, inicial ≥ 10. Cria a linha −900 (bolsa 11, `object_id` = pet, `property1` = o pet como o `createWidthString` lê) e marca `pets.held`: o pet sai da lista do dono, também ao logar de novo | 4540 com `isDel`, 4352, 109 |
| listas e busca | `itemFrom` 2; a busca e a ordem usam nome, nível e cor (`(Quality − 1) / 5 + 1`) do pet (`game/mall.py` `goods_row`); a categoria Sylph é a 4/309 do −900 | 4353, 4354, 4356, 4359 |
| lance, compra, fim | como o item: o −900 vai pelo correio, com o `object_id` | 148 |
| 5022 do −900 | vai para a lista de pets (dono, `held` falso, fim da fila) e o −900 some; lista cheia (6 + vagas compradas) dá `result` false e o anexo fica ("You cannot accept the Sylph if your roster is full") | 114, 4131, 4540 |
| 8454 | o pet volta à lista; lista cheia dá −15 | 4540, 4358 |

O correio mostra o ícone do −900 ("Blank Hero Seal Card"), sem os dados do pet: o cliente só busca o `itemlist` para
`AnnexN > 0` e o servidor manda os anexos negativos (o mesmo limite dos itens do leilão: sem encantamento nem pedras no correio). O texto da carta leva o
nome do pet.

## Dependências

O que falta, com o que o servidor faz hoje:

- **Sylph livre**: todo pet nasce vinculado e batalha, devorar e equipar vinculam (ver
  [heroi-exercito.md](heroi-exercito.md)). Sem um jeito de ganhar pet livre, a venda só serve a pets já livres no banco.
- **Vínculo**: item vinculado (`Item.is_binds`) dá −7 "Item is bound!", e o travado (8809) também. Livre é só o
  comprado em Balens e o que já veio do leilão (ver [itens.md](itens.md#vínculo-itemis_binds-migração-0043)).
- **Preço mínimo pela quantidade**: `StartingPrice × count` *(dedução)*; o `AuctionSellSubmitPane` só confere o 2.
- **Taxa ao cancelar**: não volta *(ponytail: o cliente não diz)*.
- **Nível de abertura do leilão**: o servidor não confere; a aba de itens não tem trava de nível no `AuctionFrame`.
- **Limite de anúncios por jogador**: não há; o cliente não tem código de "muitos anúncios".
- **Cartas do mercado**: títulos e corpo ("Won Item", "Sale Income", "Returned Item", "Bid Refund", "Purchased Item")
  são do servidor; sem captura do oficial. A ajuda (item 8) diz que o anúncio novo aparece "several minutes" depois;
  aqui aparece na hora.
- **Encerramento agendado**: a cada 60 s, sem dormir até o menor `ends_at` (*ponytail*: até 60 s de atraso).
- **`itemId`**: assumido como `Item.id` (a linha do banco).
- **Mochila cheia ao cancelar**: recusa (`CANCEL_FAIL`); a compra não depende da mochila (vai pelo correio).
- **Ordem dos pacotes**: 115 vai antes de 4352/4358, e o 109 depois *(dedução)*.
