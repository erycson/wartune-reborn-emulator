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
o tira) e pelo mercado ([mercado.md](mercado.md)), posição 0. Não são movíveis pelo 5005. Os bags 6
(guilda), 22–26 (mascote) e 32 (depósito) dependem de sistemas que não existem e são recusados no 5005.

Item novo: equipamento nasce com `Property1` furos abertos (`join` 0); os outros furos ficam −1
(fechado) *(visto)*. `randomSkill_1` = `DefaultSkill` (o sorteio do oficial não está nos templates). *(visto)* o Kronos’un Yetkisi (1991017, `RandomSkillCount` 5) comprado na loja do labirinto chegou no 115 com `join_1` 0 e cinco `randomSkill` (70407, 71123, 70509, 70719, 70209); aqui sai só o `DefaultSkill`. Falta a regra do sorteio.

## Mochila e uso — `items.py`

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5005 ItemReqMsg | move entre os bags 0–4; destino ocupado: empilha (mesmo item, mochila/bancada) ou troca (o outro precisa caber na origem). Da bancada para a mochila o cliente manda `endPos` 0: o servidor escolhe o primeiro livre. Vestir moda pela primeira vez põe no livro (4542) | 3, 150, 115 origem, 115 destino (+4542) | *(visto)* ordem; validações *(cliente)* |
| 5006 ItemUseMsg | 298 pacote: troca pelo `GradeDrop`; 203 recurso: Property1 1 ouro, 3 elmas, 4 elmas vinculado, 5 Beden (até `weary_limit`), 6 prestígio, 7 EXP, 10 Ruh × Property2 × `count`; **15 entrada de campanha em grupo** (Büyük Sefer: `times` = Property2 × `count`, ver salas-campanha.md); 206 caixas de pedras (`GEM_BOX_LEVELS`, ids 2060008 a 2060020): pedra aleatória do nível (`TransformInfos`); 209 poção de HP: `blood` += Property1 | 203: 115, 111 "Tebrikler! Kazanılan:Altın x1000", 109 (ouro) ou 3 (+83 "5,000 EXP kazanıldı" na EXP); 206: 115, 115, 111, 3, 83; 15: 115, 4240, 111, 3; 209: 115, 113, 150, 3 | *(visto)* |
| 5007 ItemReqMsg.beginPos | vende a pilha toda | 115, 109 | preço `GoodsHelp.getSellGold` *(cliente)* |
| 8624 ItemSellReqMsg | venda em lote (pos, count) | 115, 109 | *(cliente)* |
| 8220 ArrangeReq | aplica a ordem que o cliente calculou (`BaseBagListView.sort`: cada item `oldplace`→índice), sem colisão nem fora da mochila; `isStackItem` junta pilhas incompletas (mesmo item e mesmo cadeado) e fecha os buracos | 115 com a mochila | *(cliente)*; pilhas *(dedução)* |
| 8346 ItemRemoveMsg `{bagType, pos}` | tira item vencido: o servidor confere `validDate`/`beginDate` e apaga (ainda válido: ignora). Bolsa do herói: também 3 e 150 | 115 com a posição vazia | pedido *(cliente)* `BaseBagListView`/`EquipBagII`; resposta *(dedução)* |
| 8809 LockAndUnlockMsg | opType 1 mochila, 3 equipamento, 4 medalha: alterna `isLocked`. Item travado não é vendido nem usado | 115 | *(cliente)* |
| 8484 ItemUseStoreReqMsg | gasta `count` Şeytan Kristali (208014, Property1 = EXP) no cristal: `storeGp` e `storeGrade` (`UpGradeTempInfos` Types 15, `Data` = total) | 115, 3 | *(cliente)* |
| 5010 PayTypeMsg | compra `property1` linhas de 7 espaços (até 175); linha i custa (i+1)×10 elmas até a 10ª, depois 100 (`BagBuyFrame`) | 3 (`bagCount`) | *(cliente)* |
| 8819 RentalBagOpReqMsg | aluga a mochila de 217 por `param2` dias (`rental_bag_day_cost` × 2 páginas), `param1` = payType; renovar soma ao prazo | 3, 4709 `{opType, rentalBagTime, status 1}` | *(cliente)* |
| 8199 DetailReqMsg | ficha de outro jogador (online ou do banco): equipamento do líder, atributos, `hideFashion`, `storeGrade`, `appellId` | 4125 DetailRspMsg | *(cliente)* `PlayerInfoFrameII` |
| 5129 CampaignReqMsg | baú caído na campanha: os drops de campanha não existem | 4268 BattleReportMsg `{signId}` vazio (o cliente limpa o nó) | *(cliente)* `CampaignMapController` |

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

