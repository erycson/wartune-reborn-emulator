# Mercado entre jogadores: anunciar, lances, preço fixo e busca

Handlers em `game/handlers/mall.py`; encerramento dos anúncios vencidos e cartas do sistema em
`game/mall.py`; correio com item em `game/mail.py` e `game/handlers/mail.py` (5022, 8206).
Legenda: *(visto)* = captura oficial; *(cliente)* = constante ou campo no cliente decompilado;
*(dedução)* = coerente com o resto, sem prova direta.

**Limite da fonte.** Nenhuma captura tem pacote do mercado (8448–8457 ou 4352–4359). Os nomes dos
opcodes e os campos das mensagens vêm de `ProtocolType.as`, `AcceptProtocolType.as` e do `.proto`. A
tela do leilão (preços iniciais, duração, página, ordenação) está nos módulos SWF, que o decompilado
não traz em `.as`. Por isso as regras de tela abaixo são *(dedução)* e estão listadas em
[Dependências](#dependências).

## Opcodes

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 8448 SellItemReqMsg | anuncia uma pilha da mochila (`itemId`, `itemPos`, `count`, `point`, `fixPoint`, `hour`) | 115 (a mochila muda) e 4352 SellItemRspMsg `{result, item}` | *(cliente)* campos; regras *(dedução)* |
| 8449 MallItemViewReqMsg | meus anúncios abertos, do mais novo para o mais antigo (`page`, `count`) | 4353 AuctionItemsMsg `{pageIdx, pageCount, sellItem[]}` | *(cliente)* nome `C_MALL_LIST_SELL` |
| 8450 MallItemViewReqMsg | anúncios abertos de todos os jogadores do servidor, na aba `from` (1 item, 2 mascote) | 4354 AuctionItemsMsg `{sellItem[]}` | *(cliente)* nome `C_MALL_PLAYER_ITEMS`; sentido *(dedução)* |
| 8451 AuctionItemReqMsg | dá lance em `id` por `point` | 4355 AuctionItemRspMsg `{result, itemBuy}` | *(cliente)* campos; regras *(dedução)* |
| 8452 MallItemViewReqMsg | meus lances em anúncios abertos (`itemBuy` com o meu `bidupPoint`) | 4356 AuctionItemsMsg `{pageIdx, pageCount, itemBuy[]}` | *(cliente)* nome `C_MALL_LIST_AUCTION` |
| 8453 AuctionItemReqMsg | compra pelo preço fixo: `point` tem que ser o `fixPoint` | 4357 FixAuctionItemRspMsg `{result, mallItemId}`; 115 antes, com o item na mochila | *(cliente)* |
| 8454 AuctionItemReqMsg | cancela o meu anúncio (`id`) sem lance | 115 (o item volta à mochila) e 4358 CanceltemRspMsg `{result, id}` | *(cliente)* |
| 8457 SearchItemReqMsg | busca nos anúncios abertos: nome, nível, qualidade, classe, tipo, subtipo, `usable` | 4359 AuctionItemsMsg `{sellItem[]}` (página fixa de 9) | *(cliente)* campos; página *(dedução)* |

Todo handler responde mesmo com corpo vazio ou mínimo (`tests/game/test_mall.py`). Pedido vazio cai na
recusa do próprio handler: 8448 com `sellType` 0 dá `NOT_AUCTION`; 8451, 8453 e 8454 com `id` 0 dão `GONE`.

### Códigos de resultado

Os valores são os do cliente: ``Auction.ResultAlert`` é o módulo do código *(cliente)*.

| código | nome no servidor | quando |
|---|---|---|
| 0 | `OK` | deu certo |
| −2 | `GONE` | anúncio inexistente, ou cancelar de quem não é o dono |
| −3 | `COUNT` | quantidade fora de 1..`count` da pilha |
| −4 | `PRICE` | lance abaixo do mínimo, lance ≥ preço fixo, ou compra com `point` diferente do `fixPoint` |
| −5 | `FIX_PRICE` | `fixPoint` não é maior que o `point` inicial |
| −6 | `HOUR` | duração fora de 1..72 h |
| −7 | `BLOCKED` | template sem `StartingPrice` (0 = não vai a leilão) ou item travado (8809) |
| −8 | `NO_ITEM` | a posição não tem o item de `itemId` |
| −11 | `NO_POINT` | diamante insuficiente |
| −12 | `NOT_AUCTION` | `sellType` diferente de 1 (item) |
| −14 | `FIX_FAIL` | anúncio sem preço fixo, ou mochila do comprador cheia |
| −15 | `CANCEL_FAIL` | cancelar com lance feito, ou mochila sem espaço para devolver |
| −16 | `OWN_FIX` | comprar o próprio anúncio |
| −17 | `OWN_BID` | dar lance no próprio anúncio |

## Anunciar (8448)

- Só item da mochila (bolsa 1) com `sellType` 1. Mascote (`sellType` 2) não tem leilão.
- Template com `StartingPrice` > 0 em `ItemTempInfos` (`tempinfos.xml`). O preço inicial mínimo é
  `StartingPrice × count` *(dedução)*: o template define o piso, e o jogador escolhe acima.
- `fixPoint` 0 = sem compra imediata; senão tem que ser maior que `point`.
- Pilha parcial: a quantidade anunciada vira uma linha nova na bolsa 11 (AUCTION, posição 0) e a
  mochila fica com o resto na mesma linha. Não volta a empilhar na pilha original ao cancelar.
- Anúncio inteiro: a linha do item muda para a bolsa 11 e sai da mochila na mesma gravação que cria
  o `mall_listings`. Um item nunca está nos dois lugares.

## Lances, compra e encerramento

- **Lance (8451)**: o primeiro lance é ≥ o inicial; os seguintes são > o último. Lance ≥ `fixPoint`
  é recusado: a compra é pelo 8453. O diamante sai agora (`ledger.pay`, `reason` `mall`); quem já
  lidera paga só a diferença. O lance superado vai pelo correio ("Lance iadesi", anexo −400 com o
  valor). O `mall_bids` guarda um registro por jogador e por anúncio.
- **Compra (8453)**: paga `fixPoint` (ou a diferença, se já é o líder). O item entra na mochila do
  comprador na mesma gravação; o diamante do vendedor vai pelo correio ("Satış geliri"); o lance
  superado vai de volta pelo correio; os lances e o anúncio são apagados.
- **Cancelar (8454)**: só o dono e só sem lance. O item volta à mochila na primeira posição livre.
- **Encerramento**: não há job agendado. Antes de cada pedido do mercado de qualquer jogador do
  servidor, `settle` encerra os anúncios com `ends_at <= agora` na mesma transação do pedido:
  - com lance: o item vai ao vencedor pelo correio ("Kazanılan eşya") e o diamante ao vendedor
    ("Satış geliri");
  - sem lance: o item volta ao vendedor pelo correio ("Geri dönen eşya").

  Os lances do anúncio são apagados. Isto vale também para vendedor fora do jogo: a carta fica no banco
  até ele entrar e pegar no 5022.

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
  pelo correio, e o snapshot dele não é mexido daqui.
- `MALL_LOCK` (asyncio, no processo) serializa as gravações do mercado. Um servidor por processo.
  ponytail: lock global, por anúncio se a fila pesar.

## Tabelas

Migração `0012_mercado_entre_jogadores_e_itens_no_` (`persistence/migrations/versions/`):

| tabela | conteúdo |
|---|---|
| `mall_listings` | um anúncio: `server_id`, `seller_id`, `item_id` (único; cascata do item), `seller_nick`, `point` (lance atual ou inicial), `fix_point`, `hour`, `started_at`, `ends_at` (índice), `bidder_id` (0 = sem lance) |
| `mall_bids` | `listing_id`, `bidder_id`, `price`, `bid_at`; único por `(listing_id, bidder_id)`; cascata do anúncio |
| `mail_annexes.item_id` | id do item de verdade no anexo (0 = anexo por template); `server_default` 0 |

Bolsas novas: 10 (MAIL, correio) e 11 (AUCTION, leilão), ambas com posição 0 (ver [itens.md](itens.md)).

## Dependências

Tudo abaixo é *(dedução)* ou falta de dados no cliente decompilado. O servidor responde algo coerente
e não inventa formato:

- **Duração**: 1 a 72 h, decidido aqui. O cliente não traz a lista de horas.
- **Página**: o `count` do pedido, até 50; 0 usa 9. O 8457 não manda tamanho e usa 9.
- **Preço inicial**: o piso é `StartingPrice × count`. O cliente não mostra o piso.
- **Taxa de anúncio**: não cobrada. O decompilado não traz valor de taxa.
- **Limite de anúncios por jogador**: não há. O decompilado não traz limite.
- **Preço fixo**: opcional (`fixPoint` 0). O cliente não diz se o campo é obrigatório.
- **Vínculo**: não há restrição de vínculo no cliente decompilado; o servidor cobra só diamante
  (`bind=False`) e não aceita diamante vinculado no lance. Não verificado com captura.
- **`orderBy` / `orderType`**: ignorados. A ordem é a do anúncio mais novo primeiro.
- **`from`**: lido como tipo do item (1 item, 2 mascote). Mascote não tem leilão: a lista vem vazia.
  Não confirmado se 8450 é a lista de todos os anúncios ou "itens do jogador" (o nome do opcode sugere
  os dois; o pedido não traz id de jogador, então a leitura de mercado é a única que cabe).
- **`itemId`**: assumido como `Item.id` (a linha do banco). Sem captura para confirmar.
- **Encerramento sem job**: um anúncio vencido só é encerrado no próximo pedido do mercado. Enquanto
  ninguém abrir o mercado, o item continua na bolsa 11 e o lance continua valendo. Um job agendado
  resolveria; não existe agendador no servidor.
- **Mochila cheia**: compra e cancelar recusam (`FIX_FAIL`, `CANCEL_FAIL`). O oficial não é conhecido
  para este caso.
- **Ordem dos pacotes**: 115 vai antes de 4352/4357/4358 (dedução: o cliente atualiza a mochila
  antes da resposta).
