# Progresso por sistema

O oficial de referência é o **inglês**. Cada sistema tem duas colunas de fonte:

- **Inglês**: ✅ 100% com fonte inglesa (captura) ou do cliente · 🟡 parcial (uma parte recusa, só registra ou é atalho)
  · 🧪 funciona, mas com dado inventado (`TODO(inventado)` no código) · ❌ sem dado inglês nenhum
- **Turco**: 🇹🇷 quando a fonte foi o oficial turco (o inglês não tinha). O turco também é o servidor oficial: as
  regras, fórmulas e a ordem dos pacotes são as mesmas, então o que veio dele vale como ✅ no inglês. O que pode
  mudar entre os dois (itens que não existem aqui, textos, números de evento) vira `game_settings`, sem deixar de
  ser ✅. Texto traduzido do turco continua dedução até achar o inglês (`language.txt` ou captura).

Um ❌ sem 🇹🇷 é sistema sem dado nenhum: quando for feito, já nasce do inglês. Cada 🧪 e ❌ é uma captura a gravar; o
🇹🇷 só pede conferir itens e textos quando houver a captura inglesa (como capturar: [captura-oficial-en.md](captura-oficial-en.md)).

**Este é o único arquivo de progresso.** Não criar outro: sistema novo vira linha aqui, no mesmo commit que mudar o
status. Detalhe (pacotes, ordem, fontes) vai no MD da categoria ou no código, nunca aqui. Totais:
`python tools/progresso_totais.py`.

Levantado em 24/10/2026 a partir das docs e dos marcadores do código (`(visto)`, `(cliente)`, `só turco`,
`TODO(inventado)`, `shortcut:`/`ponytail:`); detalhes de cada linha nas docs de cada sistema.

## Resumo

| Categoria | ✅ | 🟡 | 🧪 | ❌ | 🇹🇷 |
|---|---|---|---|---|---|
| Validação e base | 1 | 3 | 0 | 0 | 0 |
| Castelo | 11 | 4 | 5 | 0 | 3 |
| Herói e exército | 14 | 12 | 2 | 1 | 4 |
| Pets | 3 | 6 | 0 | 2 | 2 |
| Itens | 12 | 6 | 7 | 1 | 2 |
| Lojas e mercado | 6 | 5 | 0 | 1 | 1 |
| Chat e social | 6 | 1 | 5 | 0 | 1 |
| Clã / Guilda | 10 | 0 | 9 | 2 | 1 |
| Campanhas e masmorras | 7 | 8 | 7 | 2 | 3 |
| Labirinto (Forgotten Catacombs) | 4 | 1 | 5 | 0 | 3 |
| Batalha | 5 | 6 | 1 | 2 | 1 |
| Missões | 12 | 3 | 2 | 4 | 0 |
| Tutorial | 2 | 0 | 1 | 0 | 0 |
| Mapa do mundo (cidade externa) | 3 | 3 | 9 | 2 | 2 |
| Mundo compartilhado | 4 | 1 | 0 | 1 | 2 |
| PvP e chefes | 1 | 2 | 3 | 3 | 2 |
| Atividades e eventos | 5 | 11 | 10 | 2 | 5 |
| VIP | 1 | 0 | 5 | 1 | 0 |
| Veículos (Tank Trials) | 3 | 1 | 0 | 1 | 1 |
| Conta e segurança | 3 | 1 | 2 | 2 | 1 |
| **Total** | **113** | **74** | **73** | **27** | **34** |

## Validação e base

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Conta nova até o castelo no Flash Player projector | 🟡 | | pelo portal, acompanhando `logs/packets.log`; ainda não validado |
| Tutorial no cliente real | 🟡 | | o oráculo bate com a tutorial_en sem exclusões (só ritmo, [tutorial.md](tutorial.md)); falta jogar no cliente |
| Cobertura de opcodes (`scan_opcodes.py`, C>S, classes novas) | ✅ | | os 438 C→S do cliente têm handler (o 20001 é o login da sessão) |
| `shortcut:`/`ponytail:` do código | 🟡 | | classificar: comportamento faltando (implementar), dado inventado (`TODO(inventado)`), atalho (fica) |

