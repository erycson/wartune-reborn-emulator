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
| Castelo | 12 | 2 | 6 | 0 | 3 |
| Herói e exército | 14 | 9 | 5 | 1 | 4 |
| Pets | 5 | 4 | 1 | 1 | 2 |
| Itens | 13 | 2 | 11 | 0 | 2 |
| Lojas e mercado | 8 | 3 | 1 | 0 | 1 |
| Chat e social | 6 | 1 | 5 | 0 | 1 |
| Clã / Guilda | 10 | 0 | 11 | 0 | 1 |
| Campanhas e masmorras | 7 | 7 | 9 | 1 | 3 |
| Labirinto (Forgotten Catacombs) | 4 | 1 | 5 | 0 | 3 |
| Batalha | 5 | 6 | 2 | 1 | 1 |
| Missões | 12 | 3 | 2 | 4 | 0 |
| Tutorial | 2 | 0 | 1 | 0 | 0 |
| Mapa do mundo (cidade externa) | 4 | 2 | 11 | 0 | 2 |
| Mundo compartilhado | 4 | 1 | 1 | 0 | 2 |
| PvP e chefes | 1 | 2 | 5 | 1 | 2 |
| Atividades e eventos | 5 | 10 | 12 | 1 | 5 |
| VIP | 1 | 0 | 6 | 0 | 0 |
| Veículos (Tank Trials) | 4 | 1 | 0 | 0 | 1 |
| Conta e segurança | 3 | 1 | 2 | 2 | 1 |
| **Total** | **121** | **58** | **96** | **12** | **34** |

## Validação e base

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Conta nova até o castelo no Flash Player projector | 🟡 | | pelo portal, acompanhando `logs/packets.log`; ainda não validado |
| Tutorial no cliente real | 🟡 | | o oráculo bate com a tutorial_en sem exclusões (só ritmo, [tutorial.md](tutorial.md)); falta jogar no cliente |
| Cobertura de opcodes (`scan_opcodes.py`, C>S, classes novas) | ✅ | | os 438 C→S do cliente têm handler (o 20001 é o login da sessão) |
| `shortcut:`/`ponytail:` do código | 🟡 | | classificados: taxas foram para `game_settings` (0124 montaria/destino/mascote/estrelas/painel, 0130 luta e veículo, 0134 runa 2x-20x e prazo da senha, 0135 compras do torneio de fadas, robô do coliseu, castTime padrão e defesa do veículo); comportamento feito (troca da sorte, pet livre, fundo vinculado, cartas na luta, velocidade do tanque e skill de caixa sem `Maximum` pelo cliente); atalho legítimo fica (memória/desempenho: guild 50 eventos, farm snapshots, mall lock, rules busca linear, rankings, login 1 exército, chat 1 s); `TODO(inventado)` sem fonte: mall arredondamento e taxa sem devolução (language auction.view.AuctionHelp não diz), timebox, gemmaze 5+ em linha, guild box isReceived |

