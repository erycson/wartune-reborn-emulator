# Mochila, itens, loja, forja e moda

Handlers em `game/handlers/items.py` (mochila e uso), `shop.py` (lojas), `forge.py` (forja) e
`fashion.py` (moda). Regras da mochila em `game/bag.py`; moeda premium em `services/cash.py`.
Legenda: *(visto)* = captura oficial; *(cliente)* = arquivo `.as` do cliente decompilado;
*(dedução)* = coerente com os dois, sem prova direta.

Regra de todos os handlers: tudo é validado no servidor (dono, posição, quantidade, preço, nível,
espaço), o snapshot muda antes de qualquer `await` e uma `save` grava tudo junto. Recusa sem
resposta só quando o cliente não espera nenhuma; senão vai o resultado de erro que ele sabe mostrar.

## Bolsas (`bagType`)

| bagType | o que é | posições |
|---|---|---|
| 0 | bancada da forja/moda (`Hide`) | 0 = equipamento, 1 = pedra da sorte; 0..11 na decomposição |
| 1 | mochila | 0 .. 42 + `bagCount` (−1); 217 com a mochila alugada ativa (`PlayerInfo.bagTotalCount`) *(cliente)* |
| 2 | runas de batalha do herói (SonType 214) | 0..2, uma a cada nível 20/30/40 *(cliente)* |
| 3 | medalha de honra do herói (MasterType 3) | 0 |
| 4 | equipamento do herói (`objectId` = id do herói) | por SonType (`GoodsSonType.getSonTypePos`) *(cliente)* |

Espaços do herói: 101→0, 103→1, 104→2, 106→3, 107→4/5, 108→6/7, 109 asa→8, 110 chapéu→9,
112 roupa de moda→10, 111 arma de moda→11, 117→12, 118→13. Equipar confere `Job` (lista com 0 ou o
job do herói), `Sexs` (2 ou o sexo) e `NeedGrades` (`GoodsCheck.checkGoodsCanEquip`) *(cliente)*.
Os bags 10 (correio) e 11 (leilão) são do servidor: o item entra neles pelo correio (anexo de item, 5022
o tira) e pelo mercado ([mercado.md](mercado.md)), posição 0. Não são movíveis pelo 5005. O bag 6 é o
armazém da guilda (`ConsortiaCaseBag`, *cliente*): itens do próprio jogador, `storeLevel*5` espaços (56 no
nível 10, `ConsortiaModel.currentCasecellNum`), move e empilha pelo 5005 e organiza pelo 8220 (o cliente manda a
ordem). O que acontece com eles ao sair da guilda não tem fonte: ficam lá e podem sair para a mochila. Os bags
22 (árvore dourada), 23 (pesca), 24 (labirinto), 25 (estrada do ouro), 26 (equipamento de mascote,
`objectId` = pet) e 32 (depósito) são de outros sistemas; o 32 é recusado no 5005.

### Equipamento de mascote (bolsa 26, `MasterType` 5)

Vestir e tirar pelo 5005 (`PetBagCellClickMediator`, `PetEquipBagCellClickMediator`): o cliente manda `endObjId` 0 e
o mascote em `objectId`. Espaço pelo SonType: 113 → 0/1, 114 → 2, 115 → 3/4, 116 → 5; o mascote tem de ser do
jogador. Vestir vincula o item e o mascote ("Sylph will become bound after putting on equipment"); a resposta leva
o 4540 do mascote com os `bag*` novos. Os `bag*` (`rules.pet_equipment`) somam o atributo do template, o
encantamento (`int(base × 1,08^mouldGrade − base)`), as Divinity Souls dos furos e os atributos sorteados. A batalha
ainda não usa (**dedução** do total, sem captura).

| C>S | Resposta | Regra |
|---|---|---|
| 8644 encantar | 115, 4558 | peça da bancada (posição 0) abaixo do `StrengthenMax`; 3 + 3 materiais (3250101, 3260101), os que faltam em Balens pelo Point da loja (80); taxa min(100, max(1, 50 − 10·nível) + bênção). Sucesso: +1 e bênção 0; falha: bênção +5 abaixo do nível 10, senão +3, teto 100. Vincula |
| 5153 avanço (receita `Types` 10) | 115, 89 | a peça da bancada com o encantamento no máximo; materiais 2..4 (os que faltam em Balens pelo Point), `NeedGold`; mesma linha com o template novo, furos abertos até o `Property1` novo, encantamento e bênção voltam a 0; `composeResult` true |
| 5153 avanço do herói (`Types` 5) | 115, 89 (+3, 150) | a peça equipada no líder primeiro, senão a da mochila; mantém reforço, pedras e atributos; "Received: … x1" |
| 5151 / 5152 | como no herói | engaste com Divinity Soul (SonType 329) sem repetir atributo; furo com a Soul Socketing Rod (3280101) só abaixo do `Profile` |
| 8336 / 8339 refino | como no herói | pedras por `Profile` (`PET_STONES`, 6 → 24, outro → 100); sem o Refinement Lock: cada cadeado paga 45; as pedras que faltam saem em Balens pelo Point |

