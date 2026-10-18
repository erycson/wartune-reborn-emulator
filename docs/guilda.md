# Guilda (consortia)

Código: `game/guild.py` (estado e mensagens), `game/handlers/guild/` (gestão: `info`, `members`, `upgrades`, `altar`, `box`, `election`; ajudantes em `common`),
`game/handlers/guild_events.py` (altar, terra secreta, guerras). Testes: `tests/game/test_guild.py`.

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
  oficial *(visto)* `login.json #116`, bit `i-1` LSB primeiro (`BitArray.getBit`, m2). Índices usados:
  1 chefe, 2 pesquisa, 3 melhoria/abrir altar, 4 avisos, 5 expulsar, 6 convidar, 9 aceitar e
  `openApp`, 18 renomear, 19 cargos, 30 descrição, 33 recusar *(cliente)* m6 `ConsortiaStaffPage`,
  `ConsortiaPlayerMenu`. Só o chefe tem o 3; o vice tem o 2.
- Criar e se candidatar: nível 12; criar custa 200000 de ouro; nome único sem diferença de caixa
  *(cliente)* m6 `CreatConsortiaFrame`.
- Sair por conta própria (`isAuto`) dá 24 h de espera (`lastOutConsortia`); `isPay` paga
  `Consortia_ClearCD_Point` (50) diamantes. Ao sair, `clear_CDType` 1 paga com o item 208013 ou 50
  diamantes para não ter espera *(cliente)* m6 `ConsortiaStaffPage.exitCallback`.
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
| 5130 | criar | 117, 3 e 109 para quem criou; 164 para os membros | *(cliente)* m6 `CreatConsortiaFrame`, m2 `ConsortiaControler` |
| 8213 | buscar guildas | 4139 `ConsortiaSearchRspMsg` | *(cliente)* m6 `ConsortiaSocektSendManager` |
| 8212 | informações | 4138 | *(visto)* `login.json` |
| 8343 | link de guilda do chat | 4267 `ConsortiaLinkRspMsg` | *(cliente)* m2 |
| 8211 | cargos | 4137 com os bitmaps | *(visto)* `login.json #116` |
| 8207 | membros | 4133 em pedaços | *(visto)* `login.json` |
| 8210 | eventos | 4136 | *(cliente)* m2 |
| 8209 | candidaturas e convites do jogador | 4135 | *(cliente)* m2 |
| 5135 | candidatar-se | 35 `{applyId}`; 4266 para quem pode aceitar | *(cliente)* m2 `__joinConsortiaHandler` |
| 5141 | apagar candidatura | 36 | *(cliente)* m2 |
| 8214 | candidatos da guilda | 4140, `parameter1` = id da candidatura | *(cliente)* m6 |
| 5134 | aceitar/recusar candidatura (direito 9/33) | 40; 117+3 para o candidato; 164 | *(cliente)* m2 |
| 5149 | abrir/fechar candidaturas | 164 | *(cliente)* m6 |
| 5142 | convidar (direito 6) | 41 para o alvo online sem guilda; alvo com "recusar convites" (8286) ligado: nada, sem aviso ao convidante (só log) | *(cliente)* m2; o bloqueio pelo 8286 é *(dedução)*: o botão não tem texto no cliente |
| 8197 | convite automático no nível 15 | 41 | *(cliente)* m2; ponytail: o oficial tinha guildas-robô, aqui é a guilda aberta com mais membros |
| 5143 | responder convite | 37 `{result, applyId}` antes de apagar; 117+3; 164 | *(cliente)* m2 |
| 5146 | sair | 117 com id 0, 3; 115 se gastou o cartão | *(cliente)* m6 `ConsortiaStaffPage` |
| 5132 | expulsar (direito 5, cargo menor) | 117 id 0 para o expulso; 164 | *(cliente)* m6 |
| 5131 | passar a chefia | 164 (o antigo vira 5) | *(cliente)* m2 `refreshChairman` |
| 5137 | mudar cargo (direito 19) | 50 `{otherId, positionId}` para os membros | *(cliente)* m2 |
| 5139, 5140, 8544 | aviso, descrição, aviso do grupo | 164 | *(cliente)* m6 |
| 5148 | renomear (direito 18, 1000 diamantes) | 49, 3, 164; 3 para os membros | *(cliente)* m6 `ConsortiaRenameFrame` |
| 5144 | contribuir | 109, 3, 111, 42, 164 | *(visto)* `birlik_katkisi...json` #15–17, #38–39 |
| 8208 | ranking de contribuição | 4134 | *(visto)* `birlik_katkisi...json` #5 |
| 5133 | melhorar prédio (1–5) / pesquisar habilidade (6–12) | 164 | *(cliente)* m6 `ConsortiaUpgradeFrame`; templates `ConsortiaLevelInfos` |
| 8545 | acabar a espera da melhoria | 3, 164 | *(cliente)* m6 |
| 5147 | aprender habilidade | 3, 150 | *(cliente)* m2 `consortiaStudy` |
| 8215 | info do altar | 4141 (bênçãos usadas hoje), 4142 prêmio pendente | *(cliente)* m2 `__refreshAltarInfo` |
| 8217 | casas da roleta | 4144 `site[]` (`DropViewInfos.Site`) | *(cliente)* m2 `ConsortiaDropTemplateCate` |
| 5145 | bênção | 45 `{blessLeftTime, blessSite, blessTempId, blessCount}`; `blessSite` = posição no 4144, -1 = nada; o prêmio fica no membro até o 8216 | *(cliente)* m2 `__getAltarBlessInfo`, m6 `ConsortiaAltarFrame` |
| 8216 | pegar o prêmio da bênção (sem espaço livre: 4143 `result` falso e o prêmio fica) | 115, 4143 `{result}` | *(cliente)* m2 `__addFreshItem` |
| 8577 | baú | 4466 | *(visto)* `birlik_katkisi...json` #4 |
| 8579 | membros para distribuir | 4465 | *(cliente)* m6 |
| 8578 | distribuir (chefe) | 115 para quem está online e tem espaço; 148 quando vai pelo correio (*dedução*); 4466 | *(cliente)* m6 |
| 8241 | eleição: candidatos | 4389 | *(cliente)* m2 `__setVotingUsers` |
| 8481 | votar | 4390 `{result}` | *(cliente)* m2 |
| 8335 | anúncio de recrutamento | nada (o cliente só deixa com `speakTimes > 0`, sempre 0) | *(cliente)* m6 |
| 8257 | buscar jogador por apelido | 4170, sem `info` = não achou; fica no sistema social (`handlers/friends.py`), que o correio também usa | *(cliente)* m6 (chefia, recrutar), m2 (correio) |
| 15005 canal 5 | chat da guilda | 83 para os membros online | [chat.md](chat.md) |
| 8541 | abrir o altar do demônio | 4436 `{result: 1, pop}` para os membros, 164 | *(cliente)* m6 `sendOpenDemon`, m2 `ConsortiaManager.__demonSwitchHandler` |
| 8542 | entrar no altar | nada (ver pendências) | *(cliente)* m2 |
| 8549, 8550, 8593 | dentro do altar: chegar no nó, buff, habilidade | nada | *(cliente)* m2 |
| 8537 | entrar na terra secreta | nada (ver pendências) | *(cliente)* m2 |
| 8565, 8566, 8743 | dentro da terra secreta: árvore, buff, nó do senhor | nada | *(cliente)* m2 |
| 8546 | grupos da guerra de guildas | 4441 vazio (abre a janela com a entrada desligada) | *(cliente)* m2 `GvgReadyController` |
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
`birlik_katkisi...json` #60 (goodId 19, 2040106, 40 de contribuição). A recusa responde só 90 com
`buyInfo.result`: 9 sem guilda ou nível do mercado baixo, 10 nível do jogador, 2 presente para
outro jogador (exige gravar outro personagem), 3 quantidade ou item, 4 contribuição, 11 mochila
(`ShopManager.shopingResult` *(cliente)*; o 0 não tem texto lá, por isso não é usado). A mochila é a da loja comum (`bag.fits`/`bag.add`): espaços comprados contam
e a compra empilha. Atenção: o
5154 tem dois nomes em `opcodes.json` (`FashionShopMsg`, `ShopMsg`) e o registro decodifica pelo
primeiro.

