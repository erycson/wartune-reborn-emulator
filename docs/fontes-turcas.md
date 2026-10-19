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
| Fuso dos testes | todas as turcas | `game_timezone="+03:00"` em tests/game/harness.py | conftest, harness, configuracao.md | (trocar só junto com os dados acima) |
| Textos do leilão e do help | language.txt turco | `Auction.*`, "Şanslı Ödülü", "Çanta dolu..." | mercado.md, boss-eventos.md | language.txt inglês do CDN res134 |