Poção de HP e Bağlı Elmas/Elmas vindos de item gravam o `cash_ledger` com `reason` `item`.
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
| 5006 → 115, 110 `PropertyUpdatedMsg{propertyType = PropertyType1 do efeito, value = grau}`, 4188 `ItemBufferRspMsg{templateId = efeito, validityDate = minutos restantes, grade, type 2, typeTemplateid = item, isCancel false}`, 3 (sem texto) | liga o efeito | *(visto)* captura turca `exp_kitabi_kullanim_kahraman_sarayi...` #2-#10, 2013002: `{30, 100}` e `{2030, 60, 100, 2, 2013002}` (o 4902/150/4434 no meio são de outros sistemas) |
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
com elmas; 1 só elmas. Preço em `Point` só aceita elmas. Lojas de pontuação (ShopType 8, 13, 15, 20)
ficam sem suporte.

`BuyInfo.result` *(cliente, `ShopManager`)*: 1 ok, 2 jogador ausente (presente para outro: depende
do correio), 3 item, 4 sem dinheiro (silencioso), 6 limite do dia (`VIP0Count`), 7 VIP, 8 item
inexistente / oferta, 9 nível de guilda, 10 nível, 11 falhou (mochila cheia; o oficial manda pelo
correio, 12).

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5154 ShopMsg | compra (o registro decodifica como FashionShopMsg; o handler relê como ShopMsg) | 3 ou 109 (ou 115 da moeda-item), 115 do item, 111 e 83 "{nome} x{n} başarıyla alındı!", 90 ShopMsg `{buyInfo + result}` | *(visto)* |
| 8592 FashionShopMsg | compra de moda, uma ou várias | o mesmo por item (90 cada) e 4486 `{result}` no fim | *(cliente)* `FashionAllBuyFrame` |
| 5633 ShopMsg | compra e usa a poção de HP (ShopType 100) | 109/3, 113 `{heroId, hp, blood, bloodId}`, 170 `{result, templateId}` | *(visto)* |
| 8218 | compras de hoje | 4145 `hasDataInfo[{userId, itemId, counts, buyDate}]` | *(visto)* |
| 8693 ShopMsg | quantos daquele item já comprei hoje | 4599 `buyInfo.count` | *(cliente)* |
| 8632 | ofertas relâmpago: vêm do 4238 (eventos do operador), nenhuma ativa | 4547 `{refreshDate}` vazio | *(cliente)* |
| 8645 ShopMsg | compra coletiva: só existe com uma oferta type 3 do 4238; recusa sem resposta | — | *(cliente)* |
| 8483 ShopFreshReqMsg | loja misteriosa (ShopType 5): lista; `isButton` atualiza pagando `ShopFresh_NeedDiamond` (10). Os itens trocam sozinhos 14400 s depois do `freshLastdate` (`MysteryShopModel.remainTime`, que pede a lista de novo ao zerar); as compras do dia zeram na virada das 5h | 3, 4384 `{itemId[], freshLastdate, isCanBuy[], buyCount, maxBuyCount}` | *(cliente)* |
| 8482 ShopItemBuyMsg | compra o item `index` da misteriosa (uma vez cada, até `ShopBuy_MaxCount` 20 por dia) | 3/109, 115, 111, 83, 4383 `{result, buyCount}`, 4384 | *(cliente)* |
| 8597 AppellExchangeMsg | `look`: títulos (vazio); trocar exige ter o título (conquistas não existem); `appellId` 0 tira o título | 4484 AppellsMsg | *(cliente)* |

Misteriosa: 8 itens sorteados pelo peso `Rands` entre os do nível do jogador; troca sozinha uma vez
por dia (`# ponytail:`, a tela não está no cliente decompilado). Limite diário por item em
`shop_buys` (zera quando muda o dia).

