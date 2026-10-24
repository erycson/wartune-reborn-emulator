# Pendências: o que ainda não é igual ao oficial

Todo opcode que o cliente manda tem handler (`tests/game/test_cobertura_c2s.py`), mas "tem handler" não é
"faz o que o oficial faz". Esta é a lista do que falta, por sistema, com o motivo. O detalhe de cada item
está na doc do sistema (link na coluna). No fim, a lista gerada de todas as simplificações marcadas no
código com `# ponytail:`. O que capturar no oficial, junto e por sessão de jogo: [roteiro-captura.md](roteiro-captura.md).

Motivos usados abaixo:
- **sem dado**: o comportamento depende de tabela ou captura do oficial que não temos (templates, `captures/`).
- **depende de**: falta outro sistema do servidor.
- **dedução**: implementado, mas com número/regra deduzido; conferir quando houver captura.

## Loja e itens ([itens.md](itens.md), [guilda.md](guilda.md))

Varredura da `ShopTempInfos` (4292 produtos) contra o que o 5154 valida:

| Situação | Produtos | Status |
|---|---|---|
| Pacotes de nível/recompensa (SonType 298, ex. "Yeni Oyuncu Paketi") | nenhum está à venda | ok: só saem de missão/recompensa, a loja não acha o produto |
| Item que não existe no `ItemTempInfos` | 27 (lojas 1, 13 e 99) | ok: recusado (`GONE`) |
| Lojas pagas com pontuação (ShopType 8, 13, 15, 20) e `NeedItem` 2125048 (Cesur Dönüş Kitabı) | 79 | ok: recusado (moeda não existe aqui). **depende de**: pontuação de lordes, guerra de guildas, cristal de fada, volta de jogador |
| Limite diário `VIP0Count` (o cliente chama de `OneDayCount`; não existe limite "uma vez na vida" na tabela) | 22 | ok na loja comum; **corrigido** no mercado da guilda (antes comprava sem limite) |
| `NeedMinVip`, `VIP1Count`..`VIP6Count` | todos 0 / -1 | nada a fazer hoje |
| Loja de honra (ShopType 3): medalhas com `ValidDate` (7, 15 e 30 dias) | 10 | ~~falta item com validade~~ **feito**: `items.valid_date`/`begin_date` (0036), no 115 e apagado no 8346, no login e no relógio (20008). **dedução**: apagar sem aviso e a varredura do servidor. **falta captura**: deixar uma medalha de 7 dias vencer no oficial e capturar o login e o 8346 (ver itens.md) |
| Loja do labirinto (ShopType 4): moeda e preço (Labirent Parası, `MazeCoin`) conferidos na captura (105 e 110). Andar: o cliente esconde o botão com `MazeLayers` > `maxIndex` (o recorde: 0 sem progresso) ou `MazeLayers2` > 0, e o servidor recusa o mesmo | 119 | **dedução** no código. **falta**: o progresso do labirinto (andar e recorde). O progresso real do labirinto não existe aqui |
| Loja misteriosa (ShopType 5): peso `Rands` | 110 | ok: 6 itens (`MysteryShopModel.MAX_GOODS_NUM`) pelo peso `Rands`, a partir do nível 26 |
| Presente para outro jogador (`receiveId`) | — | recusado. **depende de**: entrega pelo correio na compra |
| Mochila cheia | — | recusa (o oficial manda pelo correio, resultado 12) |
| Ofertas por tempo (4238, Timed Sales) | — | ok: `game_settings.shop_offers` (0053, oficial_encantar #57-#58), compra com limite do dia. `currentCount` = vendidos no servidor, 4375 a todos a cada compra (oficial_encantar #2640-#2666). Rodízio (8632) e compra coletiva (8645): nenhuma oferta `type` 2/3 nas capturas |

Itens fora da loja:
- Refino da forja (8336): sorteio uniforme entre os 1584 atributos com `Grades` > 0 (visto: os 42 das capturas têm Grades 1–10). Falta o peso por nível: **precisa de captura** 8336 → 4258 com itens de NeedGrades baixo e alto. Pedras por `Profile` e cadeado (208027 ou 45 Balens) já vêm da `RefreshView` inglesa.
- Avaliação de moda (8781) e composição de moda (8594): o cliente inglês tem as travas e os custos (ver [itens.md](itens.md)), não o resultado. **sem dado**.
- `randomSkill` dos itens novos: **feito** pela faixa do nível ([itens.md](itens.md)). **TODO(inventado)**: o tipo 701
  sem amostra e o peso dentro da faixa (uniforme); o refino (8336) sorteia igual, sem captura.
- Sem teto diário para Beden e EXP vindos de itens. **dedução**.
- Títulos (8597): lista vazia. **depende de**: conquistas.
- ~~Poções de atributo sem efeito~~: somam no `total*` do herói (150 no uso e no 8283); ~~pergaminho de EXP fora do
  relatório do fim da masmorra~~: aplicado no 137. **dedução**: Defense = Agility, o 150 e o `propJoin`; **precisa de
  captura** ([itens.md](itens.md#pergaminhos-de-efeito-sontype-201)).

## Minigames e eventos ([eventos.md](eventos.md))

8 de 38 são reais: fundo de novato (8751), fundo normal (8703), árvore dourada (8604) e labirinto de gemas (9508, 9509, 9513, 9516, 9517). 2 recusam sem efeito (9510, 9515: ajuda de amigo do labirinto). Os outros 28 respondem o estado "fechado" que o cliente sabe mostrar. Calendário de cada um: `game_settings` (0038), do operador.

| Minigame | Opcodes | Falta |
|---|---|---|
| ~~Garrafa~~ Árvore dourada | 8604 | **real** (0038, #72). **dedução**: início da edição, pesos (uniforme), dono do andar = quem bateu, raro = `isNewItems`, ordem das respostas, "once per day" do help não aplicado. **precisa de captura**: 8604 de cada op e 4825 ([eventos.md](eventos.md)) |
| ~~Fundo normal~~ | 8703 | **real** (0038, #86). **dedução**: `activeType` 2/0 fora da compra, compra recusada fora da janela. **precisa de captura**: compra e resgate |
| Quiz | 9501 | `HeartTempInfos` não tem resposta certa (são perguntas de personalidade); agenda do help (seg/qua/sex 19:30) diferente do template (1,3,5,6 às 14:35). **precisa de captura** de uma rodada |
| Labirinto de gemas | 9508–9517 | **real** ([eventos.md](eventos.md)). **precisa de captura**: subida de nível (tabela de `maxExp`), pesos dos prêmios, o que o oficial faz com troca sem combinação, bolsa do prêmio das caixas (9513), período da renovação diária (dedução), ajuda de amigo (9510/9515/4925), ranking semanal, preço e teto da compra (dedução) |
| Estrada dourada | 9520–9522 | casas (4933 `cellInfo`) e custo dos dados: **precisa de captura** (abrir e jogar nos 3 modos) |
| Pesca, caça ao tesouro, minério | 9507, 9502, 9645 | regras de aparecimento, nós e prêmios (**precisa de captura**: abrir e jogar uma vez cada); o 9645 separa minério (`extend1` 35) de super assinatura (38) pelo cabeçalho (`GameSession.packet`) |
| Loteria, caça-níquel, cadeiras, caixa de ano novo, história, sorteio de grupo | 8748/8750, 9500, 9638, 8994, 8629/8630, 9523 | template e tabela de prêmios: a captura EN só os tem fechados. **precisa de captura** num dia em que o oficial abre |
| Recuperar EXP | 9503 | **depende de**: os sistemas (campanha, arena, chefe, imposto) gravarem a participação do dia (a fórmula do custo está conferida) |
| Troca da sorte | 9610 | as edições da captura inglesa não têm as trocas (vencida e futura) |
| Privilégio 360 | 8722/8723 | só para o agente 360 do cliente |
| Fundo de novato | 8751 | **dedução**: janela oficial desconhecida (`endDate` 2099) |

Outros eventos:
- 8519/8521 (roleta VIP) são reais ([eventos.md](eventos.md#vip-e-contrato-do-rei)); 8518 responde o 4412 vazio (contadores do painel do dia: **depende de** cada sistema contar); 8756 só registra; loja de teste (8582) recusa: o mapa de teste não existe.
- Quadro de recompensas 8291 sem passe, 8298, 8729: **depende de** batalha, missões e mensagens reportarem progresso.
- SumActive: contam 12 (devoção), 13, 14, 21/22 (alquimia), 26 (coliseu), 108/109 (destino) e 110 (torneio
  de fadas); diário x período todo vem dos textos "today" do cliente (**dedução** para os sem texto). Os outros
  tipos ficam em status 3 (**depende de** cada sistema: gasto e recarga de Balens, troca, montaria, recompensa,
  campo de batalha, runas, cartas...). **precisa de captura**: se o oficial empurra 4476 sozinho quando um
  contador sobe (aqui só vai no pedido 8586 tipo 1). Lista em [eventos.md](eventos.md).
- Devoção (leed): ~~8, 15, 17, 18, 24, 25, 33 sem gancho~~ e ~~devoção do VIP~~ feitos (18, 24, 25 por **dedução**
  do título; VIP pelo tipo 2 "Devotion Bonus"). ~~22 "Altar of Ennoblement"~~ feito (entrada na Rest House). **Depende de**: 13 arena em grupo, 23 entrada no labirinto (Catacombs), 27 campo de batalha, 28 Spire. **Precisa de captura**: VIP 3+
  no login e os leeds 18/24/25 ([eventos.md](eventos.md#captura-que-falta-devoção)).

## Chefe do mundo ([boss-eventos.md](boss-eventos.md))

- Pronto: agenda empurrada no relógio, entrar e sair, luta com vida compartilhada (último golpe único), ranking,
  moral, morte de 30 s e reviver pago, fim da janela com prêmios pelo correio e vida da próxima janela. Config
  e estado no banco (0031). Números da Internet (**dedução** onde a Internet não dá a regra).
- **precisa de captura** para conferir: o nó do chefe (127), a ordem dos pacotes da entrada, o 157 do chefe e o
  4203 real. O avatar do nó (`sonType` 2145) é **dedução**: conferir os 404 do Apache e baixar com
  `tools/fetch_missing.py`.
- ~~Missões tipo 40 (participar do chefe) e 66 (lutar agora) não contam.~~ Contam: 40 no fim de cada luta (dedução: luta, não entrada), 66 no 8264 pago.
- Buff comprado (8470) e dublê (8526) recusados (o buff saiu no Patch 5.5). O 4435 não é mandado.
- A vida não segue o nível dos jogadores: cresce/cai pela janela anterior (`grow_pct`/`shrink_pct`).
- O 8264 também é o reviver do altar da guilda: separar pelo mapa quando o altar existir.

## Salas, times e masmorras ([salas-campanha.md](salas-campanha.md))

- Salas e times só em memória. Decisão: salas não persistem; times não persistem até haver captura de login com time; o contador de campanha multi (4240) persiste (migração `0021`); o item "Büyük Sefer" soma 1 no dia; falta o gasto da entrada (**precisa de captura**, ver Persistência em salas-campanha.md).
- Masmorra Kurt İni (1001, mapas 1011 e 1021, 5039): feita, com nós, névoa, lutas, Pandora, baús e fim; a carta sai no clique (5122, depois do 135), uma por mapa ([salas-campanha.md](salas-campanha.md)). O relay atrasa o S>C uns 30 pacotes: não use a ordem C>S x S>C dele. Falta: resposta do 5180 (1 sair, 2 de novo); cartas pagas (`isPay`, `payCardCount`); recusa do 5039 sem Beden (o gasto de 20 por mapa está feito); missões (112, 4476/4484); progresso da masmorra (só a carta é gravada: sair recomeça no 1011); repetir depois do 1021 (dedução); EXP do fim (630) é texto copiado da captura (o `BaseGp` 600 não bate); baú 101104 (Bronze Treasure Chest) nunca visitado na captura: (dedução) dá o do 102104, de mesmo sonType; 5121 sem captura; chance de cada item da carta.
- Caixa Pandora (5033 com S>C 29, mapId 879/880, nodeId 101107/102107): feita na masmorra, com o buff 1301/1701 da captura. Falta a recompensa além do buff (a captura traz `itemTempId` 0). Exército na campanha (5121): falta captura da resposta. **depende de**: nada agora; o progresso de campanha ainda não é salvo.
- Falas dos NPCs (4163, migração 0076, `campaign.talk_tick`): *(visto)* repertório por sonType e ritmo de 12-18 s das capturas inglesas; a chance por tique (0,7) e a do chase (0,2) são **dedução** das contagens; NPC sem fala vista fica calado.
- Tecnologias de atributo (MasterType 14, `rules.tech_effects`): Hero PATK/MATK/PDEF/MDEF/HP/Troop somam no herói, Troop HP/PATK/PDEF/MATK/MDEF no `effect_Data`/`base_Join` do pawnLive e na luta (*cliente*: Property1 × nível, o `Activity` do template). Upgrade: 110 tipo 3 (velho negativo, novo) com 150 cada e o 109 final (só turco: teknoloji_upgrade #2-#13). **Divergência**: o turco aplica ×1,5 (342 no Hero MATK 19, 81 no Troop PATK 9); sem fonte do multiplicador, fica ×1.
- Prédios pelo nível (`castle.level_buildings`, `UpGradeTempInfos` tipo 3): *(visto)* o personagem nasce com conselho, quartel e casa (tutorial_en #582), o depósito no 9 (#2246) e a academia no 18 com a tecnologia 1304 e a fila de tecnologia (oficial_20261023-231733-1 #3939-#3946). *(template)* a Gold Refinery no 24. Personagens antigos do banco ficam com os prédios que já tinham.
- Astral rara (8269): *(visto)* oficial_encantar #2753/#2824, a Profile 5 sorteada sai no 83 canal 2 para todos ("X just received the extremely rare [astral] Astral!"); a Profile 7 também por *dedução* (`game_settings.star_rare_profiles`).
- Chefe da cidade externa abatido: 83 canal 2 para todos com o link 111 (painel dos chefes) (só turco: teknoloji_upgrade #1). O texto inglês é `TODO(inventado)`, montado do turco com o "Wilds" do language.txt.
- Patrulha dos monstros (4122, migração 0079, `campaign.patrol_tick`): *(visto)* pontos por campDataId (união das capturas inglesas), tique de 6 s (pedreira 20 s) e chance 0,62 (0,3) das contagens. Nó com um ponto só visto volta para a origem (*dedução*). shortcut: nó de campanha sem 4122 nas capturas fica parado; capturar esses mapas para completar a tabela.
- Orc Plains 1005 e Tribal Plateau 1006 (migração 0075): feitas da captura `oficial_20261023-231733-1`, as duas
- Reforços (72, migrações 0075 e 0077, `battle.Battle._reinforce`): *(visto)* quando o lado inimigo cai e a luta tem outra onda, sai o 72 com os soldados novos e a luta segue; as ondas vêm dos 72 das capturas (`tools/extract_dungeon.py`). *(dedução)* a ordem das ondas é fixa (a `oficial_encantar` teve a do 114203 invertida).
- Login completo (migração 0078, `login.switches_msg`): *(visto)* tutorial_en e oficial_20261023-215937-1: 4438 (prosperidade 0), 4912/4373/4428 vazios, 4251 (os 9 avisos de atividade, `active_notices`), 4393 vazio, 4422 (as 67 chaves, `switches`; mina 3006 e estrada dourada 3031 fechadas por `closed_switches`), 4392, 4471 (honra do dia 0 / `honor_day_max` 6000: o geste não sobe aqui), 4900, 4725 (moedas zeradas) e, depois do 4182, 4451, 4637, 462, 4741, 4683 e 4685.
- **Falta**: títulos (4484, `AppellInfos`, 33 tipos de condição): o oficial manda os 221 no login e de novo a cada progresso (ex.: título 30 com value 240 na 215937 #62); aqui a lista vai vazia (`shop.appell_exchange`).
- Presença online (11 `RoomPlayerListMsg`, `room.waiting_login`/`waiting_broadcast`): *(visto)* oficial_20261023-231733-1 #105 a lista no login e um 11 por entrada (state 1) ou saída (state 0) de outro. *(dedução)* a lista é a dos online do servidor inteiro.
- 4476 + 4426: *(visto)* oficial_20261023-231733-1, com montaria todo 4476 traz o 4426 (`events._sum_data`); o 4476 agora sai também na loja (171155 #229-#230, texto "Successfully purchased {nome} x{n}."), na loja da guilda, na forja e na varredura (só turco). A varredura conta cada rodada como campanha (leed 4) e avisa "Received items: ..." (só turco: savasa_baskin #10-#31; o "Kazanılan Eşyalar" traduzido por dedução).
  etapas de cada. **TODO(inventado)**: a luta do "[Elite] Bloodthirsty Tauren" 115116 (o herói 1062 sozinho, como o
  Kronos); pesos das cartas por igual (dedução).
- Temple of Ibalize (Inner) 1004 (migração 0069): feita da captura; pesos das cartas e o baú de prata/Mystery Box
  são **dedução** de uma volta só.
- Temple of Ibalize (Outer) 1003 (migração 0062): Perene Bone **TODO(inventado)** x1 nos Undead Crusader/Gladiator (103104, 103106, 103202, 103203, 103206), que não lutaram com a missão 190 aberta; Mystery Box 103108 sorteia 5.000 Gold ou Lvl. 2 Luck Stone x2 por igual (dedução, três amostras).
- Exército do sistema (5038): lista só para 1011, 1021 e 2011 (captura). Os demais mapas precisam de captura do 5038.
- Torre (8297/8300): limites vistos na captura; totalGp e itens **dependem de** progresso da torre.
- Varredura (8528): campanha feita (`game/sweep.py`); a do labirinto **depende de** progresso da torre.
- Guarda de batalha (8742): o login oficial manda 4631 com `watchInfo` e o servidor não manda. **depende de** modelar gemas.
- Pedágio (8752–8755): fechado, sem agenda. Configuração e tabelas de recompensa existem no template, mas o parser descarta as tabelas aninhadas.
- Link de sala no chat (9504): feito (4913). Sala inexistente: sem resposta (dedução).
- 5027 só registra (aba de convite que não existe no cliente); 8740 sem remetente no cliente (efeito deduzido).

## Cidade externa e mapa do mundo ([cidade-externa.md](cidade-externa.md), [mundo-compartilhado.md](mundo-compartilhado.md))

- Mapa compartilhado: **parcial**. O mapa do castelo é uma instância de cada conta (minas e castelo só do
  jogador). Nos mapas 1 a 5 o 4129 leva os castelos de outros jogadores nas grades. Não existem: exércitos
  alheios andando (169, 4167, 4168; precisa de presença entre sessões). Castelos NPC dos mapas 1 a 5: **feito**
  ([cidade-externa.md](cidade-externa.md#castelos-npc-do-mundo-mapas-1-a-5-gamenpc_castlespy)); **TODO(inventado)**:
  os das grades não vistas, a vida das pilhas, o saque e o `fight` fora do grau 12. Minas dos
  mapas 1 a 5: **feito** ([cidade-externa.md](cidade-externa.md#minas-do-mundo-mapas-1-a-5-gameminespy));
  **TODO(inventado)**: minas das grades não vistas, guardas 21-60, a luta pela mina de outro jogador e as cartas.
  O 5160 luta só contra mina livre; castelo e exército alheio só param o exército. 8488 (PvP no mapa) e 5004
  só registram. **precisa de captura**: resposta do 5160 e do 8488 contra castelo ou exército alheio.
- Minas de ouro: refresh de 12 h feito, por jogador (`castles.mines_at`, `createDate` no fuso UTC+3; nível
  sorteado de novo a cada ciclo, ocupação do ciclo anterior vence). **precisa de captura**: a perda de soldados
  numa derrota contra a mina (nas vitórias nenhum morre), o refresh com o jogador online e um login mais de
  12 h depois do último (para saber quando o ciclo abre).
- Monstros dos Wilds: **parcial**. Aparecem no 4129 dos mapas 1 a 5 (sorteio por mapa e ciclo de
  `WorldMapFreshTime`), dá para lutar e abater (5160, battleType 3841 só com o herói, como no oficial), os
  contadores do dia e a regra dos 15 níveis valem, os chefes vão no painel 4938 e a Divine Light tira a névoa do
  mapa. Luta e baú do normal nível 10 *(visto)*. Quantidades por mapa (40/20/5) e quais chefes cada mapa sorteia
  são **dedução** (o oficial mostrou 1 chefe de nível 10 + 4 de 50-80 nos dois ciclos do mapa 1); a queda de
  elite e chefe é **dedução** sobre a wiki e relatos (nenhum morto na captura). Luta em equipe/entrar na luta
  não existe (**precisa de captura** do fluxo de grupo: o 11 antes do ataque ao chefe, #7417).
- Treasure Cache (type 22): **feito** ([cidade-externa.md](cidade-externa.md#treasure-cache-4129-type-22-gamecachespy)).
  **TODO(inventado)**: vagas por mapa e o prêmio (pedra do nível ou equipamento da classe). Falta: os 4484 de título
  depois do item.
- Subida de nível: o exército completa com as tropas do castelo até a nova liderança e vai 139 (castelo
  vazio), 100, 150 e 4640 (fundo de novato) como no replay #625-#628 e tutorial_en. **dedução**: o mesmo nas
  subidas por batalha, coliseu, fazenda, livro de EXP e prêmio 8287 (as capturas só têm a da missão).
- ~~Ataque a castelo: 9506 compra tentativas, mas nada as gasta.~~ O 5160 no castelo-robô gasta e grava na hora; o 9506 cobra AddAttck_Point (395 EN). Castelo de jogador: segue sem luta (exército alheio).
- ~~Gancho (8293, 8292, 8295) zerado~~ **feito**: Rest House ([salas-campanha.md](salas-campanha.md#rest-house)). Falta o PK no mapa (8525, BattleType 19).
- Passe de progresso (8636/8637): área 1 fixa, prêmio recusado. **depende de**: 8753/8755.
- Mapa do tesouro (8744): só receber o mapa; atualizar, cavar, usar e prêmio **dependem de** pontos de tesouro e batalha em equipe. Limite diário e nível 55 são **dedução**.
- 8699 (guia do tutorial) sem nó de coleta para abrir; 8745 depende do mapa da guilda; 8535 depende do mapa de PvP do chefe.
- Mineração de ametista (mapa 30000, teleporte do space): **depende de** minas.

## Mercado entre jogadores ([mercado.md](mercado.md))

- Encerramento agendado a cada 60 s (`game/mall.py` `run`): um anúncio vencido sai até 60 s depois do fim, mesmo sem pedido ao mercado. Antes, só o próximo pedido encerrava.
- *(cliente inglês, `m7/scripts/auction`)*: inicial ≥ 2, fixo obrigatório e > inicial, 8/24/48 h, taxa de 250 × horas de ouro (−10), −19 abaixo do preço padrão, 7 linhas na busca, `orderBy`/`orderType` no 8452 e 8457, primeiro lance igual ao inicial, líder não cobre o próprio lance (−17), imposto de 20% do vendedor, compra pelo fixo entregue pelo correio, até 9 unidades. Limite diário configurável (`game_settings.mall_daily_limit`, padrão sem limite). **dedução**: preço mínimo `StartingPrice × count`, teto de página 50, arredondamento do imposto, taxa não devolvida ao cancelar.
- **falta**: mascote no leilão (aba "Sell Sylphs", nível 50, `sellType` 2); cartas oficiais (título, texto, momento). Detalhe em [mercado.md](mercado.md#dependências).
- Lance e compra pagam só elmas (sem vinculado), sem prova de que o oficial restrinja.
- Lista do mercado (8450) e busca (8457) ignoram a ordenação.
- Cancelar parte de uma pilha não reempilha com a original.
- Correio não é apagado por validade; uma limpeza futura precisa pular carta com item não retirado.

## Guilda ([guilda.md](guilda.md))

- Mapas e batalhas das atividades (altar 7601, guerra 4501, entre servidores 4601) e os
  pacotes dentro deles: recusados. **precisa de captura**: os nós de 7601 e 4501 não estão em nenhuma
  fonte; o 4601 tem os nós, mas o evento está fechado pelo template. O que capturar está em
  [guilda.md](guilda.md#pendências).
- Rankings e prêmios das atividades: o gancho `add_to_box` existe, ninguém chama (depende das atividades).
- Bênção (5145): o prêmio é sempre um item do mercado liberado pelo nível do altar, na casa 1. A tabela do
  oficial e a bênção rápida (x10) **precisam de captura**. O prêmio pendente agora fica na linha do membro.
- Eleição (8241/8481): nada inicia a eleição (só editando o banco). A regra está no `chairmanElection.help`
  inglês (ver [guilda.md](guilda.md)); falta o relógio que abre e fecha.
- 8335 recrutamento: **feito** (5 por dia, migração 0068). **TODO(inventado)**: o canal (mundo) e o remetente do 83.
- Sair da guilda antes de pegar o prêmio da bênção perde o prêmio (*ponytail*).
- Habilidades (5147): bônus no herói e sequência **feitos** *(visto)*. **TODO(inventado)**: o "Gold Production +N%"
  (tipo 11) sobre a produção de ouro por hora (`castle.gold_yield`), sem captura com esse nível.
- Terra secreta 7501: **feita** (`handlers/fam.py`, 0073 e 0074). *(visto)* entrada, sala, derrota contra o
  Invasor e saída (oficial_20261023-171155-1 #5056-#5172). **dedução** do cliente: a árvore (invocar 1 por dia, só
  o líder; nível pelo `UpGradeTempInfos` tipo 20 com a EXP zerando, que fecha com a guilda de 36 dias da captura),
  energizar, o buff 8566 e as coletas a cada 3 min. *(visto)* as ondas de Invasores a cada 2 h com o aviso no chat
  da guilda e o aviso de cada vitória (10 de contribuição e +10 de riqueza); o Invasor vencido some para todos e só
  um luta com ele por vez (`fam.Invasion`). **TODO(inventado)**: o que o vencedor vê, a EXP de cada tique, o bônus da
  energia e a contribuição da coleta (`fam_tree`), o texto "Received: N Contribution". As coletas ainda são uma
  cópia por jogador e os outros membros não aparecem no mapa (só o número no 4453). O 8743 (Master
  Treasure Thief) fica recusado: depende da Class Wars entre servidores.

## Herói, exército e pets ([heroi-exercito.md](heroi-exercito.md))

- Pets: composição de um pet (8621 op 13) pela `PetComponseInfos`: 24 de 28 receitas (as 4 restantes dão tipos 117–119, sem template). Fusão de dois pets (15): **precisa de** `PetTempInfos` dos tipos 117–119 e dos itens 2125126/127/128/130/134. ~~Devorar (1) e sacrifício (6)~~ feitos pelo cliente inglês. Crescimento, skills, treino e resistência (4, 5, 7, 8): **sem dado** (o cliente não diz o ganho por item ou ação; ver heroi-exercito.md).
- Montaria: estrelas/bênção, rei das montarias, loja, refino, voo (8529 outras ops, 8843). **sem dado** (tela fora do decompilado).
- Vocação depois do tipo 102 (8643). **sem dado**.
- Cartas de poder (9505): cartas e EXP vêm da batalha (sem captura). O 4902 é feito: o poder das cartas por tipo de luta, antes do 150 do próprio exército (só turco, ver heroi-exercito.md). ~~Bônus de coleção falta~~: feito no 4905 (powcard_suite_slots); os graus dos degraus 2 e 3 são **dedução** (**precisa de captura**, ver heroi-exercito.md) e o bônus não entra na batalha.
- Posição do herói em salas (8277/8278): **depende de** salas. Teleporte (8326): **feito** (cidade-externa.md).
- Ganhar montaria, pet ou carta: **depende de** uso de item, missão ou batalha.
- ~~`battle.py` ainda não lê a tropa (`rules.battle_pawn`) nem os buffs (talento, runas, destino, dragão, cartas).~~ Lê atributos, tropa, talento, runas e destino ([batalha.md](batalha.md)). Dragão e cartas: **precisa de captura**.
- Destino tipos 2100/2200 nunca abrem. **sem dado**.
- **dedução**: chance do sorteio de estrelas, EXP de destino por pedra, atributos e pontos dos pets por nível.

## Castelo e fazenda ([castelo.md](castelo.md))

- ~~Fazenda de amigo~~: roubar, reviver, verme/erva e regar a árvore de amigo feitos, só entre amigos, com os limites do cliente. **dedução/config**: roubo de 10% (internet), grau de amizade = 1 + pontos // 10, amizade +1 dos dois lados. **precisa de captura**: roubo e praga na fazenda de amigo, tabela de grau de amizade (passos em castelo.md).
- ~~Melhorar terreno (op 9), terras pelo nível da fazenda, acelerar 50%~~ feitos pelo cliente inglês. Pets da fazenda (15044 ops 10–16): **depende de** pets.
- Colher a árvore (5178): feito; Daru e Kyanite de `tree_fruit` são internet + dedução. **precisa de captura** (passos em castelo.md).
- Recompensa offline ×1,5/×2 (8287): preço desconhecido. **sem dado**.
- 8255 (batalha em grupo), 8562 (trégua): respondem vazio. **depende de** esses sistemas. 5179 (desistir da mina):
  feito.
- Rendimento: prefeitura + minas bate exato com a captura inglesa (#579, #591, #772, #2744); bônus de guilda e efeitos ainda não entram.
- Subida de nível da fazenda (111, 4386, 83 "Your farm has been upgraded to level N!", `isUpGrade`): **feita**, visto na rega do amigo (oficial_20261023-215937-1 #1277-#1285). **dedução**: a mesma sequência na rega da própria árvore, na colheita da árvore e na ajuda nas terras, e a posição dela nesses casos.
- **dedução**: EXP offline = nível × minutos (até 8 h), arredondamento do bônus da terra melhorada, caixa por tempo vira à meia-noite UTC. Ouro de regar: visto, grau da fazenda do dono × 20 (`oficial_20261023-153200-1` #2228 e #2242; textos ingleses "Tree of the Ancients EXP +1", "Friendliness  +1").

## PvP ([pvp.md](pvp.md))

- Lordes (8710–8721), lordes casados (8975–8981), campo de guerra (8332/8334/8337/8338), campo de minas (8633), 8635: parciais. **sem dado**.
- Torneio de fadas: usa os pets salvos; a posição dos pets do oponente (`pos` = índice + 3) é **dedução**.
- Coliseu, drop da vitória (`game_settings.arena_challenge_items`, 0072): **feito** com os dois vistos (VIP Token no inglês, oficial_20261023-215937-1 #1168; Lvl. 3 Luck Stone no turco, meydan_okuma #30). **TODO(inventado)**: o resto do conjunto, pesos iguais, só na vitória e 1 por dia (as duas vistas eram a 1ª vitória do dia).
- Coliseu, início: 140, 112 (condição 35), 4152, 157 e o fim sem 150 **feitos** (oficial_20261023-215937-1 #1129-#1167).

## Cidade do céu ([mundo-compartilhado.md](mundo-compartilhado.md))

- 4595 no login (entre o 6 e o 4151) e no 5180 só depois do tutorial: **feito** (oficial_encantar 28500 sem; 171155/215937 33000+ com). **dedução**: o corte em 30000 (os dados só dizem entre 28500 e 33000) e os 4597/4594 dos outros depois do 4151 no login (o oficial não os manda ali).

## Social, chat e VIP ([social.md](social.md), [chat.md](chat.md))

- Canal de time (6) no chat: recusado.
- ~~VIP ignorado em limite de amigos e 5172 índice 0~~ **feito** pelo cliente (`VIPModel.vipFriendPrivilege`/`vipCoolPrivilege`). Cota de cornetas: `game_settings.vip_bugle_bonus` (0036), padrão 0 = **sem fonte**; **falta captura** do 8705 → 4500 de uma conta VIP (ver chat.md).
- Presente do contrato do rei para amigo (8540): recusado (gravar outro personagem). O do VIP (8513) o inglês não manda.
- ~~Contrato do rei: Lord of Time (4) depende do gancho~~ **feito**: o 8293 sai de graça ([salas-campanha.md](salas-campanha.md#rest-house)).
- ~~Mochila de 42 espaços base em coliseu, fazenda, caixa por tempo, correio e `rewards.can_grant`~~ **feito**: todos usam `bag.free_positions` (`bag.capacity`: 42 + comprados, 217 alugada).

## Oráculo do tutorial e protocolo

`tests/game/test_tutorial_oracle.py` reenvia o tutorial da captura inglesa (#98-#822) e conta as respostas.
Diferenças (`KNOWN_GAPS`), além das de ritmo e de outros jogadores (11, 4248, chegada do exército 140 ×2):
- 150 ×2 idênticos na saída do mapa do tutorial (inglesa #518-#519, 5125 1000206): aqui sai um.
- Opcode 2 (`U_C_PLAYER_GRADE`, corpo `32023332`, sem mensagem no `.proto`) depois do Lvl. 5 Starter Pack
  (#690): não existe aqui. **sem dado**: significado do campo 6 = "32".
- A missão 50 avança no 5017 20000 (#584): o oficial não manda o 112 (aqui sobra um).
- A subida de nível da missão 51 (que faltava com a captura turca) já bate com a inglesa (#636-#639).

`.proto`: gerado do cliente inglês desde 2026-10-20; o `ShopMainRspMsg` (4238) ganhou o campo 4 (`flag`) e a
captura inglesa bate byte a byte.

O que ainda depende de captura turca sem versão inglesa: [fontes-turcas.md](fontes-turcas.md).

### Diferenças contra a captura inglesa ainda abertas

- Luta com o castelo-robô (#1657): `battleType` 4, `mapTempId` 993, herói 11008 com o nome do robô, 2 pilhas
  10102 (posições 1 e 7). Aqui usa a luta do guarda da mina (`outer_city.guard_battle`, `ponytail:`).
- 363/364 vão vazios no login; a inglesa (#88/#102) tem as edições.
- 4156 sem amigos: `maxPage` 0 na inglesa (#61); aqui 1. 4544 vazio na resposta ao 8224 (#42): aqui não sai.
- 4248 com `state: 2` (#104); `warfield.py` manda 1.
- `ENEMY_CAST_MS` 3500: a inglesa tem 3500/4500/4900 por skill (#1662/#1675/#1689).

## Simplificações marcadas no código

Lista gerada de todo `ponytail:` em `src/` (atualize com `grep -rn "ponytail:" src --include=*.py`).

| Onde | Simplificação |
|---|---|
| [domain/models.py:914](../src/wartune_server/domain/models.py#L914) | nasce vinculado; o selo livre dar mascote livre não |
| [game/arena.py:292](../src/wartune_server/game/arena.py#L292) | o caçador perde até o nível ~30 porque o ataque |
| [game/arena.py:302](../src/wartune_server/game/arena.py#L302) | a captura (só turco: coliseu) tem 2 arqueiros 10202 com o robô, mas lá o jogador também tinha soldados; |
| [game/arena.py:362](../src/wartune_server/game/arena.py#L362) | perda não vista, não tira pontos |
| [game/arena.py:366](../src/wartune_server/game/arena.py#L366) | fórmula de vida do pet desconhecida; MaxHp + nível × GrowthRate / 9 dá ~5% da captura (só turco) |
| [game/arena.py:407](../src/wartune_server/game/arena.py#L407) | ~ o dano da captura turca do torneio (golpe básico ≈ vida/40): sem defesa, (A - 0) × 0,5 = vida/40 |
| [game/battle.py:60](../src/wartune_server/game/battle.py#L60) | a regra por skill não foi decifrada |
| [game/battle.py:448](../src/wartune_server/game/battle.py#L448) | a iniciativa do oficial não foi decifrada (#727 e #782 têm as mesmas unidades e ordens |
| [game/builders/login.py:250](../src/wartune_server/game/builders/login.py#L250) | 1 exército por personagem; tabela própria quando houver tropas extras |
| [game/campaign.py:215](../src/wartune_server/game/campaign.py#L215) | ``StandSecond`` não entra em nota nenhuma do 137 (não há campo de tempo avaliado); time/friend/vip |
| [game/castle.py:162](../src/wartune_server/game/castle.py#L162) | sem o bônus de raça/efeitos do limite (PlayerEffect.getTransferPowerLimitAddition) |
| [game/drops.py:42](../src/wartune_server/game/drops.py#L42) | sem filtro de classe (só turco: replay #1241/#1744, o mesmo mago tirou 1080013, Job 3, e 1080002, |
| [game/events.py:52](../src/wartune_server/game/events.py#L52) | janela diária (outros ``begin_time``/``end_time``) vira um intervalo só; o oficial só mostrou 0/86399. |
| [game/gemmaze.py:201](../src/wartune_server/game/gemmaze.py#L201) | 5 ou mais em linha segue a conta de 3 e 4 (não foi capturado) |
| [game/gemmaze.py:210](../src/wartune_server/game/gemmaze.py#L210) | pesos dos três vistos no banco (padrão iguais); a tabela oficial precisa de captura |
| [game/gemmaze.py:213](../src/wartune_server/game/gemmaze.py#L213) | troca sem combinação é aceita e gasta movimento (o cliente troca na tela e não desfaz; |
| [game/guild.py:152](../src/wartune_server/game/guild.py#L152) | só os 50 últimos na memória; o banco guarda todos |
| [game/handlers/account.py:20](../src/wartune_server/game/handlers/account.py#L20) | prazo do reset não está no cliente nem nas capturas; ajustar se aparecer |
| [game/handlers/account.py:190](../src/wartune_server/game/handlers/account.py#L190) | sala de um jogador só; broadcast quando houver sala compartilhada |
| [game/handlers/arena.py:390](../src/wartune_server/game/handlers/arena.py#L390) | limite de compras do torneio não está no cliente nem nos templates; 10/dia como no coliseu |
| [game/handlers/army.py:245](../src/wartune_server/game/handlers/army.py#L245) | o sorteio comum vai até o grau atual (o texto só diz "chance" de subir); mudar com captura |
| [game/handlers/army.py:316](../src/wartune_server/game/handlers/army.py#L316) | só a posição do próprio herói é gravada; |
| [game/handlers/army.py:336](../src/wartune_server/game/handlers/army.py#L336) | a posição do exército no mapa externo não é gravada (sistema do mapa externo).""" |
| [game/handlers/battle.py:35](../src/wartune_server/game/handlers/battle.py#L35) | a postura não muda o dano (o efeito dela não tem captura) |
| [game/handlers/campaign.py:643](../src/wartune_server/game/handlers/campaign.py#L643) | sem energia não entra e não responde; a recusa do oficial precisa de captura com estamina < 20 |
| [game/handlers/campaign.py:720](../src/wartune_server/game/handlers/campaign.py#L720) | colheita sem limite nem espera (a captura colheu duas vezes seguidas a mesma pilha, #1847 e #1861); |
| [game/handlers/campaign.py:1061](../src/wartune_server/game/handlers/campaign.py#L1061) | carta paga (isPay, autoChest) tratada como a grátis: price 0 e uma só por etapa; cartas pagas extras |
| [game/handlers/campaign_map.py:37](../src/wartune_server/game/handlers/campaign_map.py#L37) | mapa sem captura manda lista vazia; falta a lista de cada mapa (nós do .maps). Não muda estado |
| [game/handlers/castle.py:309](../src/wartune_server/game/handlers/castle.py#L309) | trégua ainda não existe; zera e confirma.""" |
| [game/handlers/chat.py:29](../src/wartune_server/game/handlers/chat.py#L29) | o cliente não limita a guilda (ChatHelper); 1 s contra spam |
| [game/handlers/chat.py:181](../src/wartune_server/game/handlers/chat.py#L181) | "cena" = todos online até existir o registro de cenas (cidade do céu). |
| [game/handlers/chat.py:249](../src/wartune_server/game/handlers/chat.py#L249) | formato do convite rápido montado do cliente (sem captura); casamento fora (sala não existe) |
| [game/handlers/events.py:490](../src/wartune_server/game/handlers/events.py#L490) | nenhum desses sistemas conta ainda; lista vazia = tudo zerado no painel.""" |
| [game/handlers/farm.py:275](../src/wartune_server/game/handlers/farm.py#L275) | dono offline vem do banco; dois ladrões ao mesmo tempo em cópias diferentes podem se sobrepor |
| [game/handlers/farm.py:494](../src/wartune_server/game/handlers/farm.py#L494) | um snapshot por amigo (até 100); se pesar, ler só terras e castelos |
| [game/handlers/fashion.py:40](../src/wartune_server/game/handlers/fashion.py#L40) | a moda vinculada é ativada quando o livro é pedido (8625), não no ganho |
| [game/handlers/fashion.py:106](../src/wartune_server/game/handlers/fashion.py#L106) | as roupas do casamento no 8595 são recusadas (não estão no livro) |
| [game/handlers/forge.py:50](../src/wartune_server/game/handlers/forge.py#L50) | o refino sorteado fica na memória até o 8339 (some se o servidor reiniciar) |
| [game/handlers/forge.py:254](../src/wartune_server/game/handlers/forge.py#L254) | autoBuy (comprar o que falta) não |
| [game/handlers/forge.py:266](../src/wartune_server/game/handlers/forge.py#L266) | o espaço é conferido antes de consumir (pode recusar quando os materiais liberariam lugar) |
| [game/handlers/forge.py:571](../src/wartune_server/game/handlers/forge.py#L571) | a bênção zera no sucesso (o cliente não diz; a barra recomeça do 0 no próximo nível). |
| [game/handlers/gemmaze.py:73](../src/wartune_server/game/handlers/gemmaze.py#L73) | o oficial manda 0 para personagem novo; o contador não foi capturado |
| [game/handlers/gemmaze.py:79](../src/wartune_server/game/handlers/gemmaze.py#L79) | ranking semanal não existe aqui (o oficial manda 1771 para um jogador de topo) |
| [game/handlers/gemmaze.py:137](../src/wartune_server/game/handlers/gemmaze.py#L137) | sem subida de nível (a tabela de EXP por nível não foi capturada): curExp passa de maxExp |
| [game/handlers/gemmaze.py:150](../src/wartune_server/game/handlers/gemmaze.py#L150) | o semanal soma o mesmo que o do dia e zera na semana nova (``gm.refresh``, dedução) |
| [game/handlers/gemmaze.py:209](../src/wartune_server/game/handlers/gemmaze.py#L209) | a caixa vai para a bolsa do labirinto (o ícone voa para ela, como o das gemas); a bolsa |
| [game/handlers/gold_tree.py:48](../src/wartune_server/game/handlers/gold_tree.py#L48) | linhas da sorte guardadas em memória (o #71 mostra 3); perdem-se no restart |
| [game/handlers/gold_tree.py:151](../src/wartune_server/game/handlers/gold_tree.py#L151) | ``isVip`` falso (o dono pode estar offline).""" |
| [game/handlers/guild/altar.py:69](../src/wartune_server/game/handlers/guild/altar.py#L69) | a tabela de prêmios do oficial não está nos templates; o prêmio é sempre um item |
| [game/handlers/guild/altar.py:125](../src/wartune_server/game/handlers/guild/altar.py#L125) | o prêmio fica na linha do membro, então sair da guilda antes de pegar perde o prêmio |
| [game/handlers/guild/box.py:69](../src/wartune_server/game/handlers/guild/box.py#L69) | `isReceived` do baú sempre falso: quando a marca de "já recebeu" zera não está no cliente |
| [game/handlers/guild/box.py:94](../src/wartune_server/game/handlers/guild/box.py#L94) | o correio por mochila cheia é dedução (o |
| [game/handlers/guild/election.py:27](../src/wartune_server/game/handlers/guild/election.py#L27) | só o voto está feito, ``voting_state`` ainda só muda pelo banco; abrir/fechar fica para depois. |
| [game/handlers/guild/info.py:198](../src/wartune_server/game/handlers/guild/info.py#L198) | VIP na lista de membros só de quem está online; o de quem está offline está nos event_states, fora da memória |
| [game/handlers/guild/members.py:223](../src/wartune_server/game/handlers/guild/members.py#L223) | o oficial tinha guildas-robô; aqui vem o convite da guilda aberta com mais membros |
| [game/handlers/guild_events.py:67](../src/wartune_server/game/handlers/guild_events.py#L67) | falta o sistema de mapas de campanha (só existe o do tutorial) e as ondas de |
| [game/handlers/hero.py:138](../src/wartune_server/game/handlers/hero.py#L138) | a EXP gasta sai da EXP do nível atual (c.gp); conferir com captura se o oficial |
| [game/handlers/hero.py:323](../src/wartune_server/game/handlers/hero.py#L323) | sem o bônus 2x/5x/10x/20x da DiamondTipTxt (o cliente não diz a chance); mudar com captura |
| [game/handlers/items.py:327](../src/wartune_server/game/handlers/items.py#L327) | sem teto de uso por dia (a captura turca tem um uso só); o gasto da entrada não existe aqui, falta |
| [game/handlers/items.py:575](../src/wartune_server/game/handlers/items.py#L575) | depois de juntar pilhas, fecha os buracos na mesma ordem (dedução) |
| [game/handlers/mall.py:335](../src/wartune_server/game/handlers/mall.py#L335) | o cancelamento não devolve a taxa (sem fonte) |
| [game/handlers/marriage.py:9](../src/wartune_server/game/handlers/marriage.py#L9) | pedidos, ofertas de casamento e pedidos de divórcio ficam em memória (somem se o |
| [game/handlers/minigames.py:130](../src/wartune_server/game/handlers/minigames.py#L130) | janela de resgate desconhecida (2099 = sem fim) |
| [game/handlers/offer.py:28](../src/wartune_server/game/handlers/offer.py#L28) | o sorteio de qualidade do oficial não é conhecido; pesos para 1..5 (5 = ouro, rende x6) |
| [game/handlers/offer.py:204](../src/wartune_server/game/handlers/offer.py#L204) | as condições (RewardCondictionInfos: capturar NPC, missões, etc.) dependem de |
| [game/handlers/offer.py:227](../src/wartune_server/game/handlers/offer.py#L227) | depende do sistema de batalha abrir a luta com o NPC da tarefa; só registra.""" |
| [game/handlers/offer.py:333](../src/wartune_server/game/handlers/offer.py#L333) | as condições (enviar mensagem, batalhas...) dependem de outros sistemas avisarem; |
| [game/handlers/offer.py:346](../src/wartune_server/game/handlers/offer.py#L346) | sem compra de vagas extras |
| [game/handlers/outer_city.py:44](../src/wartune_server/game/handlers/outer_city.py#L44) | velocidade fixa, sem |
| [game/handlers/outer_city.py:188](../src/wartune_server/game/handlers/outer_city.py#L188) | os exércitos alheios não aparecem (o 169 é só o próprio): a posição de outro jogador só existe |
| [game/handlers/pets.py:57](../src/wartune_server/game/handlers/pets.py#L57) | a chance da bênção não está no cliente; 10% até haver captura |
| [game/handlers/pets.py:59](../src/wartune_server/game/handlers/pets.py#L59) | quanto um Sepulcrum dá na aptidão não está no cliente ("Randomly improves one aptitude that is not maxed") |
| [game/handlers/pets.py:240](../src/wartune_server/game/handlers/pets.py#L240) | família (tipo, NeedGrade, cor) = template: é a leitura que fecha os 24 pares de receita com um |
| [game/handlers/pets.py:326](../src/wartune_server/game/handlers/pets.py#L326) | sorteio uniforme na faixa da dica; a distribuição oficial não está no cliente |
| [game/handlers/pets.py:540](../src/wartune_server/game/handlers/pets.py#L540) | o sorteio é uniforme entre as skills dos livros; o cliente não tem a lista nem os pesos |
| [game/handlers/pets.py:676](../src/wartune_server/game/handlers/pets.py#L676) | só jogador online |
| [game/handlers/player.py:74](../src/wartune_server/game/handlers/player.py#L74) | só o 150; quem chama não passa o nível antigo, então sem o 139/100/4640 do push_level |
| [game/handlers/rewards.py:107](../src/wartune_server/game/handlers/rewards.py#L107) | x1,5 e x2 custam diamante no oficial, mas o preço não está no cliente; recusados |
| [game/handlers/shop.py:106](../src/wartune_server/game/handlers/shop.py#L106) | nenhuma loja tem NeedMinVip hoje; regra não conferida |
| [game/handlers/shop.py:110](../src/wartune_server/game/handlers/shop.py#L110) | o cliente esconde o botão se o andar passa do maxIndex (GoodsItem.as:380; o 4205 manda 60 fixo) |
| [game/handlers/shop.py:196](../src/wartune_server/game/handlers/shop.py#L196) | presente depende do correio |
| [game/handlers/space.py:47](../src/wartune_server/game/handlers/space.py#L47) | o fim do diálogo é local no cliente (``finishStory``); aqui conta o clique ou o aceite perto do nó. |
| [game/handlers/space.py:95](../src/wartune_server/game/handlers/space.py#L95) | o outro teleporte (mina de ametista, 30000) depende do sistema de minas |
| [game/handlers/space.py:104](../src/wartune_server/game/handlers/space.py#L104) | mapa por sessão com os nós da captura (só turco: #8); pets selvagens, coleta e o chefe (4686) |
| [game/handlers/stars.py:38](../src/wartune_server/game/handlers/stars.py#L38) | o oficial não publica as chances do sorteio; pesos por qualidade (Profile) e cristal |
| [game/handlers/stars.py:171](../src/wartune_server/game/handlers/stars.py#L171) | o grátis do dia também dá ponto, o cliente não diz; mudar com captura |
| [game/handlers/systems.py:43](../src/wartune_server/game/handlers/systems.py#L43) | o cliente não diz a bênção de cada refino nem a chance; 10 de bênção e 5% de "Therion's Blessing" (o |
| [game/handlers/systems.py:147](../src/wartune_server/game/handlers/systems.py#L147) | a data de ativação não é guardada |
| [game/handlers/systems.py:332](../src/wartune_server/game/handlers/systems.py#L332) | só jogador online; offline precisa do banco |
| [game/handlers/systems.py:424](../src/wartune_server/game/handlers/systems.py#L424) | pesos da roda tirados do tamanho das fatias (FateRotaryModel.rndDic, em graus) |
| [game/handlers/systems.py:492](../src/wartune_server/game/handlers/systems.py#L492) | 1 de EXP por pedra (sem captura do treino) |
| [game/handlers/systems.py:609](../src/wartune_server/game/handlers/systems.py#L609) | a vocação (vocationGrades/Gp) que vem depois não tem tabela nem captura; começa no 1 |
| [game/handlers/tower.py:32](../src/wartune_server/game/handlers/tower.py#L32) | sem progresso salvo da torre; andar e recorde reais precisam do progresso |
| [game/handlers/tower.py:59](../src/wartune_server/game/handlers/tower.py#L59) | 8296 não entra no labirinto: os nós e monstros dos MapInfo 8001+ não estão nos templates (o .maps só tem o desenho) e não há captura do 8296 nem da resposta |
| [game/handlers/treasure.py:24](../src/wartune_server/game/handlers/treasure.py#L24) | o oficial sorteia a qualidade do mapa; sem essa tabela, dá sempre o de bronze (2190001) |
| [game/handlers/vehicle.py:34](../src/wartune_server/game/handlers/vehicle.py#L34) | a tecnologia de tanque não tem tela nem regra de evolução no cliente, fica 0 para todos |
| [game/handlers/vehicle.py:69](../src/wartune_server/game/handlers/vehicle.py#L69) | id = templateId (o oficial manda um id de banco; o cliente só usa templateId) |
| [game/handlers/vehicle.py:377](../src/wartune_server/game/handlers/vehicle.py#L377) | os mapas de guerra com veículos (CampaignInfo Types 9 / GvG) não existem; dano e alvos |
| [game/handlers/vip.py:139](../src/wartune_server/game/handlers/vip.py#L139) | o 1 não tem regra conhecida |
| [game/handlers/vip.py:152](../src/wartune_server/game/handlers/vip.py#L152) | o VIP que vence sozinho não avisa a guilda (não há relógio de vencimento) |
| [game/handlers/vip.py:174](../src/wartune_server/game/handlers/vip.py#L174) | presentear um amigo exige gravar o snapshot de outro personagem (talvez offline) |
| [game/handlers/vip.py:183](../src/wartune_server/game/handlers/vip.py#L183) | o oficial soma Vip_DailyAddGp a cada dia de VIP; aqui entra tudo na compra |
| [game/handlers/vip.py:212](../src/wartune_server/game/handlers/vip.py#L212) | a captura só tem itens; moeda vai como nas outras recompensas |
| [game/handlers/vip.py:279](../src/wartune_server/game/handlers/vip.py#L279) | se o oficial cobra a atualização, o preço não está na evidência.""" |
| [game/handlers/vip.py:399](../src/wartune_server/game/handlers/vip.py#L399) | presente para amigo (friendId de outro) igual ao VIP: precisa gravar outro personagem |
| [game/handlers/vip.py:518](../src/wartune_server/game/handlers/vip.py#L518) | o mapa do teste (andar, buffs na batalha) não existe no servidor; sem ele não há onde |
| [game/rankings.py:28](../src/wartune_server/game/rankings.py#L28) | tamanho do fight.xml sem arquivo oficial para conferir; o SortModel pagina o que vier |
| [game/vehicles.py:62](../src/wartune_server/game/vehicles.py#L62) | regras da partida de veículos que o cliente não tem (tamanho mínimo, caixas, pontos, chefe, armadilha, prêmio e EXP); trocar com captura de uma partida |
| [game/vehicles.py:397](../src/wartune_server/game/vehicles.py#L397) | andar de veículo sem conferir a velocidade, só se os tiles são andáveis |
| [game/vehicles.py:506](../src/wartune_server/game/vehicles.py#L506) | skill de caixa sem Maximum (-1) vale um uso |
| [game/vehicles.py:556](../src/wartune_server/game/vehicles.py#L556) | quantidades do prêmio e a EXP do tanque no fim da partida |
| [game/vehicles.py:590](../src/wartune_server/game/vehicles.py#L590) | dano do veículo = ataque × Power% - metade da defesa (mínimo 1), com os buffs de ataque |
| [game/vehicles.py:762](../src/wartune_server/game/vehicles.py#L762) | chefe dos veículos parado no meio, um golpe a cada 5 s num tanque ao alcance |
| [game/handlers/warfield.py:29](../src/wartune_server/game/handlers/warfield.py#L29) | sem o mapa do campo de batalha nada abre: sem o 0 nem o 4248 nas viradas (#133, #3110); mandar 0 e empurrar no relógio (20008) quando o campo existir |
| [game/handlers/worldboss.py:408](../src/wartune_server/game/handlers/worldboss.py#L408) | o mesmo 8264 é o reviver do altar de guilda (``RiverView`` tipo 2, paga em contribuição); |
| [game/items.py:56](../src/wartune_server/game/items.py#L56) | um item novo por entrada, sem empilhar (igual ao 5006); empilhar quando o |
| [game/mall.py:34](../src/wartune_server/game/mall.py#L34) | lock global do processo (um servidor por processo). Por anúncio se a fila pesar. |
| [game/mall.py:36](../src/wartune_server/game/mall.py#L36) | o agendador roda a cada 60 s sem dormir até o menor ends_at: até 60 s de atraso no encerramento |
| [game/mall.py:44](../src/wartune_server/game/mall.py#L44) | arredondamento para baixo; o texto do cliente não diz como o oficial arredonda |
| [game/mines.py:29](../src/wartune_server/game/mines.py#L29) | (dedução) o ciclo vencido só renova no próximo acerto de ouro, login, 8201 ou 5160 e começa nessa hora; |
| [game/monsters.py:21](../src/wartune_server/game/monsters.py#L21) | prêmio 0 (nenhuma fonte; ver docs/cidade-externa.md) e luta sozinho (o state 4 deixa |
| [game/outer_city.py:34](../src/wartune_server/game/outer_city.py#L34) | 2 pilhas de 10102 com 282 de vida cada, as do robô de grau 8 (o único do catálogo); outro grau sem captura |
| [game/outer_city.py:81](../src/wartune_server/game/outer_city.py#L81) | o oficial escolhe um ponto livre; usamos o centro (só turco: transfer, mapa 2 em 2191,1952, perto do |
| [game/rules.py:38](../src/wartune_server/game/rules.py#L38) | guerreiro e caçador são o espelho |
| [game/rules.py:73](../src/wartune_server/game/rules.py#L73) | o total é dedução (o cliente só lê o pronto) e a batalha do mascote (``arena.pet_unit``) não soma. |
| [game/rules.py:345](../src/wartune_server/game/rules.py#L345) | teto de salto em vez da lista exata de saveId; a lista seria o próximo passo |
| [game/rules.py:354](../src/wartune_server/game/rules.py#L354) | busca linear nas 352 linhas a cada chamada; indexar por TemplateId em GameTemplates se pesar. |
| [game/rules.py:420](../src/wartune_server/game/rules.py#L420) | sem a poção de Captain (add_gp não recebe a hora); passar now por add_gp/grant se pesar |
| [game/social.py:177](../src/wartune_server/game/social.py#L177) | página única; paginar se a lista passar do tamanho de um pacote (200 amigos cabem). |
| [game/timebox.py:63](../src/wartune_server/game/timebox.py#L63) | dedução, a fórmula do oficial não está no cliente; nível x minutos fora, até 8 horas |
| [game/worldboss.py:38](../src/wartune_server/game/worldboss.py#L38) | janela que cruza a meia-noite não existe nos templates; não é tratada. |
| [http/app.py:242](../src/wartune_server/http/app.py#L242) | respostas do suporte sempre vazias até existir o atendimento |
| [services/characters.py:93](../src/wartune_server/services/characters.py#L93) | cada jogador só vê o próprio castelo, então dividir o ponto não colide; com mapa |