**8699 não é da guilda**: só o tutorial manda (m8 `sendEnterCollectionBattle`).

## Contribuição, melhorias e habilidades

- 1000 ouro = 1, 1 diamante = 1; o ouro é arredondado para baixo *(visto)*: −1000 → +1, −55000 → +55.
  Vai para a riqueza (`offer`/`totalOffer`) da guilda e a contribuição do jogador; `todayOffer`
  zera por dia. ponytail: os diamantes gastam primeiro os vinculados.
- `ConsortiaLevelInfos`: tipo 1 guilda, 2 mercado, 3 altar (`Property1` custo da bênção,
  `Property2` bênçãos por dia), 4 escola, 5 depósito, 6–12 habilidades (6 ataque, 7 defesa sem
  habilidade de jogador, 8 agilidade, 9 inteligência, 10 comando, 11 ouro, 12 físico). Custo
  `NeedOffer` da riqueza; requisito `PreTemplateId` (o nível daquela linha no tipo dela).
- O nível sobe na hora; `CodeTime` (só prédios) trava a próxima melhoria. O cliente calcula
  `codeNeedDate - (currentDate - codeBeginDate)`. Acabar já custa 1 diamante a cada 10 min.
- Aprender (5147) custa a contribuição pessoal `NeedOffer` do nível seguinte e não passa do nível
  pesquisado pela guilda.

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
| 7501 | terra secreta | 2000×2000, tipo 7 | nenhum objeto de campanha | captura |
| 4501 | guerra de guildas | 8000×4000, tipo 6 | nenhum objeto de campanha | captura |
| 4601 | guerra entre servidores | 6000×3500, tipo 16 | 41 nós com `id`: 20 carros de guilda, 5 torres, 5 nós de energia e o resto (recursos e outros) | evento fechado (abaixo) |