Loja do labirinto (ShopType 4, 119 linhas, todas com preço só em `MazeCoin`): paga com Labirent Parası (208009). *(visto)*
`yeralti_labirent_marketi_alisveris`: o 105 (Altın Kutusu, 1 moeda, andar 5) tirou 1 (118 → 117) e o 110 (Kronos’un
Yetkisi, 25 moedas, andar 15) tirou 25 (117 → 92). A resposta é a da loja comum: 115 da moeda, 115 do item, 111, 83 e 90
(o 4476, 4426 e 4484 da mesma captura são de outros sistemas, não da compra). O andar (`MazeLayers`, `MazeLayers2`): o
cliente esconde o botão quando o andar passa de `towerInfo1.maxIndex` (`GoodsItem.as:380`) ou de `towerInfo2.maxIndex`
(`:384`). O servidor manda `maxIndex` 60 fixo no 4205 (`MAZE_MAX_INDEX`) e nunca manda o segundo labirinto; por isso
recusa (`FAIL`, *(dedução)*) os 23 produtos com `MazeLayers` > 60 e os 22 com `MazeLayers2` > 0. Isso **não é o progresso
do labirinto**: todos os 4205 das capturas têm `maxIndex` 60 (com `towerIndex` 1, 2, 3 e 5), e a compra do andar 15 foi
feita entre um 4205 com `towerIndex` 3 e outro com 5. Falta: o `maxIndex` que o oficial manda depois de avançar no
labirinto (captura de 4205 com o labirinto mais fundo).

## Forja — `forge.py`

O cliente põe o equipamento na bancada (5005 para o bag 0, pos 0) e manda a operação.

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5150 (vazio) | reforço: taxa `clamp(100 − g×10, 10, 100)` + Property1 da pedra da sorte (bancada pos 1, SonType 204); ouro `NG≥80 ? (NG/10+1)²×P×(g+1)^2.1×10 : 1.5^(NG/10+1)×(P+1)×(g+1)^2.2×5+500`; até `StrengthenMax`. A pedra vai mesmo na falha e o nível não cai | 115 da pedra, 109, (115 do item no sucesso), 86 StoreRspMsg `{strengResult, strengthenGrade}` | *(visto)* falha; fórmulas *(cliente)* |
| 5151 StoreReqMsg `{mountPos, bagType, bagPos}` | engasta a pedra (SonType 205) no furo aberto; furo ocupado troca e cobra o Property3 da antiga, que volta para a mochila; nunca duas do mesmo atributo (Property1) | 109, 115 da pedra, 115 do item, 111/83 "Başarıyla mozaik yapıldı!" | *(visto)* |
| 5152 StoreReqMsg `{holePos, operate}` | true: abre o furo com 1 Elmas Delici (208004); o 4º só em item Profile 5. false: tira a pedra (Property3 em ouro) e devolve | abrir: 115, 115; tirar: 109, 115, 115, 111 "Başarıyla söküldü!", 83 "…Kazanılan:{pedra} x1!" | *(visto)*; abrir *(cliente)* |
| 5153 StoreReqMsg `{composeId, composeNum}` | receita `ComposeTempInfos` (Material1–4 × Count × n, NeedGold × n, NeedMinLevel) | 115, 109, 115, 111 "Kazanılan:{nome} x{n}", 89 `{composeResult false, composeTemplateId −1}`, 83 | *(visto)* |
| 8538 StoreReqMsg `{srcItemid, desItemid, count}` | troca pedras do mesmo nível (`TransformInfos`, CostGold × count) | 115, 109, 115, 111/83 "Dönüşüm başarılı" | *(visto)* |
| 8336 SmithFreshReqMsg `{lock[]}` | sorteia os atributos do item da bancada gastando 1 pedra de refino (`Refresh`), `RandomSkillCount` atributos; travados mantêm. Pool: `SkillTempInfos` 70000–77199 com `Grades` > 0 e `SkillPropertyTempInfos` (1584 de 2157) | 115, 4258 `{randomSkill[]}` | *(cliente)*; pool *(visto)*: os 42 atributos das capturas têm `Grades` 1–10, nenhum 0 (0 = placeholder: +0 com 500000, "Asker Miktarı"); peso *(dedução)* uniforme |
| 8339 (vazio) | aplica o último sorteio | 4259 `{result}`, 115 | *(cliente)* |
| 8464 RefreshPropertyReqMsg `{itemId}` | atributos sorteados do item (o pendente, se houver) | 4368 `{randomSkill[], lockPos[], result}` | *(dedução)* |
| 8340 (vazio) | decomposição: sem chamador no cliente decompilado (`sendResolve`) e sem tabela de produtos nos templates; falta captura | 4260 `{result false}` | *(cliente)* |
| 8644 PayTypeMsg | moldagem: os materiais 2120100–2120103 não existem nos templates; recusa sem resposta | — | *(cliente)* |

