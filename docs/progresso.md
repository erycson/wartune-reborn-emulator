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
| Castelo | 10 | 4 | 4 | 2 | 3 |
| Herói e exército | 13 | 14 | 0 | 2 | 4 |
| Pets | 3 | 6 | 0 | 2 | 2 |
| Itens | 12 | 6 | 4 | 4 | 2 |
| Lojas e mercado | 5 | 4 | 0 | 3 | 1 |
| Chat e social | 4 | 5 | 1 | 2 | 1 |
| Clã / Guilda | 9 | 4 | 6 | 2 | 1 |
| Campanhas e masmorras | 6 | 8 | 4 | 5 | 4 |
| Labirinto (Forgotten Catacombs) | 2 | 1 | 4 | 3 | 4 |
| Batalha | 5 | 6 | 1 | 2 | 1 |
| Missões | 4 | 6 | 0 | 6 | 0 |
| Tutorial | 2 | 0 | 1 | 0 | 0 |
| Mapa do mundo (cidade externa) | 2 | 5 | 7 | 3 | 2 |
| Mundo compartilhado | 4 | 1 | 0 | 1 | 2 |
| PvP e chefes | 1 | 1 | 2 | 5 | 2 |
| Atividades e eventos | 5 | 11 | 2 | 4 | 5 |
| VIP | 1 | 3 | 1 | 2 | 0 |
| Veículos (Tank Trials) | 3 | 1 | 0 | 1 | 1 |
| Conta e segurança | 3 | 1 | 1 | 2 | 1 |
| **Total** | **95** | **90** | **38** | **51** | **36** |

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
| Trégua (8562) | ❌ | | só zera e confirma |
| Reforço em batalha (8255) | ❌ | | depende de batalha em grupo |

