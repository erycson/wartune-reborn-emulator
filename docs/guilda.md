# Guilda (consortia)

Código: `game/guild.py` (estado e mensagens), `game/handlers/guild/` (gestão: `info`, `members`, `upgrades`, `altar`, `box`, `election`; ajudantes em `common`),
`game/handlers/guild_events.py` (altar, guerras), `game/handlers/fam.py` e `game/fam.py` (terra secreta). Testes: `tests/game/test_guild.py`.

Fontes: *(visto)* captura e índice; *(cliente)* arquivo `.as` (m2 = `D:\wartune\decompiled\m2`, m6 =
janelas da guilda decompiladas do CDN, ver [ferramentas.md](ferramentas.md)); *(dedução)* sem fonte
direta.

## Estado

A guilda, os membros, as candidaturas/convites, os eventos e o baú ficam em tabelas próprias
(`consortias`, `consortia_members`, `consortia_invites`, `consortia_events`, `consortia_items`,
migração `0003`) e na memória em `Guilds` (`GameContext.guilds`, carregado no início).

Motivo: o chefe aceita, expulsa ou promove quem está online. Se isso mexesse no `Character` da
outra sessão, o próximo `save` dela gravaria o objeto antigo por cima. No `Character` fica só o que
o próprio jogador muda: contribuição (`consortia_offer`, `consortia_total_offer`), os seis níveis
de habilidade, `is_auto` e `last_out_consortia`. Itens para outro jogador (baú) entram no snapshot da
sessão dele se estiver online, ou no snapshot carregado do banco se estiver offline, e tudo vai numa
gravação só. O prêmio da bênção pendente fica na linha do membro (`consortia_members.bless_item`,
migração `0018`), não na memória.

Todo handler valida e muda a memória sem `await` no meio, e grava tudo numa `characters.save`. O
baú lê as mochilas dos destinatários offline antes de validar (só leitura). A criação grava com
`characters.write`, porque o membro precisa do id da guilda, e só põe a guilda na memória depois
do commit; as candidaturas dele saem da memória antes do `await` (outra guilda não o aceita no
meio). O baú, depois das leituras, troca pelo snapshot da sessão quem logou enquanto lia.

## Regras do cliente

- **Cargos** 1 chefe, 2 vice, 3 ancião, 4 e 5 membros. Os direitos são bitmaps copiados do 4137
  oficial *(visto)* `login.json #116` (só turco: `login`), bit `i-1` LSB primeiro (`BitArray.getBit`, m2). Índices usados:
  1 chefe (e correio de guilda), 2 pesquisa, 3 melhoria/abrir altar, 4 avisos, 5 expulsar, 9 aceitar,
  convidar e `openApp` (todo botão de convite do cliente inglês usa o 9), 18 renomear, 19 cargos, 30 descrição, 33 recusar *(cliente)* m6 `ConsortiaStaffPage`,
  `ConsortiaPlayerMenu`. Só o chefe tem o 3; o vice tem o 2.
- Criar e se candidatar: nível 12; criar custa 200000 de ouro; nome único sem diferença de caixa
  *(cliente)* m6 `CreatConsortiaFrame`.
- Sair por conta própria (`isAuto`) dá 24 h de espera (`lastOutConsortia`); `isPay` paga
  `Consortia_ClearCD_Point` (395 no template) diamantes. Ao sair, `clear_CDType` 1 paga com o item 208013 ou os mesmos
  `Consortia_ClearCD_Point` diamantes para não ter espera *(cliente)* m6 `ConsortiaStaffPage.exitCallback`.
- O chefe só sai sozinho; aí a guilda acaba.
- Máximo 10 candidaturas. Vagas: `levels*20+10` *(cliente)* m6 `ConsortiaItem`.
- Listas 4134, 4139 e 4140 em páginas de 8; busca além do fim volta à 1 com `isReset`.
- 4133 em pedaços com o mesmo `uuid` até somar `totalRows`; membro sem apelido é descartado.
- 4138/164: datas sempre `YYYY-MM-DD hh:mm:ss`; `warnDate` 8 dias ou mais atrás mostra
  "guilda inativa"; `currentDate` é a base da contagem da espera da melhoria.