Login: 4184 ItemSmithyMsg com todos os Ids de `ComposeTempInfos` *(visto)*.
Atributos: o equipamento reforçado soma `int(base×g×0.1) + g×5` em cada atributo > 0
(`GoodsHelp.getStrengthenAddition`), mais os 5 `randomSkill` (`SkillPropertyTempInfos`) e as pedras.

Simplificações (`# ponytail:`): o refino sorteia uniforme entre os atributos com `Grades` > 0 e os cadeados são de graça (tabela e custo não estão no cliente); o sorteio pendente fica na memória até o 8339; `autoBuy` na composição é recusado.
Falta para o peso: captura 8336 → 4258 com itens de `NeedGrades` baixo e alto. Nas capturas o valor sobe com o item (NG 1–8: +2 a +21; NG 40–48: +16 a +171), mas são 42 amostras: correlação, não tabela.

## Moda — `fashion.py`

| C>S | o que faz | S>C | fonte |
|---|---|---|---|
| 5008 HeroHideFashionReqMsg | `hide` 1 esconde, 2 mostra, 0 só pede a aparência | 149 HeroEquUpdatedMsg para todos | *(cliente)* `ArmySocketOutManager` |
| 8625 (vazio) | livro de moda | 4542 FashionMsg `{info[{tempId, isSwitch, appraisalSkill}], fashionIds[]}`; `fashionIds` = todas as 1388 modas (MasterType 1, SonType 109–112) | *(visto)* |
| 8595 FashionMsg / StoreReqMsg | `templateId` = `saveBook`, só usado pelas roupas do casamento; vazio = troca na bancada, regra fora do cliente decompilado: recusa | — | *(cliente)* `FashionManager`, `MarryUIMediator` |
| 8631 FashionMsg | apaga o ícone de "novo" (estado só do cliente) | — | *(cliente)* |
| 8781 FashionMsg | avaliação: sorteia `appraisalSkill` por tabela desconhecida; recusa | 4542 como está | *(cliente)* |
| 8594 StoreReqMsg `{operate, payType}` | compor moda na bancada (curinga 208020): regra desconhecida | 4487 StoreRspMsg `{composeResult false}` (o `FashionBag` ignora) | *(cliente)* |

Login: 4542 depois dos itens *(visto)*. A moda entra no livro na primeira vez que é vestida
*(dedução)*. Compra de moda: 8592, na loja.

## Moeda premium e `cash_ledger`

`services/cash.py`: `pay(c, total, pay_type, reason, ref, now, gift_ok)` debita (vinculado primeiro
com `payType` 0 quando o preço aceita) e devolve o `CashLedger`; `change(...)` para créditos e GM.
Quem chama passa o registro para a mesma `CharacterService.save` da operação. `reason` em uso: `shop`
(loja e misteriosa), `bag` (5010), `rental_bag` (8819), `item` (elmas vindos de item). Ouro não grava.

## Dependências de outros sistemas

- Correio: presente para outro jogador (result 2) e compra com mochila cheia (o oficial manda pelo correio).
- Guilda: preço em `ConsortiaOffer`, `NeedConsortiaLevels`, itens 203/8.
- VIP: `NeedMinVip`, limites `VIP1Count`..`VIP6Count`, itens 203/12.
- Eventos do operador (4238): descontos, ofertas relâmpago (8632), compra coletiva (8645).
- Conquistas: títulos (8597).
- Casamento: `saveBook` (8595).
- Campanha: drop dos baús (5129). Campanha em grupo: o gasto da entrada (4240), ver [salas-campanha.md](salas-campanha.md).
- Mascote: bags 22–26 e cadeado opType 2.
