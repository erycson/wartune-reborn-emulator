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
| Loja do labirinto (ShopType 4): `MazeLayers`/`MazeLayers2` (andar mínimo) | 97 / 22 | **falta**: conferir o andar. **depende de**: progresso do labirinto/torre. Hoje vende para quem tiver Labirent Parası |
| Loja misteriosa (ShopType 5): peso `Rands` | 110 | **dedução**: sorteio uniforme de 8 itens, sem o peso |
| Presente para outro jogador (`receiveId`) | — | recusado. **depende de**: entrega pelo correio na compra |
| Mochila cheia | — | recusa (o oficial manda pelo correio, resultado 12) |
| Ofertas da home (4238), compra coletiva (8645), relâmpago (8632) | — | nenhuma ativa. **depende de**: configuração de ofertas do operador |

Itens fora da loja:
- Refino da forja (8336): sorteio uniforme entre os 1584 atributos com `Grades` > 0 (visto: os 42 das capturas têm Grades 1–10). Falta o peso por nível e o custo do cadeado: **precisa de captura** 8336 → 4258 com cadeado e itens de NeedGrades baixo e alto.
- Decomposição (8340), avaliação de moda (8781), moldagem (8644), composição de moda (8594), troca na bancada (8595). **sem dado**.
- Itens novos ganham só o `DefaultSkill` como atributo sorteado (o oficial sorteia `RandomSkillCount`). **sem dado**.
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

- Salas e times só em memória. Decisão: salas não persistem; times não persistem até haver captura de login com time; o contador de campanha multi (4240) deve persistir, mas falta o efeito do item "Büyük Sefer" e o reset (ver Persistência em salas-campanha.md).
- Começar a campanha da sala (5039, visto no replay): responde 125, 140 e 21, mas precisa do mapa 1011 (exército inicial e nós). **depende de**: mapa de nós.
- Caixa Pandora (5033 com S>C 29, mapId 879/880, nodeId 101107/102107): o 5033 só ecoa a escolha; falta a recompensa e a resposta do servidor (captura de abrir a caixa). Confirmar/terminar campanha (5180), carta (5122), névoa (5126, não é guardada), exército na campanha (5121, falta captura da resposta). **depende de**: mapa de nós 1011/2011 e progresso.
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

- Sem agendador: um anúncio vencido só é encerrado no próximo pedido ao mercado de qualquer jogador.
- **dedução**: duração 1–72 h, 9 por página (até 50), preço mínimo `StartingPrice × count`, sem taxa, sem limite de anúncios.
- Lance e compra pagam só elmas (sem vinculado), sem prova de que o oficial restrinja.
- Lista do mercado (8450) e busca (8457) ignoram a ordenação.
- Cancelar parte de uma pilha não reempilha com a original.
- Correio não é apagado por validade; uma limpeza futura precisa pular carta com item não retirado.

## Guilda ([guilda.md](guilda.md))

- Atividades com mapa (altar 8542, terra secreta 8537/8565/8566/8743, guerra 8471, entre servidores 8783) e os pacotes dentro do mapa: recusados. **sem dado**: os nós dos mapas 7601/7501 não estão nos `.maps`.
- Rankings e prêmios das atividades: o gancho `add_to_box` existe, ninguém chama.
- Bênção (5145): o prêmio é sempre um item do mercado liberado pelo nível do altar; o prêmio pendente fica só em memória; bênção rápida (VIP 6) recusada. **sem dado**: tabela oficial.
- Eleição (8241/8481): nada inicia a eleição (só editando o banco). **sem dado**.
- 8335 só registra (`speakTimes` sempre 0).
- Criar guilda grava em duas transações; se a segunda falhar, o ouro some e a guilda fica sem membros.
- Item da caixa para membro offline com mochila cheia se perde. **depende de**: correio na entrega.
- Altar, caixa e prêmios usam só os 42 espaços base da mochila.

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
- Mochila de 42 espaços base (sem os comprados/alugados) em: guilda, coliseu, fazenda, caixa por tempo, correio.

## Simplificações marcadas no código