Item novo: equipamento nasce com `Property1` furos abertos (`join` 0); os outros furos ficam −1
(fechado) *(visto)*. `randomSkill_1..5` (`bag.roll_random_skills`): com `DefaultSkill`, os dele *(visto: 1013103 com 70306/70406/70506)*; senão, só em equipamento, `RandomSkillCount` atributos de tipos distintos entre 701 e 711, cada um na faixa `NeedGrades // 10` do tipo (faixa = uma subida de `Grades` no `SkillTempInfos`: 70201-03, 70204-06, 70207-10...; 70604-06, 70607-12...). *(dedução de 16 sorteios)*: níveis 3 e 8 na 1ª faixa, 12 e 15 na 2ª (oficial_20261023-153200-1/171155-1, tutorial_en); *(visto, só turco: "yeraltı labirent marketi alışveriş")* o Kronos' Authority (1991017, nível 20, `RandomSkillCount` 5) com os 5 na 3ª (70407, 71123, 70509, 70719, 70209). **TODO(inventado)**: o tipo 701 (sem amostra) e o sorteio uniforme dentro da faixa. O refino (8336) sorteia igual (mascote: uniforme entre todos).

### Vínculo (`Item.is_binds`, migração `0043`)

O `ItemInfoMsg.bind` vem de `items.is_binds` (tooltip `EquipTipsContent.bind1/bind2`: "Bound"/"Unbound"). Os
templates não têm campo de vínculo: depende de onde o item veio *(cliente)*.