`MapNodeInfos` e `CampaignData` não têm nenhuma linha para esses quatro mapas. A luta usaria o fluxo
PvE de `game/battle.py` com esses nós; sem eles o cliente carregaria um mapa vazio, sem saída, então
8542, 8537, 8471 e 8783 continuam recusados.

**O que capturar** (uma captura por atividade, de uma sessão completa):

- **Altar (7601)**: guilda nível 5 ou mais, o chefe abre o altar (8541), um membro entra (8542) e
  chega ao fim. Precisa do 125 do mapa 7601, da lista de nós (5125 ou `CampaignNodeList`) com os
  monstros e o altar, e dos pacotes 8549, 8550, 8593, 8264 (reviver), 4437 (relatório), 4448 e 4449.
- **Terra secreta (7501)**: entrar (8537), regar a árvore (8565), comprar o buff (8566), chegar ao
  nó do senhor (8743), com a lista de nós.
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

**Eleição (8241/8481)**: nada abre a votação, só editando o banco (`voting_state`). A regra do chefe
sumido não está no cliente nem nas capturas.

**Sem dado**: 8335 recrutamento (o cliente só deixa com `speakTimes` > 0, e aqui é sempre 0); guildas-robô
(o oficial tinha, aqui é a guilda aberta com mais membros); renomear grátis depois de juntar servidores
(`same`, precisa da guerra entre servidores).

**Pendente, sem fonte**: sair da guilda antes de pegar o prêmio da bênção perde o prêmio (fica na
linha do membro). O oficial não mostrou esse caso.
