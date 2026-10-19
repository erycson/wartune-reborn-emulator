# Pendências: o que ainda não é igual ao oficial

Todo opcode que o cliente manda tem handler (`tests/game/test_cobertura_c2s.py`), mas "tem handler" não é
"faz o que o oficial faz". Esta é a lista do que falta, por sistema, com o motivo. O detalhe de cada item
está na doc do sistema (link na coluna). No fim, a lista gerada de todas as simplificações marcadas no
código com `# ponytail:`.

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
| Loja de honra (ShopType 3): medalhas com `ValidDate` (7, 15 e 30 dias) | 10 | ~~falta item com validade~~ **feito**: `items.valid_date`/`begin_date` (0037), no 115 e apagado no 8346, no login e no relógio (20008). **dedução**: apagar sem aviso e a varredura do servidor. **falta captura**: deixar uma medalha de 7 dias vencer no oficial e capturar o login e o 8346 (ver itens.md) |
| Loja do labirinto (ShopType 4): moeda e preço (Labirent Parası, `MazeCoin`) conferidos na captura (105 e 110). Andar: o cliente esconde o botão com `MazeLayers` > `maxIndex` (60 fixo) ou `MazeLayers2` > 0, e o servidor recusa o mesmo | 119 (23 e 22 bloqueadas) | **dedução** no código. **falta**: o `maxIndex` depois de avançar no labirinto (captura de 4205 com o labirinto mais fundo). O progresso real do labirinto não existe aqui |
| Loja misteriosa (ShopType 5): peso `Rands` | 110 | **dedução**: sorteio uniforme de 8 itens, sem o peso |
| Presente para outro jogador (`receiveId`) | — | recusado. **depende de**: entrega pelo correio na compra |
| Mochila cheia | — | recusa (o oficial manda pelo correio, resultado 12) |
| Ofertas da home (4238), compra coletiva (8645), relâmpago (8632) | — | nenhuma ativa. **depende de**: configuração de ofertas do operador |

