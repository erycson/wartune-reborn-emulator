# Mercado entre jogadores: anunciar, lances, preço fixo e busca

Handlers em `game/handlers/mall.py`; encerramento dos anúncios vencidos (na hora do pedido e agendado) e cartas
do sistema em `game/mall.py`; correio com item em `game/mail.py` e `game/handlers/mail.py` (5022, 8206).
Legenda: *(visto)* = captura oficial; *(cliente)* = constante, campo ou texto no cliente decompilado;
*(dedução)* = coerente com o resto, sem prova direta.

**Limite da fonte.** Nenhuma das 32 capturas de `captures/` nem o `server-relay/replay_packets.json` tem pacote do
mercado (8448–8457 ou 4352–4359). `captures/amfi_marketi_alisveris.json` é a loja de NPC (5154), não o leilão. Os
nomes dos opcodes e os campos vêm de `ProtocolType.as`, `AcceptProtocolType.as`, `m2/scripts/mvc/module/auction/` e
do `.proto`. Os textos da tela (`Auction.ResultAlert*`, `Auction.SubmitHour*`, `Auction.LeftTime*`) estão em
`ui/zh_cn/language.txt` do CDN local (zlib, em turco; lido sem alterar nada). A ajuda da tela
(`auction.view.AuctionHelp.helpContent`, 11 itens) dá as regras de imposto, entrega e limite diário: citada abaixo como
*(cliente, ajuda item N)*. O que a ajuda não dá (valor da taxa em ouro, nível de abertura) pede captura: ver
[Dependências](#dependências).

## Opcodes

Estado: 8448, 8451, 8453 e 8454 completos, com as regras que faltam listadas em [Dependências](#dependências).
8449 e 8452 listam as minhas linhas. 8450 e 8457 são **parciais**: `orderBy` e `orderType` são ignorados e o
cliente decompilado não mostra o sentido da ordenação.

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 8448 SellItemReqMsg | anuncia uma pilha da mochila (`itemId`, `itemPos`, `count`, `point`, `fixPoint`, `hour`) | 115 (a mochila muda) e 4352 SellItemRspMsg `{result, item}` | *(cliente)* campos, duração, quantidade e textos; preço mínimo *(dedução)* |
| 8449 MallItemViewReqMsg | meus anúncios abertos, do mais novo para o mais antigo (`page`, `count`) | 4353 AuctionItemsMsg `{pageIdx, pageCount, sellItem[]}` | *(cliente)* nome `C_MALL_LIST_SELL`; página 9 |
| 8450 MallItemViewReqMsg | anúncios abertos de todos os jogadores do servidor, na aba `from` (1 item, 2 mascote) | 4354 AuctionItemsMsg `{sellItem[]}` | *(cliente)* nome `C_MALL_PLAYER_ITEMS`; sentido *(dedução)* |
| 8451 AuctionItemReqMsg | dá lance em `id` por `point` | 4355 AuctionItemRspMsg `{result, itemBuy}` | *(cliente)* campos; regras *(dedução)* |
| 8452 MallItemViewReqMsg | meus lances em anúncios abertos (`itemBuy` com o meu `bidupPoint`) | 4356 AuctionItemsMsg `{pageIdx, pageCount, itemBuy[]}` | *(cliente)* nome `C_MALL_LIST_AUCTION`; página 9 |
| 8453 AuctionItemReqMsg | compra pelo preço fixo: `point` tem que ser o `fixPoint` | 4357 FixAuctionItemRspMsg `{result, mallItemId}`; o item vai pelo correio (148), sem 115 | *(cliente)*; entrega *(cliente, ajuda item 3)* |
| 8454 AuctionItemReqMsg | cancela o meu anúncio (`id`) sem lance | 115 (o item volta à mochila) e 4358 CanceltemRspMsg `{result, id}` | *(cliente)* |
| 8457 SearchItemReqMsg | busca nos anúncios abertos: nome, nível, qualidade, classe, tipo, subtipo, `usable` | 4359 AuctionItemsMsg `{sellItem[]}` (página fixa de 9) | *(cliente)* campos; página *(dedução)* |

Todo handler responde mesmo com corpo vazio ou mínimo (`tests/game/test_mall.py`). Pedido vazio cai na
recusa do próprio handler: 8448 com `sellType` 0 dá `NOT_AUCTION`; 8451, 8453 e 8454 com `id` 0 dão `GONE`.

### Códigos de resultado

Os valores são os do cliente: `SellResultType` (`yishi/datas/consant/SellResultType.as`) dá o nome e o módulo
do código; o texto de cada um é `Auction.ResultAlert<valor absoluto>` no `language.txt`.

| código | nome no servidor | quando | texto do cliente |
|---|---|---|---|
| 0 | `OK` | deu certo | "Başarılı!" |
| −2 | `GONE` | anúncio inexistente, ou cancelar de quem não é o dono | "Eşya mevcut değil!" |
| −3 | `COUNT` | quantidade fora de 1..`count` da pilha | "Uygunsuz miktar!" |
| −4 | `PRICE` | lance abaixo do mínimo, lance ≥ preço fixo, ou compra com `point` diferente do `fixPoint` | "…var olan fiyatten yüksek olmak zorunda" |
| −5 | `FIX_PRICE` | `fixPoint` não é maior que o `point` inicial | "Sabit Fiyat yanlış" |
| −6 | `HOUR` | duração fora de 1..72 h (dedução; a tela oferece 8, 24 e 48 h, `Auction.SubmitHour1..3`) | "Saat yanlış" |
| −7 | `BLOCKED` | item travado (8809) | "Eşya bağlı halde" (vinculado; ver Dependências) |
| −8 | `NO_ITEM` | a posição não tem o item de `itemId` | "Eşya mevcut değil" |
| −11 | `NO_POINT` | diamante insuficiente | "Elmas yetersiz!" |
| −12 | `NOT_AUCTION` | `sellType` diferente de 1 (item), ou template com `StartingPrice` 0 (não vai a leilão) | "Bu eşyanın teklifi verilemez" |
| −14 | `FIX_FAIL` | anúncio sem preço fixo | "Alım başarısız!" |
| −15 | `CANCEL_FAIL` | cancelar com lance feito, ou mochila sem espaço para devolver | "Eşya silinmedi!" |
| −16 | `OWN_FIX` | comprar o próprio anúncio | "Kendi eşyanızı alamazsınız." |
| −17 | `OWN_BID` | dar lance no próprio anúncio | "…en yüksek fiyat verensiniz" (ver Dependências) |
| −18 | `SELL_MAX_COUNT` | mais de 9 unidades num anúncio | "Satılan eşyanın en fazla 9 adet olmalıdır" |
| −52 | `DAILY_LIMIT` | lance ou compra que passa do limite diário do nível | "İhale günlük satın alma sınırına ulaştı!" |

Não usados ainda: −9 (item já à venda), −10 (ouro insuficiente: a taxa existe, o valor não), −13 (falha de lance
genérica). Mudou nesta revisão: template sem `StartingPrice` dava −7; o texto do cliente de −7 é outro, e
−12 é o que o cliente usa para "não dá para dar lance".

## Anunciar (8448)

- Só item da mochila (bolsa 1) com `sellType` 1. Mascote (`sellType` 2) não tem leilão.
- Template com `StartingPrice` > 0 em `ItemTempInfos` (`tempinfos.xml`). O preço inicial mínimo é
  `StartingPrice × count` *(dedução)* e nunca menos de 2 *(cliente, `Auction.SubmitAlert2` "İlk Fiyat 2'den az
  olamaz")*: o template define o piso, e o jogador escolhe acima.
- A ajuda diz que anunciar cobra ouro de imposto *(cliente, ajuda item 4)*. O valor não está no cliente: o servidor
  não cobra (ver Dependências).
- Duração: a tela oferece 8, 24 ou 48 h (`Auction.SubmitHour1..3`); o servidor aceita 1 a 72 *(dedução)*, porque o
  valor que o cliente manda (horas ou índice da opção) não está no decompilado. O fim é `started_at + hour`:
  `AuctionListItemData.timeLeft` calcula `hour × 3600000 − (agora − startTime)` sobre o `hour` que o servidor devolve,
  então o servidor grava `ends_at = started_at + hour` *(cliente)*.
- Quantidade: 1 a 9 por anúncio *(cliente)*: `Auction.ResultAlert18` diz "Satılan eşyanın en fazla 9 adet olmalıdır"
  (o item vendido tem no máximo 9 unidades) e a tela pede "İhale sayısını girin" (`Auction.EnterSellNum`).
- `fixPoint` 0 = sem compra imediata; senão tem que ser maior que `point`.
- Pilha parcial: a quantidade anunciada vira uma linha nova na bolsa 11 (AUCTION, posição 0) e a
  mochila fica com o resto na mesma linha. Não volta a empilhar na pilha original ao cancelar.
- Anúncio inteiro: a linha do item muda para a bolsa 11 e sai da mochila na mesma gravação que cria
  o `mall_listings`. Um item nunca está nos dois lugares.

## Lances, compra e encerramento

- **Lance (8451)**: o primeiro lance é ≥ o inicial *(dedução)*; os seguintes são > o último. Lance ≥ `fixPoint`
  é recusado: a compra é pelo 8453. O diamante sai agora (`ledger.pay`, `reason` `mall`); quem já
  lidera paga só a diferença *(dedução)*. O lance superado vai pelo correio ("Teklif iadesi", anexo −400 com o
  valor). O `mall_bids` guarda um registro por jogador e por anúncio.
- **Compra (8453)**: paga `fixPoint` (ou a diferença, se já é o líder). O item vai ao comprador pelo correio
  ("Satın alınan eşya") *(cliente, ajuda item 3: "a compra chega pela mensagem do sistema"; o 4357 do cliente só tira
  a linha da lista)*, então mochila cheia não recusa a compra. O diamante do vendedor vai pelo correio
  ("Satış geliri"); o lance superado vai de volta pelo correio; os lances e o anúncio são apagados.
- **Imposto da venda**: o vendedor recebe 80% do preço (`game/mall.py` `income`) *(cliente, ajuda item 7: "o sistema
  tira 20% de imposto do vendedor")*, na compra pelo fixo e no vencido com lance. *ponytail*: arredondado para baixo,
  o texto não diz.
- **Limite diário de compra**: diamante pago no mercado por dia (`characters.mall_spent` / `mall_day`, migração
  `0018`), por nível: até 59 = 500, 60–69 = 1000, 70 ou mais = 1500 *(cliente, ajuda itens 9–11: Lv40-60 500, Lv60-70
  1000, Lv70-80 1500)*. Passou: −52, recusado antes de cobrar; o contador grava na mesma gravação do débito.
  *ponytail*: as faixas do texto se sobrepõem em 60 e 70 (aqui contam na de cima), abaixo de 40 vale 500 e acima de 80
  vale 1500; conta o diamante pago em lance e compra, e lance devolvido não volta para a cota.
- **Cancelar (8454)**: só o dono e só sem lance. O item volta à mochila na primeira posição livre.
- **Encerramento**: dois caminhos, na mesma transação e sob `MALL_LOCK`:
  - **agendado**: `game/mall.py` `run`, iniciado em `app.py` (`serve`) e cancelado ao desligar. Roda já na subida e
    depois a cada 60 s (`SWEEP_SECONDS`). Uma rodada que falha é registrada (`log.exception`) e a próxima tenta de
    novo. Assim o anúncio vencido encerra mesmo sem nenhum jogador pedir o mercado.
  - **no pedido**: antes de cada pedido do mercado de qualquer jogador, `_transact` roda `settle` como antes, então
    um pedido nunca vê um anúncio vencido aberto.

  `settle` encerra os anúncios com `ends_at <= agora`:
  - com lance: o item vai ao vencedor pelo correio ("Kazanılan eşya") e o diamante, menos 20%, ao vendedor
    ("Satış geliri");
  - sem lance: o item volta ao vendedor pelo correio ("Geri dönen eşya").

  Os lances do anúncio são apagados. Isto vale também para vendedor fora do jogo: a carta fica no banco
  até ele entrar e pegar no 5022. O 148 sai depois do commit, só para quem está online.

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

## Dependências

Tudo abaixo é *(dedução)*, texto do cliente sem valor, ou falta de dado. O servidor responde algo coerente e não
inventa formato:

- **Duração**: a tela oferece 8, 24 ou 48 h, mas o servidor aceita 1 a 72 *(dedução)*. **Precisa de captura**:
  anunciar com cada uma das três opções da tela e ler o `hour` do 8448 (horas ou índice da opção).
- **Quantidade**: 1 a 9 por anúncio *(cliente, `Auction.ResultAlert18`)*. Não há captura que mostre o que o oficial
  faz com 10 unidades.
- **Página**: a lista pede 9 por página *(cliente: `sendMyAuctionListReq(1,9,1)`)*. O teto de 50 é *(dedução)*.
  O 8457 não manda tamanho e usa 9.
- **Preço inicial**: o piso é `StartingPrice × count` *(dedução)*, nunca abaixo de 2 *(cliente, `SubmitAlert2`)*.
  "İlk Fiyat fazla düşük" (`SubmitAlert5`) não tem o número. **Precisa de captura**: anunciar exatamente em
  `StartingPrice × count` e um abaixo, e ler o código.
- **Preço fixo**: `fixPoint` 0 = sem compra imediata. O cliente tem "Sabit Fiyat, İlk Fiyattan yüksek olmak zorundadır"
  (`SubmitAlert4`), que é o −5 e confere. "Sabit Fiyat girin" (`SubmitAlert3`) não diz se o campo é obrigatório.
- **Taxa de anúncio em ouro**: existe *(cliente, ajuda item 4: "ao vender é preciso pagar ouro de imposto")*, com o
  −10 "Altın yetersiz!". O valor não está no cliente decompilado (a tela de venda é do módulo `auction`, fora do
  decompilado) nem nos templates; o servidor não cobra. **Precisa de captura**: anunciar o mesmo item com preços e
  durações diferentes e medir o ouro que sai (e um anúncio com ouro 0 para ver o −10).
- **Nível de abertura**: a ajuda diz "İhale fonksiyonu {0} seviyede açılır" (`AuctionShopTip`), mas o `{0}` é
  preenchido na tela fora do decompilado. O servidor não confere o nível. **Precisa de captura** (ou do SWF do módulo
  `auction` decompilado): um personagem abaixo do nível tentar abrir o leilão.
- **Limite de anúncios por jogador**: não há. O cliente não tem código de "muitos anúncios".
- **Limite diário de compra**: valores da ajuda (itens 9–11), aplicados. **Precisa de captura** só para as bordas:
  se lance superado conta, o que vale abaixo de 40 e acima de 80, e a hora em que o dia vira (aqui, a data do relógio
  do servidor).
- **Vínculo**: −7 é "Eşya bağlı halde" (item vinculado) no cliente. O item do servidor não tem estado de vínculo
  (`builders/player.py` manda `bind=True` para todo item), então não há como recusar vinculado com o dado que existe.
  O −7 do servidor é item travado (8809), que é outra coisa ("kilit" é o travamento). Lance e compra pagam só elmas
  (`bind=False`) *(dedução)*. **Precisa de captura**: anunciar um item vinculado e um não vinculado (o cliente diz
  "Bu eşya bağlı değildir" para item que ainda não está vinculado) e ler o código.
- **Lance no primeiro preço**: o primeiro lance é ≥ o inicial *(dedução)*. O texto do −4 é "Girilecek fiyat, var olan
  fiyatten yüksek olmak zorunda" (o preço tem que ser maior que o atual): pode ser > também no primeiro lance.
  **Precisa de captura**: dar lance igual ao inicial.
- **Líder subindo o próprio lance**: o servidor deixa e cobra só a diferença *(dedução)*. O texto de −17 é "Teklif
  başarısız, en yüksek fiyat verensiniz" (o lance falha: você já dá o maior preço), e o servidor usa −17 para o dono
  dar lance no próprio anúncio (o cliente já bloqueia isso antes, `AuctionCheckResult1`). **Precisa de captura**: o
  líder dar lance maior.
- **Encerramento agendado**: a cada 60 s, sem dormir até o menor `ends_at` (*ponytail*: até 60 s de atraso no fim).
  O pedido do mercado ainda encerra na hora. **Precisa de captura** para o formato das cartas do oficial: deixar um
  anúncio vencer com lance e sem lance, comprar pelo fixo, e gravar o título, o anexo e o momento da carta. Os títulos
  ("Kazanılan eşya", "Satış geliri", "Geri dönen eşya", "Teklif iadesi", "Satın alınan eşya") são do servidor, não do
  oficial. A ajuda (item 8) diz que o anúncio novo aparece "pouco depois" na vitrine; aqui aparece na hora.
- **`orderBy` / `orderType`**: ignorados em todas as listas (8449, 8450, 8452, 8457). A ordem é a do
  anúncio mais novo primeiro. Parcial em 8450 e 8457: o sentido da ordenação não aparece no cliente.
- **`from`**: lido como tipo do item (1 item, 2 mascote). Mascote não tem leilão: a lista vem vazia.
- **Mapeamento das listas (não confirmado)**: os nomes das constantes (`C_MALL_LIST_SELL`,
  `C_MALL_PLAYER_ITEMS`, `C_MALL_LIST_AUCTION`) sugerem "meus anúncios", "itens de jogadores" e
  "meus lances". Por isso 8449 e 8452 leem as minhas listas e 8450 lê o mercado. Sem captura nem tela
  decompilada, o sentido de 8450 pode ser outro.
- **`itemId`**: assumido como `Item.id` (a linha do banco). Sem captura para confirmar.
- **Mochila cheia**: cancelar recusa (`CANCEL_FAIL`); a compra não depende da mochila (vai pelo correio). O oficial
  não é conhecido para o cancelar.
- **Ordem dos pacotes**: 115 vai antes de 4352/4358 (dedução: o cliente atualiza a mochila
  antes da resposta).