- **Bênção** (m6 `consortia/view/myConsortia/building/ConsortiaAltarFrame.as` e `consortia/helper/ConsortiaAltarHelper.as`): cada bênção custa `Property1` da contribuição pessoal, e o limite do dia é `Property2` do nível do altar (tipo 3 do `ConsortiaLevelInfos`). A rápida chama `consortiaAltarBless(10)` com VIP 6; o cliente não multiplica custo nem limite pelo 10.

## Opcodes (cliente -> servidor)

| Opcode | O que faz | Responde | Fonte |
|---|---|---|---|
| 5130 | criar (nome de 4 a 10, com caractere fora de 0x00–0xff valendo 2, também no 5148) | 117, 3 e 109 para quem criou; 164 para os membros | *(cliente)* m6 `CreatConsortiaFrame`, m2 `ConsortiaControler` |
| 8213 | buscar guildas | 4139 `ConsortiaSearchRspMsg` | *(cliente)* m6 `ConsortiaSocektSendManager` |
| 8212 | informações | 4138 | *(visto)* `login.json` (só turco: `login`) |
| 8343 | link de guilda do chat | 4267 `ConsortiaLinkRspMsg` | *(cliente)* m2 |
| 8211 | cargos | 4137 com os bitmaps | *(visto)* `login.json #116` (só turco: `login`) |
| 8207 | membros: `strategy` (Daru), `gpOrder` (posição por EXP), `headId`, `isVip`/`vipType` (também offline, pelos `event_states`), `isTeamPlayer` true; `matchWin`/`matchFailed` 0 (**TODO(inventado)**: o coliseu não conta) | 4133 em pedaços | *(visto)* `login.json` (só turco); oficial_20261023-171155-1 #4572 |
| 8210 | eventos | 4136 | `remark` em partes separadas por `|`, montadas pelo tipo do `ConsortiaEventItem` (m6): 3 entrou/saiu/fundou, 1 expulsou, 7 chefia, 9 altar, 11 melhoria; o texto de cada parte é *dedução*; os antigos sem `|` viram tipo 0 (migração 0046) |
| 8209 | candidaturas e convites do jogador, a mais nova primeiro; `createDate` e `inviteDate` = dia da candidatura às 00:00:00 | 4135 | *(cliente)* m2; *(visto)* oficial_20261023-171155-1 #4253, #4259 |
| 5135 | candidatar-se | 35 `{applyId}`; 4266 para quem pode aceitar | *(cliente)* m2 `__joinConsortiaHandler` |
| 5141 | apagar candidatura | 36 | *(cliente)* m2 |
| 8214 | candidatos da guilda | 4140, `parameter1` = id da candidatura; sem o direito 9 (recrutar), `totalRows` 0 | *(cliente)* m6; *(visto)* oficial_20261023-171155-1 #5132 |
| 5134 | aceitar/recusar candidatura (direito 9/33) | 40; 3, 150, 117, 111 "Congratulations! You have joined Guild  [nome]." e 4266 para quem entrou; 83 canal 5 type 5 "… has just become the guilds newest member!" aos membros; 164 | *(visto)* oficial_20261023-171155-1 #4561–#4567 |
| 5149 | abrir/fechar candidaturas | 164 | *(cliente)* m6 |
| 5142 | convidar (direito 9) | 41 para o alvo online sem guilda e de nível 12+; alvo com "recusar convites" (8286) ligado: nada, sem aviso ao convidante (só log) | *(cliente inglês)* m6 `ConsortiaRecruitFrame` (`grades >= 12`, sem guilda, `getRightsByIndex(9)`); o bloqueio pelo 8286 é *(dedução)*: no cliente o `refuseInvite` (SettingFrame, C_ROOM_REFUSE) é dos convites de pesca, estrada e caça-níquel |
| 8197 | convite automático no nível 15 | 41 | *(cliente)* m2; ponytail: o oficial tinha guildas-robô, aqui é a guilda aberta com mais membros |
| 5143 | responder convite | 37 `{result, applyId}` antes de apagar; 3, 150, 117, 111 "Congratulations! You have joined Guild  [nome]." e 4266 para quem entrou; 83 canal 5 type 5 "… has just become the guilds newest member!" aos membros; 164 | *(visto)* #4561–#4567 (entrada por candidatura; o convite segue igual, dedução) |
| 5146 | sair | 117 com id 0, 3; 115 se gastou o cartão | *(cliente)* m6 `ConsortiaStaffPage` |
| 5132 | expulsar (direito 5, cargo menor) | 117 id 0 para o expulso; 164 e o 83 canal 5 "<link> kicked <link>" aos que ficaram | *(cliente)* m6; *(visto)* oficial_20261023-231733-1 #4448-#4449 |
| 5131 | passar a chefia | 164 (o antigo vira 5) | *(cliente)* m2 `refreshChairman` |
| 5137 | mudar cargo (direito 19) | 50 `{otherId, positionId}` para os membros | *(cliente)* m2 |
| 5139, 5140, 8544 | aviso, descrição, aviso do grupo (o 8544 pelo direito 3: `ConsortiaGroupChatFrame` mostra o "Update" com `getRightsByIndex(3)`) | 164 | *(cliente)* m6 |
| 5148 | renomear (direito 18, 1000 diamantes, `cash_ledger` `guild_rename`) | 49, 3, 164; 3 para os membros | *(cliente)* m6 `ConsortiaRenameFrame` |
| 5144 | contribuir | 109, 3, 111 "Contribution Submitted!", 4152 (1ª do dia), 150, 42, 164, 83 (devoção) | *(visto)* oficial_20261023-171155-1 #4951–#4974, #5028–#5036 |
| 8208 | ranking de contribuição | 4134 (`selfOrder` 0 sem contribuição no período) | *(visto)* `birlik_katkisi...json` #5; oficial_20261023-171155-1 #4949 |
| 5133 | melhorar prédio (1–5) / pesquisar habilidade (6–12) | 164 | *(cliente)* m6 `ConsortiaUpgradeFrame`; templates `ConsortiaLevelInfos` |
| 8545 | acabar a espera da melhoria | 3, 164 | *(cliente)* m6 |
| 5147 | aprender habilidade | 3 (contribuição já debitada, nível antigo), 110 `{propertyType 3, value bônus}`, 150, 3, 111 "Successfully learned skill!" | *(visto)* oficial_20261023-171155-1 #5045–#5051 |
| 8215 | info do altar | 4141 (bênçãos usadas hoje), 4142 prêmio pendente | *(cliente)* m2 `__refreshAltarInfo` |
| 8217 | casas da roleta | 4144 `site[]` (`DropViewInfos.Site`), embaralhadas a cada abertura; o 5145 usa a mesma ordem | *(cliente)* m2 `ConsortiaDropTemplateCate`; *(visto)* oficial_20261023-171155-1 #5151 (2,1,4,5,8,7,9,6,3,10); *(dedução)* ordem nova a cada 8217 |
| 5145 | bênção | 45 `{blessLeftTime, blessSite, blessTempId, blessCount}`; `blessSite` = posição no 4144, -1 = nada; o prêmio fica no membro até o 8216; 83 canal 2 para todos: "Congratulations to <jogador> for obtaining <item> x1 from Guild Blessing!" | *(cliente)* m2 `__getAltarBlessInfo`, m6 `ConsortiaAltarFrame`; *(visto)* o 83 de outros jogadores em oficial_encantar #1723/#1749/#2377/#2383 e 231733 #3250 (o turco buyuk_hp_iksiri #2 é o mesmo); *(dedução)* todo prêmio é anunciado |
| 8216 | pegar o prêmio da bênção (sem espaço livre: 4143 `result` falso e o prêmio fica) | 115, 4143 `{result}` | *(cliente)* m2 `__addFreshItem` |
| 8577 | baú | 4466, sempre com a linha do 2060044 (count 0 se não há) | *(visto)* `birlik_katkisi...json` #4; oficial_20261023-171155-1 #4947, #5005 |
| 8579 | membros para distribuir | 4465 | *(cliente)* m6 |
| 8578 | distribuir (chefe) | 115 para quem está online e tem espaço; 148 quando vai pelo correio (*dedução*); 4466 | *(cliente)* m6 |
| 8241 | eleição: candidatos | 4389 | *(cliente)* m2 `__setVotingUsers` |
| 8481 | votar (contribuição total 100+) | 4390 `{result}` | *(cliente)* m2; o 100 é do `chairmanElection.help` inglês |
| 8205 `sendType` 2 | correio de guilda (chefe, para membros) | 148 para cada um, 3 | *(cliente inglês)* m6 `ConsortiaEmailGroupSendView`: 175 Balens, `payType` 0 gasta os vinculados primeiro; `cash_ledger` `guild_mail` |
| 8335 | anúncio de recrutamento (direito 9; 5 por dia, volta às 5h; até 54 caracteres) | 83 no canal mundo, `type` 2 com `consortiaId`/`consortiaName` ("[guilda]，Recruit Members" clicável + texto) a todos; 164 com `speakTimes` | *(cliente)* m6 `RecruitMemberFrame`, `ChatFormat`; *(visto)* `speakTimes` 5 (#4944); canal e remetente **TODO(inventado)** |
| 8257 | buscar jogador por apelido | 4170, sem `info` = não achou; fica no sistema social (`handlers/friends.py`), que o correio também usa | *(cliente)* m6 (chefia, recrutar), m2 (correio) |
| 15005 canal 5 | chat da guilda | 83 para os membros online | [chat.md](chat.md) |
| 8541 | abrir o altar do demônio | 4436 `{result: 1, pop}` para os membros, 164 | *(cliente)* m6 `sendOpenDemon`, m2 `ConsortiaManager.__demonSwitchHandler` |
| 8542 | entrar no altar | nada (ver pendências) | *(cliente)* m2 |
| 8549, 8550, 8593 | dentro do altar: chegar no nó, buff, habilidade | nada | *(cliente)* m2 |
| 8537 | entrar na terra secreta (só membro) | 125 {1, 7501}, 140, 21; no 5035 state 4: 127, 21, 21, 4432, 4632, 4453 | *(visto)* oficial_20261023-171155-1 #5056-#5066 |
| 5125 no Invasor (masterType 151) | luta battleType 23 | 140, 131, 128, 157; derrota: 113, 3, 83, 150, 4103, 3, 150, 100, 4122, 140, 4104, 131, 128 state 1, 83; 4382 no 5035 state 4 | *(visto)* #5080-#5117; vitória *(visto, de fora)* 231733 #4104: 83 canal 5 "<link> has defeated an invader and earned 10 guild contribution!" a toda a guilda e 164 com a riqueza +10 (`fam_invader_offer`, 0073); o nó some para todos e só um luta por vez (o usuário; quem chega depois recebe 111 "Target is in battle, please wait…", texto do cliente); **TODO(inventado)** o que o próprio vencedor vê (111/83 "Received: N Contribution") |
| (relógio 20008) | ondas de Invasores a cada 2 h (hora par, `fam.INVADER_HOURS`): os 3 Invasores voltam e sai o 83 canal 5 "The Guild Chamber is under attack! Grab your weapons and drive the invaders away!" a todos os membros online | 83 | *(visto)* 16:00, 18:00 e 20:00 (171155 #4756, 215937 #65, 231733 #4093); shortcut: em memória (`Guilds.invasions`) |
| 5025 / 8747 | sair | 4165, 150, 150, 140, 22, 4595; no 8747 o 83 "Left Guild Chamber" | *(visto)* #5163-#5172 |
| 8565 | invocar a árvore (só o líder, 1 por dia) | 4432 `opreate` 2 a todos os membros online; na sala a árvore e as 21 coletas aparecem (128) | **dedução** do cliente (`ConsortiaSecretInfoView`, `ConsortiaSecretInfo`) e da ajuda |
| 5125 na árvore / numa coleta | energizar (1 por invocação, até `levels × 20 + 10` e `FamTree_WaterMax`) / colher | 4432 e 4453 à sala / 128 state 8, 3, 111, 83 | **dedução**; **TODO(inventado)** o bônus da energia e a contribuição da coleta (`fam_tree`, 0074) |
| 8566 | buff +20% de EXP por `Fam_Buffer_Price` (200) de contribuição, 1 por invocação | 3 e 4453 com o `rate` novo | **dedução** do cliente |
| 20008 na sala | EXP a cada 15 s nos 15 min da invocação | 3 e 83 "Received N EXP " | **TODO(inventado)** a EXP do tique (`fam_tree.exp_per_grade`, 0074) |
| (contribuição da sala) | a coleta e o Invasor contam a missão 29 (contribuição total) com o 112; nenhum `LeedTemp` nem missão fala da sala (as de "Tree of Ancients" são da fazenda) | 112 | templates |
| 8743 | chamar o Master Treasure Thief | recusado: precisa do ranking da Class Wars (entre servidores); o 4632 manda `isCanCall` falso e o botão não aparece | *(cliente)* ajuda da Class Wars, item 7 |
| 8546 | grupos da guerra de guildas | 4441 (guildas, `fightPower`, `isGuildSize`) e 4458 (ordem da semana) | *(visto)* oficial_20261023-171155-1 #5135–#5136; **TODO(inventado)**: as 8 de maior poder agora, sem grupos/resultados, e a "semana passada" = agora (a guerra não roda) |
| 8472, 8477 | desafios e lista da guerra | 4377, 4379 vazios | *(cliente)* m2; o cliente não chama |
| 8471, 8473, 8547 | entrar, montar time, buff da guerra | nada | *(cliente)* m2 |
| 8782 | grupos da guerra entre servidores | 4682 sem `info` (não inscrita) | *(cliente)* m2 `__crossguild_group_ownerHandler` |
| 8779 | inscrição entre servidores | 4682 sem `info` | *(dedução)* |
| 8778, 8783 | time e entrada entre servidores | nada | *(cliente)* m2 |

**Mercado da guilda**: não tem opcode próprio. O cliente compra pelo 5154 genérico
(`ShopManager.sendShoping` *(cliente)* m2; a janela `BuyFrameI` manda o pedido). O handler do 5154
(`handlers/shop.py`) passa primeiro para `handlers.guild.shop_buy(s, buyInfo)` quando o `goodId` é
de `ShopTempInfos.ShopType` 2 (41 linhas no tempinfos; são as únicas com `ConsortiaOffer` ou
`NeedConsortiaLevels`): preço na coluna `ConsortiaOffer`
(contribuição pessoal), `NeedConsortiaLevels` contra o nível do mercado, `NeedGrades` contra o
nível do jogador. A compra certa responde 3, 115, 111, 90 `ShopMsg{buyInfo}`, 83 canal 3 *(visto)*
`birlik_katkisi...json` #60 (goodId 19, 2040106, 40 de contribuição; só turco: `birlik_katkisi`). A recusa responde só 90 com
`buyInfo.result`: 9 sem guilda ou nível do mercado baixo, 10 nível do jogador, 2 presente para
outro jogador (exige gravar outro personagem), 3 quantidade ou item, 4 contribuição, 11 mochila
(`ShopManager.shopingResult` *(cliente)*; o 0 não tem texto lá, por isso não é usado). A mochila é a da loja comum (`bag.fits`/`bag.add`): espaços comprados contam
e a compra empilha. Atenção: o
5154 tem dois nomes em `opcodes.json` (`FashionShopMsg`, `ShopMsg`) e o registro decodifica pelo
primeiro.

**8699 não é da guilda**: só o tutorial manda (m8 `sendEnterCollectionBattle`).

## Contribuição, melhorias e habilidades

- 1000 ouro = 1, 5 Balens = 1 *(cliente inglês)* `ConsortiaContributeFrame` (`/ 1000`, `/ 5`, "Contribution
  minimum:5 Balens"); os dois arredondados para baixo e só se gasta o que vira contribuição *(visto)*:
  −1000 → +1, −55000 → +55.
  Vai para a riqueza (`offer`/`totalOffer`) da guilda e a contribuição do jogador; `todayOffer`
  zera por dia. Os Balens vinculados vão primeiro (`useBindPoint`: "Use Bound Balens first"). Todo gasto
  de Balens da guilda (contribuição, espera, renomear, acelerar, correio) entra no `cash_ledger`.
- `ConsortiaLevelInfos`: tipo 1 guilda, 2 mercado, 3 altar (`Property1` custo da bênção,
  `Property2` bênçãos por dia), 4 escola, 5 depósito, 6–12 habilidades (6 ataque, 7 defesa sem
  habilidade de jogador, 8 agilidade, 9 inteligência, 10 comando, 11 ouro, 12 físico). Custo
  `NeedOffer` da riqueza; requisito `PreTemplateId` (o nível daquela linha no tipo dela).
- O nível sobe na hora; `CodeTime` (só prédios) trava a próxima melhoria. O cliente calcula
  `codeNeedDate - (currentDate - codeBeginDate)`. Acabar já custa 1 diamante a cada 10 min.
- Aprender (5147) custa a contribuição pessoal `NeedOffer` do nível seguinte e não passa do nível
  pesquisado pela guilda. O bônus é o número do `Description` do nível ("Strength +40 (Hero)"), somado no
  próprio herói (`rules.guild_skills` → `HeroStats.of(base=...)`): Strength +40 levou `basePower` de 1 a 41,
  `PhyAttack` +160 e `PhyDefence` +40 *(visto #5048)*. "Gold Production +N%" (tipo 11) multiplica a produção
  de ouro por hora — **TODO(inventado)**: sem captura com esse nível.

## Pendências

**Resolvido nesta rodada**: criar guilda grava guilda, membro, evento e candidaturas numa transação
só (antes eram duas); o prêmio da bênção fica na linha do membro (`consortia_members.bless_item`,
migração `0018`), então reiniciar o servidor não perde o prêmio; altar, prêmio e baú usam a mochila
inteira (`bag.capacity`: espaços comprados contam e o item empilha); item do baú que não cabe na
mochila do membro vai pelo correio, com o nome do item como título (*(dedução)*: o oficial não
mostrou o caso, a loja é a única referência e manda pelo correio).

**Mapas e batalhas das atividades: precisa de captura.** Os quatro mapas existem em `MapInfos`
(nome, tamanho, `MapFileId`) e `Campaigns`, mas os nós não existem em nenhuma das fontes. Conferido
em 2026-10-17 com o decodificador dos `.maps` do CDN (memória `campaign-nodes-in-maps-files`):

| Mapa | Atividade | `MapInfos` | `.maps` (nós com `id` diferente de 0) | Situação |
|---|---|---|---|---|
| 7601 | altar do demônio | 4000×3000, `Campaigns` tipo 8 | 4.591 objetos com dados de campanha, todos com `id` 0 | captura |
| 7501 | terra secreta | 2000×2000, tipo 7 | nenhum objeto de campanha | **feito** pela captura (0073) |
| 4501 | guerra de guildas | 8000×4000, tipo 6 | nenhum objeto de campanha | captura |
| 4601 | guerra entre servidores | 6000×3500, tipo 16 | 41 nós com `id`: 20 carros de guilda, 5 torres, 5 nós de energia e o resto (recursos e outros) | evento fechado (abaixo) |

`MapNodeInfos` e `CampaignData` não têm nenhuma linha para esses quatro mapas. A luta usaria o fluxo
PvE de `game/battle.py` com esses nós; sem eles o cliente carregaria um mapa vazio, sem saída, então
8542, 8471 e 8783 continuam recusados; a terra secreta saiu da captura (0073).

**O que capturar** (uma captura por atividade, de uma sessão completa):

- **Altar (7601)**: guilda nível 5 ou mais, o chefe abre o altar (8541), um membro entra (8542) e
  chega ao fim. Precisa do 125 do mapa 7601, da lista de nós (5125 ou `CampaignNodeList`) com os
  monstros e o altar, e dos pacotes 8549, 8550, 8593, 8264 (reviver), 4437 (relatório), 4448 e 4449.
- **Terra secreta (7501)**: entrada, sala, derrota e saída já vistas. Falta: o líder invocar a árvore (8565) e
  a sala inteira dos 15 min (EXP dos tiques, energizar, buff 8566, coletas) e uma vitória contra um Invasor.
- **Guerra (4501)**: no dia de `Guild_WarDay` (1, 3 e 5) entre 20:00 e 21:00, duas guildas: grupos
  (8546 e 4441), desafios e lista (8472/8477 com 4377/4379), entrar (8471, 125 do 4501), montar time
  (8473), buff (8547) e os pacotes de dentro do mapa.
- **Bênção**: pelo menos 30 bênçãos no altar de nível 10, gravando o 45 e o 4143 de cada uma, para
  ver as 10 casas e a tabela de prêmios. Mais uma rápida (x10) com VIP 6: custo em contribuição antes
  e depois, o 45 e o 4143. Sem isso, a tabela e a forma da resposta do x10 não saem de lugar nenhum.
- **Guerra entre servidores (4601)**: só se o evento reabrir (inscrição 8779 e a resposta 4682 com
  `info`, depois o time 8778 e a entrada 8783).

**Fechado pelo template**: `CrossGuild_TimeOutDate` é 2025-11-14 (fim do ícone) e a inscrição
(`GuildSignOpen`/`GuildSignStop`) foi de 2025-09-16 a 2025-09-20. A guerra entre servidores está
fechada no servidor hoje, por isso 8782 responde "não inscrita". *(dedução)* sobre o estado do evento.

**Custos e horários já nos templates** (`ConfigInfos`), que o próximo que implementar o mapa usa.
A descrição está em chinês; a ligação com o opcode é *(dedução)*:

- `AltarLive_Offer` 50: contribuição para reviver no altar (8264).
- `ConsortiaAltarBufferNeedOffer` 200: buff do altar (8550).
- `ConsortiaAltarSceneNeedOffe_Fix` 10000: travar os monstros da tela (8593).
- `ConsortiaAltarSceneNeedOffe_Live` 10000 e `ConsortiaAltarSceneLive` 20: custo e vida recuperada do altar.
- `Fam_Buffer_Price` 200 e `FamTree_WaterMax` 50: buff da terra secreta e carga diária da árvore.
- `Guild_WarDay` 1,3,5 e `GuildWar_Time` 20:00,21:00: dias e horas da guerra de guildas.

**Prêmio da bênção (5145/8216)**: a tabela do oficial não está nos templates nem nas capturas.
`DropViewInfos` tem só nome e ícone das 10 casas (`pray_001` a `pray_010`); `LeedDrop` (sites 1 a 5) e
`VipDrop` (sites 1 a 9) têm outras casas, não as 10 da bênção; `DistrictDrop` (distritos 101 a 107) não é chamado pelo
cliente; e nenhuma captura tem o 45 ou o 4143. Continua valendo o *ponytail*: o prêmio é sempre um
item do mercado liberado pelo nível do altar, na casa 1.

**Bênção rápida (x10, VIP 6)**: recusada. O m6 (`ConsortiaAltarFrame`) mostra o VIP 6
(`QUICK_BLESS_VIP_GRADE`) e as 10 bênçãos (`QUICK_BLESS_COUNT`, `consortiaAltarBless(10)`). O
`ConsortiaAltarHelper.canBless` confere um custo e o limite diário de uma bênção, e nenhum custo
nem forma de resposta do x10 aparece no cliente. Captura: a seção do altar acima.

**Eleição (8241/8481)**: nada abre a votação, só editando o banco (`voting_state`). A regra está no
`chairmanElection.help` inglês: chefe offline 10 dias abre; candidatos são os vice-chefes online nos
últimos 3 dias (senão os outros cargos); um só vira chefe direto; vota quem tem 100+ de contribuição
(feito), por 3 dias; o chefe voltando encerra. Falta abrir e fechar a eleição pelo relógio. O cliente lê
`isVotingman` como "é candidato", o "já votou" da própria linha (`votingTime > 0`) e só mostra o "Impeach" com
`votingStatic` 3 ou 4; o voto vale nos dois (qual é "votando" e qual é "encerrada" é *dedução*).

**Armazém da guilda (bolsa 6)**: pessoal, `storeLevel*5` espaços (56 no nível 10), pelo 5005 e o 8220; ver
[itens.md](itens.md). **Baú de prêmios**: no máximo 10 por membro (`ConsortiaPrizeAllotItem`); o `isReceived`
vai falso (*ponytail*: quando ele zera não está no cliente) e nada enche o baú (prêmio da guerra de guildas).
**Posição (`orderInfo.gradeOrder`)**: nível e depois riqueza total entre as guildas do servidor (*dedução*).
`fightPower` é a soma do poder dos membros e `fightPowerOrder` a posição por ele (*dedução*; o oficial #4944 tinha
884460 com 99 membros e 1 nas duas posições).

**Sem dado**: guildas-robô
(o oficial tinha, aqui é a guilda aberta com mais membros). Renomear grátis (`same`) vale para o chefe de
uma guilda com "!" no nome (servidores juntados, `ConsortiaFrame.resetConsortiaName`); hoje nenhum nome tem "!".

**Pendente, sem fonte**: sair da guilda antes de pegar o prêmio da bênção perde o prêmio (fica na
linha do membro). O oficial não mostrou esse caso.