## Castelo

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Prédios: upgrade (8203) | ✅ | 🇹🇷 | upgrade comum conferido em 42 pedidos ingleses; tecnologia de atributo só no turco |
| Tecnologia: nível e fila 2 (8202/8203) | 🟡 | 🇹🇷 | ordem dos efeitos (110/150) do turco; fila de tecnologia no login vista no 4155 inglês (orderId 3, orderType 2: 191924 #27, 152321 #39, 140316 #29) |
| Filas de construção (8279, 5175, 8281) | ✅ | | |
| Aceleração de filas (5172) | ✅ | | preço do cliente; resposta e texto vistos (191924 #1341-#1346) |
| Cobrança de ouro (8327) | ✅ | | |
| Produção de ouro e teto (5015) | ✅ |  | tecnologia de ouro conferida no inglês (231733 #3969-#3979, 60 no grau 1); bônus de guilda no total (`castle.py:105`, TODO(inventado) a base) |
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
| Recompensa offline (8287) | 🧪 | | ×1 grátis; ×1,5 e ×2 pagos em Balens por hora fora (`game_settings.offline_reward_cost`, 0115, TODO(inventado) o preço); EXP = nível × minutos × rate/10 |
| Trégua (8562) | ✅ | | City Protection Token grava o fim (buff 2001), 4452 em segundos no uso/login/8201, 8562 e atacar acabam; castelo em trégua não é atacável (`PlayerBufferManager`, `MapPhysicsCastle.attack`) |
| Reforço em batalha (8255) | 🧪 | | pelo cliente (`CampaignArmyViewHelper`, `ReinforceHandler`): `Battle.join` põe o herói (cópia) numa posição livre do lado 1, 72 para os de dentro, 157 com o estado atual para quem chega, luta o resto e leva o prêmio (`_battle_over` mate); também no 8745 do tesouro. Nenhuma captura de 8255: ordem dos pacotes e posições (`TEAM_POS`) inventadas |

## Herói e exército

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Tropas: recrutar (5155) | ✅ | | |
| Tropas: formação (8276) e posição (8328) | ✅ | | |
| Tropas: evoluir (5158) e trocar tipo (8580) | ✅ | | |
| Tropas: especialidades (8455/8456) | 🧪 | | a 1ª vem sozinha no nível 10 (visto: Lancer 100, Hunter 200); o sorteio comum pode dar o grau seguinte (helpContent), peso do TakeRandom TODO(inventado) |
| Tropas: formação de campanha (8277/8278) | 🧪 | | posição de cada membro gravada na sala (`Room.positions`), 4186 a todos, usada na luta em grupo; os lugares do lado 1 seguem `TEAM_POS` inventado |
| Herói: aprender skills e talento (5185/5187) | ✅ | | custo do talento por dedução |
| Herói: resetar skills e 2º conjunto | ✅ | | |
| Herói: redistribuir atributos (5170) | ✅ | | `*_point` voltam a `remain_point`; sem custo: no inglês nenhuma tela nem item chama o 5170 e a resposta 66 não tem handler |
| Subida de nível (139, 100, 150, 4640) | 🟡 | | vista na missão; por batalha, coliseu, fazenda e livro de EXP por dedução |
| Runas (8605) | 🟡 | 🇹🇷 | bônus 2x-20x com pesos em `taxas.rune_diamond_multiplier` (0134, `TODO(inventado)`); o 4495 do login do turco |
| Montaria: lista (8530) | ✅ |  | o 4426 junto do 4427 no inglês (231733 #11-#14), igual ao turco |
| Montaria: treinar, montar, ativar, voo | ✅ | | |
| Montaria: carta (5006, SonType 218) | ✅ | | |
| Montaria: refino de estrela | 🟡 | | lógica do cliente; bênção por refino e chance em `game_settings.taxas` (migração 0124, `TODO(inventado)`: procurado no decomp inglês, XMLs do mirror e templates) |
| Montaria: ops 7-12 e evento (8843) | ❌ | | sem tela no cliente inglês |
| Destino: abrir (8628) | 🧪 | 🇹🇷 | tipos 2000/3000 do turco; 2100/2200 abrem nos níveis de `game_settings.fate_unlock` (0116, TODO(inventado) 65/75) |
| Destino: treinar pedras (8626) | 🟡 | | lógica do cliente; EXP por pedra em `game_settings.taxas` (migração 0124, `TODO(inventado)`: procurado no decomp inglês, XMLs do mirror e templates) |
| Destino: roda (8627) | 🟡 | | lógica do cliente; pesos das fatias (graus do FateRotaryModel.rndDic, dedução) em `game_settings.taxas` (migração 0124, `TODO(inventado)`: procurado no decomp inglês, XMLs do mirror e templates) |
| Dragão: abrir e login (8642, 4555) | ✅ | 🇹🇷 | abre no 40 e vai no login (turco) |
| Dragão: alimentar (8641) | ✅ | | |
| Dragão: transferência (8643) | 🧪 | | vocação sobe pela comida na tabela 107 (dedução) e dá % de ataque por grau na luta (`game_settings.dragon_vocation_bonus`, 0116, TODO(inventado)) |
| Cartas de poder: subir e ativar (9505) | 🟡 | 🇹🇷 | usar a carta (5006, SonType 600) pela captura 20261029-121453-1 #4043-#4107: 115, 111, 4902, 150, 4903, 83 "Congrats! You just received the 1st card, [coleção]." (1ª da coleção), 83 "Card X has been successfully activated!", 4905 (`isActive` 1 só na carta nova: efeito do MagicCardSlotItem), 4902 sem userid e 3; op 2 (183522 #9217-#9234): uma cópia de cada carta nova da mochila abre com `isActive` 1, um 115 por item, 111 "N cards have been successfully activated.", 4902/150, 83 Congrats/activated (4903 depois do 1º), 4905, 4902; sem nenhuma, só o 111 (#4120); kits conferidos com 183522 #9184/#9203 (3 Expert -> 3 de Profile 2, 6 Novice -> 5 de 1 e 1 de 2); 4902 vazio do 32 e por caminho (#422, #536, #615, #653); kits 2131016-2131018 dão 1 carta por kit pela raridade (`Profile`) da descrição, peso 80/20 TODO(inventado) em `taxas.summoner_kits` (0138; 5 Expert -> 4+1, #4026); pelo cliente: só a carta nova abre (1 cópia por uso), a repetida fica na mochila; op 3 (card.cardHelper.content01, ajuda "burn the same kind") engole as repetidas da mochila em EXP até o `Data` do grau seguinte (`MagicCardInfo.currentGP`), `taxas.card_burn_gp` 1 por carta TODO(inventado) (0139); op 1 sobe com o `Data` (Types 29+Profile) e desconta o gp; op 3 (183522 #9236-#9250): um 115 por item, 111 "N cards have been successfully upgraded", 4902/150, 4903, 4905 (todas `isActive` 0), 4902 e 83 "{carta} gained N points of Card EXP." (1 por cópia, bate com o `card_burn_gp` 1); falta captura do op 1 |
| Cartas: bônus de coleção (4905) | 🟡 | | degraus em `powcard_suite_slots` (0037) por dedução; o bônus entra na luta (campaign.player_hero → camp_stats) |
| Cartas: ganho nas batalhas | 🧪 | | carta do saque da campanha fica na mochila como item (o inglês só muda a coleção no uso, d31 #4026-#4043); mochila cheia: correio (`shop.place`), também para material e caixa do caçador |
| Estrelas: sortear (8269) | 🟡 | | grátis do dia sem 109 como o inglês (#19350, #6727); chances por qualidade em `star_weights` (0035) e o ponto do grátis em `game_settings.taxas` (0124), `TODO(inventado)`; 4388 (SNS) na estrela de qualidade 4 com md5 inventado |
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
| Compor (op 13) | ✅ | | 24 de 28 receitas; as 4 restantes (19, 26, 29, 32) pedem pets PetType 117-119, que não existem no PetTempInfos inglês (só 101-106): nenhum pet de entrada pode existir, então não há o que compor |
| Avanço de qualidade (op 4) | 🟡 | | lógica do cliente; chance da bênção 5x em `game_settings.taxas` (migração 0124, `TODO(inventado)`: procurado no decomp inglês, XMLs do mirror e templates) |
| Encantar aptidão (op 7) | 🟡 | | lógica do cliente; quanto sobe (faixa) em `game_settings.taxas` (migração 0124, `TODO(inventado)`: procurado no decomp inglês, XMLs do mirror e templates) |
| Aprender skill (op 5) | 🟡 | | lógica do cliente; peso de cada skill no aleatório (padrão 1) em `game_settings.taxas` (migração 0124, `TODO(inventado)`: procurado no decomp inglês, XMLs do mirror e templates) |
| Crescimento e treino do mascote (fazenda 15044 ops 12-15) | 🧪 | | `handlers/farm_pets.py`: 2 terras, nível 50, 10 partes e 5 comidas do cliente (`FarmLandLayer`, `PetLandInfo.canFeed`); horas, EXP/h e % por comida TODO(inventado) `farm_pet_practice` (0118). Comida do amigo: `isFeed` no 4190 e aviso ao dono online (145 + 4387; texto inventado); o cliente não tem prêmio para quem alimenta. Resistência (8621 op 8, `trainResistance`) sem chamador no cliente inglês: bloqueio |
| Fusão de dois pets (op 15) | ❌ | | sem template |
| Mascote em batalha (EXP, despertar 4600) | 🟡 | 🇹🇷 | do turco; ganho, gasto, teto e o despertar lento abaixo do nível 55 (cliente PetFrame.help01) em `battle_formula` (0130); quanto mais lento é TODO(inventado) |
| Guarda da fazenda é o mascote | ✅ | 🇹🇷 | op 16 (`FarmPetSelectMeun`) escolhe o guarda; sem escolha, o de batalha (turco). Ops 10 (GIVE_POWER) e 11 (TREE_PICK, vai pelo 5178) sem `sendFarmOper` no cliente |

## Itens

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Mochila: mover, empilhar, organizar | ✅ | | |
| Mochila: vender | ✅ | | |
| Mochila: expandir e aluguel | ✅ | | |
| Mochila: travar e remover vencido | ✅ | | |
| Itens com validade (medalhas) | ✅ | | o cliente apaga o vencido com o 8346 sem aviso (BaseBagListView.as:192, EquipBagII.as:95); o idioma não tem texto de validade |
| randomSkill dos itens novos | 🧪 | | tipo 701 e peso dentro da faixa inventados |
| Teto diário de Beden e EXP vindos de itens | 🧪 | | Beden (stamina de poção) 300/dia do cliente (`wearyLimit`); EXP de itens 5.000.000/dia inventado (`game_settings.item_exp_daily`) e o texto do aviso inventado |
| Vínculo de itens | ✅ | | |
| Uso de recurso (203: ouro, Balens, EXP, Daru, Spirit Covenant) | ✅ | | texto e ordem do inglês (231733; EXP Book e Spirit Covenant em 191924) |
| Caixas de pedra (206) e outras caixas | 🧪 | | 284 de 553 abrem pela descrição ("Contains:" fixo, "one of the following" sorteio uniforme TODO(inventado)); com chance/random ou nome desconhecido é recusada |
| Poção de HP e reserva de vida (209) | 🧪 | | "HP Pack has been exhausted." e a cura ao evoluir tropa vistos (171155, 231733); contrato de cura (`rules.py:210`) |
| Pergaminhos de EXP, ouro e população | ✅ | | ordem vista em 191924 (#1737, #2241, #3379) |
| Pergaminhos de outros efeitos | 🧪 | | % de ataque/defesa/vida/crítico e tropa (46) na luta, honra (48) no campo; 2000 Camouflage é só aparência (4188) |
| Poções de atributo | 🟡 | | ordem do inglês: 115, 150, 4434, 110, 150, 4188, 150, 3 (191924 #1737, Crit Scroll) e sem o 1º 150 no EXP (#2241); o cliente não define ordem (PlayerEffectHelper ignora o 110). Sem captura: ouro/população e o 8283 |
| Cristal, guilda e Token de proteção (5006) | 🧪 | | 203 tipo 11 (Kyanite Pack -> cristais) e tipo 8 (Contribution Badge -> contribuição, 115/42/111/3 e "Received:Guild Contribution x1350" vistos na 183522 #15178), texto do Kyanite TODO(inventado); o City Protection Token já ia (`items.py` PROTECTION, Trégua); 203 tipo 9 (soldados do PawnTempInfos Property3 no castelo, sem conferir população TODO(inventado)), 14 (um contrato do rei por Property2 horas, `vip.use_covenant`) e 16 (Medallion: +500 de honra) |
| Títulos (4484/8597) | 🧪 | | contadores (vitórias no coliseu, abates no campo, guerra de guildas, astral 10, catacumbas, necrópole), rankings (poder geral e por classe, coliseu, cross, pesca, gemas), posse de item/montaria e recorde do labirinto (`titles.py`); rankings de honra, charme, força da montaria e Sylph (pontuação `rank:*` gravada no login/8597; Sylph pelo nível do pet, inventado), golpe final no chefe do mundo e líder da guilda vencedora da guerra; sem sistema: guerra de classes, arena de Sylph, Hero Returns, guerra entre servidores e monstros dos Wilds |
| Forja: reforço (5150) | ✅ |  | sucesso e falha no inglês (171155 #2323-#2384), igual ao turco |
| Forja: engaste e furos (5151/5152) | ✅ | 🇹🇷 | engaste no inglês (231733 #1392: sem 109 no furo vazio, "Successfully Socketed Gem!"); troca e furos do turco |
| Forja: composição de pedras (5153/8538) | ✅ | 🇹🇷 | 5153 e transformação 8538 no inglês (231733 #1492, 26/10 #10315, sem aviso); caixa de pedras do turco |
| Forja: refino de atributos (8336/8339) | 🧪 | | ordem e "Refinement Complete!" do inglês (24/10 #8019-#8027); o sorteio continua inventado (`bag.roll_random_skill`); o sorteio pendente fica no EventState `refine` até o 8339 |
| Forja: decomposição (8340) | ✅ | | ordem vista em 191924 #2259-#2278; recusa calada por dedução (o cliente limpa a bancada com qualquer 4260) |
| Equipamento do mascote: encantar (8644) | 🟡 | | lógica do cliente; zerar a bênção no sucesso em `game_settings.taxas` (migração 0124, `TODO(inventado)`: procurado no decomp inglês, XMLs do mirror e templates) |
| Equipamento do mascote na luta | 🧪 | | bagAttack + bagMagicattack somam no ataque do mascote (`campaign.fighting_pet`, dedução) |
| Moda: composição (8594) | 🧪 | | cliente dá custo (níveis x 10000 de ouro), charms e chance por diferença de nível (só o nome); inventado: % das chances, sorteio da moda, consumo na falha e dos 5 curingas (`game_settings["fashion"]`) |
| Moda: avaliação (8781) | 🧪 | | cliente dá custo (Property1 em ouro), chance (TransformId) e skills; visto #2524 (109, 111, 4542); inventado: pesos das estrelas 1-5 e a família sorteada; sem aviso no sucesso; o bônus soma nos atributos do líder (livro inteiro, como o cliente); refino com Property2 Fashion Cores sempre acerta (inventado) |
| Moda: livro, provador, esconder | ✅ | | |

## Lojas e mercado

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Loja comum (5154) | ✅ | | lojas 8/15 pela essência (NeedItem/Score), 11 pela Amethyst, 20 pelo Venus Crystal (4725 masterType 12; ganho local: missão do casal, `venus_crystal_sources` 0118 TODO(inventado)); a 13 não tem linha em nenhum template |
| Loja de moda (8592) e poção (5633) | ✅ | | |
| Loja misteriosa (8483/8482) | ✅ | | 4470 vazio depois de cada 4384 (232017 #3057); quem entra na lista de sortudos, sem captura |
| Ofertas por tempo (4238/8218/8632) | 🟡 | | só o tipo 1 tem dado; o 8632 manda só o `refreshDate`, como o oficial (#1633): rodízio sem lista no inglês |
| Compra coletiva (8645) | 🟡 | | ligada por padrão (migração 0104, `game_settings.group_buy` com `source`): oferta `type` 3 no 4238 em rodízio por edição, preço cai em 3 degraus pelos compradores do servidor, sinal + limite do dia, acerto cobra/devolve a diferença e entrega (4559/4560); sem acerto até `sendDate`, acerto automático pelo correio no login/8645 (8645/4559/4560 ausentes das capturas decodificadas), 1 sorteio de grupo por compra (`group_buy.py`, pelo cliente); catálogo/preços inventados |
| Presente a outro jogador e mochila cheia pelo correio | ✅ | | loja, ofertas e misteriosa: `receiveId` de outro (id pelo 8223/4148) cobra quem compra e manda pelo correio do sistema; mochila cheia paga e o que não cabe vai pelo correio (item com vínculo e validade). VIP e contrato a amigo seguem abaixo |
| Lojas de honra, glória, ametista | ✅ | | |
| Loja do labirinto (ShopType 4) | ✅ | 🇹🇷 | compra do turco; a Necropolis é outro sistema |
| Leilão: anunciar, lance, comprar, cancelar, buscar | 🟡 | | regras do cliente, sem captura; 8450 ordena; cancelar reempilha na pilha incompleta |
| Leilão: venda de pet | ✅ | | o pet nasce livre e se vincula pelo uso (language `PetAdvancedView.useBindPointTip`/`useBindGoodsTip`, `PetBagCellDropMediator.prompt02`) |
| Correio: envio, retirada, lista | ✅ | | carta não vence |
| Correio: verificação de e-mail (9591) | 🧪 | | estados 0-3 do `MailCheckFrame`; sem SMTP o PIN vai por correio do jogo e o prêmio `mail_rewards` (-500 x3000) também, uma vez (EventState `mail_check`, 337 estado 2 no login) TODO(inventado) |

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
| Altar: bênção | 🧪 | | casas, ordem do 4144 e entrega do 8216 (item, ouro, Daru, Bound Balens) conferidas em 17 bênçãos (121659, 191924); pesos, casa dos raros e sementes inventados; ×10 (VIP 6, `QUICK_BLESS_COUNT`) faz o que o dia e a contribuição deixam, entrega n-1 na hora e a última fica no altar TODO(inventado) |
| Altar do demônio (boss de guilda) | 🧪 | | handlers/altar.py: ondas sobre o Pool do world boss, vida do herói 1042 do template, reviver 8264 tipo 2 por contribuição, buff 8550, habilidades 8593; ondas/tempos/recompensas TODO(inventado) `altar_demon` (0110) |
| Terra secreta: entrada e saída | ✅ | | |
| Terra secreta: invasores | 🧪 | | onda a toda hora cheia, somem na meia hora (visto 183522); onda e vencidos em `server_states` (0109); contribuição 10 vista (0073) |
| Terra secreta: árvore sagrada | 🧪 | | tique 34×6×17 com 4382 e coletas 1/5/10, 10 de 21 por leva, chat da guilda (visto 183522, 0146); relógio do servidor (1 s): um 4382 por tique e levas no segundo certo; coleta pega some para a guilda toda na leva; bônus da energia inventado |
| Anúncio de recrutamento | 🧪 | | canal e remetente inventados |
| Correio de guilda | ✅ | | |
| Guerra de guildas | ✅ | | mapa 4501 (26/10 #2464-#6452): par das 8 maiores, torres, placar/10000, vantagem de 4000, feridas, buffs, prêmio; PvP 8548 com luta real (battleType 24 do cliente, cópia do inimigo, sem captura) e o perdedor no acampamento; TODO: janela diária e carro/invencível sem efeito |
| Guerra entre servidores | 🧪 | | fila local (`handlers/cruzado.py`): 8779 inscreve, dois jogadores daqui lutam (cópia do herói, battleType 10), o primeiro assiste; pontos no `crossScore`; torres/inspirar/grupos seguem como antes TODO(inventado) |
| Master Treasure Thief (8743) | 🧪 | | `isCanCall` pelo 1º do ranking local da arena, 1x/dia (TODO(inventado)); 3 levas de 20 dos 30 nós a 0/180/360 s, 4632 `currentTurns` 2-4, chat da chamada e da 3ª leva, luta 72004 (battleType 39) e baú 2030801 ×3 (visto 183522, 0146); a 3ª leva também dura 3 min (decisão do usuário); chamada e o aviso da 3ª leva em `server_states` (`lords`, não repete após reinício); levas pelo relógio do servidor |

## Campanhas e masmorras

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Entrada (5039) e estamina | ✅ | | sem estamina entra sem prêmio (EXP, drop, carta) e sem gastar, com "Insufficient Stamina" (cliente); sem captura |
| 1001 Worg Lair | 🟡 | 🇹🇷 | cartas 1080012 e 1080002 no inglês, 1080013 no turco; Pandora só dá o buff; sair no meio recomeça o mapa, como o cliente avisa (mainBar.MainToolBar.campaignMsg: sair sem completar não dá prêmio); a etapa vencida fica em `campaign_stage` |
| 1002 Baylon Plains | ✅ | | caixa do caçador com uma amostra |
| 1003 Temple of Ibalize (Outer) | 🧪 | | drops de 5 nós inventados (0062) |
| 1004 Temple of Ibalize (Inner) | ✅ | | |
| 1005 Orc Plains e 1006 Tribal Plateau | 🧪 | | escolta da Elise vista (231733); luta do elite 115116 inventada (0075) |
| 1007 Camp Calorn | 🟡 | | 1ª etapa (1171 → 1172) vista em 191924 #2345-#3706 (migração 0090), chefe Viscount Remus sem vitória: fim da etapa igual ao das outras masmorras; 2ª etapa (1181 → 1182) gerada por `tools/gera_masmorras.py 1007` (migração 0131, TODO(inventado)); Mystery Box por dedução (0062) |
| Masmorras solo capturadas (1101-1107, 1201) | 🟡 | | 1101, 1103, 1104, 1105, 1107 e a 1ª etapa de 1102, 1106, 1201 das capturas (migração 0098) |
| Masmorras solo geradas (1202-1602 e 2ª etapa de 1102, 1106, 1201) | 🧪 | | TODO(inventado) tools/gera_masmorras.py (migração 0099): planta das capturadas, mapas/casas/monstros do cliente; chave `inventado` marca o que trocar |
| Masmorras em grupo capturadas (9000, 9001, 9002) | 🟡 | | das capturas inglesas 191924, 232017, 152321 (migração 0100); entrada do dia (`paraBool1` = isNoGet) e o texto do 83 vistos; mapa dividido pela sala (21 com todos, 4185 do caminho, a luta de um leva os outros no lado 1 e todos ganham o 4103 e o nó); os outros lutam no automático (ordens só de quem atacou) e o lugar do 3º/4º é inventado; baús VIP 209109/203108 com a caixa da 201110 (prêmio TODO(inventado)) |
| Masmorras em grupo geradas (9003-9013, 9104-9112) | 🧪 | | TODO(inventado) `tools/gera_masmorras.py grupo` (migração 0101): planta da 9002 (2031 meio, 2033 fim), mapas/casas do cliente, monstros 4xxx/chefes 3xxx pelo nível; pesadelo com vida x `StandardDamage` e EXP x `BaseGp` do `Campaigns` (pesadelo/normal); chave `inventado` |
| Torres 8200-8204 (Tower of Kings, Spire) | 🧪 | | sala em grupo (game/torres, migração 0102). Cliente: uma entrada por dia em cada, dificuldade N com a N-1 vencida, 4900, andar da Spire (``currentWave``/``reinforceWave``), pulo de andar (TrailCountView: 3 turnos pula 4, além do 24 limpa), loja das Spire Runes (4468/8582/4467, ``TrialSkill``) e uso na luta (10507), battleType 290/25, leed 28 e Recuperar EXP. Internet (fontes-internet.md): baú e EXP por luta da King (100k/300k/900k/2,5M), 24 chefes da Spire com 300k e 7 baús cada, sem carta no fim. King com 5 lutas contra as sombras dos 16 mais fortes (cópia do coliseu); TODO(inventado): mapas e monstros da Spire (planta da 9002), crescimento das sombras por nível, sombras geradas sem jogadores, cota diária da loja; TODO(captura): texto de entrada |
| Pedreira 6001 | ✅ | | colheita espera a animação (4 s, `game_settings.quarry_collect_seconds`) |
| Exército do sistema (5038) | 🟡 | 🇹🇷 | bate com o inglês em todos os mapas pedidos (1011-1161, 7501); a 2011 do turco; mapas sem lista mandam vazio |
| Patrulha dos monstros (4122) | 🧪 | | pontos vistos (0079); agressivo sem captura anda 4 tiles em volta da origem (`npc_patrol.guess_step`, 0117, TODO(inventado)) |
| Varredura / Blitz (8528) | 🧪 | 🇹🇷 | baú de prata e caixa misteriosa inventados (`sweep.py:40`); ouro só da 1007 turca |
| Cartas do fim (5122/5180) | 🟡 | | chance real falta; carta paga não existe no cliente inglês (isPay só no autoChest; payCardCount sem leitor) |
| Relatório da etapa (137) | 🟡 | | degraus e curva por nível (`level_scale` sobre StandardDamage/StandardHurt acima do MinLevel) em `game_settings.stage_report` (0130, curva TODO(inventado); CampaignResultView só mostra) |
| Salas de campanha (criar, entrar, senha, convite...) | ✅ | | criar/editar/convidar vistos em 191924 (4 vagas, "Select a campaign.", 4186, 24, textos do 111); playerState do dono e Start da sala do turco; 5027 só registra (aba que o cliente não tem); 5024 recusado (senha, cheia) devolve o 4270 da sala (225632 #12656) |
| Times (convite, capitão, sair) | 🧪 | | membros, capitão, posições e ausência em `server_states` (0109); quem cai fica no time e o login manda o 4624 (dedução: sem captura de relogar em time) |
| Link de sala no chat (9504) | ✅ | | |
| Salas PvP (5023, 5039, 8344, 8465) | ✅ | | criar, senha, procurar e "Cannot find a room." vistos (24/10 #11533, 27/10 #19884-#21047); arena em grupo (handlers/arena_grupo.py): salas na fila emparelham, luta battleType 10 time contra time, 4103, missão 16, leed 13, contador `match`, Insignia x10 na derrota (27/10 #19912-#19995); prêmios em game_settings.arena_party (0107); pontos semanais (crossScore do 3) e ranking em cross/crossscore.xml do PvpHeroFrame (game/arena_grupo.py); dono que cai perde e as salas voltam a 1; vitória x20, pontos 10/5, texto "Points +N" e lugares do lado 2 inventados; só salas deste servidor |
| Falas e câmera no meio da luta (171/142) | ❌ | | |
| Pedágio = Gods Descent (8752-8755 type 1, 5021 type 2) | 🧪 | | 30 chefes `CampaignData` 40002, ScoreReward/LuckyReward, regras do `GodArriveFrame` e da ajuda; janela, contagem de 30 min, pontos e posições da sorte TODO(inventado) (0119) |

## Labirinto (Forgotten Catacombs)

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Info e reset (8297/8299) | 🟡 | 🇹🇷 | do turco; ranking (`order`) por andar e desempate pelo horário (jogador 28/10), calculado no 8297 e no 4373 do login; dificuldade em `game_settings.maze.hp_pct`; reset sem prêmio pelo cliente (maze.MazeFrame.content: "forfeit all progress") |
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
| Alvo aleatório | 🟡 | | alvo único sorteado entre os inimigos vivos com chance `game_settings.battle_formula.target_random` (0130, TODO(inventado)); o cliente só reproduz o 153 (DebugBattleCreater, BattleModel.attackOrders) |
| Reforços (ondas novas) | ✅ | | ordem das ondas sorteada e um 4149 por onda (171155, 231733) |
| Iniciativa (ordem das unidades) | 🟡 | | aliados, inimigos e herói; `battle_formula.hero_first` (0130) põe o herói no início; nenhuma regra no cliente nem no language.txt |
| Crítico e bloqueio | 🟡 | | ganhos por dedução; chances da internet |
| Skills, buffs e controle | 🟡 | | atordoado sem captura |
| Passivas, talento, runas e destino | 🟡 | | runas (RuneTempInfos.SkillTemplateId, uma vez por luta) e destino (SkillTempInfos do SonType no grau, com BufferIds) pelos templates; a entrada no 157 é dedução |
| Cartas de poder e dragão na luta | 🟡 | | alma do dragão pelo cliente (DragonSoulView: SkillPropertyTempInfos das skills SonType 32 até o grau e SonType 33 depois da transferência, migração 0133 tira o % inventado da 0116); cartas na luta sem captura |
| PvP manual | ✅ | | |
| EXP do mundo e EXP descansada | 🧪 | 🇹🇷 | 10× só turco; nível mínimo e acúmulo inventados (`rules.py:519,539`) |
| Selo sagrado, itens na luta, skill de casal | ❌ | | |
| QTE, assistir batalha, postura | 🧪 | | assistir (8985): espectadores na `Battle` recebem tudo, 157/156 ao entrar e 4803 no fim; o inglês não tem botão que chame (só `BattleCDViewFrame`); QTE e postura sem efeito |

## Missões

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Aceite, progresso, entrega e recompensas | ✅ | | |
| Principais: recrutar, nível, tropa, construção | ✅ | | |
| Segundo login, nível, eventos (39, 1, 40, 63, 66, 87) | ✅ | | |
| Entregas conferidas com as capturas (5014) | 🟡 | | até o nível 20: 27 de 44 iguais ao oficial; 21-31: 10 de 26 conferidas (prédios, 503, 623); faltam catacumbas (6), mina de Amethyst (86, ligada na coleta; entrega não conferida), 241/768 pelo handler e a ordem 52/83 em 5 subidas de nível |
| Castelo e ocupação (7, 8) | 🧪 | | castelo de jogador atacável (cópia do herói, battleType 4); saque e proteção inventados (`player_castle`, migração 0113) |
| Campanha (14, 25, 26, 31) | 🟡 | | 1001-1006 jogáveis; 1007 só a 1ª etapa; masmorras solo com captura na 0098 |
| Coleta de item (27, 28, 32, 49) | 🟡 | | itens sem fonte; coleta no espaço feita no lote 9 (nó 12 do anel, 143 COLLECTION e 8733, `handlers/space.py`) |
| Diárias e repetíveis | ✅ | | repetível concluída vai no 112 do login (QuestTemps IsRepeat) |
| Conversa com NPC (85) | ✅ | | patrulha (MasterType 1) conta sem conferir a posição (o NPC anda; o cliente abre a janela sozinho) |
| Guilda (22, 29, 30, 51) | ✅ | | 22/29/51 pelo estado (`social_state_quests`, 5014), 30 no altar (5145); test_missoes_social.py e test_missoes_tipos.py |
| Chefe do mundo (40, 41) | ✅ | | entrar e dano total contados |
| Campo de batalha: entrar (44) | ✅ | | contado na entrada 8332 |
| Arena e batalhas (45, 50) | 🧪 | | 45 por abate no PvP do campo (visto #11106); 50 para o lado vencedor no fim, 112 da 818 depois do 115 (visto 152321 #11697); lado de quem entra sorteado entre os com vaga (ajuda do cliente) e empate sem vencedor (inventado) |
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
| Mudar o castelo de lugar (5176) | 🟡 | | ordem 140/152/140/105 e energia no inglês (24/10 #15689, 27/10 #18049); ponto de chegada: o livre mais próximo do ponto visto no inglês (mapa 2 em 2084,1953, mapa 3 em 1229,1103; migração 0114), centro nos outros mapas; a busca do vizinho livre é inventada |
| Minas de ouro (missão 60) | ✅ | | perda de soldados na derrota (`outer_city._casualties`, lose_troops ganhando ou perdendo, visto #1620) e virada online no 20008 (`_mines_over` com push, visto 171155 #170-#175) |
| Minas do mundo (mapas 1-5) | 🧪 | | grades não vistas inventadas (`mines.py:22`) |
| Atacar mina de outro jogador | 🧪 | | cópia do herói inventada |
| Castelos NPC do mundo | 🧪 | | grades, saque e nomes inventados (`npc_castles.py`) |
| Castelos-robô (missões 100, 411, 765) | 🧪 | | saque acima do grau 30 inventado |
| Monstros dos Wilds e patrulha | 🧪 | | luta em grupo: quem é do time entra na luta em curso (`Battle.join`) e leva o abate e o baú; quem pode entrar é inventado |
| Chefes do mapa (9525, 4938) | 🟡 | 🇹🇷 | relógio e lista no inglês (153200 #191); luta: 4938 type 4 e herói do chefe da 157 do inglês (24/10 #16254-#16256); aviso de abate do inglês (26/10 #1106); luta em equipe (Battle.join do time, `outer_city.py`) e baú do abate feitos; falta o nome inglês ("Purgatory Lord", o catálogo turco dá "Balrog") |
| Baús dos Wilds (9526) | ✅ | | |
| Treasure Cache | 🧪 | | vagas por mapa inventadas (`caches.py:48`); prêmio deduzido das 4 amostras da 171155 |
| Mapa do tesouro (8744) | 🧪 | 🇹🇷 | ops 1-6 pelo cliente e idioma (`treasure.py`, `game_settings.treasure_map` da 0105): 4 qualidades, melhora (vinho + Balens, chances de Property1/2 por dedução), lugar no item, escavar no lugar ou já (pago), luta com o Master Treasure Thief e o grupo perto, 4634 e prêmio Property6 x Crystal Shard (+% na lendária, inventado), missão 89; 8745 reforço entra na luta em curso (`Battle.join`), na partilha e na missão 89; login: só turco, nenhuma captura inglesa acima do nível 31; lugar (NPC sorteado), ladrão como inimigo e battleType inventados. 8535 é o transporte do chefe (worldboss.py), não o tesouro |
| Rest House e Altar of Ennoblement | 🧪 | | teto diário inventado (`hangup.py:49`) |
| PK no campo de animais (8525) | 🧪 | | ilha dos pets/mina: luta direta (BattleType 19); convite do menu (op 1 → 4421, op 2 só com convite pendente); battleScene inventado |
| Passe = Sky Trails (8636-8640, 8753/8755 type 0) | 🧪 | | 100 fases `CampaignData` 40001, BossReward/AreaReward, 10 lutas/dia, Heaven Horn, atividade 113; Wishing Wall 8639/8640 (4553/4554, 8 cartas, 1 corneta + Balens crescentes); ranking `singlepass.xml` (fase máxima, soma das avaliações); avaliação, prêmios e custos da parede TODO(inventado) (0119, 0122) |
| Ataque extra (9506) | ✅ | | |
| Coleta de Amethyst e Copper | 🧪 | | Amethyst: carrinho despejado na mina 30000 dá 200 (`DUMP_AMETHYST`, TODO(inventado)) e paga a loja 11; Copper sem fonte |

## Mundo compartilhado

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Presença (11) e falas dos NPCs (4163) | 🟡 | | repertório, chance e ritmo em `game_settings.npc_chat` (0076); corte do 4595 em 30000 por dedução |
| Cidade do céu: presença e visual (4606/4607, 149) | ✅ | 🇹🇷 | 4606/4607 e o 149 de quem chega no inglês (215937 #826-#830) |
| Cidade do céu: nós e NPCs | ✅ | | |
| Ilha dos pets (127, patrulha) | ✅ | 🇹🇷 | sequência do turco |
| Coleta no espaço (8733) | 🧪 | | nó 18 (Rose Lilies) do 10000: 143 COLLECTION com o anel pedindo o item, 8733 depois de 1 s dá 1 Rose Lily (mochila/correio) |
| Times livres | ✅ | | |

## PvP e chefes

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Janela do PvP | ✅ | | |
| Coliseu | 🧪 | 🇹🇷 | EXP 180/120 por nível, 157, 4176 e o VIP Token no inglês; Luck Stone do turco; prêmios por posição inventados (`arena.py:347`) |
| Torneio de fadas | 🟡 | 🇹🇷 | do turco; vida, ataque e pontos do pet em `game_settings.fairy_battle` (0130, divisores TODO(inventado); o cliente só recebe o growthRate); compras por dia em `taxas.pet_max_buy` (0135, TODO(inventado)) |
| Arena entre servidores (8590) | 🧪 | | fila local; 4482 com pontos, Warrior's Mark com 1000 pontos e o título Road Warrior (AppellInfos 25) concedido ao top 20 com o 4484; a marca é a Insignia 208001 TODO(inventado) (0121); 1x/semana |
| Senhores, casal, mina de ametista | ❌ | | fechados |
| Campo de batalha (4001-4011, mina 30000) | 🟡 | | tudo pelas capturas 152321/121453 (docs/pvp.md): 100 pontos na entrada, pontos do lado só com ganhos, 4252 (one = time 1, geste do personagem) a todos, 28 nós e acampamentos por lado, entrega no oficial do lado com qualidade sorteada (`taxas.field_ore_weights`), PvP perde ceil 15% e ganha 20 + 1/20 com 10 de honra e +10 PvP entre servidores, morto 3 carregando e renascer, 4471 com a honra do dia, fim 80/90 e 30/30 com `oneTeamId` vencedor e a ordem oficial, guardiões do 4002 que perseguem (4105/128/157/4122); frases de sequência de abates e onda de renascer (taxas 0142), perseguição pela posição andada; lado sorteado se empatado, minério uniforme e alcance 26 do guardião pelas capturas (0144), morto preso na base até a onda, empate sem vencedor (busca na internet sem regra); captura de 01/11 (4003): os 11 campos do template, onda de 35 s (0147), Morkan Knight 21/22 vivos no 4003 e vencidos com nodeState 8, oficial inimigo luta (perde 150), entrada da base inimiga fechada ("Unable to enter the enemy faction's base.") e jogador na base não é atacado (inventado); ajuda do cliente ("More Info", 0149): partidas por faixa de 10 níveis, lado sorteado com 15 por lado, fim antecipado com 5000 de diferença, guardião vencido soma (valor inventado), prêmio em 2 campos por dia (`warFieldCount`, vira às 5h); a meia hora da ajuda não vale (template e captura: de hora em hora, 25 min); 4538 fim da Class Wars na virada do período da arena (inventado); captura de 01/11 (4004): entrada abre 5 min antes (4248 state 0 e o 83 "The entrance to the Battleground has opened!..."), 5125 antes do começo devolve "Battleground has not started yet, please wait!" e o 4126, 4456 (contagem de 10 s do `PvpMapTopCenterView`) a todos no mapa às :00; 8334 antes do começo sem regra (não recusa); inventados: fase da onda, passo do exército, perda do guardião (0141), vitória contra o oficial, 4549 no login ; mina 30000 (183522 #6031-#6046): entrada em 167,183 (21) e 4548 com `count` 2 e `activeTime` = segundos até as 20:00 (1735 às 19:31:05; fora da janela 0 é TODO(inventado)) |
| Ataque a castelo/exército de jogador | 🧪 | | castelo (5160) e exército (8488) contra a cópia do herói; recusa por trégua, guilda e nível pelo cliente; saque, relatório da defesa e PvP de exércitos sem captura |
| Boss mundial: agenda e luta | 🧪 | | luta inteira vista (27/10 e 26/10: avisos, barreira, moral, fim, correios, reviver pago); vida = Live × 1,5 por abate (exato nas capturas); último golpe direto; inventado: o correio do último golpe se quem matou saiu; cair sem abate e `kill_turn` da internet |
| Boss mundial: buff e dublê | 🧪 | | buff 8470 (Types 4, 401-420, 20 Balens/vinculados, +5% por grau no herói); dublê 8526/4424/4423 por 135 Balens, prêmio na janela fechada = ouro/Daru do teto TODO(inventado) |

## Atividades e eventos

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Login diário e presente online | ✅ | | dias 1 a 4 do login acumulado no inglês (153200, 191924) |
| Baú de atividade diária (8235) | ✅ | | ordem e texto do inglês (tutorial_en #1561); mochila cheia: "Insufficient Inventory space." (27/10 #6040) |
| Devoção (leeds) | 🟡 | 🇹🇷 | leed 8 no inglês (171155 #4955); 17 e 33 do turco; 13 (arena em grupo), 27 (entrar no campo, 8332) e 28 (Spire) ligadas |
| Guia de 7 dias (8749) | 🟡 | 🇹🇷 | tarefa 23 (entrar na Spire, `torres.SPIRE_TOTAL`) feita; login do turco |
| Atividades por contador (SumActive) | 🟡 | | troca (tipo 10) vista (191924); painel conta match, reward, vehicle e minefield |
| Contadores do painel (8518 → 4412/4413) | 🟡 | 🇹🇷 | torneio de fadas (turco); match (arena em grupo), reward (entrega do bounty), vehicle (fim do veículo) e minefield (entrada na mina) contam com 4413; 5001-5003 são os chefes do mundo, contados na entrada (visto #1407) |
| Fundo de novato e fundo normal | 🟡 | | compra e resgate pelo cliente (FundManager); itens do resgate vinculados (language `fund.FundFrame.helpFrame.helpContent`); janelas do banco por dedução |
| Árvore dourada (8604) | 🟡 | | pesos, início da edição e "uma vez por dia" por dedução |
| Labirinto de gemas (9508-9517) | 🧪 | 🇹🇷 | maxExp inventado (`gemmaze.py:29`); ajuda de amigo recusada |
| Roda do destino | 🧪 | | 2100/2200 abrem pelo nível (0116, TODO(inventado)) |
| Super assinatura | ✅ | | |
| Pacote de recarga e ofertas | ✅ | | |
| Painel de recompensas e anel de tarefa | 🟡 | | aceite, andamento e entrega no inglês (231733, 121659); condições contadas: recrutar e itens (estado), forja, gemas, síntese, astral, contribuição, compra, mina, sacrifício de pet, mensagem, abates e anel; o 8729 entrega quando cumpridas; 14 (Apprehend): o 8298 abre a luta das tropas e do herói contra o herói NPC do Para1 e conta na vitória (battleType 12, cena 9, visto 20261030-145704); entrega com 4413 do contador e 4196 com o TemplateId (visto 20261030); texto do Daru inventado; vagas extras (4360 `rewardCount`) ficam 0: o cliente não tem pacote de compra; anel pela captura 20261101-165308-1 (15 anéis): aceite só 4614 + 111 "Circuit Quest has been accepted!", sorteio pelo `Rands`, 4616 só no login e na entrega, 8731 marca conversa/QTE/mouse (recrutar não responde), entrega com 4614 entregue (`isAccept` e data), 111/83 "Complete Circuit Quests (N/200) ...", recrutar leva as tropas (100) e buscar o item; "Eliminate" sorteia masmorra e alvo (`condition_2/4`) e conta só nela (varredura 18 por rodada), "Fetch" lugar/item (`condition_2/3`): listas e soma fora da 1102 TODO(inventado) (0150) |
| Alquimia e alma (8321, 8467) | 🟡 | 🇹🇷 | troca no inglês (171155 #7827), 3 antes do 4372 nas 4 capturas novas; o oficial respondeu o 8320 no nível 10 e não no 11/12 (regra desconhecida); `point` do 4224 = 2 x (usos + 1) como no inglês (o cliente não lê) |
| Anúncios agendados | ✅ | | |
| Estrada dourada (9520) | 🧪 | | tabuleiro de 36 casas do inglês (24/10 #2454, 27/10 #1354); sempre o mesmo tabuleiro (inventado) |
| Pesca (9507) | 🧪 | | abrir, pescar, errar, cesto e cd do inglês (26/10, 27/10, 28/10); ranking semanal lista também quem tem 0 pontos (no fim); ⏩, ferramentas, fúria e ajuda sem captura (chance da fúria, nomes das ferramentas 2-4, alcance dos torpedos, prêmio sem ajuda inventados: `fishing.py`) |
| Caça ao tesouro (9502) | 🟡 | | pelas capturas 20261029-121453-1 #447-#575, #2801-#2860 e 20261031-183522-1 #8956-#9254 (migrações 0136/0137/0145): 36 nós, 3 explorações iniciais, 6 h, nó 7, ordem 4476 só da atividade 101/112/4914 no op 3 e 109/115/4476/4484/148/111/4915/4914/83/83 no op 4 (cheia: correio "Treasure Hunt Rewards", 3 dias), "Operation failed" no 2º clique; op 7 gasta 1 Exploration Artifact (115, 111, 4914 op 2; sem item só o 111); prêmio sorteado, não do nó (o mesmo nó deu Expert+3 e Novice+3): kit Novice/Expert x1 e 2/3/5 shards com o peso da contagem das 15 vistas (`prizeKits`/`prizeShards`); 9 textos `eventDesc` e a moeda sorteada à parte (a mesma caravana pediu Gold e Kyanite): 1000 Gold, 600 Daru ou 20 Kyanite por nível (32000/19200 no 32, 34000/20400/680 no 34; Kyanite sai no 109 `crystalsCount`); a atividade 101 conta por dia (5 no fim do 29/10, 0 no 30 e no 31); sem reset diário das explorações; inventados: texto de moeda insuficiente; "+" com 10 recusa com o huntcountFull do idioma (o cliente não confere); 4476 de contagem com activeCharge/getCount 0 (#450); ops 5/6 sem captura; shard x4 nunca visto |
| Quiz (9501) | 🧪 | | agenda, tempos, pontos e EXP do top 10 pelo idioma; estados, 4907-4910 e ajudas pelo cliente (`quiz.py`, `game_settings.quiz`); banca (Option1 certa), pontos e EXP inventados |
| Minério de Stokes (9645/35) | 🧪 | | 187-190 e ops pelo cliente, veio do servidor com andares especiais (`ore.py`, `game_settings.stokes_ore`); veio gravado no banco; preços, limites, achados e textos inventados (`game_settings`) |
| Caça-níquel (9500) | 🧪 | | regras da ajuda inglesa e do cliente (`slot.py`, `game_settings.slot_machine`); pesos dos dígitos e preço inventados (`game_settings`) |
| Loteria (8750/8748) | 🧪 | | tentativas pelo gasto de Balens no `cash_ledger` (idioma) e mensagens do cliente (`lottery.py`, `game_settings.lottery`); avisos do 4639 gravados no banco; sorteio e texto inventados |
| Cadeiras (9638) | 🧪 | | mensagens do cliente (`chairs.py`, `game_settings.chairs`); regra inteira inventada (cadeira por recarga, sortudos pelo total) |
| Sorteio de grupo (9523) | 🟡 | | ligados por padrão (migração 0103, toda regra em `game_settings` com `source`); roleta 338/4936 pelo cliente (`group_draw.py`); cada compra coletiva (8645, `group_buy.py`) dá 1 sorteio; sorteio inventado |
| Campo minado (atividade 111), caixa de ano novo (8994), história (8629/8630) | 🧪 | | 111 = participar da Amethyst Mine (cada 8633 conta no período); caixa (visto 20261101-165308-1): "Demon-Shattering Gold Seal" nos nós 30001-30020 do 10000, 20 caixas por leva de 30 min (4811 cheio sem pedido no 20008), 30 coletas/dia, "You have already collected here." / "Out of collecting attempts today.", prêmio sorteado com pesos da captura (0148), começo 12:30 e fim TODO(inventado); história: ovo 4546 no `TimeStoryFrame`, 8630 dá ouro; janela, prêmios e 5 ovos/dia TODO(inventado) (0123) |
| Recuperar EXP (9503) | 🧪 | | lista de ontem (game/recover) e resgate ouro/item/item+diamante no inglês (27/10 #63, #745-#760, #18450-#18479); os 10 sonTypes com contador (Necropolis pelas entradas do dia da torre, fechada sem o recorde 100; Spire pela entrada do dia de game/torres); altar 20 de estamina/unidade visto; curva de EXP/ouro do chefe por nível inventada (TODO) |
| Troca da sorte (9610) | 🟡 | | edições do 363 do tutorial_en #88 em `game_settings.lucky_exchange` (0132), 364 com a sorte, +1 por troca, raro com a sorte cheia (language `luckyexchange.*`); recusa e 4247 do inglês (27/10 #11765); `percentChance` e `weights` `TODO(inventado)` |
| Corneta (passe), 360 | ❌ | | |

## VIP

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Estado e nível (4410) | 🧪 | | vipGp: `Vip_DailyAddGp` por dia de VIP pago, somado no login, na compra e na virada do dia online (agendador); o dia da compra conta (dedução); VIP que vence online avisa a guilda (4455) |
| Compra (8513) | 🧪 | | presente a amigo (online pela sessão dele, offline pelo banco), pago por quem dá, com carta do sistema ao amigo (texto inventado); o inglês não manda o 8513 |
| Presente semanal, cartão de teste, roleta | ✅ | | |
| Contrato do rei: compra | 🧪 | | presente a amigo como o VIP: 4434 ao amigo online, banco se offline, carta do sistema (texto inventado) |
| Contrato do rei: efeitos | 🧪 | | cura e varredura (`rules.py:210`, `sweep.py:40`) |
| Privilégios (todos os tipos) | 🧪 | | cada `VipPrerogativeTempInfos.type` com onde vale em `vip.PRIVILEGES` (teste confere a tabela inteira); 1, 11 e 15 sem efeito no servidor (visual, cliente repete o 8269, nenhuma luta tira honra) |
| Loja do teste (8582) | 🧪 | | é a loja da Spire: ver Torres 8200-8204 |

## Veículos (Tank Trials)

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Fila, sala e entrada | ✅ | | |
| Garagem e ativação | ✅ | | tecnologia 218 do inglês (`game_settings.vehicle_tech`) |
| Partida (dano, pontos, chefe, prêmios) | 🟡 | | sem captura de partida; pontos, caixas, alvo do chefe, Tank EXP, runestones, mínimo da fila e divisor da defesa em `game_settings.vehicle_match` (0130/0135, TODO(inventado)); velocidade, chefe parado e caixa sem `Maximum` pelo cliente |
| Login (4512/4515/4516/4501) | ✅ | 🇹🇷 | a partir do nível 35 (`OpenGradesII.VEHICLE`): o turco de nível 56 manda, os ingleses de 1-16 não; janela 4512 no inglês |
| Veículos nos mapas de guerra | ✅ | | não existe no cliente inglês: a cena VEHICLE só abre no campaignId 3001 (único mapa 30xx no mirror) |

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