## Castelo

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Prédios: upgrade (8203) | ✅ | 🇹🇷 | upgrade comum conferido em 42 pedidos ingleses; tecnologia de atributo só no turco |
| Tecnologia: nível e fila 2 (8202/8203) | 🟡 | 🇹🇷 | ordem dos efeitos (110/150) do turco; fila de tecnologia no login por dedução |
| Filas de construção (8279, 5175, 8281) | ✅ | | |
| Aceleração de filas (5172) | ✅ | | preço do cliente; resposta e texto vistos (191924 #1341-#1346) |
| Cobrança de ouro (8327) | ✅ | | |
| Produção de ouro e teto (5015) | 🟡 |  | tecnologia de ouro conferida no inglês (231733 #3969-#3979, 60 no grau 1); bônus de guilda não entra |
| Roda da bênção do seminário (8489) | 🧪 | 🇹🇷 | subida de 10 a 70 inventada (`handlers/castle.py:38`); o 1º giro (10→50) só turco |
| Fazenda: plantio e crescimento | ✅ |  | inglês: minutos inteiros e 1 min antes (215937 #1257, 171155); bate com o turco; slot vazio compra a semente (24/10 #347-#353) |
| Fazenda: compra automática da semente | 🧪 | | pacote de 9 visto só para a Gold Seed; outras sementes usam 9 (inventado); 4484 antes do 111 não reproduzido |
| Fazenda: colheita, praga, acelerar, terras | ✅ | | pragas tiram/devolvem 10% e totalGp acumulado no inglês (191924) |
| Fazenda: roubo de amigo | ✅ | | ordem, textos e 10% no inglês (191924 #244-#263) |
| Fazenda: reviver e regar do amigo | ✅ | | rega, ouro (grau × 20) e reviver no inglês (24/10 #236, 27/10 #19855) |
| Fazenda: aviso ao dono online (145, rega e praga do amigo) | 🧪 | | rega e praga no inglês; textos do mato inventados (`farm.py`, `_tell_pest`) |
| Fazenda: subida de nível (111, 4386, 83) | 🟡 | | vista na rega e na praga do amigo; nos outros casos por dedução |
| Árvore: rega própria (15017) | ✅ |  | própria e do amigo no inglês (153200, 171155, 215937), igual ao turco |
| Árvore: colheita do fruto (5178) | 🧪 | | ordem e textos vistos (25/10 #218-#227, 27/10 #5075-#5086); Daru/Kyanite/ouro vistos nos graus 6 e 10, os outros graus são reta entre eles (inventado) |
| Caixa por tempo (5019) | ✅ | | reset diário de uma amostra só |
| Recompensa offline (8287) | 🟡 | | só ×1; ×1,5 e ×2 recusados (preço desconhecido); EXP = nível × minutos por dedução |
| Trégua (8562) | ✅ | | City Protection Token grava o fim (buff 2001), 4452 em segundos no uso/login/8201, 8562 e atacar acabam; castelo em trégua não é atacável (`PlayerBufferManager`, `MapPhysicsCastle.attack`) |
| Reforço em batalha (8255) | 🧪 | | pelo cliente (`CampaignArmyViewHelper`, `ReinforceHandler`): `Battle.join` põe o herói (cópia) numa posição livre do lado 1, 72 para os de dentro, 157 com o estado atual para quem chega, luta o resto e leva o prêmio (`_battle_over` mate); também no 8745 do tesouro. Nenhuma captura de 8255: ordem dos pacotes e posições (`TEAM_POS`) inventadas |

## Herói e exército

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Tropas: recrutar (5155) | ✅ | | |
| Tropas: formação (8276) e posição (8328) | ✅ | | |
| Tropas: evoluir (5158) e trocar tipo (8580) | ✅ | | |
| Tropas: especialidades (8455/8456) | 🟡 | | a 1ª vem sozinha no nível 10 (visto: Lancer 100, Hunter 200); o sorteio do 8455 só até o grau atual (atalho, `handlers/army.py`) |
| Tropas: formação de campanha (8277/8278) | 🧪 | | posição de cada membro gravada na sala (`Room.positions`), 4186 a todos, usada na luta em grupo; os lugares do lado 1 seguem `TEAM_POS` inventado |
| Herói: aprender skills e talento (5185/5187) | ✅ | | custo do talento por dedução |
| Herói: resetar skills e 2º conjunto | ✅ | | |
| Herói: redistribuir atributos (5170) | ✅ | | `*_point` voltam a `remain_point`; sem custo: no inglês nenhuma tela nem item chama o 5170 e a resposta 66 não tem handler |
| Subida de nível (139, 100, 150, 4640) | 🟡 | | vista na missão; por batalha, coliseu, fazenda e livro de EXP por dedução |
| Runas (8605) | 🟡 | 🇹🇷 | reforço sem o bônus 2x-20x; o 4495 do login do turco |
| Montaria: lista (8530) | ✅ |  | o 4426 junto do 4427 no inglês (231733 #11-#14), igual ao turco |
| Montaria: treinar, montar, ativar, voo | ✅ | | |
| Montaria: carta (5006, SonType 218) | ✅ | | |
| Montaria: refino de estrela | 🟡 | | bênção e chance de 5% são atalho (`handlers/systems.py:43`) |
| Montaria: ops 7-12 e evento (8843) | ❌ | | sem tela no cliente inglês |
| Destino: abrir (8628) | 🟡 | 🇹🇷 | tipos 2000/3000 do turco; 2100/2200 não abrem |
| Destino: treinar pedras (8626) | 🟡 | | 1 EXP por pedra é chute |
| Destino: roda (8627) | 🟡 | | pesos das fatias por dedução |
| Dragão: abrir e login (8642, 4555) | ✅ | 🇹🇷 | abre no 40 e vai no login (turco) |
| Dragão: alimentar (8641) | ✅ | | |
| Dragão: transferência (8643) | 🟡 | | vocação sem tabela (começa no 1) |
| Cartas de poder: subir e ativar (9505) | 🟡 | 🇹🇷 | o login do turco; subir e ativar sem captura de nenhum dos dois |
| Cartas: bônus de coleção (4905) | 🟡 | | degraus por dedução; o bônus não entra na luta |
| Cartas: ganho nas batalhas | 🧪 | | carta do saque da campanha entra na coleção (`systems.gain_cards`, item 600): a 1ª abre no grau 1, as outras viram +1 gp cada (inventado); usar a carta da mochila faz o mesmo |
| Estrelas: sortear (8269) | 🟡 | | grátis do dia sem 109 como o inglês (#19350, #6727); chances por qualidade são atalho; 4388 (SNS) na estrela de qualidade 4 com md5 inventado |
| Estrelas: recolher, vender, mover | ✅ | | |
| Estrelas: compor (8331) | 🟡 | | textos e ordem do inglês (#19525, #6816, #13736); o 4484 do início sem gatilho conhecido |
| Estrelas: travar, espaço, loja | ✅ | | |
| Estrelas: login | ✅ |  | 4180 no login inglês, igual ao turco |

## Pets

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Pontos, batalha, descanso, devorar (8621 ops 1-3, 9, 10) | ✅ | | |
| Sacrifício (op 6) | ✅ | | sorteio uniforme por dedução |
| Vagas e skills do torneio (op 12, 8726) | ✅ | | |
| Compor (op 13) | 🟡 | | 24 de 28 receitas |
| Avanço de qualidade (op 4) | 🟡 | | chance da bênção 10% é atalho |
| Encantar aptidão (op 7) | 🟡 | | quanto sobe é atalho |
| Aprender skill (op 5) | 🟡 | | sorteio uniforme entre livros |
| Crescimento, treino e resistência (ops 8 e afins) | ❌ | | o cliente não diz o ganho |
| Fusão de dois pets (op 15) | ❌ | | sem template |
| Mascote em batalha (EXP, despertar 4600) | 🟡 | 🇹🇷 | do turco; +250 por golpe e gasto 150 por dedução |
| Guarda da fazenda é o mascote | 🟡 | 🇹🇷 | do turco; ops 10-16 da fazenda recusadas |

## Itens

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Mochila: mover, empilhar, organizar | ✅ | | |
| Mochila: vender | ✅ | | |
| Mochila: expandir e aluguel | ✅ | | |
| Mochila: travar e remover vencido | ✅ | | |
| Itens com validade (medalhas) | 🟡 | | apagar sem aviso por dedução; falta captura de uma vencendo |
| randomSkill dos itens novos | 🧪 | | tipo 701 e peso dentro da faixa inventados |
| Teto diário de Beden e EXP vindos de itens | 🧪 | | Beden (stamina de poção) 300/dia do cliente (`wearyLimit`); EXP de itens 5.000.000/dia inventado (`game_settings.item_exp_daily`) e o texto do aviso inventado |
| Vínculo de itens | ✅ | | |
| Uso de recurso (203: ouro, Balens, EXP, Daru, Spirit Covenant) | ✅ | | texto e ordem do inglês (231733; EXP Book e Spirit Covenant em 191924) |
| Caixas de pedra (206) e outras caixas | 🟡 | | caixa com conteúdo só na descrição é recusada |
| Poção de HP e reserva de vida (209) | 🧪 | | "HP Pack has been exhausted." e a cura ao evoluir tropa vistos (171155, 231733); contrato de cura (`rules.py:210`) |
| Pergaminhos de EXP, ouro e população | ✅ | | ordem vista em 191924 (#1737, #2241, #3379) |
| Pergaminhos de outros efeitos | 🟡 | | ícone e tempo ligam; o efeito não existe |
| Poções de atributo | 🟡 | | ordem dos pacotes por dedução |
| Cristal, guilda e Token de proteção (5006) | ❌ | | recusados |
| Títulos (4484/8597) | 🧪 | | contadores (vitórias no coliseu, abates no campo, guerra de guildas, astral 10, catacumbas, necrópole), rankings (poder geral e por classe, coliseu, cross, pesca, gemas), posse de item/montaria e recorde do labirinto (`titles.py`); rankings de honra, charme, força da montaria e Sylph (pontuação `rank:*` gravada no login/8597; Sylph pelo nível do pet, inventado), golpe final no chefe do mundo e líder da guilda vencedora da guerra; sem sistema: guerra de classes, arena de Sylph, Hero Returns, guerra entre servidores e monstros dos Wilds |
| Forja: reforço (5150) | ✅ |  | sucesso e falha no inglês (171155 #2323-#2384), igual ao turco |
| Forja: engaste e furos (5151/5152) | ✅ | 🇹🇷 | engaste no inglês (231733 #1392: sem 109 no furo vazio, "Successfully Socketed Gem!"); troca e furos do turco |
| Forja: composição de pedras (5153/8538) | ✅ | 🇹🇷 | 5153 e transformação 8538 no inglês (231733 #1492, 26/10 #10315, sem aviso); caixa de pedras do turco |
| Forja: refino de atributos (8336/8339) | 🧪 | | ordem e "Refinement Complete!" do inglês (24/10 #8019-#8027); o sorteio continua inventado (`bag.roll_random_skill`); o sorteio pendente fica no EventState `refine` até o 8339 |
| Forja: decomposição (8340) | ✅ | | ordem vista em 191924 #2259-#2278; recusa calada por dedução (o cliente limpa a bancada com qualquer 4260) |
| Equipamento do mascote: encantar (8644) | 🟡 | | bênção zera por atalho |
| Equipamento do mascote na luta | 🟡 | | a luta não usa os atributos |
| Moda: composição (8594) | 🧪 | | cliente dá custo (níveis x 10000 de ouro), charms e chance por diferença de nível (só o nome); inventado: % das chances, sorteio da moda, consumo na falha e dos 5 curingas (`game_settings["fashion"]`) |
| Moda: avaliação (8781) | 🧪 | | cliente dá custo (Property1 em ouro), chance (TransformId) e skills; visto #2524 (109, 111, 4542); inventado: pesos das estrelas 1-5 e a família sorteada; sem aviso no sucesso; o bônus soma nos atributos do líder (livro inteiro, como o cliente); refino com Property2 Fashion Cores sempre acerta (inventado) |
| Moda: livro, provador, esconder | ✅ | | |

## Lojas e mercado

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Loja comum (5154) | 🟡 | | lojas de pontuação (8, 13, 15, 20) sem suporte |
| Loja de moda (8592) e poção (5633) | ✅ | | |
| Loja misteriosa (8483/8482) | ✅ | | 4470 vazio depois de cada 4384 (232017 #3057); quem entra na lista de sortudos, sem captura |
| Ofertas por tempo (4238/8218/8632) | 🟡 | | só o tipo 1 tem dado; rodízio sem captura |
| Compra coletiva (8645) | 🟡 | | ligada por padrão (migração 0104, `game_settings.group_buy` com `source`): oferta `type` 3 no 4238 em rodízio por edição, preço cai em 3 degraus pelos compradores do servidor, sinal + limite do dia, acerto cobra/devolve a diferença e entrega (4559/4560); sem acerto até `sendDate`, acerto automático pelo correio no login/8645 (8645/4559/4560 ausentes das capturas decodificadas), 1 sorteio de grupo por compra (`group_buy.py`, pelo cliente); catálogo/preços inventados |
| Presente a outro jogador e mochila cheia pelo correio | ✅ | | loja, ofertas e misteriosa: `receiveId` de outro (id pelo 8223/4148) cobra quem compra e manda pelo correio do sistema; mochila cheia paga e o que não cabe vai pelo correio (item com vínculo e validade). VIP e contrato a amigo seguem abaixo |
| Lojas de honra, glória, ametista | ✅ | | |
| Loja do labirinto (ShopType 4) | ✅ | 🇹🇷 | compra do turco; a Necropolis é outro sistema |
| Leilão: anunciar, lance, comprar, cancelar, buscar | 🟡 | | regras do cliente, sem captura; ordenação (8450/8457) ignorada, cancelar parte não reempilha |
| Leilão: venda de pet | 🟡 | | pet livre sem fonte |
| Correio: envio, retirada, lista | ✅ | | carta não vence |
| Correio: verificação de e-mail (9591) | ❌ | | sem SMTP |

## Chat e social

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Chat: mundo, cena, guilda, privado, corneta | 🧪 | | cota VIP de cornetas sem fonte (padrão 0); cena = mesmo mapa (sala ou mapa compartilhado) ou cidade do céu; a cidade (castelo) como uma cena só é inventada |
| Chat: time e sala (canal 6) | ✅ | | time livre ou, sem time, a sala (`ChatHelper.checkTeamChatScene`); só membros online |
| Corneta entre servidores (8623) | ✅ | | processo único: 4541 a todos os online |
| Convite rápido de sala (8353) | ✅ | | formato visto em 191924 (corneta sem 4500, uma tag `<a t="6">` por linha, leed 16 e 83); tipo 1 (casamento): link `roomType` 4 para a sala do casal |
| Amigos: pedir, aceitar, grupos, busca, lista negra, recomendados | ✅ | | |
| Amizade: grau (friend_gp) | 🟡 | 🇹🇷 | grau 1 no inglês bate com 1 + gp/10; graus acima só no turco (dedução da tabela) |
| Nome, ficha e busca de jogador | ✅ | | |
| Casamento: pedido, noivado, divórcio | ✅ | | |
| Casamento: cerimônia | 🧪 | | op 5 reserva (`speTemplateId`), casa no voto 101 da sala; roupas 8595 bloqueio real (MarryQualityTemplateCate lê MarrySpecTempInfo, sem SlotId/ClothId/WingId/HatId no inglês) |
| Casamento: sala (8760) e jogo do coração (8802) | 🧪 | | coração pelo m9 (MarryHeartFrame: opções 0-based, -1 sem resposta, Rose Hazel x syncRate/5, `mar_heart_count`/`answerNum`), pendências em server_states; nº de perguntas/segundos TODO(inventado) `marriage_heart`; sala pelo cliente (handlers/wedding.py: 4662/4673/4674/4660/4672/16, padre e criado, mar_time, carro pelo Path); salões 4301-4303 gerados (0112) e falas/pontos TODO(inventado) |
| Casamento: árvore e missões do casal | 🧪 | | árvore do casal (8773/4678 e `marriageTree` no 4386) pelo cliente (MarryTreeView/MarryTreeFosterFrame) e 191924 #1249; chance de mato/praga e quantidade de Rose Hazel inventadas; missões do casal (8774/4675, RewardTemps tipo 4, `marriage_task_count`, `mar_task_add_happy`); usar item cumpre 22/23 (dedução) |
| Casamento: loja do altar (9611) | 🧪 | | `Mate_Shop` paga com os pontos do casal (`marriages.couple`, 0111); op 2 = compra e pontos como `altarScore` TODO(inventado) |

## Clã / Guilda

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Criar, candidatar-se, convidar | ✅ | | |
| Membros e informações | 🧪 | | matchWin/matchFailed somados dos membros (`guildwar:win`/`lose`, gravados no prêmio da guerra) |
| Cargos e direitos | ✅ |  | direitos byte a byte no inglês (4137 de 171155, 215937, 231733), iguais ao turco |
| Expulsar, sair, passar chefia, mudar cargo | ✅ | | |
| Eleição do chefe | 🧪 | | regras do `chairmanElection.help` (10 dias, 3 dias, 3 dias de voto) no relógio 20008; `votingState` 3 = votando (dedução), empate e texto do evento inventados |
| Contribuição e ranking | ✅ | | |
| Melhoria de prédios (1-5) | ✅ | | |
| Habilidades (6-12) | 🧪 | | "Gold Production +N%" inventado (`castle.py:103`) |
| Mercado da guilda | ✅ | 🇹🇷 | ordem da compra do turco |
| Baú da guilda (distribuir) | ✅ | | correio de mochila cheia por dedução |
| Baú de prêmios | 🧪 | | a guerra de guildas enche o baú com Guild Treasure (2060044): presentes do lado vencedor, metade para o perdedor (quantidade inventada) |
| Altar: bênção | 🧪 | | casas, ordem do 4144 e entrega do 8216 (item, ouro, Daru, Bound Balens) conferidas em 17 bênçãos (121659, 191924); pesos, casa dos raros e sementes inventados; ×10 recusada |
| Altar do demônio (boss de guilda) | 🧪 | | handlers/altar.py: ondas sobre o Pool do world boss, vida do herói 1042 do template, reviver 8264 tipo 2 por contribuição, buff 8550, habilidades 8593; ondas/tempos/recompensas TODO(inventado) `altar_demon` (0110) |
| Terra secreta: entrada e saída | ✅ | | |
| Terra secreta: invasores | 🧪 | | onda e vencidos em `server_states` (0109), voltam no arranque; contribuição inventada (0073) |
| Terra secreta: árvore sagrada | 🧪 | | EXP do tique e energia inventados (`fam.py:33`) |
| Anúncio de recrutamento | 🧪 | | canal e remetente inventados |
| Correio de guilda | ✅ | | |
| Guerra de guildas | ✅ | | mapa 4501 (26/10 #2464-#6452): par das 8 maiores, torres, placar/10000, vantagem de 4000, feridas, buffs, prêmio; PvP 8548 com luta real (battleType 24 do cliente, cópia do inimigo, sem captura) e o perdedor no acampamento; TODO: janela diária e carro/invencível sem efeito |
| Guerra entre servidores | ❌ | | |
| Master Treasure Thief (8743) | ❌ | | |

## Campanhas e masmorras

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Entrada (5039) e estamina | ✅ | | sem estamina entra sem prêmio (EXP, drop, carta) e sem gastar, com "Insufficient Stamina" (cliente); sem captura |
| 1001 Worg Lair | 🟡 | 🇹🇷 | cartas 1080012 e 1080002 no inglês, 1080013 no turco; Pandora só dá o buff; 5180, cartas pagas e progresso salvo faltam |
| 1002 Baylon Plains | ✅ | | caixa do caçador com uma amostra |
| 1003 Temple of Ibalize (Outer) | 🧪 | | drops de 5 nós inventados (0062) |
| 1004 Temple of Ibalize (Inner) | ✅ | | |
| 1005 Orc Plains e 1006 Tribal Plateau | 🧪 | | escolta da Elise vista (231733); luta do elite 115116 inventada (0075) |
| 1007 Camp Calorn | 🟡 | | 1ª etapa (1171 → 1172) vista em 191924 #2345-#3706 (migração 0090), chefe Viscount Remus sem vitória: fim da etapa sem captura; 2ª etapa (1181/1182) não jogada; Mystery Box por dedução (0062) |
| Masmorras solo capturadas (1101-1107, 1201) | 🟡 | | 1101, 1103, 1104, 1105, 1107 e a 1ª etapa de 1102, 1106, 1201 das capturas (migração 0098) |
| Masmorras solo geradas (1202-1602 e 2ª etapa de 1102, 1106, 1201) | 🧪 | | TODO(inventado) tools/gera_masmorras.py (migração 0099): planta das capturadas, mapas/casas/monstros do cliente; chave `inventado` marca o que trocar |
| Masmorras em grupo capturadas (9000, 9001, 9002) | 🟡 | | das capturas inglesas 191924, 232017, 152321 (migração 0100); entrada do dia (`paraBool1` = isNoGet) e o texto do 83 vistos; mapa dividido pela sala (21 com todos, 4185 do caminho, a luta de um leva os outros no lado 1 e todos ganham o 4103 e o nó); os outros lutam no automático (ordens só de quem atacou) e o lugar do 3º/4º é inventado; baús VIP 209109/203108 com a caixa da 201110 (prêmio TODO(inventado)) |
| Masmorras em grupo geradas (9003-9013, 9104-9112) | 🧪 | | TODO(inventado) `tools/gera_masmorras.py grupo` (migração 0101): planta da 9002 (2031 meio, 2033 fim), mapas/casas do cliente, monstros 4xxx/chefes 3xxx pelo nível; pesadelo com vida x `StandardDamage` e EXP x `BaseGp` do `Campaigns` (pesadelo/normal); chave `inventado` |
| Torres 8200-8204 (Tower of Kings, Spire) | 🧪 | | sala em grupo (game/torres, migração 0102). Cliente: uma entrada por dia em cada, dificuldade N com a N-1 vencida, 4900, andar da Spire (``currentWave``/``reinforceWave``), pulo de andar (TrailCountView: 3 turnos pula 4, além do 24 limpa), loja das Spire Runes (4468/8582/4467, ``TrialSkill``) e uso na luta (10507), battleType 290/25, leed 28 e Recuperar EXP. Internet (fontes-internet.md): baú e EXP por luta da King (100k/300k/900k/2,5M), 24 chefes da Spire com 300k e 7 baús cada, sem carta no fim. King com 5 lutas contra as sombras dos 16 mais fortes (cópia do coliseu); TODO(inventado): mapas e monstros da Spire (planta da 9002), crescimento das sombras por nível, sombras geradas sem jogadores, cota diária da loja; TODO(captura): texto de entrada |
| Pedreira 6001 | ✅ | | colheita espera a animação (4 s, `game_settings.quarry_collect_seconds`) |
| Exército do sistema (5038) | 🟡 | 🇹🇷 | bate com o inglês em todos os mapas pedidos (1011-1161, 7501); a 2011 do turco; mapas sem lista mandam vazio |
| Patrulha dos monstros (4122) | 🟡 | | nós sem captura ficam parados |
| Varredura / Blitz (8528) | 🧪 | 🇹🇷 | baú de prata e caixa misteriosa inventados (`sweep.py:40`); ouro só da 1007 turca |
| Cartas do fim (5122/5180) | 🟡 | | chance real falta; carta paga tratada como grátis |
| Relatório da etapa (137) | 🟡 | | curva por nível falta |
| Salas de campanha (criar, entrar, senha, convite...) | ✅ | | criar/editar/convidar vistos em 191924 (4 vagas, "Select a campaign.", 4186, 24, textos do 111); playerState do dono e Start da sala do turco; 5027 só registra (aba que o cliente não tem); 5024 recusado (senha, cheia) devolve o 4270 da sala (225632 #12656) |
| Times (convite, capitão, sair) | 🧪 | | membros, capitão, posições e ausência em `server_states` (0109); quem cai fica no time e o login manda o 4624 (dedução: sem captura de relogar em time) |
| Link de sala no chat (9504) | ✅ | | |
| Salas PvP (5023, 5039, 8344, 8465) | ✅ | | criar, senha, procurar e "Cannot find a room." vistos (24/10 #11533, 27/10 #19884-#21047); arena em grupo (handlers/arena_grupo.py): salas na fila emparelham, luta battleType 10 time contra time, 4103, missão 16, leed 13, contador `match`, Insignia x10 na derrota (27/10 #19912-#19995); prêmios em game_settings.arena_party (0107); pontos semanais (crossScore do 3) e ranking em cross/crossscore.xml do PvpHeroFrame (game/arena_grupo.py); dono que cai perde e as salas voltam a 1; vitória x20, pontos 10/5, texto "Points +N" e lugares do lado 2 inventados; só salas deste servidor |
| Falas e câmera no meio da luta (171/142) | ❌ | | |
| Pedágio (8752-8755) | ❌ | | fechado |

## Labirinto (Forgotten Catacombs)

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Info e reset (8297/8299) | 🟡 | 🇹🇷 | do turco; ranking (`order`) por andar e desempate pelo horário (jogador 28/10), calculado no 8297 e no 4373 do login; dificuldade em `game_settings.maze.hp_pct`; prêmio do reset sem captura |
| Corrida: entrar, luta, portal (8296) | ✅ | 🇹🇷 | do turco |
| Andares 1 a 25: monstros, chefes, escoltas, baús | ✅ | | todos vistos (24/10 #12046-#13771, 25/10 #9658-#10909); vitórias só dão EXP; subir andar conta a missão 38 (1 por andar, inferido) |
| Andares 26 em diante | 🧪 | | 26-28 como na captura 28/10 (#1369-#1766, 127 #1355/#1474/#1669: escolta 7026-7028, skills, attackModel 1; sem herói inimigo; o 28 não foi vencido na captura, EXP 11200 é a regra). Do 29 em diante a luta e o poder do nó saem do catálogo (fórmula que reproduz os 28 vistos); o ícone (sonType) vem do desenho já visto (29), do 30 em diante falta captura |
| Aviso de respawn (4207) | ✅ | | manda após a derrota: 0 grátis e 25 depois (28/10 #1105, #1547, #1742, #1827). Morto e sem reviver, a saída (5025) manda 4419 com os itens e zera a corrida (25/10 #11411, 26/10 #13469, 28/10 #1839-#1854); revivido (8300) ou vivo, sai sem 4419 e a corrida continua (24/10 #13956-#13965) |
| Corrida dobrada (Crypt Key) | 🧪 | | EXP em dobro inventada (`tower.py:170`) |
| Reviver (8300) | ✅ | | grátis: 111 "Respawn Successful!" e 4175; pago: 3, devoção, 150, 4434 antes (28/10 #1134, #1566, #1755) |
| Varredura do labirinto (8528 tipo 2) | 🧪 | | baús dos andares 5/10/15/20 com fichas e gema, ordem 115/83/111/4425 (25/10 #9394-#9650); o oficial sorteia a gema por corrida, aqui fixa; itens extras após o status 5 (#9630-#9643) sem origem; dobrado inventado (`sweep.py:155`) |
| Necropolis (8101) | 🧪 | | 30 andares pelo cliente/templates (mapas 8101-8130, chefes GameHeroTemp 8001-8030 "Level k Guardian", `checkMaze2`/`towerInfo2`, varredura até 29), abre com o recorde 100 das Catacombs; mesma torre do labirinto (`maze.Kind`): entrada diária, morte/reviver, baús, ranking, varredura, primeiro abate no 4205 (firstHit = 1º do ranking, inventado; `first_kill` desliga; o cliente só mostra com MAZE_FIRST_KILL, que nenhum 4422 liga). Sem captura: EXP (400 x (100+k)), baús, sonType dos nós e varredura a partir do 10 inventados (`maze.py` NECROPOLIS) |
| Guarda de batalha e gemas (8742/4631) | 🧪 | 🇹🇷 | pelo cliente: abrir encaixe (nível, Kingdom Mark, 300 de resistência na Willpower), encaixar/trocar/tirar gema (volta à mochila ou correio), resistências no herói (150/HeroMsg), login 4631 com o estado (turco #35), missão 926; compor/subir nível pelo 5153 (Types 6). Sem captura do 8742: ordem da resposta e gema devolvida vinculada inventadas; na batalha o golpe de elemento do mascote cai pela resistência do alvo menos o ReduceResi (fórmula inventada, attle.resist_factor) |

## Batalha

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Fluxo, relógio e quadros | ✅ | | |
| Fórmula de dano | ✅ | | |
| Alvos, morte e reposição de tropas | ✅ | | |
| Alvo aleatório | 🟡 | | ordem do oficial não decifrada |
| Reforços (ondas novas) | ✅ | | ordem das ondas sorteada e um 4149 por onda (171155, 231733) |
| Iniciativa (ordem das unidades) | 🟡 | | ordem fixa, sem dado |
| Crítico e bloqueio | 🟡 | | ganhos por dedução; chances da internet |
| Skills, buffs e controle | 🟡 | | atordoado sem captura |
| Passivas, talento, runas e destino | 🟡 | | runas e destino por dedução |
| Cartas de poder e dragão na luta | 🟡 | | dragão sem tabela de skill |
| PvP manual | ✅ | | |
| EXP do mundo e EXP descansada | 🧪 | 🇹🇷 | 10× só turco; nível mínimo e acúmulo inventados (`rules.py:519,539`) |
| Selo sagrado, itens na luta, skill de casal | ❌ | | |
| QTE, assistir batalha, postura | ❌ | | |

## Missões

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Aceite, progresso, entrega e recompensas | ✅ | | |
| Principais: recrutar, nível, tropa, construção | ✅ | | |
| Segundo login, nível, eventos (39, 1, 40, 63, 66, 87) | ✅ | | |
| Entregas conferidas com as capturas (5014) | 🟡 | | até o nível 20: 27 de 44 iguais ao oficial; 21-31: 10 de 26 conferidas (prédios, 503, 623); faltam catacumbas (6), mina de Amethyst (86, ligada na coleta; entrega não conferida), 241/768 pelo handler e a ordem 52/83 em 5 subidas de nível |
| Castelo e ocupação (7, 8) | 🧪 | | castelo de jogador atacável (cópia do herói, battleType 4); saque e proteção inventados (`player_castle`, migração 0113) |
| Campanha (14, 25, 26, 31) | 🟡 | | 1001-1006 jogáveis; 1007 só a 1ª etapa; masmorras solo com captura na 0098 |
| Coleta de item (27, 28, 32, 49) | 🟡 | | itens sem fonte; coleta no espaço não feita |
| Diárias e repetíveis | ✅ | | repetível concluída vai no 112 do login (QuestTemps IsRepeat) |
| Conversa com NPC (85) | ✅ | | patrulha (MasterType 1) conta sem conferir a posição (o NPC anda; o cliente abre a janela sozinho) |
| Guilda (22, 29, 30, 51) | ✅ | | 22/29/51 pelo estado (`social_state_quests`, 5014), 30 no altar (5145); test_missoes_social.py e test_missoes_tipos.py |
| Chefe do mundo (40, 41) | ✅ | | entrar e dano total contados |
| Campo de batalha: entrar (44) | ✅ | | contado na entrada 8332 |
| Arena e batalhas (45, 50) | 🧪 | | 45 por vitória no PvP do campo (visto #11106); 50 para o lado com mais pontos no fim (lados equilibrados na entrada e desempate sem vencedor, inventados) |
| Arena e batalhas (35, 79, 80) | ✅ | | 35 no desafio do coliseu (8253); 79 ao entrar na batalha de tanques, 80 a quem vence (vehicle.py); posição do 112 inventada |
| Arena e batalhas (16) | ✅ | | 16 no fim de cada luta da arena em grupo (arena_grupo.py; 112 visto 27/10 #19929); test_arena_grupo.py |
| Arena e batalhas (93) | ❌ | | 93 Sky Trail sem sistema identificado no cliente (TODO em rules.py) |
| Equipamento, forja e runa (17, 18, 19, 46, 47, 77) | ✅ | | forge.py (5150, 5151, 5153, 8336, 8340) e hero.py (77 nas pedras gastas) |
| Demais tipos (12, 21, 56, 57, 59, 61, 64, 65, 71, 74, 86, 91) | ✅ | | 64 alquimia (8321), 65 alquimia de Daru (8467), 74 entrada na Spire, 86 coleta na mina de ametista (5032), 91 exploração (9502 op 3); os demais já ligados; posição do 112 inventada |
| Demais tipos (58, 90) | ❌ | | sem a ação no servidor: 58 Soul Engraving (sem tela no cliente), 90 gemas da guarda (8742); TODO em rules.py (89 Lost Treasure conta no treasure.py) |
| Janelas fechadas e Koyu Kristal | ❌ | | |
| Mini-client (33) e celular (48) | ❌ | | |

## Tutorial

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Campanha de treino (10001/10002), retomada, missões e guia | ✅ | | oráculo com tutorial_en |
| Nível e atributos de guerreiro e caçador | 🧪 | | crescimento espelhado do mago (palpite); o ×1,05 do 150 fora da maga |
| Oráculo: diferenças conhecidas | ✅ | | só ritmo e outros jogadores ([tutorial.md](tutorial.md)) |

## Mapa do mundo (cidade externa)

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Grade, andar e exércitos | ✅ | | exércitos dos outros online no 169, rota no 4167 e saída no 4168 (`OuterCityController`) |
| Mudar o castelo de lugar (5176) | 🟡 | | ordem 140/152/140/105 e energia no inglês (24/10 #15689, 27/10 #18049); ponto de chegada: o livre mais próximo do centro (regra do ponto inventada) |
| Minas de ouro (missão 60) | 🟡 | | perda de soldados na derrota e refresh com o jogador online sem captura |
| Minas do mundo (mapas 1-5) | 🧪 | | grades não vistas inventadas (`mines.py:22`) |
| Atacar mina de outro jogador | 🧪 | | cópia do herói inventada |
| Castelos NPC do mundo | 🧪 | | grades, saque e nomes inventados (`npc_castles.py`) |
| Castelos-robô (missões 100, 411, 765) | 🧪 | | saque acima do grau 30 inventado |
| Monstros dos Wilds e patrulha | 🧪 | | luta em grupo: quem é do time entra na luta em curso (`Battle.join`) e leva o abate e o baú; quem pode entrar é inventado |
| Chefes do mapa (9525, 4938) | 🟡 | 🇹🇷 | relógio e lista no inglês (153200 #191); luta: 4938 type 4 e herói do chefe da 157 do inglês (24/10 #16254-#16256); aviso de abate do inglês (26/10 #1106); falta luta em equipe, prêmio do abate e nome inglês ("Purgatory Lord", o catálogo turco dá "Balrog") |
| Baús dos Wilds (9526) | ✅ | | |
| Treasure Cache | 🧪 | | vagas por mapa inventadas (`caches.py:48`); prêmio deduzido das 4 amostras da 171155 |
| Mapa do tesouro (8744) | 🧪 | 🇹🇷 | ops 1-6 pelo cliente e idioma (`treasure.py`, `game_settings.treasure_map` da 0105): 4 qualidades, melhora (vinho + Balens, chances de Property1/2 por dedução), lugar no item, escavar no lugar ou já (pago), luta com o Master Treasure Thief e o grupo perto, 4634 e prêmio Property6 x Crystal Shard (+% na lendária, inventado), missão 89; 8745 reforço entra na luta em curso (`Battle.join`), na partilha e na missão 89; login: só turco, nenhuma captura inglesa acima do nível 31; lugar (NPC sorteado), ladrão como inimigo e battleType inventados. 8535 é o transporte do chefe (worldboss.py), não o tesouro |
| Rest House e Altar of Ennoblement | 🧪 | | teto diário inventado (`hangup.py:49`) |
| PK no campo de animais (8525) | 🧪 | | ilha dos pets/mina: luta direta (BattleType 19); outras salas: convite 4421 e op 2; battleScene inventado |
| Passe de progresso (8636/8637) | ❌ | | |
| Ataque extra (9506) | ✅ | | |
| Coleta de Amethyst e Copper | ❌ | | |

## Mundo compartilhado

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Presença (11) e falas dos NPCs (4163) | 🟡 | | chance das falas e corte do 4595 em 30000 por dedução |
| Cidade do céu: presença e visual (4606/4607, 149) | ✅ | 🇹🇷 | 4606/4607 e o 149 de quem chega no inglês (215937 #826-#830) |
| Cidade do céu: nós e NPCs | ✅ | | |
| Ilha dos pets (127, patrulha) | ✅ | 🇹🇷 | sequência do turco |
| Coleta no espaço (8733) | ❌ | | |
| Times livres | ✅ | | |

## PvP e chefes

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Janela do PvP | ✅ | | |
| Coliseu | 🧪 | 🇹🇷 | EXP 180/120 por nível, 157, 4176 e o VIP Token no inglês; Luck Stone do turco; prêmios por posição inventados (`arena.py:347`) |
| Torneio de fadas | 🟡 | 🇹🇷 | do turco; vida e dano do pet aproximados |
| Arena entre servidores (8590) | ❌ | | |
| Senhores, casal, mina de ametista | ❌ | | fechados |
| Campo de batalha (4005/4007, mina 30000) | 🟡 | | entrada, coleta, entrega, 4255, HP, fim e prêmio, carrinho da mina e 4185 com serverName (25-27/10), 4269 na entrega, 4549 na abertura/fecho da mina (no login dentro da janela, inventado); PvP 8334 entre jogadores locais (157 battleType 32 contra a cópia do alvo, 4494 state 2/0, 4104/4175 com o perdedor em 179,75 por 25 s, 4103, 4388 tipo 4, 4269 de ganho e perda; perda de 15% e ganho igual, inventados); missões 45 (abate no PvP, 767 vista #11106) e 50 (vitória da partida, posição do 112 inventada); honra e Amethyst sem moeda; nós, vencedor e constantes no código (sem `game_settings`) inventados |
| Ataque a castelo/exército de jogador | 🧪 | | castelo (5160) e exército (8488) contra a cópia do herói; recusa por trégua, guilda e nível pelo cliente; saque, relatório da defesa e PvP de exércitos sem captura |
| Boss mundial: agenda e luta | 🧪 | | luta inteira vista (27/10 e 26/10: avisos, barreira, moral, fim, correios, reviver pago); vida = Live × 1,5 por abate (exato nas capturas); último golpe direto; inventado: o correio do último golpe se quem matou saiu; cair sem abate e `kill_turn` da internet |
| Boss mundial: buff e dublê | ❌ | | |

## Atividades e eventos

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Login diário e presente online | ✅ | | dias 1 a 4 do login acumulado no inglês (153200, 191924) |
| Baú de atividade diária (8235) | ✅ | | ordem e texto do inglês (tutorial_en #1561); mochila cheia: "Insufficient Inventory space." (27/10 #6040) |
| Devoção (leeds) | 🟡 | 🇹🇷 | leed 8 no inglês (171155 #4955); 17 e 33 do turco; 13 (arena em grupo), 27 (entrar no campo, 8332) e 28 (Spire) ligadas |
| Guia de 7 dias (8749) | 🟡 | 🇹🇷 | tarefa 23 nunca; login do turco |
| Atividades por contador (SumActive) | 🟡 | | troca (tipo 10) vista (191924); painel conta match, reward, vehicle e minefield |
| Contadores do painel (8518 → 4412/4413) | 🟡 | 🇹🇷 | torneio de fadas (turco); match (arena em grupo), reward (entrega do bounty), vehicle (fim do veículo) e minefield (entrada na mina) contam com 4413; 5001-5003 são os chefes do mundo, contados na entrada (visto #1407) |
| Fundo de novato e fundo normal | 🟡 | | janelas por dedução; compra e resgate do fundo normal sem captura |
| Árvore dourada (8604) | 🟡 | | pesos, início da edição e "uma vez por dia" por dedução |
| Labirinto de gemas (9508-9517) | 🧪 | 🇹🇷 | maxExp inventado (`gemmaze.py:29`); ajuda de amigo recusada |
| Roda do destino | 🟡 | | tipos 2100/2200 nunca abrem |
| Super assinatura | ✅ | | |
| Pacote de recarga e ofertas | ✅ | | |
| Painel de recompensas e anel de tarefa | 🟡 | | aceite, andamento e entrega no inglês (231733, 121659); condições contadas: recrutar e itens (estado), forja, gemas, síntese, astral, contribuição, compra, mina, sacrifício de pet, mensagem, abates e anel; o 8729 entrega quando cumpridas; 14 (Apprehend): o 8298 abre a luta com o herói NPC do Para1 e conta na vitória (battleType e cena do mundo, inventados); texto do Daru inventado; vagas extras (4360 `rewardCount`) ficam 0: o cliente não tem pacote de compra |
| Alquimia e alma (8321, 8467) | 🟡 | 🇹🇷 | troca no inglês (171155 #7827), 3 antes do 4372 nas 4 capturas novas; o oficial respondeu o 8320 no nível 10 e não no 11/12 (regra desconhecida); `point` diferente (o cliente não lê) |
| Anúncios agendados | ✅ | | |
| Estrada dourada (9520) | 🧪 | | tabuleiro de 36 casas do inglês (24/10 #2454, 27/10 #1354); sempre o mesmo tabuleiro (inventado) |
| Pesca (9507) | 🧪 | | abrir, pescar, errar, cesto e cd do inglês (26/10, 27/10, 28/10); ranking semanal lista também quem tem 0 pontos (no fim); ⏩, ferramentas, fúria e ajuda sem captura (chance da fúria, nomes das ferramentas 2-4, alcance dos torpedos, prêmio sem ajuda inventados: `fishing.py`) |
| Caça ao tesouro (9502) | 🧪 | | ops 1-7, 10 explorações com recarga, diálogo, achado e troca de 100 shards pelo cliente e idioma (`treasure_hunt.py`); nós, achados, 30 min e preço do "+" inventados |
| Quiz (9501) | 🧪 | | agenda, tempos, pontos e EXP do top 10 pelo idioma; estados, 4907-4910 e ajudas pelo cliente (`quiz.py`, `game_settings.quiz`); banca (Option1 certa), pontos e EXP inventados |
| Minério de Stokes (9645/35) | 🧪 | | 187-190 e ops pelo cliente, veio do servidor com andares especiais (`ore.py`, `game_settings.stokes_ore`); veio gravado no banco; preços, limites, achados e textos inventados (`game_settings`) |
| Caça-níquel (9500) | 🧪 | | regras da ajuda inglesa e do cliente (`slot.py`, `game_settings.slot_machine`); pesos dos dígitos e preço inventados (`game_settings`) |
| Loteria (8750/8748) | 🧪 | | tentativas pelo gasto de Balens no `cash_ledger` (idioma) e mensagens do cliente (`lottery.py`, `game_settings.lottery`); avisos do 4639 gravados no banco; sorteio e texto inventados |
| Cadeiras (9638) | 🧪 | | mensagens do cliente (`chairs.py`, `game_settings.chairs`); regra inteira inventada (cadeira por recarga, sortudos pelo total) |
| Sorteio de grupo (9523) | 🟡 | | ligados por padrão (migração 0103, toda regra em `game_settings` com `source`); roleta 338/4936 pelo cliente (`group_draw.py`); cada compra coletiva (8645, `group_buy.py`) dá 1 sorteio; sorteio inventado |
| Campo minado, caixa de ano novo, história | ❌ | | |
| Recuperar EXP (9503) | 🧪 | | lista de ontem (game/recover) e resgate ouro/item/item+diamante no inglês (27/10 #63, #745-#760, #18450-#18479); os 10 sonTypes com contador (Necropolis pelas entradas do dia da torre, fechada sem o recorde 100; Spire pela entrada do dia de game/torres); altar 20 de estamina/unidade visto; curva de EXP/ouro do chefe por nível inventada (TODO) |
| Troca da sorte (9610) | 🟡 | | recusa "Insufficient exchange items." e 4247 do inglês (27/10 #11765); sem tabela das edições |
| Corneta (passe), 360 | ❌ | | |

## VIP

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Estado e nível (4410) | 🧪 | | vipGp: `Vip_DailyAddGp` por dia de VIP pago, somado no login, na compra e na virada do dia online (agendador); o dia da compra conta (dedução); VIP que vence online avisa a guilda (4455) |
| Compra (8513) | 🧪 | | presente a amigo (online pela sessão dele, offline pelo banco), pago por quem dá, com carta do sistema ao amigo (texto inventado); o inglês não manda o 8513 |
| Presente semanal, cartão de teste, roleta | ✅ | | |
| Contrato do rei: compra | 🧪 | | presente a amigo como o VIP: 4434 ao amigo online, banco se offline, carta do sistema (texto inventado) |
| Contrato do rei: efeitos | 🧪 | | cura e varredura (`rules.py:210`, `sweep.py:40`) |
| Privilégios extras (montaria, missões, cornetas) | ❌ | | lista em [eventos.md](eventos.md); só o aviso 4610 da montaria VIP (cartão e primeiro login vencido) |
| Loja do teste (8582) | 🧪 | | é a loja da Spire: ver Torres 8200-8204 |

## Veículos (Tank Trials)

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Fila, sala e entrada | ✅ | | |
| Garagem e ativação | ✅ | | tecnologia 218 do inglês (`game_settings.vehicle_tech`) |
| Partida (dano, pontos, chefe, prêmios) | 🟡 | | sem captura de partida |
| Login (4512/4515/4516/4501) | ✅ | 🇹🇷 | a partir do nível 35 (`OpenGradesII.VEHICLE`): o turco de nível 56 manda, os ingleses de 1-16 não; janela 4512 no inglês |
| Veículos nos mapas de guerra | ❌ | | |

## Conta e segurança

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Senha secundária e recompensa da primeira | 🧪 | | prazo do reset (3 dias) inventado (`account.py:20`) |
| Relógio de integridade e launcher | ✅ | | |
| Anti-vício (AAS) | ❌ | | desligado |
| Captcha, SMS, celular | ❌ | | |
| Login: ordem dos pacotes | ✅ | 🇹🇷 | conta até o nível 16 conferida no inglês; nível alto (4631/4633/4555/4495) só no turco |
| Login em outro lugar (3842) | 🧪 | | a sessão antiga recebe o 3842 antes de ser derrubada (`BaseManager.__loginOtherHandler`); sem captura: texto inventado |
| Taxa de EXP periódica (4247) | ✅ | | sem evento: vazio no login e uma linha zerada (época no fuso do servidor) a cada 5 min, visto nas 7 capturas de 23-24/10; fase do tick (~114,2 s) na constante `RATE_PHASE` (0 aqui) |
| Login: 363/364 (troca da sorte) | 🟡 | | diferenças contra a inglesa ([tutorial.md](tutorial.md)) |
