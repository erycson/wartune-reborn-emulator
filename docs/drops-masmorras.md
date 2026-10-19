# Drops das masmorras

A carta do fim da etapa é sorteada pela tabela `campaign_cards` (migração 0034), no formato (campanha, item,
peso, fonte). O peso é quantas vezes o item saiu nas capturas, inglesa e turca. Os itens da coluna `Item` de
`Campaigns` que nunca foram vistos pesam 1. Uma campanha sem linhas na tabela usa a coluna `Item` com pesos iguais
(`game/drops.py`). As tabelas por campanha abaixo são um retrato do template, para conferir com vídeos e capturas.

## O que é visto, deduzido e o que falta

- *(visto)* Inglesa #1102-#1123 (1001): 135 (5 cartas, `payCardCount` 5, `price` 0), depois 5122 → 115, 26 e 83
  "Received: Banshee Plume x1". O 134 só vem como resposta do 5180.
- *(visto)* Cartas da 1001: 1080012 Banshee Plume duas vezes (inglesa #1122 e #1544, mago); 1080013 e 1080002 uma
  vez cada (turca #1241 e #1744).
- *(visto)* Cartas da 1002: 2040102 Lvl. 2 Luck Stone nas duas (#2727, #3181). Esse item **não está** no
  `CampaignInfo.Item` da 1002, então o sorteio do oficial não é a lista do template.
- *(dedução)* O peso vem da contagem dessa amostra pequena. Não há filtro de classe: o mesmo personagem tirou
  item de mago (Job 3) e de guerreiro/arqueiro (Job 1,2). Os atributos saem do mesmo sorteio do refino (8336).
- *(dedução)* O -700 (EXP) das torres não é carta: a EXP vem do `BaseGp`.
- **Carta paga**: nenhuma captura paga (`isPay`, `payCardCount`). A carta paga é tratada como a grátis, uma por
  etapa.
- **Falta**: a chance real de cada item; a carta em grupo (9000+, um por jogador?); o prêmio das listas vazias
  (chefe do mundo 4001+, 5001/5003, 3001, 7501, 7601, labirintos 8001/8101). Anote na coluna *Visto em* o vídeo
  ou a captura (ex.: `vídeo X 03:12, caiu 1011104`).
- **Loot das lutas**: o campo `drops[nó]` do conteúdo da campanha (`campaign_contents`) guarda [item, quantidade,
  chance]. Nenhuma tabela do tempinfos liga nó a item, então a lista vem só das capturas. Os itens empilham
  (`bag.add`): o Worg Tooth cai numa pilha só.

## 1001 Worg Lair (Lv 5, solo)

Ligada no servidor: mapas 1011 e 1021 (`campaign_contents` 1001).

Drops das lutas, por nó:

| Nó | Item | Quantidade | Chance | Visto em |
|---|---|---|---|---|
| 102102 | Worg Tooth (2100001) | 2 | 1 | inglesa e turca (#1360) |
| 102102 | Lvl. 1 Luck Stone (2040101) | 1 | 0,5 *(dedução)* | só na turca (#1355, #1386); a inglesa não deu |
| 102103 | Worg Tooth (2100001) | 2 | 1 | inglesa #1275-#1280 |
| 102105 | Worg Tooth (2100001) | 3 | 1 | inglesa e turca |
| 102106 | Worg Tooth (2100001) | 3 | 1 | inglesa #1397-#1418 |
| 1011 (101102 a 101109) e 102109 | nenhum | — | — | sem item nas duas capturas |

Cartas:

| Item | Nome | Classe | Atributos | Peso | Visto em |
|---|---|---|---|---|---|
| 1080003 | Kazılmış Damga | guerreiro/arqueiro | 3 | 1 |  |
| 1080013 | Karanlık İzler | mago | 3 | 1 | turca #1241 |
| 1080002 | Parlak İşaret | guerreiro/arqueiro | 1 | 1 | turca #1744 |
| 1080012 | Banshee Plume | mago | 1 | 2 | inglesa #1122, #1544 |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 | 1 |  |

## 1002 Baylon Plains (Lv 9, solo)

Ligada no servidor: etapas 1131 → 1132 e 1141 → 1142.

Drops: o 114104 deu 1080011 x1 *(dedução: chance 0,5)*. As caixas do caçador (113203, 114203) dão 10.000 Daru, e
a tumba 114105 dá 5.000 Daru.

| Item | Nome | Classe | Atributos | Peso | Visto em |
|---|---|---|---|---|---|
| 2040102 | Lvl. 2 Luck Stone | todas | 0 | 2 | inglesa #2727, #3181 (fora do `CampaignInfo.Item`) |
| 1011104 | Dev Kılıç | guerreiro | 3 | 1 |  |
| 1012104 | Bıçak Kemik Rüzgar Yaran | arqueiro | 5 | 1 |  |
| 1013104 | Kan Ruhu Asa | mago | 5 | 1 |  |
| 1011102 | Adalet Kılıcı | guerreiro | 1 | 1 |  |
| 1012102 | Karanlık Kemik Yayı | arqueiro | 1 | 1 |  |
| 1013102 | Ay Taşı Değneği | mago | 1 | 1 |  |
| 2040101 | Şans Taşı Lv.1 | todas | 0 | 1 |  |

## 6001 Resource Quarry (pedreira)

Não tem carta. Cada colheita (5032 numa pilha, sonType 2352) dá Wood (2100022) x2 ou x3, e a luta do 8699 dá
Wood x18 (inglesa #2050-#2066), ganhando ou perdendo.

## 1003 Juits Dış Saray (Lv 11, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030103 | Dövüşçü Kaskı | todas | 3 |  |
| 1030102 | Sadık Şapkası | todas | 1 |  |
| 2040101 | Şans Taşı Lv.1 | todas | 0 |  |

## 1004 Juits Sarayı (Lv 13, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070103 | Üzücü Yüzük | todas | 3 |  |
| 1070102 | Şifalı Yüzük | todas | 1 |  |
| 2040101 | Şans Taşı Lv.1 | todas | 0 |  |

## 1005 Vahşiler Düzlüğü (Lv 15, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041103 | Muhafızın Zırhı | guerreiro | 3 |  |
| 1042103 | Savunmacı Zırhı | arqueiro | 3 |  |
| 1043103 | Gizemli Rozet Pelerini | mago | 3 |  |
| 1043102 | Eski Pelerin | mago | 1 |  |
| 1042102 | Canavar Savaş Zırhı | arqueiro | 1 |  |
| 1041102 | Boğa Başlılar Zırhı | guerreiro | 1 |  |
| 2040101 | Şans Taşı Lv.1 | todas | 0 |  |

## 1006 Kabile Dağlığı (Lv 17, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060103 | Kanlı Lanet Kolyesi | todas | 3 |  |
| 1060102 | Cin Kolyesi | todas | 1 |  |
| 2040101 | Şans Taşı Lv.1 | todas | 0 |  |

## 1007 Carlo Kampı (Lv 19, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080103 | Süvari Simgesi | guerreiro/arqueiro | 3 |  |
| 1080113 | Kanlı Canavar Simgesi | mago | 3 |  |
| 1080102 | Öncü Madalyası | guerreiro/arqueiro | 1 |  |
| 1080112 | Uçurum Kolyesi | mago | 1 |  |
| 2040101 | Şans Taşı Lv.1 | todas | 0 |  |

## 1101 Derin Uçurum (Lv 20, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011203 | Çılgın Kılıç | guerreiro | 3 |  |
| 1012203 | Uzun Savaş Oku | arqueiro | 3 |  |
| 1013203 | Sihirli Kan Asa | mago | 3 |  |
| 1011202 | Mezarlık Kılıcı | guerreiro | 1 |  |
| 1012202 | Uzun Kertenkele Oku | arqueiro | 1 |  |
| 1013202 | Büyük Savaş Asası | mago | 1 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040102 | Şans Taşı Lv.2 | todas | 0 |  |

## 1102 Bağırma Bataklığı (Lv 21, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030203 | Uçurum Gözü Şapkası | todas | 3 |  |
| 1030202 | Süvari Kaskı | todas | 1 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040102 | Şans Taşı Lv.2 | todas | 0 |  |

## 1103 Seher Savaş Alanı (Lv 23, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070203 | Gölge Yüzüğü | todas | 3 |  |
| 1070202 | Dev Taş Yüzüğü | todas | 1 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040102 | Şans Taşı Lv.2 | todas | 0 |  |

## 1104 Yılan Kartal Yuvası (Lv 23, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070203 | Gölge Yüzüğü | todas | 3 |  |
| 1070202 | Dev Taş Yüzüğü | todas | 1 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040102 | Şans Taşı Lv.2 | todas | 0 |  |

## 1105 Karanlık Orman (Lv 24, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041203 | Saldırı Zırhı | guerreiro | 3 |  |
| 1042203 | Canavar Avcısı Zırhı | arqueiro | 3 |  |
| 1043203 | Kara Yolculuk Pelerin | mago | 3 |  |
| 1041202 | Şanslı Zırh | guerreiro | 1 |  |
| 1042202 | Öncü Koruma Zırhı | arqueiro | 1 |  |
| 1043202 | Gecenin Büyüsü Pelerini | mago | 1 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040102 | Şans Taşı Lv.2 | todas | 0 |  |

## 1106 Loya Köyü (Lv 26, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060203 | Unutulmuş Kolye | todas | 3 |  |
| 1060202 | Lanetli Kolye | todas | 1 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040102 | Şans Taşı Lv.2 | todas | 0 |  |

## 1107 Hedef Uçurum (Lv 28, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080203 | Sönmez Ruh Taşı | guerreiro/arqueiro | 3 |  |
| 1080213 | Unutulmuş Sihirli Göz | mago | 3 |  |
| 1080202 | Nefret Kalbi | guerreiro/arqueiro | 1 |  |
| 1080212 | Lanet Simgesi | mago | 1 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040102 | Şans Taşı Lv.2 | todas | 0 |  |

## 1201 Ölüm Perisi Sulağı (Lv 30, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011303 | Ağlayan Cadı Bıçağı | guerreiro | 3 |  |
| 1012303 | Suikastçı Yayı | arqueiro | 3 |  |
| 1013303 | Güçlü Ruh Değneği | mago | 3 |  |
| 1011302 | Yıkıcı Bıçağı | guerreiro | 1 |  |
| 1012302 | Kızgın Alev Yayı | arqueiro | 1 |  |
| 1013302 | Cüce Ustası Değneği | mago | 1 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |

## 1202 Karanlık Bataklık (Lv 32, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030303 | Deri Şapkası | todas | 3 |  |
| 1030302 | Seyahat Şapkası | todas | 1 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |

## 1203 Ölüm Bataklığı (Lv 34, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070303 | Simgeli Yüzük | todas | 3 |  |
| 1070302 | Buzlu Yüzük | todas | 1 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |

## 1204 Huzur Gölü (Lv 34, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070303 | Simgeli Yüzük | todas | 3 |  |
| 1070302 | Buzlu Yüzük | todas | 1 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |

## 1205 Buda Türbesi (Lv 36, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041303 | Zincirli Akıncı Zırhı | guerreiro | 3 |  |
| 1042303 | Şerefli Zırh | arqueiro | 3 |  |
| 1043303 | Görkemli Pelerin | mago | 3 |  |
| 1041302 | Gümüş Zırhı | guerreiro | 1 |  |
| 1042302 | Korkusuz Işık Zırhı | arqueiro | 1 |  |
| 1043302 | Karanlık Haberci Pelerini | mago | 1 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |

## 1206 Ölümsüz Harabe (Lv 38, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060303 | Düğümlü Kolye | todas | 3 |  |
| 1060302 | Tövbe Kolyesi | todas | 1 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |

## 1207 Dinlenme Yeri (Lv 38, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080303 | Gölge Simgesi | guerreiro/arqueiro | 3 |  |
| 1080313 | Kaybolan Simge | mago | 3 |  |
| 1080302 | Ölümsüz Oyma | guerreiro/arqueiro | 1 |  |
| 1080312 | Üzücü İzleri | mago | 1 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |

## 1301 Alev Taşı (Lv 40, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011403 | Sihirli Büyük Kılıç | guerreiro | 3 |  |
| 1012403 | Antik Yay | arqueiro | 3 |  |
| 1013403 | Gölge Değneği | mago | 3 |  |
| 1011402 | Aydınlık Kılıcı | guerreiro | 1 |  |
| 1012402 | Avcı Oku | arqueiro | 1 |  |
| 1013402 | Yıldırım Değneği | mago | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1302 Lanetli Çöl (Lv 42, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030403 | Hayal Kaskı | todas | 3 |  |
| 1030402 | Yeşil Ejderha Kaskı | todas | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1303 Alacakaranlık Savaş Alanı (Lv 44, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070403 | Kasırga Yüzüğü | todas | 3 |  |
| 1070402 | Dağılmış Ruh Yüzüğü | todas | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1304 Ölü kum tepesi (Lv 46, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041403 | Asil Süvari Zırhı | guerreiro | 3 |  |
| 1042403 | Tanrı Sözü Zırhı | arqueiro | 3 |  |
| 1043403 | Sabah Meleği Pelerini | mago | 3 |  |
| 1041402 | Ağır Canavar Zırhı | guerreiro | 1 |  |
| 1042402 | Doğal Zırh | arqueiro | 1 |  |
| 1043402 | Şafak Pelerini | mago | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1305 Umutsuzluk Çölü (Lv 46, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041403 | Asil Süvari Zırhı | guerreiro | 3 |  |
| 1042403 | Tanrı Sözü Zırhı | arqueiro | 3 |  |
| 1043403 | Sabah Meleği Pelerini | mago | 3 |  |
| 1041402 | Ağır Canavar Zırhı | guerreiro | 1 |  |
| 1042402 | Doğal Zırh | arqueiro | 1 |  |
| 1043402 | Şafak Pelerini | mago | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1306 Kanat Bataklığı (Lv 47, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060403 | Katil Şeytan Kolyesi | todas | 3 |  |
| 1060402 | Temizlik Kolyesi | todas | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1307 Ölüm İllüzyonu (Lv 48, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080403 | Güneş Simgesi | guerreiro/arqueiro | 3 |  |
| 1080413 | Kraliçe Simgesi | mago | 3 |  |
| 1080402 | Eşsiz Simge | guerreiro/arqueiro | 1 |  |
| 1080412 | Kızgın Avcı Simgesi | mago | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1308 Ejderha Mezarlığı (Lv 48, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080403 | Güneş Simgesi | guerreiro/arqueiro | 3 |  |
| 1080413 | Kraliçe Simgesi | mago | 3 |  |
| 1080402 | Eşsiz Simge | guerreiro/arqueiro | 1 |  |
| 1080412 | Kızgın Avcı Simgesi | mago | 1 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |

## 1401 Cesaret Denemesi (Lv 50, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011503 | Kara Kristal Kılıcı | guerreiro | 3 |  |
| 1012503 | Lanetli Kristal Yayı | arqueiro | 3 |  |
| 1013503 | Ateş Kölesi Değneği | mago | 3 |  |
| 1011502 | Kristal Kılıcı | guerreiro | 1 |  |
| 1012502 | Goblin Yayı | arqueiro | 1 |  |
| 1013502 | Magma Değneği | mago | 1 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1402 Kanlı Deneme (Lv 52, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030503 | Ölümsüz Kask | todas | 3 |  |
| 1030502 | Lanetli Göz Kaskı | todas | 1 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1403 Kabus Deneme (Lv 54, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070503 | Gezegen Yüzüğü | todas | 3 |  |
| 1070502 | Sert Vuruş Yüzüğü | todas | 1 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1404 Şeytani Deneme (Lv 54, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070503 | Gezegen Yüzüğü | todas | 3 |  |
| 1070502 | Sert Vuruş Yüzüğü | todas | 1 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1405 Kaos Deneme (Lv 56, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041503 | Mavi Kristal Zırhı | guerreiro | 3 |  |
| 1042503 | Öfkeli Zırhı | arqueiro | 3 |  |
| 1043503 | Büyücü Pelerini | mago | 3 |  |
| 1041502 | Ejderha Zırhı | guerreiro | 1 |  |
| 1042502 | Zehirli Arı Zırhı | arqueiro | 1 |  |
| 1043502 | Şeytan Pelerini | mago | 1 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1406 Ölüm Deneme (Lv 56, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041503 | Mavi Kristal Zırhı | guerreiro | 3 |  |
| 1042503 | Öfkeli Zırhı | arqueiro | 3 |  |
| 1043503 | Büyücü Pelerini | mago | 3 |  |
| 1041502 | Ejderha Zırhı | guerreiro | 1 |  |
| 1042502 | Zehirli Arı Zırhı | arqueiro | 1 |  |
| 1043502 | Şeytan Pelerini | mago | 1 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1407 Ruh Deneme (Lv 58, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080503 | Batan Güneş Simgesi | guerreiro/arqueiro | 3 |  |
| 1080513 | Element Fırtına Simgesi | mago | 3 |  |
| 1080502 | Parlak Beyaz Simge | guerreiro/arqueiro | 1 |  |
| 1080512 | Kardeş Simgesi | mago | 1 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1501 Gece Kanyonu (Lv 60, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011603 | Kırık Sihirli Kılıç | guerreiro | 3 |  |
| 1012603 | Yıldızlı Sihirli Yay | arqueiro | 3 |  |
| 1013603 | Hayalet Kadrosu | mago | 3 |  |
| 1011602 | Uygulama Kılıcı | guerreiro | 1 |  |
| 1012602 | Gece Klan Savaşı Yayı | arqueiro | 1 |  |
| 1013602 | Meteor Kristali | mago | 1 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1502 Yanan Tapınak (Lv 62, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030603 | Magma Arıtma Kaskı | todas | 3 |  |
| 1030602 | Dev Kemik Kask | todas | 1 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1503 Sihirli Deneme Alanı (Lv 64, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070603 | Yeşil Ejderha Yüzüğü | todas | 3 |  |
| 1070602 | Lanetli Yüzük | todas | 1 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1504 Ruh Mezarlığı (Lv 64, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070603 | Yeşil Ejderha Yüzüğü | todas | 3 |  |
| 1070602 | Lanetli Yüzük | todas | 1 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1505 Yabani Tapınak (Lv 66, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041603 | Devlerin Savaş Zırhı | guerreiro | 3 |  |
| 1042603 | Devlerin Savaş Zırhı | arqueiro | 3 |  |
| 1043603 | Keskin Nişancı Zırhı | mago | 3 |  |
| 1041602 | Ejderha Sırtı Zırhı | guerreiro | 1 |  |
| 1042602 | Ejderha Sırtı Zırhı | arqueiro | 1 |  |
| 1043602 | Adelan Koruma Zırhı | mago | 1 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1506 Azap Tahtı (Lv 68, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080603 | Gravür Dev Ayı | guerreiro/arqueiro | 3 |  |
| 1080613 | Alev Büyüsü Gravürü | mago | 3 |  |
| 1080602 | Barbar Simgesi | guerreiro/arqueiro | 1 |  |
| 1080612 | Büyük Büyücü Arması | mago | 1 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1507 Lanet Kaynağı (Lv 68, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080603 | Gravür Dev Ayı | guerreiro/arqueiro | 3 |  |
| 1080613 | Alev Büyüsü Gravürü | mago | 3 |  |
| 1080602 | Barbar Simgesi | guerreiro/arqueiro | 1 |  |
| 1080612 | Büyük Büyücü Arması | mago | 1 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1601 Sonsuz Tapınak (Lv 70, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011703 | Ejderha Dişi Kılıç | guerreiro | 3 |  |
| 1012703 | Ölüm Perisi Yayı | arqueiro | 3 |  |
| 1013703 | Antik Gizemli Değnek | mago | 3 |  |
| 1030703 | Araf Kaskı | todas | 3 |  |
| 1080703 | Girdap Madalyası | guerreiro/arqueiro | 3 |  |
| 1080713 | Tabu Mühürü | mago | 3 |  |
| 2129006 | Şeytan Taşı Lv.6 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 1602 Sonsuz Yol (Lv 70, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060703 | Dansçı Kolyesi | todas | 3 |  |
| 1070703 | Koç Kafası Yüzük | todas | 3 |  |
| 1041703 | Kaos Zırhı | guerreiro | 3 |  |
| 1042703 | Ejderha Kanı Zırhı | arqueiro | 3 |  |
| 1043703 | Kara Ay Pelerini | mago | 3 |  |
| 2129006 | Şeytan Taşı Lv.6 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |

## 8200 Kule Kralı (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131002 | Kralın Bakır Hazinesi | todas | 0 |  |

## 8201 Deneme Kulesi (Lv 46, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2060045 | Deneme Hazinesi | todas | 0 |  |

## 8202 Kule Kralı (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131003 | Kralın Gümüş Hazinesi | todas | 0 |  |

## 8203 Kule Kralı (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131004 | Kralın Altın Hazinesi | todas | 0 |  |

## 8204 Kule Kralı (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131005 | Kralın Elmas Hazinesi | todas | 0 |  |

## 9000 Saklı Orman (Lv 20, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991011 | İnanç Kılıcı | guerreiro | 5 |  |
| 1991013 | İnanç Kaskı | guerreiro | 5 |  |
| 1992011 | Yayın Kaderi | arqueiro | 5 |  |
| 1992013 | Başarı Kaderi Şapkası | arqueiro | 5 |  |
| 1993011 | Şeref Değneği | mago | 5 |  |
| 1993013 | Şeref Şapkası | mago | 5 |  |
| 1011204 | Lanet Kılıcı | guerreiro | 5 |  |
| 1012204 | Sonsuzluk Yayı | arqueiro | 5 |  |
| 1013204 | Kaos Şeytanı Değneği | mago | 5 |  |
| 1030204 | Sonsuz Güç Kaskı | todas | 5 |  |
| 2128101 | Parçalanmış Silah | todas | 0 |  |
| 2128103 | Parçalanmış Kask | todas | 0 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |
| 1011203 | Çılgın Kılıç | guerreiro | 3 |  |
| 1012203 | Uzun Savaş Oku | arqueiro | 3 |  |
| 1013203 | Sihirli Kan Asa | mago | 3 |  |
| 1030203 | Uçurum Gözü Şapkası | todas | 3 |  |
| 1070203 | Gölge Yüzüğü | todas | 3 |  |

## 9001 Büyük Kristal (Lv 25, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991014 | İnanç Zırhı | guerreiro | 5 |  |
| 1991016 | İnanç Kolyesi | guerreiro | 5 |  |
| 1992014 | Başarı Kaderi Zırhı | arqueiro | 5 |  |
| 1992016 | Başarı Kaderi Zinciri | arqueiro | 5 |  |
| 1993014 | Şeref Pelerini | mago | 5 |  |
| 1993016 | Şeref Zinciri | mago | 5 |  |
| 1041204 | Vahşi Kralı Zırhı | guerreiro | 5 |  |
| 1042204 | İzinsizlik Zırhı | arqueiro | 5 |  |
| 1043204 | Şeytanın Nefesi Pelerini | mago | 5 |  |
| 1060204 | Umut Gözyaşı Kolyesi | todas | 5 |  |
| 2128102 | Parçalanmış Zırh | todas | 0 |  |
| 2128104 | Parçalanmış Kolye | todas | 0 |  |
| 2128101 | Parçalanmış Silah | todas | 0 |  |
| 2128103 | Parçalanmış Kask | todas | 0 |  |
| 2129001 | Şeytan Taşı Lv.1 | todas | 0 |  |
| 2040103 | Şans Taşı Lv.3 | todas | 0 |  |
| 1041203 | Saldırı Zırhı | guerreiro | 3 |  |
| 1042203 | Canavar Avcısı Zırhı | arqueiro | 3 |  |
| 1043203 | Kara Yolculuk Pelerin | mago | 3 |  |
| 1060203 | Unutulmuş Kolye | todas | 3 |  |
| 1080203 | Sönmez Ruh Taşı | guerreiro/arqueiro | 3 |  |
| 1080213 | Unutulmuş Sihirli Göz | mago | 3 |  |

## 9002 Karanlık Mezarlık (Lv 30, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991021 | Korkusuz Kılıç | guerreiro | 5 |  |
| 1991023 | Korkusuz Kask | guerreiro | 5 |  |
| 1992021 | Rüzgar Ustanın Yayı | arqueiro | 5 |  |
| 1992023 | Rüzgar Ustanın Şapkası | arqueiro | 5 |  |
| 1993021 | Bilginin Değneği | mago | 5 |  |
| 1993023 | Bilginin Şapkası | mago | 5 |  |
| 1011304 | Şimşek Gölge Kılıcı | guerreiro | 5 |  |
| 1012304 | Ejderha Yok Edici Ok | arqueiro | 5 |  |
| 1013304 | Sakin Ruh Değneği | mago | 5 |  |
| 1030304 | İmza Koruyucusu Kaskı | todas | 5 |  |
| 2128201 | Eski Silah | todas | 0 |  |
| 2128203 | Eski Kask | todas | 0 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |
| 1011303 | Ağlayan Cadı Bıçağı | guerreiro | 3 |  |
| 1012303 | Suikastçı Yayı | arqueiro | 3 |  |
| 1013303 | Güçlü Ruh Değneği | mago | 3 |  |
| 1030303 | Deri Şapkası | todas | 3 |  |
| 1070303 | Simgeli Yüzük | todas | 3 |  |

## 9003 Kan Banyosu (Lv 35, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991024 | Korkusuz Zırh | guerreiro | 5 |  |
| 1991026 | Korkusuz Kalp | guerreiro | 5 |  |
| 1992024 | Rüzgar Ustanın Zırhı | arqueiro | 5 |  |
| 1992026 | Rüzgar Ustanın İnancı | arqueiro | 5 |  |
| 1993024 | Bilginin Pelerini | mago | 5 |  |
| 1993026 | Bilginin Yüreği | mago | 5 |  |
| 1041304 | Kutsal Savaş Zırhı | guerreiro | 5 |  |
| 1042304 | Rüzgar Yaratıcısı Zırhı | arqueiro | 5 |  |
| 1043304 | Gizemli İzler Pelerini | mago | 5 |  |
| 1060304 | Uçurum Kolyesi | todas | 5 |  |
| 2128202 | Eski Zırh | todas | 0 |  |
| 2128204 | Eski Kolye | todas | 0 |  |
| 2128201 | Eski Silah | todas | 0 |  |
| 2128203 | Eski Kask | todas | 0 |  |
| 2129002 | Şeytan Taşı Lv.2 | todas | 0 |  |
| 2040104 | Şans Taşı Lv.4 | todas | 0 |  |
| 1041303 | Zincirli Akıncı Zırhı | guerreiro | 3 |  |
| 1042303 | Şerefli Zırh | arqueiro | 3 |  |
| 1043303 | Görkemli Pelerin | mago | 3 |  |
| 1060303 | Düğümlü Kolye | todas | 3 |  |
| 1080303 | Gölge Simgesi | guerreiro/arqueiro | 3 |  |
| 1080313 | Kaybolan Simge | mago | 3 |  |

## 9004 Uçurum Kapısı (Lv 40, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991031 | Büyük Usta Kılıcı | guerreiro | 5 |  |
| 1991033 | Büyük Usta Kaskı | guerreiro | 5 |  |
| 1992031 | İsabetli Yaycı Yayı | arqueiro | 5 |  |
| 1992033 | İsabetli Yaycı Şapkası | arqueiro | 5 |  |
| 1993031 | Element Ustası Değneği | mago | 5 |  |
| 1993033 | Element Ustası Şapkası | mago | 5 |  |
| 1011404 | Ejderha Kanı Bıçağı | guerreiro | 5 |  |
| 1012404 | Parlak Ay Yayı | arqueiro | 5 |  |
| 1013404 | Ejderha Pençesi Değneği | mago | 5 |  |
| 1030404 | Lanet Temizleyicisi Kaskı | todas | 5 |  |
| 2128301 | Paslanmış Silah | todas | 0 |  |
| 2128303 | Paslanmış Kask | todas | 0 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1011403 | Sihirli Büyük Kılıç | guerreiro | 3 |  |
| 1012403 | Antik Yay | arqueiro | 3 |  |
| 1013403 | Gölge Değneği | mago | 3 |  |
| 1030403 | Hayal Kaskı | todas | 3 |  |
| 1070403 | Kasırga Yüzüğü | todas | 3 |  |

## 9005 Çöl Kıyameti (Lv 45, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991034 | Büyük Usta Zırhı | guerreiro | 5 |  |
| 1991036 | Büyük Usta Ruhu | guerreiro | 5 |  |
| 1992034 | İsabetli Yaycı Zırhı | arqueiro | 5 |  |
| 1992036 | İsabetli Yaycı Ruhu | arqueiro | 5 |  |
| 1993034 | Element Ustası  Pelerini | mago | 5 |  |
| 1993036 | Element Ustası  Ruhu | mago | 5 |  |
| 1041404 | Kutsal Koruyucu Zırhı | guerreiro | 5 |  |
| 1042404 | Ejderha Pulu·Zırhı | arqueiro | 5 |  |
| 1043404 | Peygamberin Gücü Pelerini | mago | 5 |  |
| 1060404 | Kara Ejderha Kalbi | todas | 5 |  |
| 2128302 | Paslanmış Zırh | todas | 0 |  |
| 2128304 | Paslanmış Kolye | todas | 0 |  |
| 2128301 | Paslanmış Silah | todas | 0 |  |
| 2128303 | Paslanmış Kask | todas | 0 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1041403 | Asil Süvari Zırhı | guerreiro | 3 |  |
| 1042403 | Tanrı Sözü Zırhı | arqueiro | 3 |  |
| 1043403 | Sabah Meleği Pelerini | mago | 3 |  |
| 1060403 | Katil Şeytan Kolyesi | todas | 3 |  |
| 1080403 | Güneş Simgesi | guerreiro/arqueiro | 3 |  |
| 1080413 | Kraliçe Simgesi | mago | 3 |  |

## 9006 Ölüm Sırrı (Lv 50, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991061 | Canavar Büyücü Kılıcı | guerreiro | 5 |  |
| 1991063 | Canavar Büyücü Kaskı | guerreiro | 5 |  |
| 1992061 | Ejderha Avcısı Yayı | arqueiro | 5 |  |
| 1992063 | Ejderha Avcısı Şapkası | arqueiro | 5 |  |
| 1993061 | Şeytan Hocası Değneği | mago | 5 |  |
| 1993063 | Şeytan Hocası Şapkası | mago | 5 |  |
| 1011504 | Kalp Delici Kılıcı | guerreiro | 5 |  |
| 1012504 | Sihirli Yay - Ruh Parçalayıcı | arqueiro | 5 |  |
| 1013504 | Ölüm Ruhu Değneği | mago | 5 |  |
| 1030504 | Lanetli Cadı Kaskı | todas | 5 |  |
| 2128401 | Gizemli Silah | todas | 0 |  |
| 2128403 | Gizemli Kask | todas | 0 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1011503 | Kara Kristal Kılıcı | guerreiro | 3 |  |
| 1012503 | Lanetli Kristal Yayı | arqueiro | 3 |  |
| 1013503 | Ateş Kölesi Değneği | mago | 3 |  |
| 1030503 | Ölümsüz Kask | todas | 3 |  |
| 1070503 | Gezegen Yüzüğü | todas | 3 |  |

## 9007 Sihirli Ejder Yuvası (Lv 55, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991064 | Canavar Büyücü Zırhı | guerreiro | 5 |  |
| 1991066 | Canavar Büyücü Ruhu | guerreiro | 5 |  |
| 1992064 | Ejderha Avcısı Zırhı | arqueiro | 5 |  |
| 1992066 | Ejderha Avcısı Ruhu | arqueiro | 5 |  |
| 1993064 | Şeytan Hocası Pelerini | mago | 5 |  |
| 1993066 | Şeytan Hocası Ruhu | mago | 5 |  |
| 1041504 | Kara Delik Zırhı | guerreiro | 5 |  |
| 1042504 | Kanlı Ejderha Zırhı | arqueiro | 5 |  |
| 1043504 | Drama Pelerini | mago | 5 |  |
| 1060504 | Su Tanrısı Özü | todas | 5 |  |
| 2128402 | Gizemli Zırh | todas | 0 |  |
| 2128404 | Gizemli Kolye | todas | 0 |  |
| 2128401 | Gizemli Silah | todas | 0 |  |
| 2128403 | Gizemli Kask | todas | 0 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1041503 | Mavi Kristal Zırhı | guerreiro | 3 |  |
| 1042503 | Öfkeli Zırhı | arqueiro | 3 |  |
| 1043503 | Büyücü Pelerini | mago | 3 |  |
| 1060503 | Katil Şeytan Kolyesi | todas | 3 |  |
| 1080503 | Batan Güneş Simgesi | guerreiro/arqueiro | 3 |  |
| 1080513 | Element Fırtına Simgesi | mago | 3 |  |

## 9008 Sihirli Kabile (Lv 60, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991081 | Ejderha Süvari Kılıcı | guerreiro | 5 |  |
| 1991083 | Ejderha Süvari Kaskı | guerreiro | 5 |  |
| 1992081 | Elf Kralının Yayı | arqueiro | 5 |  |
| 1992083 | Elf Kralının Şapkası | arqueiro | 5 |  |
| 1993081 | Büyük Bilge Değneği | mago | 5 |  |
| 1993083 | Büyük Bilge Şapkası | mago | 5 |  |
| 1011604 | Şeytan Kesme | guerreiro | 5 |  |
| 1012604 | Hayalet Kalbi | arqueiro | 5 |  |
| 1013604 | Sihirli Ateş | mago | 5 |  |
| 1030604 | Kanlı Kurt Savaşı Kaskı | todas | 5 |  |
| 2128501 | Antika Silah | todas | 0 |  |
| 2128503 | Antika Kask | todas | 0 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1011603 | Kırık Sihirli Kılıç | guerreiro | 3 |  |
| 1012603 | Yıldızlı Sihirli Yay | arqueiro | 3 |  |
| 1013603 | Hayalet Kadrosu | mago | 3 |  |
| 1030603 | Magma Arıtma Kaskı | todas | 3 |  |
| 1070603 | Yeşil Ejderha Yüzüğü | todas | 3 |  |

## 9009 Şeytan Türbesi (Lv 65, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991084 | Ejderha Süvari Zırhı | guerreiro | 5 |  |
| 1991086 | Ejderha Süvari Ruhu | guerreiro | 5 |  |
| 1992084 | Elf Kralının Derisi | arqueiro | 5 |  |
| 1992086 | Elf Kralının Ruhu | arqueiro | 5 |  |
| 1993084 | Büyük Bilge Pelerini | mago | 5 |  |
| 1993086 | Büyük Bilge Ruhu | mago | 5 |  |
| 1041604 | Kutsal Yabani | guerreiro | 5 |  |
| 1042604 | Parlak·Zırh | arqueiro | 5 |  |
| 1043604 | Cinli Zırh | mago | 5 |  |
| 1060604 | Su Tanrısı Özü | todas | 5 |  |
| 2128502 | Antika Zırh | todas | 0 |  |
| 2128504 | Antika Kolye | todas | 0 |  |
| 2128501 | Antika Silah | todas | 0 |  |
| 2128503 | Antika Kask | todas | 0 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1041603 | Devlerin Savaş Zırhı | guerreiro | 3 |  |
| 1042603 | Devlerin Savaş Zırhı | arqueiro | 3 |  |
| 1043603 | Keskin Nişancı Zırhı | mago | 3 |  |
| 1060603 | Sihirli Kolye | todas | 3 |  |
| 1080603 | Gravür Dev Ayı | guerreiro/arqueiro | 3 |  |
| 1080613 | Alev Büyüsü Gravürü | mago | 3 |  |

## 9010 Hicret Bölgesi (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991091 | Yüce Ares Kılıcı | guerreiro | 5 |  |
| 1991093 | Yüce Ares Kaskı | guerreiro | 5 |  |
| 1992091 | Yabani Peri Yayı | arqueiro | 5 |  |
| 1992093 | Yabani Peri Kaskı | arqueiro | 5 |  |
| 1993091 | Antik Büyü Değneği | mago | 5 |  |
| 1993093 | Antik Büyü Kaskı | mago | 5 |  |
| 1011704 | Kılıç Gökyüzü | guerreiro | 5 |  |
| 1012704 | Kutsal Yay | arqueiro | 5 |  |
| 1013704 | Sakin Ruh Efsane | mago | 5 |  |
| 1030704 | Kral Ejderha Kaskı | todas | 5 |  |
| 2128601 | Antik Silah | todas | 0 |  |
| 2128603 | Antik Kask | todas | 0 |  |
| 2129006 | Şeytan Taşı Lv.6 | todas | 0 |  |
| 2040106 | Şans Taşı Lv.6 | todas | 0 |  |
| 1011703 | Ejderha Dişi Kılıç | guerreiro | 3 |  |
| 1012703 | Ölüm Perisi Yayı | arqueiro | 3 |  |
| 1013703 | Antik Gizemli Değnek | mago | 3 |  |
| 1030703 | Araf Kaskı | todas | 3 |  |
| 1070703 | Koç Kafası Yüzük | todas | 3 |  |

## 9011 Hayalet Alanı (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991094 | Yüce Ares Zırhı | guerreiro | 5 |  |
| 1991096 | Yüce Ares Ruhu | guerreiro | 5 |  |
| 1992094 | Yabani Peri Kuş Tüyü | arqueiro | 5 |  |
| 1992096 | Yabani Peri Ruhu | arqueiro | 5 |  |
| 1993094 | Antik Büyü Pelerini | mago | 5 |  |
| 1993096 | Antik Büyü Ruhu | mago | 5 |  |
| 1041704 | Büyülü Sonsuzluk Kaskı | guerreiro | 5 |  |
| 1042704 | Kutsal Kask - Büyülü İz | arqueiro | 5 |  |
| 1043704 | Pelerin Yeniden Doğmak | mago | 5 |  |
| 1060704 | Deneme Tekeri | todas | 5 |  |
| 2128602 | Antik Zırh | todas | 0 |  |
| 2128604 | Antik Kolye | todas | 0 |  |
| 2129006 | Şeytan Taşı Lv.6 | todas | 0 |  |
| 2040106 | Şans Taşı Lv.6 | todas | 0 |  |
| 1041703 | Kaos Zırhı | guerreiro | 3 |  |
| 1042703 | Ejderha Kanı Zırhı | arqueiro | 3 |  |
| 1043703 | Kara Ay Pelerini | mago | 3 |  |
| 1060703 | Dansçı Kolyesi | todas | 3 |  |
| 1080703 | Girdap Madalyası | guerreiro/arqueiro | 3 |  |
| 1080713 | Tabu Mühürü | mago | 3 |  |

## 9012 Nirvana Tanrısı (Lv 80, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129800 | Lv.80 Efsane Taşı | todas | 0 |  |
| 2040107 | Şans Taşı Lv.7 | todas | 0 |  |
| 1041803 | Royal Zırhı | guerreiro | 3 |  |
| 1042803 | Sürgün Zırhı | arqueiro | 3 |  |
| 1043803 | Yılan Derisi Pelerin | mago | 3 |  |
| 1060803 | Ateş Yüzüğü | todas | 3 |  |
| 1080803 | Şahin Gözü | guerreiro/arqueiro | 3 |  |
| 1080813 | Sonsuz Rune Taşı | mago | 3 |  |

## 9104 Uçurum Kapısı (Lv 40, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129400 | Lv.40 Efsane Taşı | todas | 0 |  |
| 1991031 | Büyük Usta Kılıcı | guerreiro | 5 |  |
| 1991033 | Büyük Usta Kaskı | guerreiro | 5 |  |
| 1992031 | İsabetli Yaycı Yayı | arqueiro | 5 |  |
| 1992033 | İsabetli Yaycı Şapkası | arqueiro | 5 |  |
| 1993031 | Element Ustası Değneği | mago | 5 |  |
| 1993033 | Element Ustası Şapkası | mago | 5 |  |
| 1011404 | Ejderha Kanı Bıçağı | guerreiro | 5 |  |
| 1012404 | Parlak Ay Yayı | arqueiro | 5 |  |
| 1013404 | Ejderha Pençesi Değneği | mago | 5 |  |
| 1030404 | Lanet Temizleyicisi Kaskı | todas | 5 |  |
| 2128301 | Paslanmış Silah | todas | 0 |  |
| 2128303 | Paslanmış Kask | todas | 0 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1011403 | Sihirli Büyük Kılıç | guerreiro | 3 |  |
| 1012403 | Antik Yay | arqueiro | 3 |  |
| 1013403 | Gölge Değneği | mago | 3 |  |
| 1030403 | Hayal Kaskı | todas | 3 |  |
| 1070403 | Kasırga Yüzüğü | todas | 3 |  |

## 9105 Çöl Kıyameti (Lv 45, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129400 | Lv.40 Efsane Taşı | todas | 0 |  |
| 1991034 | Büyük Usta Zırhı | guerreiro | 5 |  |
| 1991036 | Büyük Usta Ruhu | guerreiro | 5 |  |
| 1992034 | İsabetli Yaycı Zırhı | arqueiro | 5 |  |
| 1992036 | İsabetli Yaycı Ruhu | arqueiro | 5 |  |
| 1993034 | Element Ustası  Pelerini | mago | 5 |  |
| 1993036 | Element Ustası  Ruhu | mago | 5 |  |
| 1041404 | Kutsal Koruyucu Zırhı | guerreiro | 5 |  |
| 1042404 | Ejderha Pulu·Zırhı | arqueiro | 5 |  |
| 1043404 | Peygamberin Gücü Pelerini | mago | 5 |  |
| 1060404 | Kara Ejderha Kalbi | todas | 5 |  |
| 2128302 | Paslanmış Zırh | todas | 0 |  |
| 2128304 | Paslanmış Kolye | todas | 0 |  |
| 2128301 | Paslanmış Silah | todas | 0 |  |
| 2128303 | Paslanmış Kask | todas | 0 |  |
| 2129003 | Şeytan Taşı Lv.3 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1041403 | Asil Süvari Zırhı | guerreiro | 3 |  |
| 1042403 | Tanrı Sözü Zırhı | arqueiro | 3 |  |
| 1043403 | Sabah Meleği Pelerini | mago | 3 |  |
| 1060403 | Katil Şeytan Kolyesi | todas | 3 |  |
| 1080403 | Güneş Simgesi | guerreiro/arqueiro | 3 |  |
| 1080413 | Kraliçe Simgesi | mago | 3 |  |

## 9106 Ölüm Sırrı (Lv 50, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129500 | Lv.50 Efsane Taşı | todas | 0 |  |
| 1991061 | Canavar Büyücü Kılıcı | guerreiro | 5 |  |
| 1991063 | Canavar Büyücü Kaskı | guerreiro | 5 |  |
| 1992061 | Ejderha Avcısı Yayı | arqueiro | 5 |  |
| 1992063 | Ejderha Avcısı Şapkası | arqueiro | 5 |  |
| 1993061 | Şeytan Hocası Değneği | mago | 5 |  |
| 1993063 | Şeytan Hocası Şapkası | mago | 5 |  |
| 1011504 | Kalp Delici Kılıcı | guerreiro | 5 |  |
| 1012504 | Sihirli Yay - Ruh Parçalayıcı | arqueiro | 5 |  |
| 1013504 | Ölüm Ruhu Değneği | mago | 5 |  |
| 1030504 | Lanetli Cadı Kaskı | todas | 5 |  |
| 2128401 | Gizemli Silah | todas | 0 |  |
| 2128403 | Gizemli Kask | todas | 0 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1011503 | Kara Kristal Kılıcı | guerreiro | 3 |  |
| 1012503 | Lanetli Kristal Yayı | arqueiro | 3 |  |
| 1013503 | Ateş Kölesi Değneği | mago | 3 |  |
| 1030503 | Ölümsüz Kask | todas | 3 |  |
| 1070503 | Gezegen Yüzüğü | todas | 3 |  |

## 9107 Sihirli Ejder Yuvası (Lv 55, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129500 | Lv.50 Efsane Taşı | todas | 0 |  |
| 1991064 | Canavar Büyücü Zırhı | guerreiro | 5 |  |
| 1991066 | Canavar Büyücü Ruhu | guerreiro | 5 |  |
| 1992064 | Ejderha Avcısı Zırhı | arqueiro | 5 |  |
| 1992066 | Ejderha Avcısı Ruhu | arqueiro | 5 |  |
| 1993064 | Şeytan Hocası Pelerini | mago | 5 |  |
| 1993066 | Şeytan Hocası Ruhu | mago | 5 |  |
| 1041504 | Kara Delik Zırhı | guerreiro | 5 |  |
| 1042504 | Kanlı Ejderha Zırhı | arqueiro | 5 |  |
| 1043504 | Drama Pelerini | mago | 5 |  |
| 1060504 | Su Tanrısı Özü | todas | 5 |  |
| 2128402 | Gizemli Zırh | todas | 0 |  |
| 2128404 | Gizemli Kolye | todas | 0 |  |
| 2128401 | Gizemli Silah | todas | 0 |  |
| 2128403 | Gizemli Kask | todas | 0 |  |
| 2129004 | Şeytan Taşı Lv.4 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1041503 | Mavi Kristal Zırhı | guerreiro | 3 |  |
| 1042503 | Öfkeli Zırhı | arqueiro | 3 |  |
| 1043503 | Büyücü Pelerini | mago | 3 |  |
| 1060503 | Katil Şeytan Kolyesi | todas | 3 |  |
| 1080503 | Batan Güneş Simgesi | guerreiro/arqueiro | 3 |  |
| 1080513 | Element Fırtına Simgesi | mago | 3 |  |

## 9108 Sihirli Kabile (Lv 60, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129600 | Lv.60 Efsane Taşı | todas | 0 |  |
| 1991081 | Ejderha Süvari Kılıcı | guerreiro | 5 |  |
| 1991083 | Ejderha Süvari Kaskı | guerreiro | 5 |  |
| 1992081 | Elf Kralının Yayı | arqueiro | 5 |  |
| 1992083 | Elf Kralının Şapkası | arqueiro | 5 |  |
| 1993081 | Büyük Bilge Değneği | mago | 5 |  |
| 1993083 | Büyük Bilge Şapkası | mago | 5 |  |
| 1011604 | Şeytan Kesme | guerreiro | 5 |  |
| 1012604 | Hayalet Kalbi | arqueiro | 5 |  |
| 1013604 | Sihirli Ateş | mago | 5 |  |
| 1030604 | Kanlı Kurt Savaşı Kaskı | todas | 5 |  |
| 2128501 | Antika Silah | todas | 0 |  |
| 2128503 | Antika Kask | todas | 0 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1011603 | Kırık Sihirli Kılıç | guerreiro | 3 |  |
| 1012603 | Yıldızlı Sihirli Yay | arqueiro | 3 |  |
| 1013603 | Hayalet Kadrosu | mago | 3 |  |
| 1030603 | Magma Arıtma Kaskı | todas | 3 |  |
| 1070603 | Yeşil Ejderha Yüzüğü | todas | 3 |  |

## 9109 Şeytan Türbesi (Lv 65, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129600 | Lv.60 Efsane Taşı | todas | 0 |  |
| 1991084 | Ejderha Süvari Zırhı | guerreiro | 5 |  |
| 1991086 | Ejderha Süvari Ruhu | guerreiro | 5 |  |
| 1992084 | Elf Kralının Derisi | arqueiro | 5 |  |
| 1992086 | Elf Kralının Ruhu | arqueiro | 5 |  |
| 1993084 | Büyük Bilge Pelerini | mago | 5 |  |
| 1993086 | Büyük Bilge Ruhu | mago | 5 |  |
| 1041604 | Kutsal Yabani | guerreiro | 5 |  |
| 1042604 | Parlak·Zırh | arqueiro | 5 |  |
| 1043604 | Cinli Zırh | mago | 5 |  |
| 1060604 | Su Tanrısı Özü | todas | 5 |  |
| 2128502 | Antika Zırh | todas | 0 |  |
| 2128504 | Antika Kolye | todas | 0 |  |
| 2128501 | Antika Silah | todas | 0 |  |
| 2128503 | Antika Kask | todas | 0 |  |
| 2129005 | Şeytan Taşı Lv.5 | todas | 0 |  |
| 2040105 | Şans Taşı Lv.5 | todas | 0 |  |
| 1041603 | Devlerin Savaş Zırhı | guerreiro | 3 |  |
| 1042603 | Devlerin Savaş Zırhı | arqueiro | 3 |  |
| 1043603 | Keskin Nişancı Zırhı | mago | 3 |  |
| 1060603 | Sihirli Kolye | todas | 3 |  |
| 1080603 | Gravür Dev Ayı | guerreiro/arqueiro | 3 |  |
| 1080613 | Alev Büyüsü Gravürü | mago | 3 |  |

## 9110 Hicret Bölgesi (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129700 | Lv.70 Efsane Taşı | todas | 0 |  |
| 2129701 | Lv.70 Epik Silah Parçası | todas | 0 |  |
| 2129703 | Lv.70 Epik Kask Parçası | todas | 0 |  |
| 2129704 | Lv.70 Epik Kıyafet Parçası | todas | 0 |  |
| 2129706 | Lv.70 Epik Kolye Parçası | todas | 0 |  |
| 1991091 | Yüce Ares Kılıcı | guerreiro | 5 |  |
| 1991093 | Yüce Ares Kaskı | guerreiro | 5 |  |
| 1992091 | Yabani Peri Yayı | arqueiro | 5 |  |
| 1992093 | Yabani Peri Kaskı | arqueiro | 5 |  |
| 1993091 | Antik Büyü Değneği | mago | 5 |  |
| 1993093 | Antik Büyü Kaskı | mago | 5 |  |
| 1011704 | Kılıç Gökyüzü | guerreiro | 5 |  |
| 1012704 | Kutsal Yay | arqueiro | 5 |  |
| 1013704 | Sakin Ruh Efsane | mago | 5 |  |
| 1030704 | Kral Ejderha Kaskı | todas | 5 |  |
| 2128601 | Antik Silah | todas | 0 |  |
| 2128603 | Antik Kask | todas | 0 |  |
| 2129006 | Şeytan Taşı Lv.6 | todas | 0 |  |
| 2040106 | Şans Taşı Lv.6 | todas | 0 |  |
| 1011703 | Ejderha Dişi Kılıç | guerreiro | 3 |  |
| 1012703 | Ölüm Perisi Yayı | arqueiro | 3 |  |
| 1013703 | Antik Gizemli Değnek | mago | 3 |  |
| 1030703 | Araf Kaskı | todas | 3 |  |
| 1070703 | Koç Kafası Yüzük | todas | 3 |  |

## 9111 Hayalet Alanı (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129700 | Lv.70 Efsane Taşı | todas | 0 |  |
| 2129701 | Lv.70 Epik Silah Parçası | todas | 0 |  |
| 2129703 | Lv.70 Epik Kask Parçası | todas | 0 |  |
| 2129704 | Lv.70 Epik Kıyafet Parçası | todas | 0 |  |
| 2129706 | Lv.70 Epik Kolye Parçası | todas | 0 |  |
| 1991094 | Yüce Ares Zırhı | guerreiro | 5 |  |
| 1991096 | Yüce Ares Ruhu | guerreiro | 5 |  |
| 1992094 | Yabani Peri Kuş Tüyü | arqueiro | 5 |  |
| 1992096 | Yabani Peri Ruhu | arqueiro | 5 |  |
| 1993094 | Antik Büyü Pelerini | mago | 5 |  |
| 1993096 | Antik Büyü Ruhu | mago | 5 |  |
| 1041704 | Büyülü Sonsuzluk Kaskı | guerreiro | 5 |  |
| 1042704 | Kutsal Kask - Büyülü İz | arqueiro | 5 |  |
| 1043704 | Pelerin Yeniden Doğmak | mago | 5 |  |
| 1060704 | Deneme Tekeri | todas | 5 |  |
| 2128602 | Antik Zırh | todas | 0 |  |
| 2128604 | Antik Kolye | todas | 0 |  |
| 2129006 | Şeytan Taşı Lv.6 | todas | 0 |  |
| 2040106 | Şans Taşı Lv.6 | todas | 0 |  |
| 1041703 | Kaos Zırhı | guerreiro | 3 |  |
| 1042703 | Ejderha Kanı Zırhı | arqueiro | 3 |  |
| 1043703 | Kara Ay Pelerini | mago | 3 |  |
| 1060703 | Dansçı Kolyesi | todas | 3 |  |
| 1080703 | Girdap Madalyası | guerreiro/arqueiro | 3 |  |
| 1080713 | Tabu Mühürü | mago | 3 |  |

## 9112 Nirvana Tanrısı (Lv 80, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129800 | Lv.80 Efsane Taşı | todas | 0 |  |
| 2040107 | Şans Taşı Lv.7 | todas | 0 |  |
| 1041803 | Royal Zırhı | guerreiro | 3 |  |
| 1042803 | Sürgün Zırhı | arqueiro | 3 |  |
| 1043803 | Yılan Derisi Pelerin | mago | 3 |  |
| 1060803 | Ateş Yüzüğü | todas | 3 |  |
| 1080803 | Şahin Gözü | guerreiro/arqueiro | 3 |  |
| 1080813 | Sonsuz Rune Taşı | mago | 3 |  |