- **Nasce vinculado**: drops, recompensas, composição ("All synthesized items are bound"), conversão de pedras ("All
  converted items are bound"), lojas de outras moedas (glória, ametista, honra, labirinto, Balens vinculados). A
  captura inglesa só tem `bind` true. Os itens que já existiam ficaram vinculados.
- **Sai livre**: compra na loja com preço em Balens (`ShopTempInfos.Point`; o `charge` não aceita vinculado nesse
  preço), na loja comum (5154) e na misteriosa (8482). *(dedução)*: o cliente não diz isso com todas as letras, mas as
  ajudas das outras lojas dizem que elas são vinculadas. Item vendido no leilão continua livre (a linha muda de dono).
- **Vincula**: equipar no herói (bolsa 4) ou pôr nas runas (2) (`PlayerBagCellClickMediator`/`DropMediator`, "This
  operation will change this item to become bound"); juntar pilha livre com vinculada (`GoodsCheck.isAddToChecker`,
  mesma confirmação); reforço, mesmo na falha (`helpContent01`); engaste (`helpContent02`).
- **Empilhar**: a loja e as recompensas (`bag.add`/`bag.fits`) só completam pilhas de mesmo vínculo; o 8220 não
  junta livre com vinculado; o 5005 junta (o cliente já pediu a confirmação) e a pilha fica vinculada.
- **Leilão**: item vinculado dá −7 "Item is bound!" ([mercado.md](mercado.md)).
- **Forja**: a decomposição dá a pedra com o vínculo do equipamento ("Recycling unbound equipment will produce unbound
  Refinement Crystals"); o refino com pedra vinculada vincula o equipamento livre.
- **Moda**: a vinculada entra no livro (ativada) ao pedir o livro; a livre, ao vestir (que vincula).
- **Falta**: mascote vinculado (leilão de mascote).

## Mochila e uso — `items.py`

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5005 ItemReqMsg | move entre os bags 0–4; destino ocupado: empilha (mesmo item, mochila/bancada) ou troca (o outro precisa caber na origem). Da bancada para a mochila o cliente manda `endPos` 0: o servidor escolhe o primeiro livre; o equipamento que veio do herói volta para o corpo dele (*(visto)*: tutorial_en #3217, 231733 #4804; a origem fica na sessão). Tirar equipamento: a vida acima do máximo novo volta para a reserva (113, 231733 #233/#300). Vestir moda pela primeira vez põe no livro (4542) | com o herói: (113, 100,) 3, 83 do HP pack, 150, 115 origem, 115 destino (+4542); na volta da bancada o 115 do herói vem antes; mochila↔bancada: só os dois 115 | *(visto)* ordem; validações *(cliente)* |
| 5006 ItemUseMsg | 298 pacote: troca pelo `GradeDrop`; 203 recurso: Property1 1 ouro, 3 Balens, 4 Bound Balens, 5 Stamina (até `weary_limit`), 6 prestígio, 7 EXP, 10 Daru × Property2 × `count`; **15 entrada de campanha em grupo** (The Empire Crusade: `times` = Property2 × `count`, ver salas-campanha.md); 206 caixas de pedras (`GEM_BOX_LEVELS`, ids 2060008 a 2060020): pedra aleatória do nível (`TransformInfos`); 209 poção de HP: `blood` += Property1 | 203: 115, 109 (só no ouro), 111 "Received:Gold x1000" (sem separador de milhar), 3, e o 83 "Received 5,000 EXP " na EXP (*visto* 153200 #2188-#2192, 231733 #4131-#4150 Daru/Stamina; a forma do EXP é a da inglesa #428; o turco põe "Tebrikler! " na frente); 206: 115, 115, 111, 3, 83; 15: 115, 4240, 111, 3; 209: 115, 113, 150, 3 | *(visto, só turco: "büyük exp kitabı-orta ruh incisi-altın kutusu kullanımı", "lvl1 değerli taş sandığı açımı…", "büyük sefer kullanımı…", "büyük hp iksiri kullanım")* |
| 5007 ItemReqMsg.beginPos | vende a pilha toda | 115, 109 | preço `GoodsHelp.getSellGold` *(cliente)* |
| 8624 ItemSellReqMsg | venda em lote (pos, count) | 115, 109 | *(cliente)* |
| 8220 ArrangeReq | aplica a ordem que o cliente calculou (`BaseBagListView.sort`: cada item `oldplace`→índice), sem colisão nem fora da mochila; `isStackItem` junta pilhas incompletas (mesmo item e mesmo cadeado) e fecha os buracos | 115 com a mochila | *(cliente)*; pilhas *(dedução)* |
| 8346 ItemRemoveMsg `{bagType, pos}` | tira item vencido: o servidor confere `validDate`/`beginDate` e apaga (ainda válido: ignora). Bolsa do herói: também 3 e 150 | 115 com a posição vazia | pedido *(cliente)* `BaseBagListView`/`EquipBagII`; resposta *(dedução)* |
| 8809 LockAndUnlockMsg | opType 1 mochila, 3 equipamento, 4 medalha: alterna `isLocked`. Item travado não é vendido nem usado | 115 | *(cliente)* |
| 8484 ItemUseStoreReqMsg | gasta `count` Soul Crystal (208014, Property1 = EXP) no cristal: `storeGp` e `storeGrade` (`UpGradeTempInfos` Types 15, `Data` = total) | 115, 3 | *(cliente)* |
| 5010 PayTypeMsg | compra `property1` linhas de 7 espaços (até 175); linha i custa (i+1)×10 Balens até a 10ª, depois 100 (`BagBuyFrame`) | 3 (`bagCount`) | *(cliente)* |
| 8819 RentalBagOpReqMsg | aluga a mochila de 217 por `param2` dias (`rental_bag_day_cost` × 2 páginas), `param1` = payType; renovar soma ao prazo | 3, 4709 `{opType, rentalBagTime, status 1}` | *(cliente)* |
| 8199 DetailReqMsg | ficha de outro jogador (online ou do banco): equipamento do líder, atributos, `hideFashion`, `storeGrade`, `appellId` | 4125 DetailRspMsg | *(cliente)* `PlayerInfoFrameII` |
| 5129 CampaignReqMsg | baú da luta (`paraString1` = `signId` do 4103; `paraInt1` 0 = tudo, ou um `templateId`) | 115, 4476, 111 e 83 por item; mochila cheia: 4268 `{signId, baseItem}` com o que sobrou (o cliente põe o baú de volta); `signId` desconhecido: nada | (visto) inglesa #2910-#2939; *(cliente)* `BattleFallGoodsView`, `CampaignMapController` |

### Itens com validade

`Item.valid_date` (minutos) e `begin_date` (migração 0036) vão no 115 como `validDate` e `beginDate`
(`"YYYY-MM-DD hh:mm:ss"`, o mesmo `fmt_time` do `sysCurtime`, porque o cliente compara os dois) *(cliente)*
`ItemHelper`, `GoodsInfo.leftTime`. Vence quando `agora - beginDate >= validDate` minutos (a conta do cliente).
Só a loja dá validade (varredura do `tempinfos.xml`: nenhuma outra tabela tem `ValidDate`; a captura inglesa não tem `validDate` > 0): `ShopTempInfos.ValidDate` em minutos (as 10 medalhas da loja de honra, ShopType 3:
10080/21600/43200 = 7/15/30 dias; `NumBuyFrame` põe o número direto em `validDate`) *(cliente)*. Item com validade
não empilha (5005, 8220, `bag.add`). Vencido some: no 8346 do cliente, no login (antes do 115) e no relógio de 60 s
(20008), que pega também a medalha vestida (bolsa 3), que o cliente nunca confere *(dedução)*. Sem aviso: o cliente
não mostra nada ao mandar o 8346 *(dedução)*.

**Captura que falta**: no oficial, comprar uma medalha de 7 dias (Honor Shop), deixar vencer com ela na mochila e
outra vestida, e capturar o login seguinte e o 8346 → resposta (algum 83/111 ou correio avisando?).

Poção de HP e Bound Balens/Balens vindos de item gravam o `cash_ledger` com `reason` `item`.
Divine Light (SonType 316): um por uso, tira a névoa do mapa do castelo por 20 s (4939); ver
[cidade-externa.md](cidade-externa.md).
Depende de outro sistema (recusado com log no 5006): cristal (203/11), guilda (203/8), City Protection
Token (201/2001, conta pelo 4452 `defenceLeftTime` e para com o 8562), caixas 206 cujo conteúdo só está na
descrição (Property1 = o próprio id).

### Pergaminhos de efeito (SonType 201)

`game/buffs.py` + `items._use_effect`. Property1 = `EffectTempInfo` (chave do buff no cliente), Property2 =
minutos por unidade (× `count`), Property3 = grau (o `{Grades}` da descrição). Estado em `event_states`: chave
`buff:<efeito>`, `value` = grau, `text` = item, `updated_at` = fim (sobrevive a reinício; sem migração).

| pacote | o que faz | fonte |
|---|---|---|
| 5006 → 115, 110 `PropertyUpdatedMsg{propertyType = PropertyType1 do efeito, value = grau}`, 4188 `ItemBufferRspMsg{templateId = efeito, validityDate = minutos restantes, grade, type 2, typeTemplateid = item, isCancel false}`, 3 (sem texto) | liga o efeito | *(visto, só turco: `exp_kitabi_kullanim_kahraman_sarayi...` #2-#10)*, 2013002: `{30, 100}` e `{2030, 60, 100, 2, 2013002}` (o 4902/150/4434 no meio são de outros sistemas) |
| + 109 | depois dos pergaminhos de ouro/população | *(dedução)* |
| mesmo efeito, grau menor | recusa sem resposta | *(cliente)* `MulItemUseFrame` já barra: "Stronger buff already active, overlapping not allowed." |
| mesmo efeito, grau igual / maior | soma o tempo / substitui grau e tempo | *(dedução)* |
| 8283 `EffectRemoveReqMsg{templateId}` | o cliente manda quando o relógio do ícone zera ou o jogador tira o buff ("Are you sure you want to remove this buff?"): encerra, 110 `value 0`, 4188 `validityDate 0` (o cliente só apaga o ícone com ele) | *(cliente)* `PlayerBufferManager`/`PlayerBufferItem`; resposta *(dedução)* |
| login | 4188 com os ativos, depois do 4247 | *(dedução)*: nenhuma captura de login com buff |

`validityDate` arredonda os minutos para cima: o relógio do cliente acaba depois do servidor.
Efeito aplicado: **2030 EXP Boost** (2013001-4, 50/100/200/1000%) multiplica o `gpBonus` de cada batalha
de campanha/masmorra (`campaign._battle_over`; o 4103, o 83 e o 4382 levam o valor com bônus; o
`gpBonus` capturado é a base) e também a EXP do relatório do fim da etapa (`_dungeon_end`, 137 `totalGp`, o 83
"Received N EXP " e o `add_gp`): *(cliente)* a descrição do 2013002 diz "Increases EXP received from instances by
100%, ... only takes effect in campaigns and MP dungeons". *(dedução)* o grau vai no `propJoin` do 137 (o campo "prop"
do `CampaignResultView`); a captura do 137 só tem `propJoin` 0, sem pergaminho. **2008** (Gold Expansion Scroll,
"Warehouse Capacity +25%") sobe o teto do armazém (`castle.gold_max`) e **2005** (Population Expansion Scroll) a
população máxima (`rules.population`, também no recrutamento).

**Poções de atributo** (2013501-2014006, 2015101-3 e os itens de coleção 2125001-10): o `EffectTempInfo.PropertyType1`
diz o atributo, o grau (Property3) são os pontos: 135 Power, 137 Agility (*dedução*: "Defense"/"Armor"; o 2141 "All
Stats" diz "Strength, Intellect, Armor, Endurance"), 138 Intellect, 139 Captain (Charisma), 140 Physique (Endurance),
202 os quatro (Power, Intellect, Agility, Physique). Entram em `rules.leader_stats` como linha de bônus
(`buffs.stat_bonuses`): somam no `total*` e nos derivados (PhyAttack, Live...), não no `base*` (o cliente marca o
atributo com efeito quando total > base, `BasePropertyInfo.hasEffect`), e valem na batalha e no poder de combate.
*(cliente)* `PlayerEffectHelper` ignora o 110 desses tipos; por isso o 5006 manda também o **150** com o herói novo,
depois do 4188 (115, 110, 4188, 150, 3), e o 8283 manda o 150 sem a poção. *(dedução)* a ordem e o 150 no 8283; não há
captura de poção de atributo (a do pergaminho de EXP tem um 150 entre o 115 e o 110).

Os outros 201 (pergaminhos 2041-2048, Camouflage 2000, Blessing 7001) ligam o ícone e o tempo, mas o efeito ainda não
existe no servidor.

Captura que falta: usar uma Power Potion (2013501) e gravar o 5006 inteiro (onde vem o 150 e se o 110 sai) e o 8283
dela; terminar uma etapa de masmorra solo com o 2013002 ativo e gravar o 137 (`totalGp` e `propJoin`).

## Loja — `shop.py`

Preço e moeda como `ShopGoodsInfo.setPrice` *(cliente)*: a primeira coluna > 0 entre `Point`,
`GiftToken`, `Gold`, `Honor` (item 208001), `ConsortiaOffer` (guilda: não suportado) e `MazeCoin`
(item 208009). Preço em `GiftToken` aceita vinculado: `payType` 0 usa o vinculado primeiro e completa
com Balens; 1 só Balens. Preço em `Point` só aceita Balens. Lojas de pontuação (ShopType 8, 13, 15, 20)
ficam sem suporte.

`BuyInfo.result` *(cliente, `ShopManager`)*: 1 ok, 2 jogador ausente (presente para outro: depende
do correio), 3 item, 4 sem dinheiro (silencioso), 6 limite do dia (`VIP0Count`), 7 VIP, 8 item
inexistente / oferta, 9 nível de guilda, 10 nível, 11 falhou (mochila cheia; o oficial manda pelo
correio, 12).

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5154 ShopMsg | compra (o registro decodifica como FashionShopMsg; o handler relê como ShopMsg) | 3 ou 109 (ou 115 da moeda-item), 115 do item, 4476 (e 4426 com montaria), 111 e 83 "Successfully purchased {nome} x{n}.", 90 ShopMsg `{buyInfo + result}` | *(visto)* oficial_20261023-171155-1 #227-#242 |
| 8592 FashionShopMsg | compra de moda, uma ou várias | o mesmo por item (90 cada) e 4486 `{result}` no fim | *(cliente)* `FashionAllBuyFrame` |
| 5633 ShopMsg | compra e usa a poção de HP (ShopType 100) | 109/3, 113 `{heroId, hp, blood, bloodId}`, 170 `{result, templateId}` | *(visto)* |
| 8218 | compras de hoje (ofertas com `isDiscount` e `itemId` = id da oferta) | 4145 `hasDataInfo[{userId, itemId, counts, buyDate, isDiscount}]` | *(visto)*; ofertas: *(cliente)* `__getBuyDataInfosSuccess` |
| 8693 ShopMsg | quantos daquele item já comprei hoje | 4599 `buyInfo.count` | *(cliente)* |
| 8632 | rodízio das ofertas `type` 2 do 4238; o 0053 só tem `type` 1 | 4547 `{refreshDate}` sem `hasDataInfo` | *(visto)* oficial_encantar #1632-#1633, igual |
| 8645 ShopMsg | compra coletiva: só existe com uma oferta type 3 do 4238 (o 0053 não tem); recusa sem resposta | — | *(cliente)* |
| 5154 ShopMsg `isDiscount` | compra de oferta (`goodId` = id da oferta): `price` em Balens por unidade (nunca vinculado), dentro de `beginDate`..`endDate`, até `oneDayCount` por dia (result 6); entrega `templateId`×`counts` e `templateIdN`×`countN` do pacote, livres | 3, 115, 111/83, 90 | *(cliente)* `MainShopInfo.price`/`canOneCount`, `ShopManager.__shoppingHandler` |
| 8483 ShopFreshReqMsg | loja misteriosa (ShopType 5): lista; `isButton` atualiza pagando `ShopFresh_NeedDiamond` (45 no inglês). Os itens trocam sozinhos 14400 s depois do `freshLastdate` (`MysteryShopModel.remainTime`, que pede a lista de novo ao zerar); as compras do dia zeram na virada das 5h | 3, 4384 `{itemId[], freshLastdate, isCanBuy[], buyCount, maxBuyCount}` | *(cliente)* |
| 8482 ShopItemBuyMsg | compra o item `index` da misteriosa (uma vez cada, até `ShopBuy_MaxCount` 20 por dia) | 3/109, 115, 111, 83, 4383 `{result, buyCount}`, 4384 | *(cliente)* |
| 8597 AppellExchangeMsg | `look`: os 221 títulos (`titles.appells_msg`, igual ao do login); trocar exige ter o título (`isGet` pelo `Para`: Honor, contribuição, itens; responde 3 e 150); `appellId` 0 tira o título | 4484 AppellsMsg | *(cliente)* |

Misteriosa (tela inglesa em `m7/scripts/auction/view/mysteryshop`): 6 itens (`MysteryShopModel.MAX_GOODS_NUM`;
o `MAX_RARE_GOODS_NUM` 8 é a vitrine de raros, outra lista) sorteados pelo peso `Rands` entre os do nível do jogador;
abre no nível 26 (`MysteryShopView`, "Unlocks at Lvl. 26."; abaixo disso o 8483 não responde e o 8482 dá `LEVEL`).
No 4384, `isCanBuy` 0 = à venda e 1 = comprado (`BuyGoodsItem`). Limite diário por item em `shop_buys` (zera
quando muda o dia).

Loja do labirinto (ShopType 4, 119 linhas, todas com preço só em `MazeCoin`): paga com Crypt Tokens (208009). *(visto, só turco)*
`yeralti_labirent_marketi_alisveris`: o 105 (Gold Chest, 1 moeda, andar 5) tirou 1 (118 → 117) e o 110 (Kronos'
Authority, 25 moedas, andar 15) tirou 25 (117 → 92). A resposta é a da loja comum: 115 da moeda, 115 do item, 111, 83 e 90
(o 4476, 4426 e 4484 da mesma captura são de outros sistemas, não da compra). O andar (`MazeLayers`, `MazeLayers2`): o
cliente esconde o botão quando o andar passa de `towerInfo1.maxIndex` (`GoodsItem.as:380`) ou de `towerInfo2.maxIndex`
(`:384`). O `maxIndex` é o recorde (maior andar: "My Record" do `MazeFrame`, e a missão tipo 38 compara `maxIndex >=
Para2`, `TaskTemplate.checkMazeRecord`). Sem progresso salvo, o servidor manda 0 no 4205 (`MAZE_MAX_INDEX`) e nunca
manda o segundo labirinto; por isso recusa (`FAIL`, *(dedução)*) os produtos com `MazeLayers` > 0 e os com
`MazeLayers2` > 0. Os 4205 turcos têm `maxIndex` 60: o recorde daquele personagem (com `towerIndex` 1, 2, 3 e 5), que
comprou o andar 15. Falta: o progresso do labirinto (andar e recorde).

## Forja — `forge.py`

O cliente põe o equipamento na bancada (5005 para o bag 0, pos 0) e manda a operação.

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5150 (vazio) | reforço: taxa `clamp(100 − g×10, 10, 100)` + Property1 da pedra da sorte (bancada pos 1, SonType 204); ouro `NG≥80 ? (NG/10+1)²×P×(g+1)^2.1×10 : 1.5^(NG/10+1)×(P+1)×(g+1)^2.2×5+500`; até `StrengthenMax`. A pedra vai mesmo na falha e o nível não cai | 109, 109 (iguais), 115 da pedra, (115 do item no sucesso ou se ficou vinculado), 86 StoreRspMsg: sucesso `{strengResult, strengthenGrade, pos, objectId, bagType}`, falha só `{strengResult: false}` | *(visto)* sucesso com pedra em `oficial_encantar` #218-#223 (gravador; Templar Priest Staff +1→+2 com Lvl. 2 Luck Stone, 603 de ouro = a fórmula), sucesso sem pedra na inglesa #3207-#3212, falha no turco "atölye item basma ve mozaik" #9-#12; taxa *(cliente)* |
| 5151 StoreReqMsg `{mountPos, bagType, bagPos}` | engasta a pedra (SonType 205) no furo aberto; furo ocupado troca e cobra o Property3 da antiga, que volta para a mochila; nunca duas do mesmo atributo (Property1) | 109, 115 da pedra, 115 do item, 111/83 "Socketing successful!" | *(visto, só turco: "atölye item basma ve mozaik")* |
| 5152 StoreReqMsg `{holePos, operate}` | true: abre o furo com 1 Socketing Rod (208004); o 4º só em item Profile 5. false: tira a pedra (Property3 em ouro) e devolve | abrir: 115, 115; tirar: 109, 115, 115, 4476 e os 4484 do item ganho, 111 "Unsocketing successful!", 83 "Unsocketing successful! Received: {pedra} x1!" | *(visto, só turco)*; abrir *(cliente)* |
| 5153 StoreReqMsg `{composeId, composeNum}` | receita `ComposeTempInfos` (Material1–4 × Count × n, NeedGold × n, NeedMinLevel) | 115, 109, 115, 111 "Received: {nome} x{n}", 89 `{composeResult false, composeTemplateId −1}`, 83 | *(visto, só turco: "değerli taş birleştirme")* |
| 8538 StoreReqMsg `{srcItemid, desItemid, count}` | troca pedras do mesmo nível (`TransformInfos`, CostGold × count) | 115, 109, 115, 111/83 "Conversion successful" | *(visto, só turco)* |
| 8336 SmithFreshReqMsg `{lock[], bindType, payType}` | sorteia os atributos do item da bancada (`RefreshView`, m14) gastando as pedras de refino dele (`Refresh`) por `Profile` (2 → 1, 3 → 4, 4 e 5 → 18): `bindType` 0 as vinculadas primeiro (equipamento livre fica vinculado), 2 só as livres. `RandomSkillCount` atributos; travados mantêm; cada cadeado gasta um Refinement Lock (208027) ou 45 Balens (`payType`), e travar todos os atributos é recusado ("No Stats to Refine"). Equipamento travado (8809) não refina. Pool: `SkillTempInfos` 70000–77199 com `Grades` > 0 e `SkillPropertyTempInfos` (1584 de 2157) | 115, 3 (com Balens), 4258 `{randomSkill[]}` | *(cliente)*; pool *(visto, só turco)*: os 42 atributos das capturas têm `Grades` 1–10, nenhum 0 (0 = placeholder: +0 com 500000, "Troop Count"); peso *(dedução)* uniforme |
| 8339 (vazio) | aplica o último sorteio | 4259 `{result}`, 115 | *(cliente)* |
| 8464 RefreshPropertyReqMsg `{itemId}` | atributos sorteados do item (o pendente, se houver) | 4368 `{randomSkill[], lockPos[], result}` | *(dedução)* |
| 8340 (vazio) | decomposição (`ResolveView`, m14): os equipamentos da bancada 0..11, sem pedra e sem cadeado, viram a pedra de refino deles (`Refresh`) por `Profile` (2 → 1, 3 → 4, 4 e 5 → 18), com o vínculo do equipamento; 1.000 de ouro cada. Recusa (vazio, pedra, ouro, mochila): 4260 false | 115 (bancada vazia e pedras), 109, 4260 `{result true}` | *(cliente)*; ordem e recusa *(dedução)* |
| 8644 PayTypeMsg | reforço de equipamento de mascote (`PetEquipStrengView`, Light of Magic 3250101 e Glint of Magic 3260101, resposta 4558); o equipamento de mascote não existe: recusa sem resposta | — | *(cliente)* |

Login: 4184 ItemSmithyMsg com todos os Ids de `ComposeTempInfos` *(visto)*.
Atributos: o equipamento reforçado soma `int(base×g×0.1) + g×5` em cada atributo > 0
(`GoodsHelp.getStrengthenAddition`), mais os 5 `randomSkill` (`SkillPropertyTempInfos`) e as pedras.

Simplificações (`# ponytail:`): o refino sorteia uniforme entre os atributos com `Grades` > 0 (a tabela não está no cliente); a compra das pedras que faltam (`REFRESH_BUY`, desligado no `SwitchInfo`) não existe: falta pedra, recusa; o sorteio pendente fica na memória até o 8339; `autoBuy` na composição é recusado.
Falta para o peso: captura 8336 → 4258 com itens de `NeedGrades` baixo e alto. Nas capturas o valor sobe com o item (NG 1–8: +2 a +21; NG 40–48: +16 a +171), mas são 42 amostras: correlação, não tabela.

## Moda — `fashion.py`

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5008 HeroHideFashionReqMsg | `hide` 1 esconde, 2 mostra, 0 só pede a aparência | 149 HeroEquUpdatedMsg para todos | *(cliente)* `ArmySocketOutManager` |
| 8625 (vazio) | livro de moda; antes ativa as modas vinculadas que o jogador tem | 4542 FashionMsg `{info[{tempId, isSwitch, appraisalSkill}], fashionIds[]}`; `fashionIds` = todas as 1388 modas (MasterType 1, SonType 109–112) | *(visto)* |
| 8595 FashionMsg `{templateId}` | provador (`FashionSwitchView`, um por parte): a moda vestida no líder com o mesmo SonType passa a ser esse modelo. Recusa (sem resposta) modelo fora do livro (`tipData02`), sem moda vestida no espaço (`tipData01`) ou igual à vestida (`tipData03`). Sem custo. As roupas do casamento (`MarryUIMediator`) não estão no livro: recusadas | 3, 150, 115 da peça | *(cliente)*; a peça trocar de modelo *(dedução)* |
| 8631 FashionMsg | apaga o ícone de "novo": grava `isSwitch` | 4542 | *(cliente)* `FashionSwitchItem` |
| 8781 FashionMsg | avaliação: sorteia `appraisalSkill` por tabela desconhecida; recusa. O cliente inglês dá só a trava e o custo: nível 27, `appraisalSkill` abaixo do Grades 5; a primeira custa `Property1` de ouro, a renovação `Property2` Fashion Cores (208020); taxa mostrada [0, 20, 30, 40, 50, 60][`TransformId`] | 4542 como está | *(cliente)* |
| 8594 StoreReqMsg `{operate, payType}` | compor moda na bancada: o resultado (que peça e nível ficam, o `randomSkill1` novo, a chance real e o que a falha tira) não está no cliente nem nos templates; recusa. O que o `FashionComposeView` inglês dá: as duas peças na bolsa 0 (posições 0 e 1, pelo 5005), mesmo SonType (109–112) ou uma delas o Fashion Core 208020 (duas Cores não); nível = `Grades` do `randomSkill1` (ou da 1ª `DefaultSkill`), 0 não compõe, 9 é o teto; ouro (nível1 + nível2) × 10000; 1 Core (5 nas asas); Good Luck Charm 208021 (`operate`): 2^(nível − 2) (× 5 nas asas), só com níveis iguais entre 2 e 8, o que falta a 395 Balens (`payType` 0 aceita vinculados); o resultado vem vinculado; texto da chance pela diferença de nível: 0 Fair (100% com o Charm ou nível 1), 1 Medium, 2 Poor, 3+ Abysmal | 4487 StoreRspMsg `{composeResult false}` (o `FashionBag` ignora); no sucesso o cliente lê `pos`, `objectId` e `bagType` da peça e pede o 8625 | *(cliente)* |

Login: 4542 depois dos itens *(visto)*. Livro (`FashionBook`): a moda entra ativada com `isSwitch` false (ícone de "novo") ao ser vestida ou, se vinculada, no próximo 8625 ("New bound clothing will automatically be activated when it is obtained"). Compra de moda: 8592, na loja.

## Moeda premium e `cash_ledger`

`services/cash.py`: `pay(c, total, pay_type, reason, ref, now, gift_ok)` debita (vinculado primeiro
com `payType` 0 quando o preço aceita) e devolve o `CashLedger`; `change(...)` para créditos e GM.
Quem chama passa o registro para a mesma `CharacterService.save` da operação. `reason` em uso: `shop`
(loja e misteriosa), `bag` (5010), `rental_bag` (8819), `item` (Balens vindos de item). Ouro não grava.

Os outros gastos de Balens passam por `services/ledger.pay` (vinculado primeiro quando o `payType` aceita) e gravam na mesma `save`: `pawn_change` (8580), `teleport` (8326), `skill_reset` (5184), `second_skill` (8479), `rune_exp` (runa com diamante), `pet_slots` e `pet_reset` (8621), `star_bag` (8270), `mount_train` (8529), `fate_turn` (8627), `arena_count` (8253) e `arena_cool` (8265, grátis com VIP), além de `order_quick` (5172) e os de eventos, VIP, correio e minigames.

## Dependências de outros sistemas

- Correio: presente para outro jogador (result 2) e compra com mochila cheia (o oficial manda pelo correio).
- Guilda: preço em `ConsortiaOffer`, `NeedConsortiaLevels`, itens 203/8.
- VIP: `NeedMinVip`, limites `VIP1Count`..`VIP6Count`, itens 203/12.
- Ofertas por tempo (4238): feitas (`game_settings.shop_offers`, migração 0053, 53 ofertas de oficial_encantar #57-#58).
  `currentCount` = unidades vendidas neste servidor (`purchases` `source` `offer`), no login e no 4375 que vai a
  todos a cada compra, com a oferta inteira (visto: oficial_encantar #2640-#2666, compras de outros jogadores); o
  `maxCount` (-1 em todas) limita o total. Faltam o rodízio (`type` 2, 8632) e compra coletiva (`type` 3, 8645) sem nenhuma oferta desses tipos.
- Conquistas: títulos (8597).
- Casamento: `saveBook` (8595) com as roupas do `MarryQualityTempInfo`.
- Campanha em grupo: o gasto da entrada (4240), ver [salas-campanha.md](salas-campanha.md).
- Mascote: bags 22–26 e cadeado opType 2.
