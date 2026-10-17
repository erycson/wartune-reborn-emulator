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
| Loja de honra (ShopType 3): medalhas com `ValidDate` (7, 15 e 30 dias) | 10 | **falta**: item com validade. Hoje a medalha comprada fica para sempre. Precisa de `begin_date`/`valid_date` no item, mandar no 115 e expirar (o cliente já some com o item vencido: `BaseBagListView`) |
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

## Minigames e eventos ([eventos.md](eventos.md))

6 de 38 são reais: fundo de novato (8751) e labirinto de gemas (9508, 9509, 9513, 9516, 9517). 2 recusam sem efeito (9510, 9515: ajuda de amigo do labirinto). Os outros 30 respondem o estado "fechado" que o cliente sabe mostrar.

| Minigame | Opcodes | Falta |
|---|---|---|
| Garrafa | 8604 | depósito, martelo, caixas por pontuação/andar, pesos (`BottleItems` existe) |
| Quiz | 9501 | banco de perguntas com resposta |
| Labirinto de gemas | 9508–9517 | **real** ([eventos.md](eventos.md)). **precisa de captura**: subida de nível (tabela de `maxExp`), pesos dos prêmios, o que o oficial faz com troca sem combinação, bolsa do prêmio das caixas (9513), período da renovação diária (dedução), ajuda de amigo (9510/9515/4925), ranking semanal, preço e teto da compra (dedução) |
| Estrada dourada | 9520–9522 | tabela das casas |
| Pesca, caça ao tesouro, minério | 9507, 9502, 9645 | regras de aparecimento, nós e prêmios; no 9645 o cabeçalho (`extend1`) que separa minério de super assinatura não chega ao handler |
| Loteria, caça-níquel, cadeiras, caixa de ano novo, história, sorteio de grupo | 8748/8750, 9500, 9638, 8994, 8629/8630, 9523 | template e configuração do evento |
| Recuperar EXP | 9503 | nenhum sistema conta atividade perdida (a fórmula do custo está conferida) |
| Fundo normal | 8703 | captura do 4612 |
| Troca da sorte | 9610 | a tabela da captura venceu em 2026-05-17 |
| Privilégio 360 | 8722/8723 | só para o agente 360 do cliente |
| Fundo de novato | 8751 | **dedução**: janela oficial desconhecida (`endDate` 2099) |

Outros eventos:
- 8518, 8519/8521 (roleta) respondem vazio; 8756 só registra; loja de teste (8582) recusa: o mapa de teste não existe.
- Quadro de recompensas 8291 sem passe, 8298, 8729: **depende de** batalha, missões e mensagens reportarem progresso.
- Tipos de SumActive além de 13/14 ficam em status 3.

## Chefe do mundo ([boss-eventos.md](boss-eventos.md))

