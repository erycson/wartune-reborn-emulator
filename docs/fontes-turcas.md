# Fontes que ainda são só turcas

O padrão é o inglês: a captura `captures/tutorial_en.json` ([captura-oficial-en.md](captura-oficial-en.md)) vence a turca.
Esta tabela lista o que ainda depende de captura turca (`D:\wartune\server-relay\replay_packets.json`,
`extracted_pcaps\*.txt`) sem uma versão inglesa, e o que gravar no oficial inglês para trocar
([roteiro-captura.md](roteiro-captura.md)). Nos docs e testes essas citações aparecem como "(só turco: ...)".

| sistema | captura turca | o que dá | onde é citado | o que capturar no inglês |
|---|---|---|---|---|
| Ilha dos pets | peri_adasi_tp (apagada) | sequência de entrada (`content/petisland.json`) | mundo-compartilhado.md, test_space | entrar no Sylph Atoll |
| Mapa 2 e mudança de castelo | transfer_kampi_sistemi (apagada) | chefes do mapa 2 (migração 0027), energia 500→300, monstro 210127, relógio dos chefes | cidade-externa.md, test_outer_city | mudar o castelo para o mapa 2, abrir 9525 nele |
| Segunda conta das minas | cevre_altin_madeni_savasi (apagada), replay | outras instâncias, mina nível 8 (guarda 6504), createDate em UTC+3 | cidade-externa.md, multiplayer.md, test_outer_city | minas de uma segunda conta |
| Fazenda e árvore | ciftlik (apagada) | ops 0/1/6, rega, 8231, grau de amizade (34 → 4) | castelo.md, social.md, test_castelo | fazenda própria e de amigo |
| Guilda | birlik_katkisi (apagada), login | contribuição (5144), ranking, baú, mercado (goodId 19), cargos 4137/4138/4133 | guilda.md, test_guild | criar/entrar em guilda, contribuir, comprar |
| Amizade | login | 4156 em 2 páginas | social.md, chat.md | uma lista de amigos com mais de uma página |
| Coliseu | meydan_okuma (apagada) | 4169, 157 tipo 16, 4176; drop da vitória Lvl. 3 Luck Stone (`arena_challenge_items`, 0072; o inglês viu VIP Token) | pvp.md, handlers/arena.py `_prize` | mais vitórias no coliseu (o que mais sai, se derrota dá, limite por dia) |
| Torneio de fadas | peri_turnuvasi (apagada) | 4611, 157 tipo 35, 4361, "Puan +5" | pvp.md, test_missoes_fazenda_pets_simbolos | uma luta no torneio |
| Despertar de fada | peri_uyanis | 5038 2011: herói 3011 e dois soldados | test_salas_tipos | campanha 2011 |
| Astral (kader) | kader_sistemi (apagada) | leed 17, ordem do sorteio/recolher/compor/devorar, textos 111/83 de EXP e nível (o inglês é inventado), 4484 (o anúncio da Profile 5 já é inglês: oficial_encantar #2753) | eventos.md, heroi-exercito.md, test_heroi_exercito | sortear, compor e devorar uma estrela até subir de nível |
| Leeds 8/15/33 | birlik_katkisi (apagada), replay #1289, yeralti_labirenti, city_city_upgrade | onde sai o 4152 | eventos.md, test_castelo, test_devocao | gastar Balens, girar a roda da bênção |
| Academia e tecnologia | city_city_upgrade_academy_upgrade | tecnologia de atributo (110 tipo 3, 150, ×1,5); a de ouro e o nascimento da academia já têm fonte inglesa (oficial_20261023-231733-1 #3939-#3981) | castelo.md, pendencias.md | subir uma tecnologia de atributo (Hero/Troop) |
| Varredura (Blitz) | savasa_baskin_ve_elmas_ile_hizlandirma (apagada) | ordem do 8528 (início 109, 3, 140, 4425; rodadas 109, 3, 115, 4152, 112, 140, 109, 115, 4476/4426, 83, 4484, 111, 83, 4476/4426, 4425; pergunta depois do fim: status 5, sweepType 0); a rodada da 1007 no nível 56 deu gp 0, 6000 de ouro (-100) e 1 Skeleton Key, que o servidor não reproduz (as cartas da 1007 não têm fonte) | salas-campanha.md, test_varredura | varrer uma campanha e acelerar com Balens |
| Pergaminho de EXP | exp_kitabi_kullanim | 115, 110, 4188, 3 (2013002) | itens.md, test_pergaminhos | usar o Lvl. 2 Bonus EXP Scroll (a inglesa tem e não usou) |
| Loja do labirinto subterrâneo | yeralti_labirent_marketi_alisveris | 5154 goodId 105/110 | test_loja_labirinto | comprar na loja |
| Montaria, cartas, login com veículos | login.json | soulScore 400, cartas de poder (#76), 4512/4515/4516, 4696, eventos do login | heroi-exercito.md, diversos.md, eventos.md | login de conta antiga (nível alto) |
| Login 20001 | relay | chave e corpo cifrado do 20001 (`test_cipher_and_packet`, `pcap_samples` c2s 20001) | tests/protocol | capturar desde o login (a inglesa começa no meio) |
| Amostras do .proto | replay | c2s 5172, 8574, 10020; s2c 102, 4224, 4463, 4922 | test_messages_against_pcap | usar esses sistemas |
| Textos de pontos | meydan_okuma (apagada), av_askeri (apagada) | "Puan" do chat virou "Points" por dedução (`arena.py`, `gemmaze.py`) | pvp.md, eventos.md | uma luta no torneio e uma troca no labirinto |
| Cartas das masmorras | replay #1241/#1355/#1744 | sem filtro de classe, 3 atributos no 1080013, Lvl. 1 Luck Stone 0,5 no 102102 (migração 0034) | drops-masmorras.md | rodar a 1001 mais vezes |
| Forgotten Catacombs | login.json #55, yeralti_labirenti, labirent_sandik | 4205, campanha 8001 (`handlers/tower.py`; o maxIndex 60 é o recorde daquele personagem) | salas-campanha.md | abrir e entrar (8296 e a resposta: os andares não têm nós nos templates), resetar (8299) |
| Sala em grupo | exp_kitabi_…_ek_sahne_mob #17-#23 | 12/17/32/120, playerState 2 do dono (`handlers/room.py`; 0/1 dos outros vêm do cliente) | salas-campanha.md | criar sala de campanha em grupo, entrar com outra conta, pronto, convite (5028), aba Hall (5027 → 4161) |
| Login de conta avançada | login.json | 4224/4372 (alquimia e alma: a conta nova inglesa não recebe, #17-#18), 4912 (recuperar EXP), 4614/4198 (anel em andamento), 4540 e pet no 150, 4905, 4201, appraisalSkill, 4426/4555 (roda, alma do dragão), bit da repetível, +30 de ouro | diversos.md, eventos.md | logar com conta de nível alto, guilda, pet, montaria |
| Castelo | city_city_upgrade, login.json | cobrança 8327 (remainTime 3600, fórmula), bênção 8489 (4152 antes do 4391) | castelo.md | cobrar impostos e usar o seminário |

## Capturas turcas já apagadas

Apagadas do `D:\wartune\server-relay` (pcapng e txt) quando tudo nelas ficou implementado e com fonte inglesa.

| captura | coberta por |
|---|---|
| gökyüzü şehrine teleport ve yürüme sistemi | cidade do céu (`game/space.py`): 4606, 4597 + 4594 de quem está lá, 4607; o oficial agrupa o 4594 por região, o nosso manda um só (o cliente desenha igual) |
| büyük exp kitabı-orta ruh incisi-altın kutusu kullanımı | recurso 203 de EXP, Daru e ouro: 115, (109), 111 "Received:EXP x5000", 3, 83 "Received 5,000 EXP " (o turco escreve "Lord EXP"; o nome inglês é o do template -700) |
| eşşiz can ilacı kullanımı | uso de recurso 203 (115, 111, 3) no formato inglês "Received:Stamina x10" (231733 #4143-#4150) |
| büyük hp iksiri kullanım | poção de HP (115, 113, 150 sem o 4902, 3); o 83 canal 2 da bênção da guilda no formato inglês (oficial_encantar #1749); o 4542 é sobra de outra ação |
| büyük sefer kullanımı- grup sahne yararı +1 | The Empire Crusade: 115, 4240, 111, 3 (`items._use_copies`, test_copias_campanha; o texto do 111 é dedução); 4234 e 109 são os periódicos |
| teknoloji upgrade | tecnologia de atributo (110 tipo 3, 150, 109; a divergência ×1,5 fica anotada em pendencias.md com os valores 342/81), 4902 das cartas (`systems.fight_add_msg`, 608/768/1521), chefe externo no 83 canal 2 (`outer_city._boss_killed`), 151/4130 e o 83 canal 3 no formato inglês ("Gold Production has been upgraded to Lvl. 1", oficial_20261023-231733-1 #3981). As partes só turcas ficam citadas no código como "teknoloji_upgrade #N" |
| arkadaş isteği gönderme | pedido de amizade: oficial_encantar #1776-#1779 (`handlers/friends.py`, `test_social`) |
| atölye item basma ve mozaik | forja: reforço (109, 109, 115, 86), engaste (109, 115, 115, 111, 83), desengaste com o 4476/4484 do item ganho; a bancada no formato inglês do 5005 (tutorial_en #3202/#3217, 231733 #4804) |
| envanterden item kuşanma | equipar pela mochila: 3, 150, 115, 115 com o 83 do HP pack entre o 3 e o 150 como no inglês (153200 #2182-#2187) |
| av askeri ve ödül toplama | labirinto de gemas (`game/gemmaze.py`, test_labirinto_gemas): tabuleiro, cascata, pontos e prêmios (`CAPTURED_*`, só turco); o 4903 dos buffs das cartas por tipo de campanha (`systems.send_camp_buffs`) |
| değerli taş birleştirme | composição de pedras 5153 (`forge.compose`): 115, 109 ×2, 115, 4476, 4426, 4484, 111 "Received: ...", 89, 83, com a ordem inglesa (231733 #1493-#1511) |
| lvl1 değerli taş sandığı açımı ve içinden çıkanlar | caixa de pedras (`items._open_gem_box`): 115, 115, 4476, 4426, 4484, 111, 3, 83 |
| market alışveriş | compra na loja 5154 (`shop.buy`): 115, 4476, 4426, 4484, 111, 83, 90 na ordem inglesa (itens.md) |
| amfi marketi alışveriş | loja da arena (5154 com Honor, `shop.buy`): 115 da honra, 115 do item, 4476, 4426, 4484, 111, 83, 90 |
| değerli taş nitelik sistemi | transformação de pedra 8538 (`forge.py`): 115, 109, 115, 4476, 4426, 4484, 111, 83 |
| çiftlik | fazenda (`handlers/farm.py`): 8231/4190, 15044 (plantar, reviver), rega própria e do amigo (4158, 109, 147, 165, 146, 83), compras na loja |
| birlik katkısı ve birlik market alışverişi | contribuição (5144) na ordem inglesa (171155 #4964-#4974), listas 4134/4138/4466/4133, 4599 e a compra no mercado da guilda |
| çevre altın madeni savaşı | mina do mundo e as outras instâncias; a ordem do fim da luta e o 4382 no 5035 seguem o inglês (tutorial_en #748-#754, 153200 #1634-#1636) |
| transfer kampı sistemi | mudança de castelo 5176 (140, 152, 105), chefes do mapa 2 (9525/4938), a entrega da missão 390 com a EXP do mundo e a descansada (`rules.exp_bonus`) e o 4540, 4387 do guarda e 150 do mascote (`pets.send_gained`); o 83 da EXP fica depois do 52 como no inglês |
| peri turnuvası | torneio de fadas (`handlers/arena.py`): 4540 da formação no 8725, 4176 tipo 1 e 4611 no 8256, a atividade contada na entrada (140, 4476, 157), 4361, 4176, 4103, o 4540/4387/150 do time, 112, 4413, 140, "Points  +5" no 83 e no 111; a missão 504 com a EXP do mundo e a descansada |
| meydan okuma | coliseu: EXP 180 por nível na vitória e 120 na derrota (`data/colosseum_rewards.json`, como as inglesas), com a EXP do mundo e a descansada; 4540/4387/150 do mascote; prêmio com 115, 4476, 4426, 4484, 111, 83 (o inglês igual); o 4902/150/4434 do meio da luta é o periódico de 5 min (`player._army_refresh`) |
| peri adası tp | entrada no Sylph Atoll (`space.enter_pet_island`): 140, 125, 21; no 5035 o 21 de novo, o 127 e a patrulha dos pets selvagens (4122, pontos na `game_settings.npc_patrol`, migração 0082) |
| kader sistemi | estrelas (`stars.py`): 1º sorteio do dia 109, 3, 4152, 3, 4180, 83; recolher sem o 3; compor e devorar com 111 de nível e de EXP, 109 só com lixo, 4479/4178, 83 de nível e o 4484 quando a temporária enche ou deixa de estar cheia (dedução); devorar equipada com 4902/150 e dois 4178 |
| savaşa baskın ve elmas ile hızlandırma | varredura (`handlers/dungeon.py`): a ordem do início, das rodadas e do fim, a missão de campanha por rodada e a pergunta depois do fim (status 5, sweepType 0) |
| online ödül, sıcak etkinlik giriş ödülü toplama, takas ve binek upgrade | resgates de atividade sem o 3 quando o pacote só tem ouro e itens, a troca idem, o countDown só nos pacotes não resgatados do tipo 14, o finishValue dos contados, o treino de montaria (109, 115, 3, 4902, 150, 4902, 4476/4426, 4426) e a atividade 18 Mount Training contada por unidade; a saída da campanha segue o inglês (tutorial_en #517-#520) |