Lista gerada de todo `ponytail:` em `src/` (atualize com `grep -rn "ponytail:" src --include=*.py`).

| Onde | Simplificação |
|---|---|
| [game/arena.py:292](../src/wartune_server/game/arena.py#L292) | o caçador perde até o nível ~30 porque o ataque |
| [game/arena.py:302](../src/wartune_server/game/arena.py#L302) | a captura tem 2 arqueiros 10202 com o robô, mas lá o jogador também tinha soldados; |
| [game/arena.py:361](../src/wartune_server/game/arena.py#L361) | perda não observada, não tira pontos |
| [game/arena.py:365](../src/wartune_server/game/arena.py#L365) | fórmula de vida do pet desconhecida; MaxHp + nível × GrowthRate / 9 dá ~5% da captura |
| [game/arena.py:406](../src/wartune_server/game/arena.py#L406) | ~ o dano da captura (golpe básico ≈ vida/40) |
| [game/bag.py:75](../src/wartune_server/game/bag.py#L75) | o oficial sorteia randomSkill_1..N (RandomSkillCount); a tabela do sorteio não está nos |
| [game/battle.py:267](../src/wartune_server/game/battle.py#L267) | a iniciativa do oficial não foi decifrada; aliados NPC, inimigos e o herói por último |
| [game/battle.py:345](../src/wartune_server/game/battle.py#L345) | fórmula de dano desconhecida. PvE calibrado na captura do tutorial (herói mata os |
| [game/builders/login.py:76](../src/wartune_server/game/builders/login.py#L76) | bate com o oficial no nível 1 (199); nível 3 dá 291 contra 278. Falta a fórmula real. |
| [game/builders/login.py:243](../src/wartune_server/game/builders/login.py#L243) | 1 exército por personagem; tabela própria quando houver tropas extras |
| [game/castle.py:80](../src/wartune_server/game/castle.py#L80) | sem bônus de guilda/efeitos; o oficial soma +30 que não sabemos de onde vem |
| [game/castle.py:154](../src/wartune_server/game/castle.py#L154) | sem o bônus de raça/efeitos do limite (PlayerEffect.getTransferPowerLimitAddition) |
| [game/farm.py:19](../src/wartune_server/game/farm.py#L19) | sem upgrade de terra (opType 9 não tem sender) |
| [game/gemmaze.py:90](../src/wartune_server/game/gemmaze.py#L90) | o período (dia, UTC) não foi capturado; os movimentos comprados não somem (fica o maior). |
| [game/gemmaze.py:196](../src/wartune_server/game/gemmaze.py#L196) | 5 ou mais em linha segue a conta de 3 e 4 (não foi capturado) |
| [game/gemmaze.py:205](../src/wartune_server/game/gemmaze.py#L205) | prêmio sorteado uniforme entre os três vistos; a tabela oficial (pesos) precisa de captura |
| [game/gemmaze.py:208](../src/wartune_server/game/gemmaze.py#L208) | troca sem combinação é aceita e gasta movimento (o cliente troca na tela e não desfaz; |
| [game/guild.py:162](../src/wartune_server/game/guild.py#L162) | só os 50 últimos na memória; o banco guarda todos |
| [game/handlers/account.py:20](../src/wartune_server/game/handlers/account.py#L20) | prazo do reset não está no cliente nem nas capturas; ajustar se aparecer |
| [game/handlers/account.py:190](../src/wartune_server/game/handlers/account.py#L190) | sala de um jogador só; broadcast quando houver sala compartilhada |
| [game/handlers/arena.py:18](../src/wartune_server/game/handlers/arena.py#L18) | só os 42 base; espaços comprados/alugados via bag.capacity(c, now) |
| [game/handlers/arena.py:353](../src/wartune_server/game/handlers/arena.py#L353) | limite de compras do torneio não está no cliente nem nos templates; 10/dia como no coliseu |
| [game/handlers/army.py:237](../src/wartune_server/game/handlers/army.py#L237) | bênção cheia = sorteio garantido um grau acima; a regra exata do oficial não tem captura |
| [game/handlers/army.py:276](../src/wartune_server/game/handlers/army.py#L276) | grade 3x3 da formação; conferir limites quando houver captura |
| [game/handlers/army.py:301](../src/wartune_server/game/handlers/army.py#L301) | só a posição do próprio herói é gravada; |
| [game/handlers/army.py:321](../src/wartune_server/game/handlers/army.py#L321) | a posição do exército no mapa externo não é gravada (sistema do mapa externo). |
| [game/handlers/battle.py:35](../src/wartune_server/game/handlers/battle.py#L35) | a postura não muda o dano (a fórmula real não é conhecida) |
| [game/handlers/campaign_map.py:44](../src/wartune_server/game/handlers/campaign_map.py#L44) | mapa sem captura manda lista vazia; falta a lista de cada mapa (nós do .maps). Não muda estado |
| [game/handlers/castle.py:280](../src/wartune_server/game/handlers/castle.py#L280) | trégua ainda não existe; zera e confirma. |
| [game/handlers/chat.py:26](../src/wartune_server/game/handlers/chat.py#L26) | o cliente não limita a guilda (ChatHelper); 1 s contra spam |
| [game/handlers/chat.py:28](../src/wartune_server/game/handlers/chat.py#L28) | o cliente não limita o privado; 1 s contra spam |
| [game/handlers/chat.py:84](../src/wartune_server/game/handlers/chat.py#L84) | cota fixa do ConfigInfo; o VIP do oficial pode aumentar (sem VIP ainda). |
| [game/handlers/chat.py:165](../src/wartune_server/game/handlers/chat.py#L165) | "cena" = todos online até existir o registro de cenas (cidade do céu). |
| [game/handlers/events.py:164](../src/wartune_server/game/handlers/events.py#L164) | só os tipos 13 e 14 têm regra; os outros ficam "ainda não" até alguém implementar |
| [game/handlers/events.py:369](../src/wartune_server/game/handlers/events.py#L369) | nenhum desses sistemas conta ainda; lista vazia = tudo zerado no painel. |
| [game/handlers/farm.py:15](../src/wartune_server/game/handlers/farm.py#L15) | só os 42 base; comprados via bag.capacity |
| [game/handlers/farm.py:171](../src/wartune_server/game/handlers/farm.py#L171) | o texto do oficial (farm.view.FarmOperMenu.accelerateTip) não está decompilado; |
| [game/handlers/farm.py:205](../src/wartune_server/game/handlers/farm.py#L205) | sem fruto (quando a árvore frutifica não está nas capturas nem no cliente decompilado) |
| [game/handlers/farm.py:238](../src/wartune_server/game/handlers/farm.py#L238) | ações em fazenda de amigo ainda recusadas (lista de amigos), então tudo falso |
| [game/handlers/forge.py:29](../src/wartune_server/game/handlers/forge.py#L29) | o refino sorteado fica na memória até o 8339 (some se o servidor reiniciar) |
| [game/handlers/forge.py:199](../src/wartune_server/game/handlers/forge.py#L199) | autoBuy (comprar o que falta) não |
| [game/handlers/forge.py:211](../src/wartune_server/game/handlers/forge.py#L211) | o espaço é conferido antes de consumir (pode recusar quando os materiais liberariam lugar) |
| [game/handlers/forge.py:268](../src/wartune_server/game/handlers/forge.py#L268) | sorteio uniforme entre os atributos com Grades > 0; peso por nível precisa de captura 8336 -> 4258 |
| [game/handlers/friends.py:30](../src/wartune_server/game/handlers/friends.py#L30) | limites do cliente não achados (módulo de UI ausente) |
| [game/handlers/friends.py:312](../src/wartune_server/game/handlers/friends.py#L312) | ``pageIndex`` tratado como 1-based (UI ausente). |
| [game/handlers/gemmaze.py:71](../src/wartune_server/game/handlers/gemmaze.py#L71) | o oficial manda 0 para personagem novo; o contador não foi capturado |
| [game/handlers/gemmaze.py:77](../src/wartune_server/game/handlers/gemmaze.py#L77) | ranking semanal não existe aqui (o oficial manda 1771 para um jogador de topo) |
| [game/handlers/gemmaze.py:167](../src/wartune_server/game/handlers/gemmaze.py#L167) | sem subida de nível (a tabela de EXP por nível não foi capturada): curExp passa de maxExp |
| [game/handlers/gemmaze.py:179](../src/wartune_server/game/handlers/gemmaze.py#L179) | o semanal soma o mesmo que o do dia e zera na semana nova (``gm.refresh``, dedução) |
| [game/handlers/gemmaze.py:238](../src/wartune_server/game/handlers/gemmaze.py#L238) | a caixa vai para a bolsa do labirinto (o ícone voa para ela, como o das gemas); a bolsa |
| [game/handlers/gemmaze.py:258](../src/wartune_server/game/handlers/gemmaze.py#L258) | o template não diz a moeda nem o limite diário: diamante (ou vinculado com buyTypes 2) é dedução |
| [game/handlers/guild.py:19](../src/wartune_server/game/handlers/guild.py#L19) | só os 42 base; espaços comprados/alugados via bag.capacity(c, now) |
| [game/handlers/guild.py:182](../src/wartune_server/game/handlers/guild.py#L182) | duas transações (o membro precisa do id da guilda); se a segunda falhar fica uma |
| [game/handlers/guild.py:440](../src/wartune_server/game/handlers/guild.py#L440) | o oficial tinha guildas-robô; aqui vem o convite da guilda aberta com mais membros |
| [game/handlers/guild.py:609](../src/wartune_server/game/handlers/guild.py#L609) | o ``same`` (renomear grátis depois de juntar servidores) é cobrado igual. |
| [game/handlers/guild.py:653](../src/wartune_server/game/handlers/guild.py#L653) | não se sabe se o oficial aceita diamante vinculado aqui; gasta primeiro o vinculado |
| [game/handlers/guild.py:865](../src/wartune_server/game/handlers/guild.py#L865) | a tabela de prêmios do oficial não está nos templates; o prêmio é sempre um item |
| [game/handlers/guild.py:898](../src/wartune_server/game/handlers/guild.py#L898) | só na memória; reiniciar o servidor perde o prêmio |
| [game/handlers/guild.py:1002](../src/wartune_server/game/handlers/guild.py#L1002) | offline grava direto; se ele logar durante o await o item só aparece no próximo |
| [game/handlers/guild.py:1038](../src/wartune_server/game/handlers/guild.py#L1038) | o oficial abre a eleição quando o chefe some por muitos dias; a regra não está no |
| [game/handlers/guild_events.py:66](../src/wartune_server/game/handlers/guild_events.py#L66) | falta o sistema de mapas de campanha (só existe o do tutorial) e as ondas de |
| [game/handlers/hero.py:127](../src/wartune_server/game/handlers/hero.py#L127) | a EXP gasta sai da EXP do nível atual (c.gp); conferir com captura se o oficial |
| [game/handlers/hero.py:290](../src/wartune_server/game/handlers/hero.py#L290) | o preço sobe com diamondIndex (usos no dia); sem contador diário fica no primeiro |
| [game/handlers/items.py:215](../src/wartune_server/game/handlers/items.py#L215) | sem o teto diário de poções de Beden; só o limite do personagem |
| [game/handlers/items.py:381](../src/wartune_server/game/handlers/items.py#L381) | depois de juntar pilhas, fecha os buracos na mesma ordem (dedução) |
| [game/handlers/mail.py:38](../src/wartune_server/game/handlers/mail.py#L38) | correio de guilda (sendType 2) recusado até existir guilda. |
| [game/handlers/mall.py:43](../src/wartune_server/game/handlers/mall.py#L43) | duração livre de 1 a 72 h e página de 9: a tela de leilão não está no cliente decompilado |
| [game/handlers/mall.py:46](../src/wartune_server/game/handlers/mall.py#L46) | lock global do processo (um servidor por processo). Por anúncio se a fila pesar. |
| [game/handlers/marriage.py:7](../src/wartune_server/game/handlers/marriage.py#L7) | pedidos, ofertas de casamento e pedidos de divórcio ficam em memória (somem se o |
| [game/handlers/minigames.py:68](../src/wartune_server/game/handlers/minigames.py#L68) | janela de resgate desconhecida (2099 = sem fim) |
| [game/handlers/offer.py:28](../src/wartune_server/game/handlers/offer.py#L28) | o sorteio de qualidade do oficial não é conhecido; pesos para 1..5 (5 = ouro, rende x6) |
| [game/handlers/offer.py:204](../src/wartune_server/game/handlers/offer.py#L204) | as condições (RewardCondictionInfos: capturar NPC, missões, etc.) dependem de |
| [game/handlers/offer.py:224](../src/wartune_server/game/handlers/offer.py#L224) | depende do sistema de batalha abrir a luta com o NPC da tarefa; só registra. |
| [game/handlers/offer.py:330](../src/wartune_server/game/handlers/offer.py#L330) | as condições (enviar mensagem, batalhas...) dependem de outros sistemas avisarem; |
| [game/handlers/offer.py:342](../src/wartune_server/game/handlers/offer.py#L342) | sem compra de vagas extras |
| [game/handlers/outer_city.py:36](../src/wartune_server/game/handlers/outer_city.py#L36) | velocidade fixa, sem montaria nem efeitos |
| [game/handlers/outer_city.py:103](../src/wartune_server/game/handlers/outer_city.py#L103) | o próprio castelo e as minas; castelos vizinhos quando houver mapa compartilhado |
| [game/handlers/pets.py:25](../src/wartune_server/game/handlers/pets.py#L25) | pontos livres por nível do pet; o oficial não publica a regra |
| [game/handlers/pets.py:57](../src/wartune_server/game/handlers/pets.py#L57) | atributo = template + pontos + nível x aptidão/100 (aproxima o login #30; fórmula real fica no servidor oficial) |
| [game/handlers/pets.py:63](../src/wartune_server/game/handlers/pets.py#L63) | mesma aproximação |
| [game/handlers/pets.py:82](../src/wartune_server/game/handlers/pets.py#L82) | a família (tipo, tier, estrela) é o template; o filtro de UI do cliente (canComposePet, NeedGrade 50) não casa com as receitas: confirmar com captura de uma composição |
| [game/handlers/pets.py:202](../src/wartune_server/game/handlers/pets.py#L202) | devorar, crescimento, skills, sacrifício, treino, resistência e a fusão de 2 pets (15) dependem de tabelas e capturas que não temos (a fusão dá tipos 117-119, sem template) |
| [game/handlers/pets.py:218](../src/wartune_server/game/handlers/pets.py#L218) | só jogador online |
| [game/handlers/rewards.py:10](../src/wartune_server/game/handlers/rewards.py#L10) | só os 42 base; comprados via bag.capacity |
| [game/handlers/rewards.py:84](../src/wartune_server/game/handlers/rewards.py#L84) | x1,5 e x2 custam diamante no oficial, mas o preço não está no cliente; recusados |
| [game/handlers/shop.py:38](../src/wartune_server/game/handlers/shop.py#L38) | a tela da loja misteriosa não está no cliente decompilado; 8 é palpite |
| [game/handlers/shop.py:92](../src/wartune_server/game/handlers/shop.py#L92) | nenhuma loja tem NeedMinVip hoje; regra não conferida |
| [game/handlers/shop.py:156](../src/wartune_server/game/handlers/shop.py#L156) | presente depende do correio |
| [game/handlers/shop.py:328](../src/wartune_server/game/handlers/shop.py#L328) | troca os itens e zera as compras uma vez por dia |
| [game/handlers/space.py:75](../src/wartune_server/game/handlers/space.py#L75) | o outro teleporte (mina de ametista, 30000) depende do sistema de minas |
| [game/handlers/space.py:84](../src/wartune_server/game/handlers/space.py#L84) | mapa por sessão com os nós da captura; pets selvagens, coleta e o chefe (4686) |
| [game/handlers/stars.py:27](../src/wartune_server/game/handlers/stars.py#L27) | o oficial não publica as chances do sorteio; pesos por qualidade (Profile) e cristal |
| [game/handlers/stars.py:189](../src/wartune_server/game/handlers/stars.py#L189) | a fonte de energia vira StarPoint (moeda da loja); confirmar com captura |
| [game/handlers/stars.py:336](../src/wartune_server/game/handlers/stars.py#L336) | 1 espaço por compra; o preço sobe a cada 4 (fórmula do cliente) |
| [game/handlers/systems.py:64](../src/wartune_server/game/handlers/systems.py#L64) | a data de ativação não é guardada |
| [game/handlers/systems.py:97](../src/wartune_server/game/handlers/systems.py#L97) | só jogador online; offline precisa do banco |
| [game/handlers/systems.py:112](../src/wartune_server/game/handlers/systems.py#L112) | estrela/bênção, rei das montarias, loja, refino e voo dependem da UI que não foi |
| [game/handlers/systems.py:145](../src/wartune_server/game/handlers/systems.py#L145) | atividade de montaria nova (evento); sem captura da resposta |
| [game/handlers/systems.py:154](../src/wartune_server/game/handlers/systems.py#L154) | pesos da roda tirados do tamanho das fatias (FateRotaryModel.rndDic, em graus) |
| [game/handlers/systems.py:222](../src/wartune_server/game/handlers/systems.py#L222) | 1 de EXP por pedra (sem captura do treino) |
| [game/handlers/systems.py:332](../src/wartune_server/game/handlers/systems.py#L332) | a vocação (vocationGrades/Gp) que vem depois não tem tabela nem captura; começa no 1 |
| [game/handlers/systems.py:369](../src/wartune_server/game/handlers/systems.py#L369) | o buff da coleção completa (bufInfos da suíte, visto 40001) não tem tabela conhecida |
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
| [game/outer_city.py:70](../src/wartune_server/game/outer_city.py#L70) | o oficial escolhe um ponto livre; sem outros castelos no servidor, usamos o centro |
| [game/outer_city.py:102](../src/wartune_server/game/outer_city.py#L102) | o oficial sorteia o nível de novo a cada RefreshTime (43200 s) e a ocupação vence nesse |
| [game/rewards.py:20](../src/wartune_server/game/rewards.py#L20) | -600 "Kristal" (cristal do castelo) ainda não existe no banco (CRYSTALS fixo em |
| [game/rewards.py:23](../src/wartune_server/game/rewards.py#L23) | sem espaços comprados (bagCount) ainda |
| [game/rewards.py:72](../src/wartune_server/game/rewards.py#L72) | o oficial sorteia randomSkill_1 nos equipamentos (RandomSkillCount); a tabela |
| [game/rules.py:21](../src/wartune_server/game/rules.py#L21) | guerreiro e caçador são o espelho dele, trocar quando houver captura. |
| [game/social.py:154](../src/wartune_server/game/social.py#L154) | página única; paginar se a lista passar do tamanho de um pacote (200 amigos cabem). |
| [game/timebox.py:19](../src/wartune_server/game/timebox.py#L19) | o dia vira à meia-noite UTC; sem o horário de reset do servidor oficial |
| [game/timebox.py:60](../src/wartune_server/game/timebox.py#L60) | dedução, a fórmula do oficial não está no cliente; nível x minutos fora, até 8 horas |
| [game/worldboss.py:17](../src/wartune_server/game/worldboss.py#L17) | fuso fixo (UTC+3, sem horário de verão); outro fuso vira config |
| [game/worldboss.py:37](../src/wartune_server/game/worldboss.py#L37) | janela que cruza a meia-noite não existe nos templates; não é tratada. |
| [http/app.py:242](../src/wartune_server/http/app.py#L242) | respostas do suporte sempre vazias até existir o atendimento |
| [services/characters.py:62](../src/wartune_server/services/characters.py#L62) | cada jogador só vê o próprio castelo, então dividir o ponto não colide; com mapa |
