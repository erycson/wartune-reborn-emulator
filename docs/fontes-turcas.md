# Fontes que ainda são só turcas

O padrão é o inglês: a captura `captures/tutorial_en.json` ([captura-oficial-en.md](captura-oficial-en.md)) vence a turca.
Esta tabela lista o que ainda depende de captura turca (`D:\wartune\server-relay\replay_packets.json`,
`extracted_pcaps\*.txt`) sem uma versão inglesa, e o que gravar no oficial inglês para trocar
([roteiro-captura.md](roteiro-captura.md)). Nos docs e testes essas citações aparecem como "(só turco: ...)".

| sistema | captura turca | o que dá | onde é citado | o que capturar no inglês |
|---|---|---|---|---|
| Ilha dos pets | peri_adasi_tp | sequência de entrada (`content/petisland.json`) | mundo-compartilhado.md, test_space | entrar no Sylph Atoll |
| Mapa 2 e mudança de castelo | transfer_kampi_sistemi | chefes do mapa 2 (migração 0027), energia 500→300, monstro 210127, relógio dos chefes | cidade-externa.md, test_outer_city | mudar o castelo para o mapa 2, abrir 9525 nele |
| Segunda conta das minas | cevre_altin_madeni_savasi, replay | outras instâncias, mina nível 8 (guarda 6504), createDate em UTC+3 | cidade-externa.md, multiplayer.md, test_outer_city | minas de uma segunda conta |
| Fazenda e árvore | ciftlik | ops 0/1/6, rega, 8231, grau de amizade (34 → 4) | castelo.md, social.md, test_castelo | fazenda própria e de amigo |
| Guilda | birlik_katkisi, login | contribuição (5144), ranking, baú, mercado (goodId 19), cargos 4137/4138/4133 | guilda.md, test_guild | criar/entrar em guilda, contribuir, comprar |
| Amizade | arkadas_istegi_gonderme, login | 78 relation 3, textos do pedido, 4156 em 2 páginas | social.md, chat.md | mandar pedido de amizade |
| Labirinto de gemas | av_askeri_ve_odul_toplama | tabuleiro, cascata, pontos, prêmios (`CAPTURED_*`) | eventos.md, test_labirinto_gemas | jogar o labirinto (4922-4924) |
| Coliseu | meydan_okuma | 4169, 157 tipo 16, 4176, drop | pvp.md | uma luta no coliseu |
| Torneio de fadas | peri_turnuvasi | 4611, 157 tipo 35, 4361, "Puan +5" | pvp.md, test_missoes_fazenda_pets_simbolos | uma luta no torneio |
| Despertar de fada | peri_uyanis | 5038 2011: herói 3011 e dois soldados | test_salas_tipos | campanha 2011 |
| Astral (kader) | kader_sistemi | leed 17, 8269/4180 | eventos.md, test_heroi_exercito | um sorteio de estrela |
| Leeds 8/15/33 | birlik_katkisi, replay #1289, yeralti_labirenti, city_city_upgrade | onde sai o 4152 | eventos.md, test_castelo, test_devocao | gastar Balens, girar a roda da bênção |
| Academia e tecnologia | city_city_upgrade_academy_upgrade, teknoloji_upgrade | 8203 de tecnologia, produção +30/h | castelo.md | subir academia e uma tecnologia |
| Aceleração paga | savasa_baskin_ve_elmas_ile_hizlandirma | texto 111 do cooldown | castelo.md | acelerar com Balens |
| Pergaminho de EXP | exp_kitabi_kullanim | 115, 110, 4188, 3 (2013002) | itens.md, test_pergaminhos | usar o Lvl. 2 Bonus EXP Scroll (a inglesa tem e não usou) |
| Campanha em grupo | buyuk_sefer_kullanimi | The Empire Crusade +1 entrada | test_copias_campanha | usar o item |
| Loja do labirinto subterrâneo | yeralti_labirent_marketi_alisveris | 5154 goodId 105/110 | test_loja_labirinto | comprar na loja |
| Montaria, cartas, login com veículos | login.json | soulScore 400, cartas de poder (#76), 4512/4515/4516, 4696, eventos do login | heroi-exercito.md, diversos.md, eventos.md | login de conta antiga (nível alto) |
| Cidade do céu | gokyuzu_sehrine_teleport | teleporte e andar | mundo-compartilhado.md | teleportar e andar |
| Login 20001 | relay | chave e corpo cifrado do 20001 (`test_cipher_and_packet`, `pcap_samples` c2s 20001) | tests/protocol | capturar desde o login (a inglesa começa no meio) |
| Amostras do .proto | replay | c2s 5172, 8574, 10020; s2c 102, 4224, 4463, 4922 | test_messages_against_pcap | usar esses sistemas |
| Textos de pontos | meydan_okuma, av_askeri | "Puan" do chat virou "Points" por dedução (`arena.py`, `gemmaze.py`) | pvp.md, eventos.md | uma luta no torneio e uma troca no labirinto |
| Cartas das masmorras | replay #1241/#1355/#1744 | sem filtro de classe, 3 atributos no 1080013, Lvl. 1 Luck Stone 0,5 no 102102 (migração 0034) | drops-masmorras.md | rodar a 1001 mais vezes |
| Forgotten Catacombs | login.json #55, yeralti_labirenti, labirent_sandik | 4205, campanha 8001 (`handlers/tower.py`; o maxIndex 60 é o recorde daquele personagem) | salas-campanha.md | abrir e entrar (8296 e a resposta: os andares não têm nós nos templates), resetar (8299) |
| Sala em grupo | exp_kitabi_…_ek_sahne_mob #17-#23 | 12/17/32/120, playerState 2 do dono (`handlers/room.py`; 0/1 dos outros vêm do cliente) | salas-campanha.md | criar sala de campanha em grupo, entrar com outra conta, pronto, convite (5028), aba Hall (5027 → 4161) |
| Forja | atolye_item_basma_ve_mozaik, degerli_tas_birlestirme | aviso do engaste, 5153 de síntese | itens.md | engastar e sintetizar pedras |
| Login de conta avançada | login.json | 4224/4372 (alquimia e alma: a conta nova inglesa não recebe, #17-#18), 4912 (recuperar EXP), 4614/4198 (anel em andamento), 4540 e pet no 150, 4905, 4201, appraisalSkill, 4426/4555 (roda, alma do dragão), bit da repetível, +30 de ouro | diversos.md, eventos.md | logar com conta de nível alto, guilda, pet, montaria |
| Castelo | city_city_upgrade, login.json | cobrança 8327 (remainTime 3600, fórmula), bênção 8489 (4152 antes do 4391) | castelo.md | cobrar impostos e usar o seminário |