- Agenda (8271 -> 4182): pronta, conferida com a captura de 12:20 (5001=2, 5003=1). O estado 0 (aberto) nunca apareceu num 4182, mas aparece no 4248 (mesma mensagem, `login.json #121`, 4010=0 às 20:06). **precisa de captura**: o 4182 dentro da janela. Ver *Captura que falta* em [boss-eventos.md](boss-eventos.md).
- Entrar (8258): validado e recusado com aviso. **precisa de captura**: o `.maps` de 5001/5003 existe mas não tem nó do chefe (decoração só), e `CampaignData` não tem linha para eles.
- Atacar: o caminho do nó é 5125 (`paraInt1` = nodeId), mas não há nó nem batalha de chefe. **precisa de captura** (entrada, 130, 157 com `battleType`, golpes).
- Dano acumulado e ranking: o cliente ordena o `woundInfo` sozinho (`WorldBossModel.commit`); o servidor não soma dano. **precisa de captura**: quem soma e com que fórmula.
- HP global (4174), morte (4175), relatórios (4203, 4369, 4435): não existem. Prêmios (4203 `gold`/`strengy`, 4369 marcos): **precisa de captura**, nenhuma tabela de prêmios cita os chefes.
- Reviver pago (8264) e buff do chefe (8470, `Types=4`): recusam sem cobrar. **depende de**: mapa e batalha do chefe.
- Dublê (8526): recusado em `handlers/dungeon.py`, sem cobrança. **depende de**: batalha do chefe e a tela `BuyAvatarFrame` (não está nas pastas decompiladas).
- O 4182 (chefe abriu) não é reenviado para quem já está online: não há tarefa periódica. O oficial empurra o 4248 só com o id que mudou no fim da janela (`replay_packets.json #619`); fazer o mesmo no 4182 quando o chefe tiver mapa (antes disso o botão só leva à recusa).
- Fuso fixo UTC+3. **dedução** (conferido em duas capturas: 12:20 e 20:06).
- O 8264 também é o reviver do altar da guilda: separar pelo mapa quando o altar existir.
- Templates: moral (buff `Types=7`) são 701–720, não 701–710. O herói do chefe (2002/2003, `Live` 2 000 000) liga ao chefe só pelo nome. **dedução**.
- Fora do chefe: 4002 não é chefe, é campo de batalha (Savaş Alanı, 12:00–12:25). O 4248 tem 0 = aberto (`login.json #121`, 4010=0 aos 6 min da janela) e um 3 aos 20 min (`replay_packets.json #103`, 4002=3), talvez "entrada encerrada" (**dedução**). `warfield.py` manda 1 para todos (fechado de propósito); o 3 precisa ser entendido antes de abrir o campo.

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
- "Emek oranınız ..." (83, taxa de trabalho): o sistema não existe.
- Subida de nível: o oficial manda também 139, 100 e 4640 (replay #625-#628); aqui só o 150.
- Presente da atividade de soma (8586 tipo 2, replay #678): recusado.
- Ataque a castelo: 9506 compra tentativas, mas nada as gasta.
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
- Cartas de poder (9505): cartas e EXP vêm da batalha (4902); bônus de coleção falta.
- Posição do herói em salas (8277/8278) e teleporte (8326): **depende de** salas/cidade externa.
- Ganhar montaria, pet ou carta: **depende de** uso de item, missão ou batalha.
- `battle.py` ainda não lê a tropa (`rules.battle_pawn`) nem os buffs (talento, runas, destino, dragão, cartas).
- Destino tipos 2100/2200 nunca abrem. **sem dado**.
- **dedução**: chance do sorteio de estrelas, EXP de destino por pedra, atributos e pontos dos pets por nível.

## Castelo e fazenda ([castelo.md](castelo.md))

- Roubar e reviver na fazenda de amigo (15044 ops 5/6), verme/erva: recusados. Regar a árvore de amigo (15017): recusado; a captura ciftlik já dá ouro, EXP e amizade, falta a regra de quem pode regar (ver castelo.md). A lista de amigos já existe; falta ligar.
- Melhorar terreno e pets da fazenda (15044 ops 9–16): sem remetente no cliente; a fazenda fica em 3 terrenos.
- Colher a árvore (5178): **precisa de captura**; nenhuma tem `fruitCount` > 0. Passos e itens em castelo.md.
- Recompensa offline ×1,5/×2 (8287): preço desconhecido. **sem dado**.
- 8255 (batalha em grupo), 8562 (trégua), 5179 (terras selvagens): respondem vazio. **depende de** esses sistemas.
- Rendimento: o oficial soma +30/h que não explicamos; sem bônus de terras, guilda ou efeitos.
- **dedução**: EXP offline = nível × minutos (até 8 h), acelerar a fazenda amadurece na hora, caixa por tempo vira à meia-noite UTC. Ouro de regar: visto (nível do dono × 20).

## PvP ([pvp.md](pvp.md))

- Lordes (8710–8721), lordes casados (8975–8981), campo de guerra (8332/8334/8337/8338), campo de minas (8633), 8635: parciais. **sem dado**.
- Torneio de fadas: usa os pets salvos; a posição dos pets do oponente (`pos` = índice + 3) é **dedução**.

## Social, chat e VIP ([social.md](social.md), [chat.md](chat.md))

- Canal de time (6) no chat: recusado.
- VIP ainda ignorado em: cota de cornetas, limite de amigos (`MAX_FRIENDS`), acelerar construção índice 0 (5172).
- Presentes do VIP/contrato do rei para amigo (8513/8540): recusados (gravar outro personagem).
- Mochila de 42 espaços base (sem os comprados/alugados) em: coliseu, fazenda, caixa por tempo, correio.

## Simplificações marcadas no código

Lista gerada de todo `ponytail:` em `src/` (atualize com `grep -rn "ponytail:" src --include=*.py`).

| Onde | Simplificação |
|---|---|
| [game/arena.py:292](../src/wartune_server/game/arena.py#L292) | o caçador perde até o nível ~30 porque o ataque |
| [game/arena.py:302](../src/wartune_server/game/arena.py#L302) | a captura tem 2 arqueiros 10202 com o robô, mas lá o jogador também tinha soldados; |
| [game/arena.py:361](../src/wartune_server/game/arena.py#L361) | perda não observada, não tira pontos |
| [game/arena.py:365](../src/wartune_server/game/arena.py#L365) | fórmula de vida do pet desconhecida; MaxHp + nível × GrowthRate / 9 dá ~5% da captura |
| [game/arena.py:406](../src/wartune_server/game/arena.py#L406) | ~ o dano da captura (golpe básico ≈ vida/40) |
| [game/bag.py:92](../src/wartune_server/game/bag.py#L92) | o oficial sorteia randomSkill_1..N (RandomSkillCount); a tabela do sorteio não está nos |
| [game/battle.py:267](../src/wartune_server/game/battle.py#L267) | a iniciativa do oficial não foi decifrada; aliados NPC, inimigos e o herói por último |
| [game/battle.py:345](../src/wartune_server/game/battle.py#L345) | fórmula de dano desconhecida. PvE calibrado na captura do tutorial (herói mata os |
| [game/builders/login.py:76](../src/wartune_server/game/builders/login.py#L76) | bate com o oficial no nível 1 (199); nível 3 dá 291 contra 278. Falta a fórmula real. |
| [game/builders/login.py:248](../src/wartune_server/game/builders/login.py#L248) | 1 exército por personagem; tabela própria quando houver tropas extras |
| [game/castle.py:80](../src/wartune_server/game/castle.py#L80) | sem bônus de guilda/efeitos; o oficial soma +30 que não sabemos de onde vem |
| [game/castle.py:165](../src/wartune_server/game/castle.py#L165) | sem o bônus de raça/efeitos do limite (PlayerEffect.getTransferPowerLimitAddition) |
| [game/drops.py:32](../src/wartune_server/game/drops.py#L32) | sorteio uniforme e sem filtro de classe (o mesmo mago tirou 1080013, Job 3, e 1080002, |
| [game/farm.py:19](../src/wartune_server/game/farm.py#L19) | sem upgrade de terra (opType 9 não tem sender) |
| [game/gemmaze.py:90](../src/wartune_server/game/gemmaze.py#L90) | o período (dia, UTC) não foi capturado; os movimentos comprados não somem (fica o maior). |
| [game/gemmaze.py:196](../src/wartune_server/game/gemmaze.py#L196) | 5 ou mais em linha segue a conta de 3 e 4 (não foi capturado) |
| [game/gemmaze.py:205](../src/wartune_server/game/gemmaze.py#L205) | prêmio sorteado uniforme entre os três vistos; a tabela oficial (pesos) precisa de captura |
| [game/gemmaze.py:208](../src/wartune_server/game/gemmaze.py#L208) | troca sem combinação é aceita e gasta movimento (o cliente troca na tela e não desfaz; |
| [game/guild.py:161](../src/wartune_server/game/guild.py#L161) | só os 50 últimos na memória; o banco guarda todos |
| [game/handlers/account.py:20](../src/wartune_server/game/handlers/account.py#L20) | prazo do reset não está no cliente nem nas capturas; ajustar se aparecer |
| [game/handlers/account.py:190](../src/wartune_server/game/handlers/account.py#L190) | sala de um jogador só; broadcast quando houver sala compartilhada |
| [game/handlers/arena.py:18](../src/wartune_server/game/handlers/arena.py#L18) | só os 42 base; espaços comprados/alugados via bag.capacity(c, now) |
| [game/handlers/arena.py:355](../src/wartune_server/game/handlers/arena.py#L355) | limite de compras do torneio não está no cliente nem nos templates; 10/dia como no coliseu |
| [game/handlers/army.py:237](../src/wartune_server/game/handlers/army.py#L237) | bênção cheia = sorteio garantido um grau acima; a regra exata do oficial não tem captura |
| [game/handlers/army.py:276](../src/wartune_server/game/handlers/army.py#L276) | grade 3x3 da formação; conferir limites quando houver captura |
| [game/handlers/army.py:301](../src/wartune_server/game/handlers/army.py#L301) | só a posição do próprio herói é gravada; |
| [game/handlers/army.py:321](../src/wartune_server/game/handlers/army.py#L321) | a posição do exército no mapa externo não é gravada (sistema do mapa externo). |
| [game/handlers/battle.py:35](../src/wartune_server/game/handlers/battle.py#L35) | a postura não muda o dano (a fórmula real não é conhecida) |
| [game/handlers/campaign.py:545](../src/wartune_server/game/handlers/campaign.py#L545) | sem energia não entra e não responde; a recusa do oficial precisa de captura com Beden < 20 |
| [game/handlers/campaign.py:720](../src/wartune_server/game/handlers/campaign.py#L720) | carta paga (isPay, autoChest) tratada como a grátis: price 0 e uma só por mapa; cartas |
| [game/handlers/campaign_map.py:37](../src/wartune_server/game/handlers/campaign_map.py#L37) | mapa sem captura manda lista vazia; falta a lista de cada mapa (nós do .maps). Não muda estado |
| [game/handlers/castle.py:292](../src/wartune_server/game/handlers/castle.py#L292) | trégua ainda não existe; zera e confirma. |
| [game/handlers/chat.py:26](../src/wartune_server/game/handlers/chat.py#L26) | o cliente não limita a guilda (ChatHelper); 1 s contra spam |
| [game/handlers/chat.py:28](../src/wartune_server/game/handlers/chat.py#L28) | o cliente não limita o privado; 1 s contra spam |
| [game/handlers/chat.py:84](../src/wartune_server/game/handlers/chat.py#L84) | cota fixa do ConfigInfo; o VIP do oficial pode aumentar (sem VIP ainda). |
| [game/handlers/chat.py:165](../src/wartune_server/game/handlers/chat.py#L165) | "cena" = todos online até existir o registro de cenas (cidade do céu). |
| [game/handlers/events.py:166](../src/wartune_server/game/handlers/events.py#L166) | só os tipos 13 e 14 têm regra; os outros ficam "ainda não" até alguém implementar |
| [game/handlers/events.py:377](../src/wartune_server/game/handlers/events.py#L377) | nenhum desses sistemas conta ainda; lista vazia = tudo zerado no painel. |
| [game/handlers/farm.py:15](../src/wartune_server/game/handlers/farm.py#L15) | só os 42 base; comprados via bag.capacity |
| [game/handlers/farm.py:183](../src/wartune_server/game/handlers/farm.py#L183) | o texto do oficial (farm.view.FarmOperMenu.accelerateTip) não está decompilado; |
| [game/handlers/farm.py:217](../src/wartune_server/game/handlers/farm.py#L217) | sem fruto (quando a árvore frutifica não está nas capturas nem no cliente decompilado) |
| [game/handlers/farm.py:254](../src/wartune_server/game/handlers/farm.py#L254) | ações em fazenda de amigo ainda recusadas (lista de amigos), então tudo falso |
| [game/handlers/forge.py:32](../src/wartune_server/game/handlers/forge.py#L32) | o refino sorteado fica na memória até o 8339 (some se o servidor reiniciar) |
| [game/handlers/forge.py:208](../src/wartune_server/game/handlers/forge.py#L208) | autoBuy (comprar o que falta) não |
| [game/handlers/forge.py:220](../src/wartune_server/game/handlers/forge.py#L220) | o espaço é conferido antes de consumir (pode recusar quando os materiais liberariam lugar) |
| [game/handlers/forge.py:271](../src/wartune_server/game/handlers/forge.py#L271) | a tabela de sorteio do oficial não está nos templates: sorteio uniforme entre os atributos |
| [game/handlers/friends.py:31](../src/wartune_server/game/handlers/friends.py#L31) | limites do cliente não achados (módulo de UI ausente) |
| [game/handlers/friends.py:320](../src/wartune_server/game/handlers/friends.py#L320) | ``pageIndex`` tratado como 1-based (UI ausente). |
| [game/handlers/gemmaze.py:71](../src/wartune_server/game/handlers/gemmaze.py#L71) | o oficial manda 0 para personagem novo; o contador não foi capturado |
| [game/handlers/gemmaze.py:77](../src/wartune_server/game/handlers/gemmaze.py#L77) | ranking semanal não existe aqui (o oficial manda 1771 para um jogador de topo) |
| [game/handlers/gemmaze.py:167](../src/wartune_server/game/handlers/gemmaze.py#L167) | sem subida de nível (a tabela de EXP por nível não foi capturada): curExp passa de maxExp |
| [game/handlers/gemmaze.py:179](../src/wartune_server/game/handlers/gemmaze.py#L179) | o semanal soma o mesmo que o do dia e zera na semana nova (``gm.refresh``, dedução) |
| [game/handlers/gemmaze.py:238](../src/wartune_server/game/handlers/gemmaze.py#L238) | a caixa vai para a bolsa do labirinto (o ícone voa para ela, como o das gemas); a bolsa |
| [game/handlers/gemmaze.py:258](../src/wartune_server/game/handlers/gemmaze.py#L258) | o template não diz a moeda nem o limite diário: diamante (ou vinculado com buyTypes 2) é dedução |
| [game/handlers/guild.py:486](../src/wartune_server/game/handlers/guild.py#L486) | o oficial tinha guildas-robô; aqui vem o convite da guilda aberta com mais membros |
| [game/handlers/guild.py:660](../src/wartune_server/game/handlers/guild.py#L660) | o ``same`` (renomear grátis depois de juntar servidores) é cobrado igual. |
| [game/handlers/guild.py:704](../src/wartune_server/game/handlers/guild.py#L704) | não se sabe se o oficial aceita diamante vinculado aqui; gasta primeiro o vinculado |
| [game/handlers/guild.py:932](../src/wartune_server/game/handlers/guild.py#L932) | a tabela de prêmios do oficial não está nos templates; o prêmio é sempre um item |
| [game/handlers/guild.py:985](../src/wartune_server/game/handlers/guild.py#L985) | o prêmio fica na linha do membro, então sair da guilda antes de pegar perde o prêmio |
| [game/handlers/guild.py:1068](../src/wartune_server/game/handlers/guild.py#L1068) | o correio por mochila cheia é dedução (o |
| [game/handlers/guild.py:1151](../src/wartune_server/game/handlers/guild.py#L1151) | o oficial abre a eleição quando o chefe some por muitos dias; a regra não está no |
| [game/handlers/guild_events.py:66](../src/wartune_server/game/handlers/guild_events.py#L66) | falta o sistema de mapas de campanha (só existe o do tutorial) e as ondas de |
| [game/handlers/hero.py:128](../src/wartune_server/game/handlers/hero.py#L128) | a EXP gasta sai da EXP do nível atual (c.gp); conferir com captura se o oficial |
| [game/handlers/hero.py:294](../src/wartune_server/game/handlers/hero.py#L294) | o preço sobe com diamondIndex (usos no dia); sem contador diário fica no primeiro |
| [game/handlers/items.py:219](../src/wartune_server/game/handlers/items.py#L219) | sem o teto diário de poções de Beden; só o limite do personagem |
| [game/handlers/items.py:260](../src/wartune_server/game/handlers/items.py#L260) | sem teto de uso por dia (a captura tem um uso só); o gasto da entrada não existe aqui, falta |
| [game/handlers/items.py:407](../src/wartune_server/game/handlers/items.py#L407) | depois de juntar pilhas, fecha os buracos na mesma ordem (dedução) |
| [game/handlers/mail.py:38](../src/wartune_server/game/handlers/mail.py#L38) | correio de guilda (sendType 2) recusado até existir guilda. |
| [game/handlers/mall.py:46](../src/wartune_server/game/handlers/mall.py#L46) | a tela oferece 8, 24 e 48 h (Auction.SubmitHour1..3); o valor enviado não está no decompilado |
| [game/handlers/mall.py:49](../src/wartune_server/game/handlers/mall.py#L49) | a lista pede 9 por página (8449, 8452); o teto de 50 é dedução, a tela de leilão não está no decompilado |
| [game/handlers/mall.py:55](../src/wartune_server/game/handlers/mall.py#L55) | o texto repete 60 e 70 nas duas faixas; aqui 60 e 70 já são da faixa de cima. Abaixo de 40 vale |
| [game/handlers/marriage.py:7](../src/wartune_server/game/handlers/marriage.py#L7) | pedidos, ofertas de casamento e pedidos de divórcio ficam em memória (somem se o |
| [game/handlers/minigames.py:68](../src/wartune_server/game/handlers/minigames.py#L68) | janela de resgate desconhecida (2099 = sem fim) |
| [game/handlers/offer.py:28](../src/wartune_server/game/handlers/offer.py#L28) | o sorteio de qualidade do oficial não é conhecido; pesos para 1..5 (5 = ouro, rende x6) |
| [game/handlers/offer.py:204](../src/wartune_server/game/handlers/offer.py#L204) | as condições (RewardCondictionInfos: capturar NPC, missões, etc.) dependem de |
| [game/handlers/offer.py:224](../src/wartune_server/game/handlers/offer.py#L224) | depende do sistema de batalha abrir a luta com o NPC da tarefa; só registra. |
| [game/handlers/offer.py:330](../src/wartune_server/game/handlers/offer.py#L330) | as condições (enviar mensagem, batalhas...) dependem de outros sistemas avisarem; |
| [game/handlers/offer.py:342](../src/wartune_server/game/handlers/offer.py#L342) | sem compra de vagas extras |
| [game/handlers/outer_city.py:37](../src/wartune_server/game/handlers/outer_city.py#L37) | velocidade fixa, sem montaria nem efeitos |
| [game/handlers/outer_city.py:135](../src/wartune_server/game/handlers/outer_city.py#L135) | os exércitos alheios não aparecem (o 169 é só o próprio): a posição de outro jogador só existe |
| [game/handlers/pets.py:25](../src/wartune_server/game/handlers/pets.py#L25) | pontos livres por nível do pet; o oficial não publica a regra |
| [game/handlers/pets.py:57](../src/wartune_server/game/handlers/pets.py#L57) | atributo = template + pontos + nível x aptidão/100 (aproxima o login #30; fórmula real |
| [game/handlers/pets.py:63](../src/wartune_server/game/handlers/pets.py#L63) | mesma aproximação |
| [game/handlers/pets.py:82](../src/wartune_server/game/handlers/pets.py#L82) | família (tipo, tier, estrela) = template: é a leitura que fecha os 24 pares de receita com um |
| [game/handlers/pets.py:202](../src/wartune_server/game/handlers/pets.py#L202) | devorar, crescimento, skills, sacrifício, treino, resistência e a fusão de 2 pets (15) |
| [game/handlers/pets.py:218](../src/wartune_server/game/handlers/pets.py#L218) | só jogador online |
| [game/handlers/rewards.py:10](../src/wartune_server/game/handlers/rewards.py#L10) | só os 42 base; comprados via bag.capacity |
| [game/handlers/rewards.py:84](../src/wartune_server/game/handlers/rewards.py#L84) | x1,5 e x2 custam diamante no oficial, mas o preço não está no cliente; recusados |
| [game/handlers/shop.py:40](../src/wartune_server/game/handlers/shop.py#L40) | a tela da loja misteriosa não está no cliente decompilado; 8 é palpite |
| [game/handlers/shop.py:94](../src/wartune_server/game/handlers/shop.py#L94) | nenhuma loja tem NeedMinVip hoje; regra não conferida |
| [game/handlers/shop.py:98](../src/wartune_server/game/handlers/shop.py#L98) | o cliente esconde o botão se o andar passa do maxIndex (GoodsItem.as:380; o 4205 manda 60 fixo) |
| [game/handlers/shop.py:163](../src/wartune_server/game/handlers/shop.py#L163) | presente depende do correio |
| [game/handlers/shop.py:335](../src/wartune_server/game/handlers/shop.py#L335) | troca os itens e zera as compras uma vez por dia |
| [game/handlers/space.py:47](../src/wartune_server/game/handlers/space.py#L47) | o fim do diálogo é local no cliente (``finishStory``); aqui conta o clique ou o aceite perto do nó. |
| [game/handlers/space.py:95](../src/wartune_server/game/handlers/space.py#L95) | o outro teleporte (mina de ametista, 30000) depende do sistema de minas |
| [game/handlers/space.py:104](../src/wartune_server/game/handlers/space.py#L104) | mapa por sessão com os nós da captura; pets selvagens, coleta e o chefe (4686) |
| [game/handlers/stars.py:30](../src/wartune_server/game/handlers/stars.py#L30) | o oficial não publica as chances do sorteio; pesos por qualidade (Profile) e cristal |
| [game/handlers/stars.py:197](../src/wartune_server/game/handlers/stars.py#L197) | a fonte de energia vira StarPoint (moeda da loja); confirmar com captura |
| [game/handlers/stars.py:344](../src/wartune_server/game/handlers/stars.py#L344) | 1 espaço por compra; o preço sobe a cada 4 (fórmula do cliente) |
| [game/handlers/systems.py:67](../src/wartune_server/game/handlers/systems.py#L67) | a data de ativação não é guardada |
| [game/handlers/systems.py:100](../src/wartune_server/game/handlers/systems.py#L100) | só jogador online; offline precisa do banco |
| [game/handlers/systems.py:115](../src/wartune_server/game/handlers/systems.py#L115) | estrela/bênção, rei das montarias, loja, refino e voo dependem da UI que não foi |
| [game/handlers/systems.py:151](../src/wartune_server/game/handlers/systems.py#L151) | atividade de montaria nova (evento); sem captura da resposta |
| [game/handlers/systems.py:160](../src/wartune_server/game/handlers/systems.py#L160) | pesos da roda tirados do tamanho das fatias (FateRotaryModel.rndDic, em graus) |
| [game/handlers/systems.py:228](../src/wartune_server/game/handlers/systems.py#L228) | 1 de EXP por pedra (sem captura do treino) |
| [game/handlers/systems.py:338](../src/wartune_server/game/handlers/systems.py#L338) | a vocação (vocationGrades/Gp) que vem depois não tem tabela nem captura; começa no 1 |
| [game/handlers/systems.py:375](../src/wartune_server/game/handlers/systems.py#L375) | o buff da coleção completa (bufInfos da suíte, visto 40001) não tem tabela conhecida |
| [game/handlers/tower.py:28](../src/wartune_server/game/handlers/tower.py#L28) | sem progresso salvo da torre; andar real precisa do progresso |
| [game/handlers/treasure.py:24](../src/wartune_server/game/handlers/treasure.py#L24) | o oficial sorteia a qualidade do mapa; sem essa tabela, dá sempre o de bronze (2190001) |
| [game/handlers/vehicle.py:34](../src/wartune_server/game/handlers/vehicle.py#L34) | id = templateId (o oficial manda um id de banco; o cliente só usa templateId) |
| [game/handlers/vehicle.py:45](../src/wartune_server/game/handlers/vehicle.py#L45) | tecnologia de veículo não existe ainda |
| [game/handlers/vehicle.py:76](../src/wartune_server/game/handlers/vehicle.py#L76) | ``param2`` (0/1 conforme uma flag do frame que não foi decompilado) é ignorado; paga |
| [game/handlers/vehicle.py:109](../src/wartune_server/game/handlers/vehicle.py#L109) | os mapas de guerra com veículos (CampaignInfo Types 9 / GvG) não existem; dano e alvos |
| [game/handlers/vip.py:96](../src/wartune_server/game/handlers/vip.py#L96) | o tipo 1 (ícone especial) não tem regra conhecida |
| [game/handlers/vip.py:115](../src/wartune_server/game/handlers/vip.py#L115) | presentear um amigo exige gravar o snapshot de outro personagem (talvez offline) |
| [game/handlers/vip.py:124](../src/wartune_server/game/handlers/vip.py#L124) | o oficial soma Vip_DailyAddGp a cada dia de VIP; aqui entra tudo na compra |
| [game/handlers/vip.py:157](../src/wartune_server/game/handlers/vip.py#L157) | a tabela de prêmios da roleta não está nos templates nem nas capturas. |
| [game/handlers/vip.py:214](../src/wartune_server/game/handlers/vip.py#L214) | presente para amigo (friendId de outro) igual ao VIP: precisa gravar outro personagem |
| [game/handlers/vip.py:324](../src/wartune_server/game/handlers/vip.py#L324) | o mapa do teste (andar, buffs na batalha) não existe no servidor; sem ele não há onde |
| [game/handlers/worldboss.py:69](../src/wartune_server/game/handlers/worldboss.py#L69) | o mesmo 8264 é o reviver do altar de guilda (``RiverView`` tipo 2, paga em contribuição); |
| [game/items.py:12](../src/wartune_server/game/items.py#L12) | só os 42 base; espaços comprados/alugados via bag.capacity(c, now) |
| [game/items.py:54](../src/wartune_server/game/items.py#L54) | um item novo por entrada, sem empilhar (igual ao 5006); empilhar quando o |
| [game/mall.py:33](../src/wartune_server/game/mall.py#L33) | lock global do processo (um servidor por processo). Por anúncio se a fila pesar. |
| [game/mall.py:35](../src/wartune_server/game/mall.py#L35) | o agendador roda a cada 60 s sem dormir até o menor ends_at: até 60 s de atraso no encerramento |
| [game/mall.py:43](../src/wartune_server/game/mall.py#L43) | arredondamento para baixo; o texto do cliente não diz como o oficial arredonda |
| [game/outer_city.py:75](../src/wartune_server/game/outer_city.py#L75) | o oficial escolhe um ponto livre; usamos o centro (captura: mapa 2 em 2191,1952, perto do |
| [game/outer_city.py:117](../src/wartune_server/game/outer_city.py#L117) | (dedução) o ciclo vencido só renova no próximo acerto de ouro, login, 8201 ou 5160 e começa nessa hora; |
| [game/rewards.py:20](../src/wartune_server/game/rewards.py#L20) | -600 "Kristal" (cristal do castelo) ainda não existe no banco (CRYSTALS fixo em |
| [game/rewards.py:23](../src/wartune_server/game/rewards.py#L23) | sem espaços comprados (bagCount) ainda |
| [game/rewards.py:72](../src/wartune_server/game/rewards.py#L72) | o oficial sorteia randomSkill_1 nos equipamentos (RandomSkillCount); a tabela |
| [game/rules.py:36](../src/wartune_server/game/rules.py#L36) | guerreiro e caçador são o espelho dele, trocar quando houver captura. |
| [game/rules.py:276](../src/wartune_server/game/rules.py#L276) | busca linear nas 352 linhas a cada chamada; indexar por TemplateId em GameTemplates se pesar. |
| [game/social.py:154](../src/wartune_server/game/social.py#L154) | página única; paginar se a lista passar do tamanho de um pacote (200 amigos cabem). |
| [game/timebox.py:19](../src/wartune_server/game/timebox.py#L19) | o dia vira à meia-noite UTC; sem o horário de reset do servidor oficial |
| [game/timebox.py:60](../src/wartune_server/game/timebox.py#L60) | dedução, a fórmula do oficial não está no cliente; nível x minutos fora, até 8 horas |
| [game/worldboss.py:17](../src/wartune_server/game/worldboss.py#L17) | fuso fixo (UTC+3, sem horário de verão); outro fuso vira config |
| [game/worldboss.py:37](../src/wartune_server/game/worldboss.py#L37) | janela que cruza a meia-noite não existe nos templates; não é tratada. |
| [http/app.py:242](../src/wartune_server/http/app.py#L242) | respostas do suporte sempre vazias até existir o atendimento |
| [services/characters.py:62](../src/wartune_server/services/characters.py#L62) | cada jogador só vê o próprio castelo, então dividir o ponto não colide; com mapa |