Itens fora da loja:
- Refino da forja (8336): sorteio uniforme entre os 1584 atributos com `Grades` > 0 (visto: os 42 das capturas têm Grades 1–10). Falta o peso por nível e o custo do cadeado: **precisa de captura** 8336 → 4258 com cadeado e itens de NeedGrades baixo e alto.
- Decomposição (8340), avaliação de moda (8781), moldagem (8644), composição de moda (8594), troca na bancada (8595). **sem dado**.
- Itens novos ganham só o `DefaultSkill` como atributo sorteado (o oficial sorteia `RandomSkillCount`). *(visto)* o Kronos’un Yetkisi da loja do labirinto (`yeralti_labirent_marketi_alisveris`) chegou com cinco `randomSkill`; falta a regra do sorteio (**precisa de captura** de mais compras de equipamento com `RandomSkillCount`).
- Sem teto diário para Beden e EXP vindos de itens. **dedução**.
- Títulos (8597): lista vazia. **depende de**: conquistas.
- ~~Poções de atributo sem efeito~~: somam no `total*` do herói (150 no uso e no 8283); ~~pergaminho de EXP fora do
  relatório do fim da masmorra~~: aplicado no 137. **dedução**: Defense = Agility, o 150 e o `propJoin`; **precisa de
  captura** ([itens.md](itens.md#pergaminhos-de-efeito-sontype-201)).

## Minigames e eventos ([eventos.md](eventos.md))

8 de 38 são reais: fundo de novato (8751), fundo normal (8703), árvore dourada (8604) e labirinto de gemas (9508, 9509, 9513, 9516, 9517). 2 recusam sem efeito (9510, 9515: ajuda de amigo do labirinto). Os outros 28 respondem o estado "fechado" que o cliente sabe mostrar. Calendário de cada um: `game_settings` (0041), do operador.

| Minigame | Opcodes | Falta |
|---|---|---|
| ~~Garrafa~~ Árvore dourada | 8604 | **real** (0041, #72). **dedução**: início da edição, pesos (uniforme), dono do andar = quem bateu, raro = `isNewItems`, ordem das respostas, "once per day" do help não aplicado. **precisa de captura**: 8604 de cada op e 4825 ([eventos.md](eventos.md)) |
| ~~Fundo normal~~ | 8703 | **real** (0041, #86). **dedução**: `activeType` 2/0 fora da compra, compra recusada fora da janela. **precisa de captura**: compra e resgate |
| Quiz | 9501 | `HeartTempInfos` não tem resposta certa (são perguntas de personalidade); agenda do help (seg/qua/sex 19:30) diferente do template (1,3,5,6 às 14:35). **precisa de captura** de uma rodada |
| Labirinto de gemas | 9508–9517 | **real** ([eventos.md](eventos.md)). **precisa de captura**: subida de nível (tabela de `maxExp`), pesos dos prêmios, o que o oficial faz com troca sem combinação, bolsa do prêmio das caixas (9513), período da renovação diária (dedução), ajuda de amigo (9510/9515/4925), ranking semanal, preço e teto da compra (dedução) |
| Estrada dourada | 9520–9522 | casas (4933 `cellInfo`) e custo dos dados: **precisa de captura** (abrir e jogar nos 3 modos) |
| Pesca, caça ao tesouro, minério | 9507, 9502, 9645 | regras de aparecimento, nós e prêmios (**precisa de captura**: abrir e jogar uma vez cada); no 9645 o cabeçalho (`extend1`) que separa minério de super assinatura não chega ao handler |
| Loteria, caça-níquel, cadeiras, caixa de ano novo, história, sorteio de grupo | 8748/8750, 9500, 9638, 8994, 8629/8630, 9523 | template e tabela de prêmios: a captura EN só os tem fechados. **precisa de captura** num dia em que o oficial abre |
| Recuperar EXP | 9503 | **depende de**: os sistemas (campanha, arena, chefe, imposto) gravarem a participação do dia (a fórmula do custo está conferida) |
| Troca da sorte | 9610 | a tabela da captura venceu em 2026-05-17 |
| Privilégio 360 | 8722/8723 | só para o agente 360 do cliente |
| Fundo de novato | 8751 | **dedução**: janela oficial desconhecida (`endDate` 2099) |

Outros eventos:
- 8519/8521 (roleta VIP) são reais ([eventos.md](eventos.md#vip-e-contrato-do-rei)); 8518 responde o 4412 vazio (contadores do painel do dia: **depende de** cada sistema contar); 8756 só registra; loja de teste (8582) recusa: o mapa de teste não existe.
- Quadro de recompensas 8291 sem passe, 8298, 8729: **depende de** batalha, missões e mensagens reportarem progresso.
- Tipos de SumActive além de 13/14 ficam em status 3.
- Devoção (leed): ~~8, 15, 17, 18, 24, 25, 33 sem gancho~~ e ~~devoção do VIP~~ feitos (18, 24, 25 por **dedução**
  do título; VIP pelo tipo 2 "Devotion Bonus"). **Depende de**: 13 arena em grupo, 22 "Altar of Ennoblement" (sistema
  desconhecido), 23 entrada no labirinto (Catacombs), 27 campo de batalha, 28 Spire. **Precisa de captura**: VIP 3+
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
- Masmorra Kurt İni (1001, mapas 1011 e 1021, 5039): feita, com nós, névoa, lutas, Pandora, baús e fim; a carta sai no clique (5122, depois do 135), uma por mapa ([salas-campanha.md](salas-campanha.md)). O relay atrasa o S>C uns 30 pacotes: não use a ordem C>S x S>C dele. Falta: loot de batalha ("Kazanılan:Kurt Dişi" em 111 e 115, 4103 com `signId`/`baseItem` 2040101, só no 1021; nenhuma tabela do tempinfos liga lobo a item); resposta do 5180 (1 sair, 2 de novo); cartas pagas (`isPay`, `payCardCount`); recusa do 5039 sem Beden (o gasto de 20 por mapa está feito); missões (112, 4476/4484); progresso da masmorra (só a carta é gravada: sair recomeça no 1011); repetir depois do 1021 (dedução); EXP do fim (630) é texto copiado da captura (o `BaseGp` 600 não bate); baú 101104 (Bakır Hazinesi) nunca visitado na captura; 5121 sem captura; chance de cada item da carta.
- Caixa Pandora (5033 com S>C 29, mapId 879/880, nodeId 101107/102107): feita na masmorra, com o buff 1301/1701 da captura. Falta a recompensa além do buff (a captura traz `itemTempId` 0). Exército na campanha (5121): falta captura da resposta. **depende de**: nada agora; o progresso de campanha ainda não é salvo.
- Exército do sistema (5038): lista só para 1011, 1021 e 2011 (captura). Os demais mapas precisam de captura do 5038.
- Torre (8297/8300): limites vistos na captura; totalGp e itens **dependem de** progresso da torre.
- Varredura (8528): falta captura do pedido C>S. Custos em `ConfigInfos` (campanha 5000 ouro e 300 s; labirinto 1000 e 30 s por andar). **depende de** progresso de campanha.
- Guarda de batalha (8742): o login oficial manda 4631 com `watchInfo` e o servidor não manda. **depende de** modelar gemas.
- Pedágio (8752–8755): fechado, sem agenda. Configuração e tabelas de recompensa existem no template, mas o parser descarta as tabelas aninhadas.
- Link de sala no chat (9504): feito (4913). Sala inexistente: sem resposta (dedução).
- 5027 só registra (aba de convite que não existe no cliente); 8740 sem remetente no cliente (efeito deduzido).

## Cidade externa e mapa do mundo ([cidade-externa.md](cidade-externa.md), [mundo-compartilhado.md](mundo-compartilhado.md))

- Mapa compartilhado: **parcial**. O mapa do castelo é uma instância de cada conta (minas e castelo só do
  jogador). Nos mapas 1 a 5 o 4129 leva os castelos de outros jogadores nas grades. Não existem: exércitos
  alheios andando (169, 4167, 4168; precisa de presença entre sessões), terras selvagens fora das 4 minas do
  mapa 100, os 2 robôs da instância e os castelos NPC "Köy" (precisa da tabela de terras e robôs por mapa).
  O 5160 luta só contra mina livre; castelo e exército alheio só param o exército. 8488 (PvP no mapa) e 5004
  só registram. **precisa de captura**: resposta do 5160 e do 8488 contra castelo ou exército alheio.
- Minas de ouro: refresh de 12 h feito, por jogador (`castles.mines_at`, `createDate` no fuso UTC+3; nível
  sorteado de novo a cada ciclo, ocupação do ciclo anterior vence). **precisa de captura**: a perda de soldados
  numa derrota contra a mina (nas vitórias nenhum morre), o refresh com o jogador online e um login mais de
  12 h depois do último (para saber quando o ciclo abre).
- Monstros dos Wilds: **parcial**. Aparecem no 4129 dos mapas 1 a 5 (sorteio por mapa e ciclo de
  `WorldMapFreshTime`), dá para lutar e abater (5160, battleType 2), os contadores do dia e a regra dos 15
  níveis valem, os chefes vão no painel 4938 e a Divine Light tira a névoa do mapa. Quantidades por mapa,
  `fightCapaity` fora do 210127 e o formato da 157 são **dedução**. **precisa de captura**: uma luta com
  monstro do mapa (157) e o baú (4940/9526). O baú existe, com a tabela de queda `world_monster_drops`: chances
  e faixas de nível são **dedução** sobre a wiki e relatos ([cidade-externa.md](cidade-externa.md)). Luta em
  equipe/entrar na luta não existe.
- "Emek oranınız ..." (83, taxa de trabalho): o sistema não existe.
- Subida de nível: o oficial manda também 139, 100 e 4640 (replay #625-#628); aqui só o 150.
- Presente da atividade de soma (8586 tipo 2, replay #678): recusado.
- ~~Ataque a castelo: 9506 compra tentativas, mas nada as gasta.~~ O 5160 no castelo-robô gasta e grava na hora; o 9506 cobra AddAttck_Point (395 EN). Castelo de jogador: segue sem luta (exército alheio).
- Gancho (8293, 8525, 8292, 8295): respondem zerado; o ganho offline do gancho não existe.
- Passe de progresso (8636/8637): área 1 fixa, prêmio recusado. **depende de**: 8753/8755.
- Mapa do tesouro (8744): só receber o mapa; atualizar, cavar, usar e prêmio **dependem de** pontos de tesouro e batalha em equipe. Limite diário e nível 55 são **dedução**.
- 8699 (guia do tutorial) sem nó de coleta para abrir; 8745 depende do mapa da guilda; 8535 depende do mapa de PvP do chefe.
- Mineração de ametista (mapa 30000, teleporte do space): **depende de** minas.

## Mercado entre jogadores ([mercado.md](mercado.md))

- Encerramento agendado a cada 60 s (`game/mall.py` `run`): um anúncio vencido sai até 60 s depois do fim, mesmo sem pedido ao mercado. Antes, só o próximo pedido encerrava.
- *(cliente, ajuda do leilão)*: imposto de 20% do vendedor, compra pelo fixo entregue pelo correio, limite diário de compra por nível (500/1000/1500, −52), piso de 2 no inicial, até 9 unidades. **dedução**: duração 1–72 h (a tela oferece 8, 24 e 48), preço mínimo `StartingPrice × count`, teto de página 50, primeiro lance ≥ inicial, arredondamento do imposto e bordas das faixas do limite.
- **precisa de captura**: valor da taxa em ouro do anúncio (a ajuda confirma que existe; −10); nível de abertura do leilão (`{0}` da `AuctionShopTip`); vínculo (−7 no cliente é "item vinculado"; o servidor não tem o dado e usa −7 para item travado); lance igual ao inicial; líder subindo o próprio lance (−17); cartas oficiais (título, texto, momento); `hour` no 8448 (horas ou índice da opção). Detalhe em [mercado.md](mercado.md#dependências).
- Lance e compra pagam só elmas (sem vinculado), sem prova de que o oficial restrinja.
- Lista do mercado (8450) e busca (8457) ignoram a ordenação.
- Cancelar parte de uma pilha não reempilha com a original.
- Correio não é apagado por validade; uma limpeza futura precisa pular carta com item não retirado.

## Guilda ([guilda.md](guilda.md))

- Mapas e batalhas das atividades (altar 7601, terra secreta 7501, guerra 4501, entre servidores 4601) e os
  pacotes dentro deles: recusados. **precisa de captura**: os nós de 7601, 7501 e 4501 não estão em nenhuma
  fonte; o 4601 tem os nós, mas o evento está fechado pelo template. O que capturar está em
  [guilda.md](guilda.md#pendências).
- Rankings e prêmios das atividades: o gancho `add_to_box` existe, ninguém chama (depende das atividades).
- Bênção (5145): o prêmio é sempre um item do mercado liberado pelo nível do altar, na casa 1. A tabela do
  oficial e a bênção rápida (x10) **precisam de captura**. O prêmio pendente agora fica na linha do membro.
- Eleição (8241/8481): nada inicia a eleição (só editando o banco). **sem dado**.
- 8335 só registra (`speakTimes` sempre 0). **sem dado**: anúncio de recrutamento.
- Sair da guilda antes de pegar o prêmio da bênção perde o prêmio (*ponytail*).

## Herói, exército e pets ([heroi-exercito.md](heroi-exercito.md))

- Pets: composição de um pet (8621 op 13) pela `PetComponseInfos`: 24 de 28 receitas (as 4 restantes dão tipos 117–119, sem template). Fusão de dois pets (15): **precisa de** `PetTempInfos` dos tipos 117–119 e dos itens 2125126/127/128/130/134. Devorar, crescimento, skills, sacrifício, treino e resistência (1, 4–8): **sem dado** (o cliente não diz o ganho por item ou ação; ver heroi-exercito.md).
- Montaria: estrelas/bênção, rei das montarias, loja, refino, voo (8529 outras ops, 8843). **sem dado** (tela fora do decompilado).
- Vocação depois do tipo 102 (8643). **sem dado**.
- Cartas de poder (9505): cartas e EXP vêm da batalha (4902). ~~Bônus de coleção falta~~: feito no 4905 (powcard_suite_slots); os graus dos degraus 2 e 3 são **dedução** (**precisa de captura**, ver heroi-exercito.md) e o bônus não entra na batalha.
- Posição do herói em salas (8277/8278) e teleporte (8326): **depende de** salas/cidade externa.
- Ganhar montaria, pet ou carta: **depende de** uso de item, missão ou batalha.
- `battle.py` ainda não lê a tropa (`rules.battle_pawn`) nem os buffs (talento, runas, destino, dragão, cartas).
- Destino tipos 2100/2200 nunca abrem. **sem dado**.
- **dedução**: chance do sorteio de estrelas, EXP de destino por pedra, atributos e pontos dos pets por nível.

## Castelo e fazenda ([castelo.md](castelo.md))

- ~~Fazenda de amigo~~: roubar, reviver, verme/erva e regar a árvore de amigo feitos, só entre amigos, com os limites do cliente. **dedução/config**: roubo de 10% (internet), grau de amizade = 1 + pontos // 10, amizade +1 dos dois lados. **precisa de captura**: roubo e praga na fazenda de amigo, tabela de grau de amizade (passos em castelo.md).
- Melhorar terreno e pets da fazenda (15044 ops 9–16): sem remetente no cliente; a fazenda fica em 3 terrenos.
- Colher a árvore (5178): **precisa de captura**; nenhuma tem `fruitCount` > 0. Passos e itens em castelo.md.
- Recompensa offline ×1,5/×2 (8287): preço desconhecido. **sem dado**.
- 8255 (batalha em grupo), 8562 (trégua), 5179 (terras selvagens): respondem vazio. **depende de** esses sistemas.
- Rendimento: o oficial soma +30/h que não explicamos; sem bônus de terras, guilda ou efeitos.
- **dedução**: EXP offline = nível × minutos (até 8 h), acelerar a fazenda amadurece na hora, caixa por tempo vira à meia-noite UTC. Ouro de regar: visto (× 20); que seja o nível de jogador do dono (e não o grau da fazenda) é dedução.

## PvP ([pvp.md](pvp.md))

- Lordes (8710–8721), lordes casados (8975–8981), campo de guerra (8332/8334/8337/8338), campo de minas (8633), 8635: parciais. **sem dado**.
- Torneio de fadas: usa os pets salvos; a posição dos pets do oponente (`pos` = índice + 3) é **dedução**.

## Social, chat e VIP ([social.md](social.md), [chat.md](chat.md))

- Canal de time (6) no chat: recusado.
- ~~VIP ignorado em limite de amigos e 5172 índice 0~~ **feito** pelo cliente (`VIPModel.vipFriendPrivilege`/`vipCoolPrivilege`). Cota de cornetas: `game_settings.vip_bugle_bonus` (0037), padrão 0 = **sem fonte**; **falta captura** do 8705 → 4500 de uma conta VIP (ver chat.md).
- Presentes do VIP/contrato do rei para amigo (8513/8540): recusados (gravar outro personagem).
- ~~Mochila de 42 espaços base em coliseu, fazenda, caixa por tempo, correio e `rewards.can_grant`~~ **feito**: todos usam `bag.free_positions` (`bag.capacity`: 42 + comprados, 217 alugada).

## Simplificações marcadas no código

Lista gerada de todo `ponytail:` em `src/` (atualize com `grep -rn "ponytail:" src --include=*.py`).

| Onde | Simplificação |
|---|---|
| [game/arena.py:293](../src/wartune_server/game/arena.py#L293) | o caçador perde até o nível ~30 porque o ataque |
| [game/arena.py:303](../src/wartune_server/game/arena.py#L303) | a captura tem 2 arqueiros 10202 com o robô, mas lá o jogador também tinha soldados; |
| [game/arena.py:362](../src/wartune_server/game/arena.py#L362) | perda não observada, não tira pontos |
| [game/arena.py:366](../src/wartune_server/game/arena.py#L366) | fórmula de vida do pet desconhecida; MaxHp + nível × GrowthRate / 9 dá ~5% da captura |
| [game/arena.py:407](../src/wartune_server/game/arena.py#L407) | ~ o dano da captura (golpe básico ≈ vida/40) |
| [game/bag.py:92](../src/wartune_server/game/bag.py#L92) | o oficial sorteia randomSkill_1..N (RandomSkillCount); a tabela do sorteio não está nos |
| [game/battle.py:289](../src/wartune_server/game/battle.py#L289) | a iniciativa do oficial não foi decifrada; aliados NPC, inimigos e o herói por último |
| [game/battle.py:376](../src/wartune_server/game/battle.py#L376) | fórmula de dano desconhecida. PvE calibrado na captura do tutorial (herói mata os |
| [game/builders/login.py:76](../src/wartune_server/game/builders/login.py#L76) | bate com o oficial no nível 1 (199); nível 3 dá 291 contra 278. Falta a fórmula real. |
| [game/builders/login.py:248](../src/wartune_server/game/builders/login.py#L248) | 1 exército por personagem; tabela própria quando houver tropas extras |
| [game/campaign.py:214](../src/wartune_server/game/campaign.py#L214) | ``StandSecond`` não entra em nota nenhuma do 137 (não há campo de tempo avaliado); time/friend/vip |
| [game/castle.py:81](../src/wartune_server/game/castle.py#L81) | sem bônus de guilda/efeitos; o oficial soma +30 que não sabemos de onde vem |
| [game/castle.py:162](../src/wartune_server/game/castle.py#L162) | sem o bônus de raça/efeitos do limite (PlayerEffect.getTransferPowerLimitAddition) |
| [game/drops.py:43](../src/wartune_server/game/drops.py#L43) | sem filtro de classe (o mesmo mago tirou 1080013, Job 3, e 1080002, Job 1,2); peso = vezes visto, |
| [game/events.py:52](../src/wartune_server/game/events.py#L52) | janela diária (outros ``begin_time``/``end_time``) vira um intervalo só; o oficial só mostrou 0/86399. |
| [game/farm.py:20](../src/wartune_server/game/farm.py#L20) | sem upgrade de terra (opType 9 não tem sender) |
| [game/gemmaze.py:93](../src/wartune_server/game/gemmaze.py#L93) | o período (dia, UTC) não foi capturado; os movimentos comprados não somem (fica o maior). |
| [game/gemmaze.py:200](../src/wartune_server/game/gemmaze.py#L200) | 5 ou mais em linha segue a conta de 3 e 4 (não foi capturado) |
| [game/gemmaze.py:209](../src/wartune_server/game/gemmaze.py#L209) | pesos dos três vistos no banco (padrão iguais); a tabela oficial precisa de captura |
| [game/gemmaze.py:212](../src/wartune_server/game/gemmaze.py#L212) | troca sem combinação é aceita e gasta movimento (o cliente troca na tela e não desfaz; |
| [game/guild.py:162](../src/wartune_server/game/guild.py#L162) | só os 50 últimos na memória; o banco guarda todos |
| [game/handlers/account.py:20](../src/wartune_server/game/handlers/account.py#L20) | prazo do reset não está no cliente nem nas capturas; ajustar se aparecer |
| [game/handlers/account.py:190](../src/wartune_server/game/handlers/account.py#L190) | sala de um jogador só; broadcast quando houver sala compartilhada |
| [game/handlers/arena.py:358](../src/wartune_server/game/handlers/arena.py#L358) | limite de compras do torneio não está no cliente nem nos templates; 10/dia como no coliseu |
| [game/handlers/army.py:238](../src/wartune_server/game/handlers/army.py#L238) | bênção cheia = sorteio garantido um grau acima; a regra exata do oficial não tem captura |
| [game/handlers/army.py:277](../src/wartune_server/game/handlers/army.py#L277) | grade 3x3 da formação; conferir limites quando houver captura |
| [game/handlers/army.py:302](../src/wartune_server/game/handlers/army.py#L302) | só a posição do próprio herói é gravada; |
| [game/handlers/army.py:322](../src/wartune_server/game/handlers/army.py#L322) | a posição do exército no mapa externo não é gravada (sistema do mapa externo).""" |
| [game/handlers/battle.py:35](../src/wartune_server/game/handlers/battle.py#L35) | a postura não muda o dano (a fórmula real não é conhecida) |
| [game/handlers/campaign.py:583](../src/wartune_server/game/handlers/campaign.py#L583) | sem energia não entra e não responde; a recusa do oficial precisa de captura com estamina < 20 |
| [game/handlers/campaign.py:660](../src/wartune_server/game/handlers/campaign.py#L660) | colheita sem limite nem espera (a captura colheu duas vezes seguidas a mesma pilha, #1847 e #1861); |
| [game/handlers/campaign.py:973](../src/wartune_server/game/handlers/campaign.py#L973) | carta paga (isPay, autoChest) tratada como a grátis: price 0 e uma só por etapa; cartas pagas extras |
| [game/handlers/campaign_map.py:37](../src/wartune_server/game/handlers/campaign_map.py#L37) | mapa sem captura manda lista vazia; falta a lista de cada mapa (nós do .maps). Não muda estado |
| [game/handlers/castle.py:299](../src/wartune_server/game/handlers/castle.py#L299) | trégua ainda não existe; zera e confirma.""" |
| [game/handlers/chat.py:28](../src/wartune_server/game/handlers/chat.py#L28) | o cliente não limita a guilda (ChatHelper); 1 s contra spam |
| [game/handlers/chat.py:30](../src/wartune_server/game/handlers/chat.py#L30) | o cliente não limita o privado; 1 s contra spam |
| [game/handlers/chat.py:178](../src/wartune_server/game/handlers/chat.py#L178) | "cena" = todos online até existir o registro de cenas (cidade do céu). |
| [game/handlers/events.py:194](../src/wartune_server/game/handlers/events.py#L194) | só os tipos 13 e 14 têm regra; os outros ficam "ainda não" até alguém implementar |
| [game/handlers/events.py:435](../src/wartune_server/game/handlers/events.py#L435) | nenhum desses sistemas conta ainda; lista vazia = tudo zerado no painel.""" |
| [game/handlers/farm.py:257](../src/wartune_server/game/handlers/farm.py#L257) | dono offline vem do banco; dois ladrões ao mesmo tempo em cópias diferentes podem se sobrepor |
| [game/handlers/farm.py:293](../src/wartune_server/game/handlers/farm.py#L293) | o texto do oficial (farm.view.FarmOperMenu.accelerateTip) não está decompilado; |
| [game/handlers/farm.py:336](../src/wartune_server/game/handlers/farm.py#L336) | sem fruto (quando a árvore frutifica não está nas capturas nem no cliente decompilado) |
| [game/handlers/farm.py:429](../src/wartune_server/game/handlers/farm.py#L429) | um snapshot por amigo (até 100); se pesar, ler só terras e castelos |
| [game/handlers/forge.py:32](../src/wartune_server/game/handlers/forge.py#L32) | o refino sorteado fica na memória até o 8339 (some se o servidor reiniciar) |
| [game/handlers/forge.py:211](../src/wartune_server/game/handlers/forge.py#L211) | autoBuy (comprar o que falta) não |
| [game/handlers/forge.py:223](../src/wartune_server/game/handlers/forge.py#L223) | o espaço é conferido antes de consumir (pode recusar quando os materiais liberariam lugar) |
| [game/handlers/forge.py:275](../src/wartune_server/game/handlers/forge.py#L275) | a tabela de sorteio do oficial não está nos templates: sorteio uniforme entre os atributos |
| [game/handlers/friends.py:32](../src/wartune_server/game/handlers/friends.py#L32) | limites do cliente não achados (módulo de UI ausente) |
| [game/handlers/friends.py:322](../src/wartune_server/game/handlers/friends.py#L322) | ``pageIndex`` tratado como 1-based (UI ausente).""" |
| [game/handlers/gemmaze.py:71](../src/wartune_server/game/handlers/gemmaze.py#L71) | o oficial manda 0 para personagem novo; o contador não foi capturado |
| [game/handlers/gemmaze.py:77](../src/wartune_server/game/handlers/gemmaze.py#L77) | ranking semanal não existe aqui (o oficial manda 1771 para um jogador de topo) |
| [game/handlers/gemmaze.py:134](../src/wartune_server/game/handlers/gemmaze.py#L134) | sem subida de nível (a tabela de EXP por nível não foi capturada): curExp passa de maxExp |
| [game/handlers/gemmaze.py:147](../src/wartune_server/game/handlers/gemmaze.py#L147) | o semanal soma o mesmo que o do dia e zera na semana nova (``gm.refresh``, dedução) |
| [game/handlers/gemmaze.py:206](../src/wartune_server/game/handlers/gemmaze.py#L206) | a caixa vai para a bolsa do labirinto (o ícone voa para ela, como o das gemas); a bolsa |
| [game/handlers/gemmaze.py:226](../src/wartune_server/game/handlers/gemmaze.py#L226) | o template não diz a moeda nem o limite diário: diamante (ou vinculado com buyTypes 2) é dedução |
| [game/handlers/gold_tree.py:46](../src/wartune_server/game/handlers/gold_tree.py#L46) | linhas da sorte guardadas em memória (o #71 mostra 3); perdem-se no restart |
| [game/handlers/gold_tree.py:149](../src/wartune_server/game/handlers/gold_tree.py#L149) | ``isVip`` falso (o dono pode estar offline).""" |
| [game/handlers/guild/altar.py:67](../src/wartune_server/game/handlers/guild/altar.py#L67) | a tabela de prêmios do oficial não está nos templates; o prêmio é sempre um item |
| [game/handlers/guild/altar.py:123](../src/wartune_server/game/handlers/guild/altar.py#L123) | o prêmio fica na linha do membro, então sair da guilda antes de pegar perde o prêmio |
| [game/handlers/guild/box.py:92](../src/wartune_server/game/handlers/guild/box.py#L92) | o correio por mochila cheia é dedução (o |
| [game/handlers/guild/election.py:19](../src/wartune_server/game/handlers/guild/election.py#L19) | o oficial abre a eleição quando o chefe some por muitos dias; a regra não está no |
| [game/handlers/guild/info.py:231](../src/wartune_server/game/handlers/guild/info.py#L231) | o ``same`` (renomear grátis depois de juntar servidores) é cobrado igual. |
| [game/handlers/guild/members.py:210](../src/wartune_server/game/handlers/guild/members.py#L210) | o oficial tinha guildas-robô; aqui vem o convite da guilda aberta com mais membros |
| [game/handlers/guild/upgrades.py:75](../src/wartune_server/game/handlers/guild/upgrades.py#L75) | não se sabe se o oficial aceita diamante vinculado aqui; gasta primeiro o vinculado |
| [game/handlers/guild_events.py:67](../src/wartune_server/game/handlers/guild_events.py#L67) | falta o sistema de mapas de campanha (só existe o do tutorial) e as ondas de |
| [game/handlers/hero.py:128](../src/wartune_server/game/handlers/hero.py#L128) | a EXP gasta sai da EXP do nível atual (c.gp); conferir com captura se o oficial |
| [game/handlers/hero.py:294](../src/wartune_server/game/handlers/hero.py#L294) | o preço sobe com diamondIndex (usos no dia); sem contador diário fica no primeiro |
| [game/handlers/items.py:289](../src/wartune_server/game/handlers/items.py#L289) | sem teto de uso por dia (a captura tem um uso só); o gasto da entrada não existe aqui, falta |
| [game/handlers/items.py:506](../src/wartune_server/game/handlers/items.py#L506) | depois de juntar pilhas, fecha os buracos na mesma ordem (dedução) |
| [game/handlers/mail.py:38](../src/wartune_server/game/handlers/mail.py#L38) | correio de guilda (sendType 2) recusado até existir guilda. |
| [game/handlers/mall.py:47](../src/wartune_server/game/handlers/mall.py#L47) | a tela oferece 8, 24 e 48 h (Auction.SubmitHour1..3); o valor enviado não está no decompilado |
| [game/handlers/mall.py:50](../src/wartune_server/game/handlers/mall.py#L50) | a lista pede 9 por página (8449, 8452); o teto de 50 é dedução, a tela de leilão não está no decompilado |
| [game/handlers/mall.py:56](../src/wartune_server/game/handlers/mall.py#L56) | o texto repete 60 e 70 nas duas faixas; aqui 60 e 70 já são da faixa de cima. Abaixo de 40 vale |
| [game/handlers/marriage.py:7](../src/wartune_server/game/handlers/marriage.py#L7) | pedidos, ofertas de casamento e pedidos de divórcio ficam em memória (somem se o |
| [game/handlers/minigames.py:129](../src/wartune_server/game/handlers/minigames.py#L129) | janela de resgate desconhecida (2099 = sem fim) |
| [game/handlers/offer.py:28](../src/wartune_server/game/handlers/offer.py#L28) | o sorteio de qualidade do oficial não é conhecido; pesos para 1..5 (5 = ouro, rende x6) |
| [game/handlers/offer.py:204](../src/wartune_server/game/handlers/offer.py#L204) | as condições (RewardCondictionInfos: capturar NPC, missões, etc.) dependem de |
| [game/handlers/offer.py:224](../src/wartune_server/game/handlers/offer.py#L224) | depende do sistema de batalha abrir a luta com o NPC da tarefa; só registra.""" |
| [game/handlers/offer.py:330](../src/wartune_server/game/handlers/offer.py#L330) | as condições (enviar mensagem, batalhas...) dependem de outros sistemas avisarem; |
| [game/handlers/offer.py:342](../src/wartune_server/game/handlers/offer.py#L342) | sem compra de vagas extras |
| [game/handlers/outer_city.py:44](../src/wartune_server/game/handlers/outer_city.py#L44) | velocidade fixa, sem montaria nem efeitos |
| [game/handlers/outer_city.py:186](../src/wartune_server/game/handlers/outer_city.py#L186) | os exércitos alheios não aparecem (o 169 é só o próprio): a posição de outro jogador só existe |
| [game/handlers/pets.py:25](../src/wartune_server/game/handlers/pets.py#L25) | pontos livres por nível do pet; o oficial não publica a regra |
| [game/handlers/pets.py:57](../src/wartune_server/game/handlers/pets.py#L57) | atributo = template + pontos + nível x aptidão/100 (aproxima o login #30; fórmula real |
| [game/handlers/pets.py:63](../src/wartune_server/game/handlers/pets.py#L63) | mesma aproximação |
| [game/handlers/pets.py:82](../src/wartune_server/game/handlers/pets.py#L82) | família (tipo, tier, estrela) = template: é a leitura que fecha os 24 pares de receita com um |
| [game/handlers/pets.py:202](../src/wartune_server/game/handlers/pets.py#L202) | devorar, crescimento, skills, sacrifício, treino, resistência e a fusão de 2 pets (15) |
| [game/handlers/pets.py:218](../src/wartune_server/game/handlers/pets.py#L218) | só jogador online |
| [game/handlers/rewards.py:107](../src/wartune_server/game/handlers/rewards.py#L107) | x1,5 e x2 custam diamante no oficial, mas o preço não está no cliente; recusados |
| [game/handlers/shop.py:42](../src/wartune_server/game/handlers/shop.py#L42) | a tela da loja misteriosa não está no cliente decompilado; 8 é palpite |
| [game/handlers/shop.py:96](../src/wartune_server/game/handlers/shop.py#L96) | nenhuma loja tem NeedMinVip hoje; regra não conferida |
| [game/handlers/shop.py:100](../src/wartune_server/game/handlers/shop.py#L100) | o cliente esconde o botão se o andar passa do maxIndex (GoodsItem.as:380; o 4205 manda 60 fixo) |
| [game/handlers/shop.py:185](../src/wartune_server/game/handlers/shop.py#L185) | presente depende do correio |
| [game/handlers/space.py:47](../src/wartune_server/game/handlers/space.py#L47) | o fim do diálogo é local no cliente (``finishStory``); aqui conta o clique ou o aceite perto do nó. |
| [game/handlers/space.py:95](../src/wartune_server/game/handlers/space.py#L95) | o outro teleporte (mina de ametista, 30000) depende do sistema de minas |
| [game/handlers/space.py:104](../src/wartune_server/game/handlers/space.py#L104) | mapa por sessão com os nós da captura; pets selvagens, coleta e o chefe (4686) |
| [game/handlers/stars.py:31](../src/wartune_server/game/handlers/stars.py#L31) | o oficial não publica as chances do sorteio; pesos por qualidade (Profile) e cristal |
| [game/handlers/stars.py:203](../src/wartune_server/game/handlers/stars.py#L203) | a fonte de energia vira StarPoint (moeda da loja); confirmar com captura |
| [game/handlers/stars.py:350](../src/wartune_server/game/handlers/stars.py#L350) | 1 espaço por compra; o preço sobe a cada 4 (fórmula do cliente) |
| [game/handlers/systems.py:68](../src/wartune_server/game/handlers/systems.py#L68) | a data de ativação não é guardada |
| [game/handlers/systems.py:101](../src/wartune_server/game/handlers/systems.py#L101) | só jogador online; offline precisa do banco |
| [game/handlers/systems.py:116](../src/wartune_server/game/handlers/systems.py#L116) | estrela/bênção, rei das montarias, loja, refino e voo dependem da UI que não foi |
| [game/handlers/systems.py:152](../src/wartune_server/game/handlers/systems.py#L152) | atividade de montaria nova (evento); sem captura da resposta |
| [game/handlers/systems.py:161](../src/wartune_server/game/handlers/systems.py#L161) | pesos da roda tirados do tamanho das fatias (FateRotaryModel.rndDic, em graus) |
| [game/handlers/systems.py:229](../src/wartune_server/game/handlers/systems.py#L229) | 1 de EXP por pedra (sem captura do treino) |
| [game/handlers/systems.py:339](../src/wartune_server/game/handlers/systems.py#L339) | a vocação (vocationGrades/Gp) que vem depois não tem tabela nem captura; começa no 1 |
| [game/handlers/tower.py:28](../src/wartune_server/game/handlers/tower.py#L28) | sem progresso salvo da torre; andar real precisa do progresso |
| [game/handlers/treasure.py:24](../src/wartune_server/game/handlers/treasure.py#L24) | o oficial sorteia a qualidade do mapa; sem essa tabela, dá sempre o de bronze (2190001) |
| [game/handlers/vehicle.py:34](../src/wartune_server/game/handlers/vehicle.py#L34) | id = templateId (o oficial manda um id de banco; o cliente só usa templateId) |
| [game/handlers/vehicle.py:45](../src/wartune_server/game/handlers/vehicle.py#L45) | tecnologia de veículo não existe ainda |
| [game/handlers/vehicle.py:76](../src/wartune_server/game/handlers/vehicle.py#L76) | ``param2`` (0/1 conforme uma flag do frame que não foi decompilado) é ignorado; paga |
| [game/handlers/vehicle.py:109](../src/wartune_server/game/handlers/vehicle.py#L109) | os mapas de guerra com veículos (CampaignInfo Types 9 / GvG) não existem; dano e alvos |
| [game/handlers/vip.py:132](../src/wartune_server/game/handlers/vip.py#L132) | o 1 não tem regra conhecida |
| [game/handlers/vip.py:151](../src/wartune_server/game/handlers/vip.py#L151) | presentear um amigo exige gravar o snapshot de outro personagem (talvez offline) |
| [game/handlers/vip.py:160](../src/wartune_server/game/handlers/vip.py#L160) | o oficial soma Vip_DailyAddGp a cada dia de VIP; aqui entra tudo na compra |
| [game/handlers/vip.py:186](../src/wartune_server/game/handlers/vip.py#L186) | a captura só tem itens; moeda vai como nas outras recompensas |
| [game/handlers/vip.py:253](../src/wartune_server/game/handlers/vip.py#L253) | se o oficial cobra a atualização, o preço não está na evidência.""" |
| [game/handlers/vip.py:370](../src/wartune_server/game/handlers/vip.py#L370) | presente para amigo (friendId de outro) igual ao VIP: precisa gravar outro personagem |
| [game/handlers/vip.py:480](../src/wartune_server/game/handlers/vip.py#L480) | o mapa do teste (andar, buffs na batalha) não existe no servidor; sem ele não há onde |
| [game/handlers/worldboss.py:402](../src/wartune_server/game/handlers/worldboss.py#L402) | o mesmo 8264 é o reviver do altar de guilda (``RiverView`` tipo 2, paga em contribuição); |
| [game/items.py:56](../src/wartune_server/game/items.py#L56) | um item novo por entrada, sem empilhar (igual ao 5006); empilhar quando o |
| [game/mall.py:33](../src/wartune_server/game/mall.py#L33) | lock global do processo (um servidor por processo). Por anúncio se a fila pesar. |
| [game/mall.py:35](../src/wartune_server/game/mall.py#L35) | o agendador roda a cada 60 s sem dormir até o menor ends_at: até 60 s de atraso no encerramento |
| [game/mall.py:43](../src/wartune_server/game/mall.py#L43) | arredondamento para baixo; o texto do cliente não diz como o oficial arredonda |
| [game/mines.py:29](../src/wartune_server/game/mines.py#L29) | (dedução) o ciclo vencido só renova no próximo acerto de ouro, login, 8201 ou 5160 e começa nessa hora; |
| [game/monsters.py:21](../src/wartune_server/game/monsters.py#L21) | prêmio 0 (nenhuma fonte; ver docs/cidade-externa.md) e luta sozinho (o state 4 deixa |
| [game/outer_city.py:73](../src/wartune_server/game/outer_city.py#L73) | o oficial escolhe um ponto livre; usamos o centro (captura: mapa 2 em 2191,1952, perto do |
| [game/rewards.py:47](../src/wartune_server/game/rewards.py#L47) | ``text`` (abaixo) ainda é o turco das missões e eventos; quando ele virar inglês, este some nele.""" |
| [game/rewards.py:77](../src/wartune_server/game/rewards.py#L77) | o oficial sorteia randomSkill_1 nos equipamentos (RandomSkillCount); a tabela |
| [game/rules.py:38](../src/wartune_server/game/rules.py#L38) | guerreiro e caçador são o espelho dele, trocar quando houver captura. |
| [game/rules.py:305](../src/wartune_server/game/rules.py#L305) | teto de salto em vez da lista exata de saveId; a lista seria o próximo passo |
| [game/rules.py:314](../src/wartune_server/game/rules.py#L314) | busca linear nas 352 linhas a cada chamada; indexar por TemplateId em GameTemplates se pesar. |
| [game/social.py:167](../src/wartune_server/game/social.py#L167) | página única; paginar se a lista passar do tamanho de um pacote (200 amigos cabem). |
| [game/timebox.py:63](../src/wartune_server/game/timebox.py#L63) | dedução, a fórmula do oficial não está no cliente; nível x minutos fora, até 8 horas |
| [game/worldboss.py:38](../src/wartune_server/game/worldboss.py#L38) | janela que cruza a meia-noite não existe nos templates; não é tratada. |
| [http/app.py:242](../src/wartune_server/http/app.py#L242) | respostas do suporte sempre vazias até existir o atendimento |
| [services/characters.py:65](../src/wartune_server/services/characters.py#L65) | cada jogador só vê o próprio castelo, então dividir o ponto não colide; com mapa |
