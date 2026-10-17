# Guilda (consortia)

Código: `game/guild.py` (estado e mensagens), `game/handlers/guild.py` (gestão),
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
de habilidade, `is_auto` e `last_out_consortia`. Itens para outro jogador (baú) passam pelo
snapshot da sessão dele se estiver online, ou carregam/gravam o snapshot se estiver offline.

Todo handler muda a memória antes do primeiro `await` e grava tudo numa `characters.save`.

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
| 5145 | bênção | 45 `{blessLeftTime, blessSite, blessTempId, blessCount}`; `blessSite` = posição no 4144, -1 = nada | *(cliente)* m2 `__getAltarBlessInfo`, m6 `ConsortiaAltarFrame` |
| 8216 | pegar o prêmio da bênção | 115, 4143 `{result}` | *(cliente)* m2 `__addFreshItem` |
| 8577 | baú | 4466 | *(visto)* `birlik_katkisi...json` #4 |
| 8579 | membros para distribuir | 4465 | *(cliente)* m6 |
| 8578 | distribuir (chefe) | 115 para cada membro online; 4466 | *(cliente)* m6 |
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
(`ShopManager.sendShoping`). `handlers.guild.shop_buy(s, buyInfo)` faz a compra quando o `goodId`
é de `ShopTempInfos.ShopType` 2: preço na coluna `ConsortiaOffer` (contribuição pessoal),
`NeedConsortiaLevels` contra o nível do mercado. Responde 3, 115, 111, 90 `ShopMsg{buyInfo}`, 83
canal 3 *(visto)* `birlik_katkisi...json` #60 (goodId 19, 2040106, 40 de contribuição). **O handler
do 5154 (sistema de loja) precisa chamar `shop_buy` primeiro.** Atenção: o 5154 tem dois nomes em
`opcodes.json` (`FashionShopMsg`, `ShopMsg`) e o registro decodifica pelo primeiro.

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

- **Mapas das atividades**: altar do demônio (7601), terra secreta (7501), guerra (4501) e entre
  servidores (4601) abrem com o 125 e os nós do mapa. O servidor só tem o mapa do tutorial
  (`game/campaign.py`). Os nós de 7601 e 7501 não estão nos `.maps` do CDN (só 13 mapas têm; os
  das atividades ficavam no banco do oficial), então falta uma captura de cada atividade. Por isso
  8542/8537/8471/8783 são recusados; o cliente não trava (só envia, com intervalo entre cliques,
  m2 `ConsortiaSocketOutManager`) e os pacotes de dentro do mapa
  (4437 relatório, 4448, 4449 fim, 4485, 4432/4632, 4440/4439/4457/4462/4460) não saem. Com o mapa
  pronto, a luta usa o fluxo PvE de `game/battle.py`, e o ranking por dano vai no `hurtOrder` do
  4437; os prêmios vão para o baú com `handlers.guild.add_to_box`.
- O altar abre e o estado (`altarState` 0/1/2, 21 min) aparece no 164/4138.
- **Prêmio da bênção**: a tabela do oficial não está nos templates. ponytail: sempre um item do
  mercado liberado pelo nível do altar, na casa 1; fica na memória até o 8216. A bênção rápida
  (x10, VIP 6) é recusada.
- **Eleição**: a regra que abre a votação (chefe sumido) não está no cliente; `voting_state` só
  muda pelo banco.
- **Baú**: membro offline com mochila cheia perde o item (falta correio).
- 8335 recrutamento, guildas-robô e o renomear grátis (`same`) não existem.