## Herói e exército

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Tropas: recrutar (5155) | ✅ | | |
| Tropas: formação (8276) e posição (8328) | ✅ | | |
| Tropas: evoluir (5158) e trocar tipo (8580) | ✅ | | |
| Tropas: especialidades (8455/8456) | 🟡 | | a 1ª vem sozinha no nível 10 (visto: Lancer 100, Hunter 200); o sorteio do 8455 só até o grau atual (atalho, `handlers/army.py`) |
| Tropas: formação de campanha (8277/8278) | 🟡 | | só a posição do herói é gravada |
| Herói: aprender skills e talento (5185/5187) | ✅ | | custo do talento por dedução |
| Herói: resetar skills e 2º conjunto | ✅ | | |
| Herói: redistribuir atributos (5170) | ❌ | | sem efeito (pontos automáticos) |
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
| Cartas: ganho nas batalhas | 🟡 | | incompleto |
| Estrelas: sortear (8269) | 🟡 | | grátis do dia sem 109 como o inglês (#19350, #6727); chances por qualidade são atalho |
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
| Teto diário de Beden e EXP vindos de itens | ❌ | | sem teto |
| Vínculo de itens | ✅ | | |
| Uso de recurso (203: ouro, Balens, EXP, Daru, Spirit Covenant) | ✅ | | texto e ordem do inglês (231733; EXP Book e Spirit Covenant em 191924) |
| Caixas de pedra (206) e outras caixas | 🟡 | | caixa com conteúdo só na descrição é recusada |
| Poção de HP e reserva de vida (209) | 🧪 | | "HP Pack has been exhausted." e a cura ao evoluir tropa vistos (171155, 231733); contrato de cura (`rules.py:210`) |
| Pergaminhos de EXP, ouro e população | ✅ | | ordem vista em 191924 (#1737, #2241, #3379) |
| Pergaminhos de outros efeitos | 🟡 | | ícone e tempo ligam; o efeito não existe |
| Poções de atributo | 🟡 | | ordem dos pacotes por dedução |
| Cristal, guilda e Token de proteção (5006) | ❌ | | recusados |
| Títulos (4484/8597) | 🧪 | | condições de time, arena e labirinto zeradas (`titles.py:25,53`) |
| Forja: reforço (5150) | ✅ |  | sucesso e falha no inglês (171155 #2323-#2384), igual ao turco |
| Forja: engaste e furos (5151/5152) | ✅ | 🇹🇷 | engaste no inglês (231733 #1392: sem 109 no furo vazio, "Successfully Socketed Gem!"); troca e furos do turco |
| Forja: composição de pedras (5153/8538) | ✅ | 🇹🇷 | 5153 e transformação 8538 no inglês (231733 #1492, 26/10 #10315, sem aviso); caixa de pedras do turco |
| Forja: refino de atributos (8336/8339) | 🧪 | | ordem e "Refinement Complete!" do inglês (24/10 #8019-#8027); o sorteio continua inventado (`bag.roll_random_skill`) |
| Forja: decomposição (8340) | ✅ | | ordem vista em 191924 #2259-#2278; recusa calada por dedução (o cliente limpa a bancada com qualquer 4260) |
| Equipamento do mascote: encantar (8644) | 🟡 | | bênção zera por atalho |
| Equipamento do mascote na luta | 🟡 | | a luta não usa os atributos |
| Moda: composição (8594) | ❌ | | regra não está no cliente |
| Moda: avaliação (8781) | ❌ | | tabela desconhecida |
| Moda: livro, provador, esconder | ✅ | | |

## Lojas e mercado

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Loja comum (5154) | 🟡 | | lojas de pontuação (8, 13, 15, 20) sem suporte |
| Loja de moda (8592) e poção (5633) | ✅ | | |
| Loja misteriosa (8483/8482) | ✅ | | |
| Ofertas por tempo (4238/8218/8632) | 🟡 | | só o tipo 1 tem dado; rodízio sem captura |
| Compra coletiva (8645) | ❌ | | nenhuma oferta tipo 3 |
| Presente a outro jogador e mochila cheia pelo correio | ❌ | | `receiveId`, VIP 8513, contrato 8540: exige gravar outro personagem; mochila cheia recusa (oficial: correio, resultado 12) |
| Lojas de honra, glória, ametista | ✅ | | |
| Loja do labirinto (ShopType 4) | ✅ | 🇹🇷 | compra do turco; a Necropolis é outro sistema |
| Leilão: anunciar, lance, comprar, cancelar, buscar | 🟡 | | regras do cliente, sem captura; ordenação (8450/8457) ignorada, cancelar parte não reempilha |
| Leilão: venda de pet | 🟡 | | pet livre sem fonte |
| Correio: envio, retirada, lista | ✅ | | carta não vence |
| Correio: verificação de e-mail (9591) | ❌ | | sem SMTP |

## Chat e social

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Chat: mundo, cena, guilda, privado, corneta | ✅ | | cota VIP de cornetas sem fonte (padrão 0) |
| Chat: time e sala (canal 6) | ❌ | | recusado até existir time |
| Corneta entre servidores (8623) | 🟡 | | só eco local |
| Convite rápido de sala (8353) | 🟡 | | formato visto em 191924 (corneta sem 4500, uma tag `<a t="6">` por linha, leed 16 e 83); casamento recusado |
| Amigos: pedir, aceitar, grupos, busca, lista negra, recomendados | ✅ | | |
| Amizade: grau (friend_gp) | 🟡 | 🇹🇷 | grau 1 no inglês bate com 1 + gp/10; graus acima só no turco (dedução da tabela) |
| Nome, ficha e busca de jogador | ✅ | | |
| Casamento: pedido, noivado, divórcio | ✅ | | |
| Casamento: cerimônia | 🟡 | | cobra e casa direto, sem sala |
| Casamento: sala (8760) e jogo do coração (8802) | ❌ | | só log |
| Casamento: árvore e missões do casal | 🧪 | | árvore do casal (8773/4678 e `marriageTree` no 4386) pelo cliente (MarryTreeView/MarryTreeFosterFrame) e 191924 #1249; chance de mato/praga e quantidade de Rose Hazel inventadas; missões do casal (8774) ainda vazias |
| Casamento: loja do altar (9611) | 🟡 | | compra recusada sem pontos |

## Clã / Guilda

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Criar, candidatar-se, convidar | ✅ | | |
| Membros e informações | 🧪 | | matchWin/matchFailed 0 (`guild/info.py:202`) |
| Cargos e direitos | ✅ |  | direitos byte a byte no inglês (4137 de 171155, 215937, 231733), iguais ao turco |
| Expulsar, sair, passar chefia, mudar cargo | ✅ | | |
| Eleição do chefe | 🟡 | | só o voto; abrir/fechar pelo banco |
| Contribuição e ranking | ✅ | | |
| Melhoria de prédios (1-5) | ✅ | | |
| Habilidades (6-12) | 🧪 | | "Gold Production +N%" inventado (`castle.py:103`) |
| Mercado da guilda | ✅ | 🇹🇷 | ordem da compra do turco |
| Baú da guilda (distribuir) | ✅ | | correio de mochila cheia por dedução |
| Baú de prêmios | 🟡 | | nada enche o baú |
| Altar: bênção | 🧪 | | casas, ordem do 4144 e entrega do 8216 (item, ouro, Daru, Bound Balens) conferidas em 17 bênçãos (121659, 191924); pesos, casa dos raros e sementes inventados; ×10 recusada |
| Altar do demônio (boss de guilda) | 🟡 | | entrada 8542 recusada |
| Terra secreta: entrada e saída | ✅ | | |
| Terra secreta: invasores | 🧪 | | só em memória; contribuição inventada (0073) |
| Terra secreta: árvore sagrada | 🧪 | | EXP do tique e energia inventados (`fam.py:33`) |
| Anúncio de recrutamento | 🧪 | | canal e remetente inventados |
| Correio de guilda | ✅ | | |
| Guerra de guildas | 🟡 | | lista inventada; entrar e time recusados; a luta (4439-4462) está em 26/10 #2464-#5970 e falta o mapa de GvG |
| Guerra entre servidores | ❌ | | |
| Master Treasure Thief (8743) | ❌ | | |

## Campanhas e masmorras

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Entrada (5039) e estamina | ✅ | | |
| 1001 Worg Lair | 🟡 | 🇹🇷 | cartas 1080012 e 1080002 no inglês, 1080013 no turco; Pandora só dá o buff; 5180, cartas pagas e progresso salvo faltam |
| 1002 Baylon Plains | ✅ | | caixa do caçador com uma amostra |
| 1003 Temple of Ibalize (Outer) | 🧪 | | drops de 5 nós inventados (0062) |
| 1004 Temple of Ibalize (Inner) | ✅ | | |
| 1005 Orc Plains e 1006 Tribal Plateau | 🧪 | | escolta da Elise vista (231733); luta do elite 115116 inventada (0075) |
| 1007 Camp Calorn | 🟡 | | 1ª etapa (1171 → 1172) vista em 191924 #2345-#3706 (migração 0090), chefe Viscount Remus sem vitória: fim da etapa sem captura; 2ª etapa (1181/1182) não jogada; Mystery Box por dedução (0062) |
| 9001 Claristun (em grupo) | 🧪 | 🇹🇷 | só a etapa 2011; chefe 201106 inventado (0084) |
| Masmorras solo 1101-1602 | ❌ | | só drops |
| Masmorras em grupo 9000-9112 | ❌ | | só drops |
| Torres 8200-8204 (Tower of Kings, Spire) | ❌ | | só drops |
| Pedreira 6001 | ✅ | | |
| Exército do sistema (5038) | 🟡 | 🇹🇷 | bate com o inglês em todos os mapas pedidos (1011-1161, 7501); a 2011 do turco; mapas sem lista mandam vazio |
| Patrulha dos monstros (4122) | 🟡 | | nós sem captura ficam parados |
| Varredura / Blitz (8528) | 🧪 | 🇹🇷 | baú de prata e caixa misteriosa inventados (`sweep.py:40`); ouro só da 1007 turca |
| Cartas do fim (5122/5180) | 🟡 | | chance real falta; carta paga tratada como grátis |
| Relatório da etapa (137) | 🟡 | | curva por nível falta |
| Salas de campanha (criar, entrar, senha, convite...) | ✅ | | criar/editar/convidar vistos em 191924 (4 vagas, "Select a campaign.", 4186, 24, textos do 111); playerState do dono e Start da sala do turco; 5027 só registra (aba que o cliente não tem) |
| Times (convite, capitão, sair) | 🟡 | | não persistem |
| Link de sala no chat (9504) | ✅ | | |
| Salas PvP (5023, 5039, 8344, 8465) | 🟡 | | criar, senha, procurar e "Cannot find a room." vistos (24/10 #11533, 27/10 #19884-#21047); a partida em si não |
| Falas e câmera no meio da luta (171/142) | ❌ | | |
| Pedágio (8752-8755) | ❌ | | fechado |

## Labirinto (Forgotten Catacombs)

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Info e reset (8297/8299) | 🟡 | 🇹🇷 | do turco; ranking (`order`) 0 por atalho; prêmio do reset sem captura |
| Corrida: entrar, luta, portal (8296) | ✅ | 🇹🇷 | do turco |
| Andares 1 a 25: monstros, chefes, escoltas, baús | ✅ | | todos vistos (24/10 #12046-#13771, 25/10 #9658-#10909); vitórias só dão EXP |
| Andares 26 em diante | 🧪 | | sem captura: repetem o monstro e a força do 25 (`content/maze_floors.json`) |
| Aviso de respawn (4207) | ❌ | | visto ("25" #11400, "0" #13436), o servidor não manda |
| Corrida dobrada (Crypt Key) | 🧪 | | EXP em dobro inventada (`tower.py:170`) |
| Reviver (8300) | 🧪 | | resposta inventada (`tower.py:207`) |
| Varredura do labirinto (8528 tipo 2) | 🧪 | 🇹🇷 | o inglês (25/10 #9643-#9650) dá fichas e as gemas dos baús; o servidor só dá GP; dobrado inventado (`sweep.py:155`) |
| Necropolis (8101) | ❌ | | sem andares |
| Guarda de batalha e gemas (8742/4631) | ❌ | 🇹🇷 | gemas não modeladas; o 4631 vazio no login (turco) |

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
| Entregas conferidas com as capturas (5014) | 🟡 | | até o nível 20: 27 de 44 iguais ao oficial; 21-31: 26 entregas registradas, nenhuma conferida (dependem de prédio, guilda, campo de batalha, war camp, Catacumbas, minas); subida de nível manda o 104 da fila do castelo |
| Castelo e ocupação (7, 8) | 🟡 | | castelo de jogador sem alvo |
| Campanha (14, 25, 26, 31) | 🟡 | | 1001-1006 jogáveis; 1007 só a 1ª etapa; masmorras sem nós |
| Coleta de item (27, 28, 32, 49) | 🟡 | | itens sem fonte; coleta no espaço não feita |
| Diárias e repetíveis | 🟡 | | repetível concluída não aparece no login |
| Conversa com NPC (85) | 🟡 | | patrulhas travam |
| Guilda (22, 29, 30, 51) | ❌ | | tipos não contados |
| Chefe do mundo (40, 41) | ✅ | | entrar e dano total contados |
| Arena e batalhas (16, 35, 44, 45, 50, 79, 80, 93) | ❌ | | 16 sem luta em grupo na arena; 44/45/50 com o campo de batalha |
| Equipamento, forja e runa (17, 18, 19, 46, 47, 77) | ❌ | | tipos não contados |
| Demais tipos (12, 21, 56-59, 61, 64, 65, 71, 74, 86, 89-91) | ❌ | | tipos não contados |
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
| Grade, andar e exércitos | 🟡 | | exércitos alheios não aparecem |
| Mudar o castelo de lugar (5176) | 🟡 | | ordem 140/152/140/105 e energia no inglês (24/10 #15689, 27/10 #18049); ponto de chegada: o inglês cai num ponto fixo, aqui o centro |
| Minas de ouro (missão 60) | 🟡 | | perda de soldados na derrota e refresh com o jogador online sem captura |
| Minas do mundo (mapas 1-5) | 🧪 | | grades não vistas inventadas (`mines.py:22`) |
| Atacar mina de outro jogador | 🧪 | | cópia do herói inventada |
| Castelos NPC do mundo | 🧪 | | grades, saque e nomes inventados (`npc_castles.py`) |
| Castelos-robô (missões 100, 411, 765) | 🧪 | | saque acima do grau 30 inventado |
| Monstros dos Wilds e patrulha | 🟡 | | luta em grupo não existe |
| Chefes do mapa (9525, 4938) | 🧪 | 🇹🇷 | relógio e lista conferidos no inglês (153200 #191); mapa 2 do turco; texto inglês do aviso de abate inventado |
| Baús dos Wilds (9526) | ✅ | | |
| Treasure Cache | 🧪 | | vagas por mapa inventadas (`caches.py:48`); prêmio deduzido das 4 amostras da 171155 |
| Mapa do tesouro (8744) | 🟡 | 🇹🇷 | só o bronze; ops 2-5 recusadas; login só turco; 8745 e 8535 dependem dos mapas de guilda e do chefe |
| Rest House e Altar of Ennoblement | 🧪 | | teto diário inventado (`hangup.py:49`) |
| PK no campo de animais (8525) | ❌ | | |
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
| Campo de batalha (4005/4007, mina 30000) | ❌ | | fluxo inteiro visto em 25-27/10 (entrada 8332, coleta e entrega, 4255, fim e prêmio); falta implementar, com outros servidores (serverName) e o movimento dos outros (4185) |
| Ataque a castelo/exército de jogador | ❌ | | |
| Boss mundial: agenda e luta | 🧪 | | luta inteira vista (27/10 e 26/10: avisos, barreira, moral, fim, correios, reviver pago); vida = Live × 1,5 por abate (exato nas capturas); último golpe direto; inventado: o correio do último golpe se quem matou saiu; cair sem abate e `kill_turn` da internet |
| Boss mundial: buff e dublê | ❌ | | |

## Atividades e eventos

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Login diário e presente online | ✅ | | dias 1 a 4 do login acumulado no inglês (153200, 191924) |
| Baú de atividade diária (8235) | ✅ | | ordem e texto do inglês (tutorial_en #1561); mochila cheia: "Insufficient Inventory space." (27/10 #6040) |
| Devoção (leeds) | 🟡 | 🇹🇷 | leed 8 no inglês (171155 #4955); 17 e 33 do turco; 13, 27, 28 sem gancho |
| Guia de 7 dias (8749) | 🟡 | 🇹🇷 | tarefa 23 nunca; login do turco |
| Atividades por contador (SumActive) | 🟡 | | troca (tipo 10) vista (191924); vários tipos sem contador |
| Contadores do painel (8518 → 4412/4413) | 🟡 | 🇹🇷 | só o torneio de fadas conta (turco); 5001-5003, match, reward, vehicle e minefield sem captura |
| Fundo de novato e fundo normal | 🟡 | | janelas por dedução; compra e resgate do fundo normal sem captura |
| Árvore dourada (8604) | 🟡 | | pesos, início da edição e "uma vez por dia" por dedução |
| Labirinto de gemas (9508-9517) | 🧪 | 🇹🇷 | maxExp inventado (`gemmaze.py:29`); ajuda de amigo recusada |
| Roda do destino | 🟡 | | tipos 2100/2200 nunca abrem |
| Super assinatura | ✅ | | |
| Pacote de recarga e ofertas | ✅ | | |
| Painel de recompensas e anel de tarefa | 🟡 | | aceite, andamento e entrega no inglês (231733, 121659); só a condição 5 (árvore de amigo) é contada, as outras e o 8729 dependem dos seus sistemas; texto do Daru inventado |
| Alquimia e alma (8321, 8467) | 🟡 | 🇹🇷 | troca no inglês (171155 #7827), 3 antes do 4372 nas 4 capturas novas; o oficial respondeu o 8320 no nível 10 e não no 11/12 (regra desconhecida); `point` diferente (o cliente não lê) |
| Anúncios agendados | ✅ | | |
| Estrada dourada (9520) | 🧪 | | tabuleiro de 36 casas do inglês (24/10 #2454, 27/10 #1354); sempre o mesmo tabuleiro (inventado) |
| Pesca, caça ao tesouro, quiz, minério | ❌ | | fechados; pesca (9507) só manda 4916/4918, as capturas não mostram resposta ao pedido |
| Caça-níquel, loteria, cadeiras, sorteio de grupo | ❌ | | fechados |
| Campo minado, caixa de ano novo, história | ❌ | | |
| Recuperar EXP (9503) | 🟡 | | 4912 e 109 no inglês (24/10 #9044, 26/10 #2207, 27/10 #745); resgate (tipo 1) sem captura |
| Troca da sorte (9610) | 🟡 | | recusa "Insufficient exchange items." e 4247 do inglês (27/10 #11765); sem tabela das edições |
| Corneta (passe), 360 | ❌ | | |

## VIP

| Sistema | Inglês | Turco | O que falta / inventado |
|---|---|---|---|
| Estado e nível (4410) | 🟡 | | vipGp diário simplificado |
| Compra (8513) | 🟡 | | presente a amigo recusado |
| Presente semanal, cartão de teste, roleta | ✅ | | |
| Contrato do rei: compra | 🟡 | | presente a amigo recusado |
| Contrato do rei: efeitos | 🧪 | | cura e varredura (`rules.py:210`, `sweep.py:40`) |
| Privilégios extras (montaria, missões, cornetas) | ❌ | | lista em [eventos.md](eventos.md) |
| Loja do teste (8582) | ❌ | | |

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
| Taxa de EXP periódica (4247) | ✅ | | sem evento: vazio no login e uma linha zerada (época no fuso do servidor) a cada 5 min, visto nas 7 capturas de 23-24/10; fase do tick (~114,2 s) na constante `RATE_PHASE` (0 aqui) |
| Login: 363/364 (troca da sorte) | 🟡 | | diferenças contra a inglesa ([tutorial.md](tutorial.md)) |
