# Drops das masmorras

A carta do fim da etapa é sorteada pela tabela `campaign_cards` (migração 0034), no formato (campanha, item,
peso, fonte). O peso é quantas vezes o item saiu nas capturas (inglesa; as cartas 1080013 e 1080002 só turco: replay). Os itens da coluna `Item` de
`Campaigns` que nunca foram vistos pesam 1. Uma campanha sem linhas na tabela usa a coluna `Item` com pesos iguais
(`game/drops.py`). As tabelas por campanha abaixo são um retrato do template, para conferir com vídeos e capturas.

## O que é visto, deduzido e o que falta

- *(visto)* Inglesa #1102-#1123 (1001): 135 (5 cartas, `payCardCount` 5, `price` 0), depois 5122 → 115, 26 e 83
  "Received: Banshee Plume x1". O 134 só vem como resposta do 5180.
- *(visto)* Cartas da 1001: 1080012 Banshee Plume duas vezes (inglesa #1122 e #1544, mago); 1080013 e 1080002 uma
  vez cada (só turco: replay #1241 e #1744).
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
| 102102 | Worg Tooth (2100001) | 2 | 1 | inglesa #1216-#1220 |
| 102102 | Lvl. 1 Luck Stone (2040101) | 1 | 0,5 *(dedução)* | (só turco: replay #1355, #1386); a inglesa não deu |
| 102103 | Worg Tooth (2100001) | 2 | 1 | inglesa #1275-#1280 |
| 102105 | Worg Tooth (2100001) | 3 | 1 | inglesa #1355-#1358 |
| 102106 | Worg Tooth (2100001) | 3 | 1 | inglesa #1397-#1418 |
| 1011 (101102 a 101109) e 102109 | nenhum | — | — | sem item na inglesa |

Cartas:

| Item | Nome | Classe | Atributos | Peso | Visto em |
|---|---|---|---|---|---|
| 1080003 | Stigma Crest | guerreiro/arqueiro | 3 | 1 |  |
| 1080013 | Duskan Glyph | mago | 3 | 1 | (só turco: replay #1241) |
| 1080002 | Coruscan Crest | guerreiro/arqueiro | 1 | 1 | (só turco: replay #1744) |
| 1080012 | Banshee Plume | mago | 1 | 2 | inglesa #1122, #1544 |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 | 1 |  |

## 1002 Baylon Plains (Lv 9, solo)

Ligada no servidor: etapas 1131 → 1132 e 1141 → 1142.

Drops: o 114104 deu 1080011 x1 *(dedução: chance 0,5)*, num baú (4103 com `signId`/`baseItem`, pego no 5129;
inglesa #2910-#2939); o material (SonType 210: Worg Tooth, Wood) vai direto para a mochila. As caixas do caçador (113203, 114203) dão 10.000 Daru, e
a tumba 114105 dá 5.000 Daru (de novo 5.000 em oficial_encantar #1111: fixo). A 114203 também deu Lvl. 3 Luck Stone x1 no lugar
do Daru (oficial_encantar #1436, aviso #1457 sem `x1`): migração 0052, `pick` sorteado por igual *(dedução: uma
amostra de cada)*. A 113203 só tem a amostra de Daru.

| Item | Nome | Classe | Atributos | Peso | Visto em |
|---|---|---|---|---|---|
| 2040102 | Lvl. 2 Luck Stone | todas | 0 | 2 | inglesa #2727, #3181 (fora do `CampaignInfo.Item`) |
| 1011104 | Indomitable Long Sword | guerreiro | 3 | 1 |  |
| 1012104 | Crackwind Bone Bow | arqueiro | 5 | 1 |  |
| 1013104 | Summoner's Blood Staff | mago | 5 | 1 |  |
| 1011102 | Ethereal Battle Sword | guerreiro | 1 | 1 |  |
| 1012102 | Tenebra Bone Bow | arqueiro | 1 | 1 |  |
| 1013102 | Lunalurite Staff | mago | 1 | 1 |  |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 | 1 |  |

## 6001 Resource Quarry (pedreira)

Não tem carta. Cada colheita (5032 numa pilha, sonType 2352) dá Wood (2100022) x2 ou x3, e a luta do 8699 dá
Wood x18 (inglesa #2050-#2066), ganhando ou perdendo.

## 1003 Temple of Ibalize (Outer) (Lv 11, solo)

Ligada no servidor (migração 0058, `oficial_20261023-153200-1`): etapa 1031 → 1032. A caixa do caçador 103105 deu
Lvl. 3 Luck Stone (2040103) x1 (aviso sem `x1`, #527) ou 10.000 Daru (oficial_20261023-171155-1), pelo `param5`.
O chefe 103207 caiu duas vezes em oficial_20261023-171155-1: 135 com 5 cartas, 5 pagas, preço 0 *(visto)*, e as
cartas 1030102 e 1030103 com `randomSkill`.

Perene Bone (2100003, missão 190) só com a missão aberta (migração 0062): 103102 x2 e 103105/103111/103112 x1
*(visto)*; 103103 x2 *(dedução: mesmo Undead Warrior)*; 103104, 103106, 103202, 103203, 103206 x1
**TODO(inventado)**. Mystery Box 103108 (Skeleton Key): 5.000 Gold ou Lvl. 2 Luck Stone x2, por igual *(dedução,
três amostras)*.

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030103 | Martial Helmet | todas | 3 |  |
| 1030102 | Wizard Cap | todas | 1 |  |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 |  |

## 1004 Temple of Ibalize (Inner) (Lv 13, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070103 | Lamenter's Band | todas | 3 |  |
| 1070102 | Healing Ring | todas | 1 |  |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 |  |

## 1005 Orc Plains (Lv 15, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041103 | Sentinel Armor | guerreiro | 3 |  |
| 1042103 | Defender's Leather Armor | arqueiro | 3 |  |
| 1043103 | Regalian Robe | mago | 3 |  |
| 1043102 | Elders Robe | mago | 1 |  |
| 1042102 | Tharg Battle Leather Armor | arqueiro | 1 |  |
| 1041102 | Tauran Armor | guerreiro | 1 |  |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 |  |

## 1006 Tribal Plateau (Lv 17, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060103 | Blood Priest Necklace | todas | 3 |  |
| 1060102 | Elven Pendant | todas | 1 |  |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 |  |

## 1007 Camp Calorn (Lv 19, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080103 | Knight Crest | guerreiro/arqueiro | 3 |  |
| 1080113 | Gorefiend Talisman | mago | 3 |  |
| 1080102 | Harbinger Medal | guerreiro/arqueiro | 1 |  |
| 1080112 | Abyssal Necklace | mago | 1 |  |
| 2040101 | Lvl. 1 Luck Stone | todas | 0 |  |

## 1101 Bretheran Abyss (Lv 20, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011203 | Berseker Rune Sword | guerreiro | 3 |  |
| 1012203 | Battalion Long Bow | arqueiro | 3 |  |
| 1013203 | Bloodforged Staff | mago | 3 |  |
| 1011202 | Vigilante Rune Sword | guerreiro | 1 |  |
| 1012202 | Daradon Long Bow | arqueiro | 1 |  |
| 1013202 | Battle Staff | mago | 1 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040102 | Lvl. 2 Luck Stone | todas | 0 |  |

## 1102 Roaring Wetlands (Lv 21, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030203 | Profundity Hood | todas | 3 |  |
| 1030202 | Knight's Helmet | todas | 1 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040102 | Lvl. 2 Luck Stone | todas | 0 |  |

## 1103 Duskin Arena (Lv 23, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070203 | Leonopteryx Ring | todas | 3 |  |
| 1070202 | Crag Ring | todas | 1 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040102 | Lvl. 2 Luck Stone | todas | 0 |  |

## 1104 Serpent's Den (Lv 23, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070203 | Leonopteryx Ring | todas | 3 |  |
| 1070202 | Crag Ring | todas | 1 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040102 | Lvl. 2 Luck Stone | todas | 0 |  |

## 1105 Forest of Doom (Lv 24, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041203 | Stormer's Chainmail | guerreiro | 3 |  |
| 1042203 | Magican Breasplate | arqueiro | 3 |  |
| 1043203 | Dakan Walker's Robe | mago | 3 |  |
| 1041202 | Panegyre Chainmail | guerreiro | 1 |  |
| 1042202 | Harbinger Breastplate | arqueiro | 1 |  |
| 1043202 | Night Veil Robe | mago | 1 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040102 | Lvl. 2 Luck Stone | todas | 0 |  |

## 1106 Edena Village (Lv 26, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060203 | Forsaken Pendant | todas | 3 |  |
| 1060202 | Maledine Necklace | todas | 1 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040102 | Lvl. 2 Luck Stone | todas | 0 |  |

## 1107 Termini Cliff (Lv 28, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080203 | Immortal Soul Stone | guerreiro/arqueiro | 3 |  |
| 1080213 | Eye of the Forgotten | mago | 3 |  |
| 1080202 | Loathsome Heart | guerreiro/arqueiro | 1 |  |
| 1080212 | Cursed Crest | mago | 1 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040102 | Lvl. 2 Luck Stone | todas | 0 |  |

## 1201 Banshee Wetlands (Lv 30, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011303 | Weeping Widow Battle Axe | guerreiro | 3 |  |
| 1012303 | Assassin's Glyph Bow | arqueiro | 3 |  |
| 1013303 | Enchanted Essence Staff | mago | 3 |  |
| 1011302 | Destroyer Battle Axe | guerreiro | 1 |  |
| 1012302 | Ragefire Glyph Bow | arqueiro | 1 |  |
| 1013302 | Dwarven Warlock Stock | mago | 1 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |

## 1202 Delphinian Swamp (Lv 32, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030303 | Yaron Fur Cap | todas | 3 |  |
| 1030302 | Traveller's Hood | todas | 1 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |

## 1203 Swamp of the Undead (Lv 34, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070303 | Heiro Ring | todas | 3 |  |
| 1070302 | Hailstone Ring | todas | 1 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |

## 1204 Serenity Lake (Lv 34, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070303 | Heiro Ring | todas | 3 |  |
| 1070302 | Hailstone Ring | todas | 1 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |

## 1205 Shrine of Sakaiya (Lv 36, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041303 | Stormbreaker Banded Mail | guerreiro | 3 |  |
| 1042303 | Ilustran Light Armor | arqueiro | 3 |  |
| 1043303 | Glitzton Robe | mago | 3 |  |
| 1041302 | Mithril Banded Mail | guerreiro | 1 |  |
| 1042302 | Intrepid Light Armor | arqueiro | 1 |  |
| 1043302 | Dakan Angel Robe | mago | 1 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |

## 1206 Immortal Ruins (Lv 38, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060303 | Winder's Necklace | todas | 3 |  |
| 1060302 | Repentor's Necklace | todas | 1 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |

## 1207 Boneyard (Lv 38, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080303 | Umbral Crest | guerreiro/arqueiro | 3 |  |
| 1080313 | Mark of the Lost | mago | 3 |  |
| 1080302 | Undead Carving | guerreiro/arqueiro | 1 |  |
| 1080312 | Repentor's Glyph | mago | 1 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |

## 1301 Blazing Desert (Lv 40, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011403 | Magic Slayer Broadsword | guerreiro | 3 |  |
| 1012403 | Ancient Battle Bow | arqueiro | 3 |  |
| 1013403 | Phantom Shadow Staff | mago | 3 |  |
| 1011402 | Luminite Broadsword | guerreiro | 1 |  |
| 1012402 | Butcher's Bow | arqueiro | 1 |  |
| 1013402 | Phantom Thunder Staff | mago | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1302 Desert of Curses (Lv 42, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030403 | Phantasmal Helmet | todas | 3 |  |
| 1030402 | Green Dragon Feather Cap | todas | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1303 Twilight Arena (Lv 44, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070403 | Hoarfrost Ring | todas | 3 |  |
| 1070402 | Soul Catcher Ring | todas | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1304 The Forgotten Dunes (Lv 46, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041403 | Imperial Knight Armor | guerreiro | 3 |  |
| 1042403 | Oracle Light Armor | arqueiro | 3 |  |
| 1043403 | Sunton Seer Robe | mago | 3 |  |
| 1041402 | Slagard Heavy Armor | guerreiro | 1 |  |
| 1042402 | Naruturan Light Armor | arqueiro | 1 |  |
| 1043402 | Auroran Robe | mago | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1305 Desert of Despair (Lv 46, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041403 | Imperial Knight Armor | guerreiro | 3 |  |
| 1042403 | Oracle Light Armor | arqueiro | 3 |  |
| 1043403 | Sunton Seer Robe | mago | 3 |  |
| 1041402 | Slagard Heavy Armor | guerreiro | 1 |  |
| 1042402 | Naruturan Light Armor | arqueiro | 1 |  |
| 1043402 | Auroran Robe | mago | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1306 Ukiah Sands (Lv 47, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060403 | Manadon's Pendant | todas | 3 |  |
| 1060402 | Purity Necklace | todas | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1307 Reaper's Illusion (Lv 48, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080403 | Twilight Talisman | guerreiro/arqueiro | 3 |  |
| 1080413 | Ice Queen Talisman | mago | 3 |  |
| 1080402 | Delphic Crest | guerreiro/arqueiro | 1 |  |
| 1080412 | Growler Regalia | mago | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1308 Buradoth's Grave (Lv 48, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080403 | Twilight Talisman | guerreiro/arqueiro | 3 |  |
| 1080413 | Ice Queen Talisman | mago | 3 |  |
| 1080402 | Delphic Crest | guerreiro/arqueiro | 1 |  |
| 1080412 | Growler Regalia | mago | 1 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |

## 1401 Desert of Palms (Lv 50, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011503 | Dakan Crystal Sword | guerreiro | 3 |  |
| 1012503 | Cursed Crystalan Bow | arqueiro | 3 |  |
| 1013503 | Fire Idol Staff | mago | 3 |  |
| 1011502 | Crystalan Sword | guerreiro | 1 |  |
| 1012502 | Goblin Bow | arqueiro | 1 |  |
| 1013502 | Basalt Staff | mago | 1 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1402 Blood Moorland (Lv 52, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030503 | Undead Helmet | todas | 3 |  |
| 1030502 | Satan's Eye Feather Cap | todas | 1 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1403 Nightmare Ruins (Lv 54, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070503 | Fallen Celestial Band | todas | 3 |  |
| 1070502 | Algid Ring | todas | 1 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1404 Demon's Rill (Lv 54, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070503 | Fallen Celestial Band | todas | 3 |  |
| 1070502 | Algid Ring | todas | 1 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1405 Forest of Chaos (Lv 56, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041503 | Azure Armor | guerreiro | 3 |  |
| 1042503 | Syr Light Armor | arqueiro | 3 |  |
| 1043503 | Warlock Exile's Robe | mago | 3 |  |
| 1041502 | Dragus Heavy Armor | guerreiro | 1 |  |
| 1042502 | Vespine Light Armor | arqueiro | 1 |  |
| 1043502 | Belial Robe | mago | 1 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1406 Devil's Trail (Lv 56, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041503 | Azure Armor | guerreiro | 3 |  |
| 1042503 | Syr Light Armor | arqueiro | 3 |  |
| 1043503 | Warlock Exile's Robe | mago | 3 |  |
| 1041502 | Dragus Heavy Armor | guerreiro | 1 |  |
| 1042502 | Vespine Light Armor | arqueiro | 1 |  |
| 1043502 | Belial Robe | mago | 1 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1407 Soul Trials (Lv 58, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080503 | Duskan Talisman | guerreiro/arqueiro | 3 |  |
| 1080513 | Elemental Storm Talisman | mago | 3 |  |
| 1080502 | Purity Crest | guerreiro/arqueiro | 1 |  |
| 1080512 | Prince Regalia | mago | 1 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1501 Bloodnite Canyon (Lv 60, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011603 | Soulrip Hexed Sword | guerreiro | 3 |  |
| 1012603 | Hexed Crossbow | arqueiro | 3 |  |
| 1013603 | Cosmic Beast's Staff | mago | 3 |  |
| 1011602 | Iron Great Sword | guerreiro | 1 |  |
| 1012602 | Duskan Crossbow | arqueiro | 1 |  |
| 1013602 | Crystalan Staff | mago | 1 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1502 Temple of Fire (Lv 62, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1030603 | Lava Helmet | todas | 3 |  |
| 1030602 | Giant Bone Helmet | todas | 1 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1503 Hall of Judgment (Lv 64, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070603 | Green Dragon Ring | todas | 3 |  |
| 1070602 | Tiger-Eye Ring | todas | 1 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1504 Soulless Tomb (Lv 64, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1070603 | Green Dragon Ring | todas | 3 |  |
| 1070602 | Tiger-Eye Ring | todas | 1 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1505 Palace of Corruption (Lv 66, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1041603 | Apostle Armor | guerreiro | 3 |  |
| 1042603 | Heavy Leather Armor | arqueiro | 3 |  |
| 1043603 | Sniper's Light Armor | mago | 3 |  |
| 1041602 | Rebirth Necklace | guerreiro | 1 |  |
| 1042602 | Dragon Bone Heavy Armor | arqueiro | 1 |  |
| 1043602 | Sunbright Armor | mago | 1 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1506 Throne of Yaros (Lv 68, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080603 | Giant Bear Jewel | guerreiro/arqueiro | 3 |  |
| 1080613 | Jewel of Yaros | mago | 3 |  |
| 1080602 | Mark of Savage | guerreiro/arqueiro | 1 |  |
| 1080612 | Archmage Regalia | mago | 1 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1507 Cursed Lair (Lv 68, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1080603 | Giant Bear Jewel | guerreiro/arqueiro | 3 |  |
| 1080613 | Jewel of Yaros | mago | 3 |  |
| 1080602 | Mark of Savage | guerreiro/arqueiro | 1 |  |
| 1080612 | Archmage Regalia | mago | 1 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1601 Eternal Sanctuary (Lv 70, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1011703 | Emerald Terror | guerreiro | 3 |  |
| 1012703 | Succubus' Crossbow | arqueiro | 3 |  |
| 1013703 | Old Cabala Staff | mago | 3 |  |
| 1030703 | Devil's Helmet | todas | 3 |  |
| 1080703 | Vortex Medallion | guerreiro/arqueiro | 3 |  |
| 1080713 | Jewel of Secrets | mago | 3 |  |
| 2129006 | Lvl. 6 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 1602 Endless Path (Lv 70, solo)

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1060703 | Dancer's Necklace | todas | 3 |  |
| 1070703 | Tauren Skull Ring | todas | 3 |  |
| 1041703 | Chaos Armor | guerreiro | 3 |  |
| 1042703 | Dragon Blood Armor | arqueiro | 3 |  |
| 1043703 | Oblivion Robe | mago | 3 |  |
| 2129006 | Lvl. 6 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |

## 8200 Tower of Kings (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131002 | Bronze King Chest | todas | 0 |  |

## 8201 The Spire (Lv 46, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2060045 | Spire Chest | todas | 0 |  |

## 8202 Tower of Kings (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131003 | Silver King Chest | todas | 0 |  |

## 8203 Tower of Kings (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131004 | Gold King Chest | todas | 0 |  |

## 8204 Tower of Kings (Lv 38, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2131005 | Diamond King Chest | todas | 0 |  |

## 9000 Nether Forest (Lv 20, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991011 | Gartan Sword | guerreiro | 5 |  |
| 1991013 | Gartan Helmet | guerreiro | 5 |  |
| 1992011 | Moirai Bow | arqueiro | 5 |  |
| 1992013 | Moirai Helmet | arqueiro | 5 |  |
| 1993011 | Gloridon Staff | mago | 5 |  |
| 1993013 | Gloridon Hat | mago | 5 |  |
| 1011204 | Soul Destroyer Sword | guerreiro | 5 |  |
| 1012204 | Doomsday Bow | arqueiro | 5 |  |
| 1013204 | Babelian Staff | mago | 5 |  |
| 1030204 | Inifity Helmet | todas | 5 |  |
| 2128101 | Broken Weapon | todas | 0 |  |
| 2128103 | Broken Helmet | todas | 0 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |
| 1011203 | Berseker Rune Sword | guerreiro | 3 |  |
| 1012203 | Battalion Long Bow | arqueiro | 3 |  |
| 1013203 | Bloodforged Staff | mago | 3 |  |
| 1030203 | Profundity Hood | todas | 3 |  |
| 1070203 | Leonopteryx Ring | todas | 3 |  |

## 9001 Claristun (Lv 25, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991014 | Gartan Armor | guerreiro | 5 |  |
| 1991016 | Gartan Necklace | guerreiro | 5 |  |
| 1992014 | Moirai Armor | arqueiro | 5 |  |
| 1992016 | Moirai Necklace | arqueiro | 5 |  |
| 1993014 | Gloridon Robe | mago | 5 |  |
| 1993016 | Gloridon Necklace | mago | 5 |  |
| 1041204 | Imperial Heavy Armor | guerreiro | 5 |  |
| 1042204 | Manon Seal Armor | arqueiro | 5 |  |
| 1043204 | Burning Vestment | mago | 5 |  |
| 1060204 | Murloc's Tears | todas | 5 |  |
| 2128102 | Broken Armor | todas | 0 |  |
| 2128104 | Broken Necklace | todas | 0 |  |
| 2128101 | Broken Weapon | todas | 0 |  |
| 2128103 | Broken Helmet | todas | 0 |  |
| 2129001 | Lvl. 1 Crystaloid | todas | 0 |  |
| 2040103 | Lvl. 3 Luck Stone | todas | 0 |  |
| 1041203 | Stormer's Chainmail | guerreiro | 3 |  |
| 1042203 | Magican Breasplate | arqueiro | 3 |  |
| 1043203 | Dakan Walker's Robe | mago | 3 |  |
| 1060203 | Forsaken Pendant | todas | 3 |  |
| 1080203 | Immortal Soul Stone | guerreiro/arqueiro | 3 |  |
| 1080213 | Eye of the Forgotten | mago | 3 |  |

## 9002 The Graveyard (Lv 30, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991021 | Valoran Sword | guerreiro | 5 |  |
| 1991023 | Valoran Helmet | guerreiro | 5 |  |
| 1992021 | Phoenix Bow | arqueiro | 5 |  |
| 1992023 | Phoenix Cap | arqueiro | 5 |  |
| 1993021 | Lorekeeper Staff | mago | 5 |  |
| 1993023 | Lorekeeper Hat | mago | 5 |  |
| 1011304 | Sacred Shadow Destroyer | guerreiro | 5 |  |
| 1012304 | Sacred Dragonslayer Bow | arqueiro | 5 |  |
| 1013304 | Requiem Staff | mago | 5 |  |
| 1030304 | Sealer's Helmet | todas | 5 |  |
| 2128201 | Worn Weapon | todas | 0 |  |
| 2128203 | Worn Helmet | todas | 0 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |
| 1011303 | Weeping Widow Battle Axe | guerreiro | 3 |  |
| 1012303 | Assassin's Glyph Bow | arqueiro | 3 |  |
| 1013303 | Enchanted Essence Staff | mago | 3 |  |
| 1030303 | Yaron Fur Cap | todas | 3 |  |
| 1070303 | Heiro Ring | todas | 3 |  |

## 9003 The Bloodlands (Lv 35, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991024 | Valoran Armor | guerreiro | 5 |  |
| 1991026 | Valoran Brooch | guerreiro | 5 |  |
| 1992024 | Phoenix Armor | arqueiro | 5 |  |
| 1992026 | Phoenix Brooch | arqueiro | 5 |  |
| 1993024 | Lorekeeper Robe | mago | 5 |  |
| 1993026 | Lorekeeper Brooch | mago | 5 |  |
| 1041304 | Apollo's Glory | guerreiro | 5 |  |
| 1042304 | Skylorn Impenetrable Armor | arqueiro | 5 |  |
| 1043304 | Arcanum Vestment | mago | 5 |  |
| 1060304 | Void Pointer | todas | 5 |  |
| 2128202 | Worn Armor | todas | 0 |  |
| 2128204 | Worn Necklace | todas | 0 |  |
| 2128201 | Worn Weapon | todas | 0 |  |
| 2128203 | Worn Helmet | todas | 0 |  |
| 2129002 | Lvl. 2 Crystaloid | todas | 0 |  |
| 2040104 | Lvl. 4 Luck Stone | todas | 0 |  |
| 1041303 | Stormbreaker Banded Mail | guerreiro | 3 |  |
| 1042303 | Ilustran Light Armor | arqueiro | 3 |  |
| 1043303 | Glitzton Robe | mago | 3 |  |
| 1060303 | Winder's Necklace | todas | 3 |  |
| 1080303 | Umbral Crest | guerreiro/arqueiro | 3 |  |
| 1080313 | Mark of the Lost | mago | 3 |  |

## 9004 The Void (Lv 40, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991031 | Crotian Sword | guerreiro | 5 |  |
| 1991033 | Crotian Helmet | guerreiro | 5 |  |
| 1992031 | Aerial Crossbow | arqueiro | 5 |  |
| 1992033 | Aerial Cap | arqueiro | 5 |  |
| 1993031 | Bender Staff | mago | 5 |  |
| 1993033 | Bender Hat | mago | 5 |  |
| 1011404 | Bloodsoaked Dragon Sword | guerreiro | 5 |  |
| 1012404 | Crescent Star Bow | arqueiro | 5 |  |
| 1013404 | Soul Collector Dragon Staff | mago | 5 |  |
| 1030404 | Exorcist Cap | todas | 5 |  |
| 2128301 | Dismal Weapon | todas | 0 |  |
| 2128303 | Dismal Helmet | todas | 0 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1011403 | Magic Slayer Broadsword | guerreiro | 3 |  |
| 1012403 | Ancient Battle Bow | arqueiro | 3 |  |
| 1013403 | Phantom Shadow Staff | mago | 3 |  |
| 1030403 | Phantasmal Helmet | todas | 3 |  |
| 1070403 | Hoarfrost Ring | todas | 3 |  |

## 9005 The Badlands (Lv 45, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991034 | Crotian Armor | guerreiro | 5 |  |
| 1991036 | Crotian Brooch | guerreiro | 5 |  |
| 1992034 | Aerial Armor | arqueiro | 5 |  |
| 1992036 | Aerial Brooch | arqueiro | 5 |  |
| 1993034 | Bender Robe | mago | 5 |  |
| 1993036 | Bender Brooch | mago | 5 |  |
| 1041404 | Sacred Defender Armor | guerreiro | 5 |  |
| 1042404 | Dragon's Rage | arqueiro | 5 |  |
| 1043404 | Prophet's Vestment | mago | 5 |  |
| 1060404 | Black Dragon Heart | todas | 5 |  |
| 2128302 | Dismal Armor | todas | 0 |  |
| 2128304 | Dismal Necklace | todas | 0 |  |
| 2128301 | Dismal Weapon | todas | 0 |  |
| 2128303 | Dismal Helmet | todas | 0 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1041403 | Imperial Knight Armor | guerreiro | 3 |  |
| 1042403 | Oracle Light Armor | arqueiro | 3 |  |
| 1043403 | Sunton Seer Robe | mago | 3 |  |
| 1060403 | Manadon's Pendant | todas | 3 |  |
| 1080403 | Twilight Talisman | guerreiro/arqueiro | 3 |  |
| 1080413 | Ice Queen Talisman | mago | 3 |  |

## 9006 Garden of Death (Lv 50, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991061 | Titan Sword | guerreiro | 5 |  |
| 1991063 | Titan Helmet | guerreiro | 5 |  |
| 1992061 | Harpy Bow | arqueiro | 5 |  |
| 1992063 | Harpy Cap | arqueiro | 5 |  |
| 1993061 | Magister Staff | mago | 5 |  |
| 1993063 | Magister Hat | mago | 5 |  |
| 1011504 | Heart Breaker Cursed Sword. | guerreiro | 5 |  |
| 1012504 | Barathrum's Bow | arqueiro | 5 |  |
| 1013504 | Necromancer's Staff | mago | 5 |  |
| 1030504 | Banshee Feather Cap | todas | 5 |  |
| 2128401 | Mystic Weapon | todas | 0 |  |
| 2128403 | Mystic Hat | todas | 0 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1011503 | Dakan Crystal Sword | guerreiro | 3 |  |
| 1012503 | Cursed Crystalan Bow | arqueiro | 3 |  |
| 1013503 | Fire Idol Staff | mago | 3 |  |
| 1030503 | Undead Helmet | todas | 3 |  |
| 1070503 | Fallen Celestial Band | todas | 3 |  |

## 9007 Tarraton's Lair (Lv 55, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991064 | Titan Armor | guerreiro | 5 |  |
| 1991066 | Titan Brooch | guerreiro | 5 |  |
| 1992064 | Harpy Armor | arqueiro | 5 |  |
| 1992066 | Harpy Brooch | arqueiro | 5 |  |
| 1993064 | Magister Robe | mago | 5 |  |
| 1993066 | Magister Brooch | mago | 5 |  |
| 1041504 | Black Hole Ultimate Armor | guerreiro | 5 |  |
| 1042504 | Dragonus Blood Armor | arqueiro | 5 |  |
| 1043504 | Spellbinder's Robe | mago | 5 |  |
| 1060504 | Galene Brooch | todas | 5 |  |
| 2128402 | Mystic Armor | todas | 0 |  |
| 2128404 | Mystic Necklace | todas | 0 |  |
| 2128401 | Mystic Weapon | todas | 0 |  |
| 2128403 | Mystic Hat | todas | 0 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1041503 | Azure Armor | guerreiro | 3 |  |
| 1042503 | Syr Light Armor | arqueiro | 3 |  |
| 1043503 | Warlock Exile's Robe | mago | 3 |  |
| 1060503 | Manadon's Pendant | todas | 3 |  |
| 1080503 | Duskan Talisman | guerreiro/arqueiro | 3 |  |
| 1080513 | Elemental Storm Talisman | mago | 3 |  |

## 9008 Moonevil Den (Lv 60, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991081 | Wyvern Sword | guerreiro | 5 |  |
| 1991083 | Wyvern Helmet | guerreiro | 5 |  |
| 1992081 | Elven Crossbow | arqueiro | 5 |  |
| 1992083 | Elven Cap | arqueiro | 5 |  |
| 1993081 | Sage Staff | mago | 5 |  |
| 1993083 | Sage Hat | mago | 5 |  |
| 1011604 | God Slayer Sword | guerreiro | 5 |  |
| 1012604 | Heart Crossbow | arqueiro | 5 |  |
| 1013604 | Burning Sun Staff | mago | 5 |  |
| 1030604 | Bloody Wolf Helmet | todas | 5 |  |
| 2128501 | Ancient Weapon | todas | 0 |  |
| 2128503 | Ancient Helmet | todas | 0 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1011603 | Soulrip Hexed Sword | guerreiro | 3 |  |
| 1012603 | Hexed Crossbow | arqueiro | 3 |  |
| 1013603 | Cosmic Beast's Staff | mago | 3 |  |
| 1030603 | Lava Helmet | todas | 3 |  |
| 1070603 | Green Dragon Ring | todas | 3 |  |

## 9009 Demon Temple (Lv 65, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991084 | Wyvern Armor | guerreiro | 5 |  |
| 1991086 | Wyvern Brooch | guerreiro | 5 |  |
| 1992084 | Elven Armor | arqueiro | 5 |  |
| 1992086 | Elven Brooch | arqueiro | 5 |  |
| 1993084 | Sage Robe | mago | 5 |  |
| 1993086 | Sage Brooch | mago | 5 |  |
| 1041604 | Fallen Armor | guerreiro | 5 |  |
| 1042604 | Glory Armor | arqueiro | 5 |  |
| 1043604 | Star Spirit Armor | mago | 5 |  |
| 1060604 | Enchanted Brooch | todas | 5 |  |
| 2128502 | Ancient Armor | todas | 0 |  |
| 2128504 | Ancient Necklace | todas | 0 |  |
| 2128501 | Ancient Weapon | todas | 0 |  |
| 2128503 | Ancient Helmet | todas | 0 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1041603 | Apostle Armor | guerreiro | 3 |  |
| 1042603 | Heavy Leather Armor | arqueiro | 3 |  |
| 1043603 | Sniper's Light Armor | mago | 3 |  |
| 1060603 | Arcane Necklace | todas | 3 |  |
| 1080603 | Giant Bear Jewel | guerreiro/arqueiro | 3 |  |
| 1080613 | Jewel of Yaros | mago | 3 |  |

## 9010 Samsara (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991091 | Apollo's Sword | guerreiro | 5 |  |
| 1991093 | Apollo's Helmet | guerreiro | 5 |  |
| 1992091 | Angel's Crossbow | arqueiro | 5 |  |
| 1992093 | Angel's Cap | arqueiro | 5 |  |
| 1993091 | Ethereal Staff | mago | 5 |  |
| 1993093 | Ethereal Hat | mago | 5 |  |
| 1011704 | Skyrender | guerreiro | 5 |  |
| 1012704 | The Eliminator | arqueiro | 5 |  |
| 1013704 | Fabled Holy Staff | mago | 5 |  |
| 1030704 | Dragonscale Helmet | todas | 5 |  |
| 2128601 | Archaic Weapon | todas | 0 |  |
| 2128603 | Archaic Helmet | todas | 0 |  |
| 2129006 | Lvl. 6 Crystaloid | todas | 0 |  |
| 2040106 | Lvl. 6 Luck Stone | todas | 0 |  |
| 1011703 | Emerald Terror | guerreiro | 3 |  |
| 1012703 | Succubus' Crossbow | arqueiro | 3 |  |
| 1013703 | Old Cabala Staff | mago | 3 |  |
| 1030703 | Devil's Helmet | todas | 3 |  |
| 1070703 | Tauren Skull Ring | todas | 3 |  |

## 9011 Lych's Lair (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 1991094 | Apollo's Armor | guerreiro | 5 |  |
| 1991096 | Apollo's Brooch | guerreiro | 5 |  |
| 1992094 | Angel's Armor | arqueiro | 5 |  |
| 1992096 | Angel's Brooch | arqueiro | 5 |  |
| 1993094 | Ethereal Robe | mago | 5 |  |
| 1993096 | Ethereal Brooch | mago | 5 |  |
| 1041704 | Divine Armor | guerreiro | 5 |  |
| 1042704 | Angelic Armor | arqueiro | 5 |  |
| 1043704 | Atonement Robe | mago | 5 |  |
| 1060704 | Brooch of Trials | todas | 5 |  |
| 2128602 | Archaic Armor | todas | 0 |  |
| 2128604 | Archaic Necklace | todas | 0 |  |
| 2129006 | Lvl. 6 Crystaloid | todas | 0 |  |
| 2040106 | Lvl. 6 Luck Stone | todas | 0 |  |
| 1041703 | Chaos Armor | guerreiro | 3 |  |
| 1042703 | Dragon Blood Armor | arqueiro | 3 |  |
| 1043703 | Oblivion Robe | mago | 3 |  |
| 1060703 | Dancer's Necklace | todas | 3 |  |
| 1080703 | Vortex Medallion | guerreiro/arqueiro | 3 |  |
| 1080713 | Jewel of Secrets | mago | 3 |  |

## 9012 Nirvana (Lv 80, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129800 | Lvl. 80 Legendary Stone | todas | 0 |  |
| 2040107 | Lvl. 7 Luck Stone | todas | 0 |  |
| 1041803 | Royal Knight Armor | guerreiro | 3 |  |
| 1042803 | Forsaken Leather Armor | arqueiro | 3 |  |
| 1043803 | Serpent’s Cursed Robe | mago | 3 |  |
| 1060803 | Ancient Gem Necklace | todas | 3 |  |
| 1080803 | Broken Eagle Eye | guerreiro/arqueiro | 3 |  |
| 1080813 | Endless Blessing Stone | mago | 3 |  |

## 9104 The Void(Nightmare) (Lv 40, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129400 | Lvl. 40 Legendary Stone | todas | 0 |  |
| 1991031 | Crotian Sword | guerreiro | 5 |  |
| 1991033 | Crotian Helmet | guerreiro | 5 |  |
| 1992031 | Aerial Crossbow | arqueiro | 5 |  |
| 1992033 | Aerial Cap | arqueiro | 5 |  |
| 1993031 | Bender Staff | mago | 5 |  |
| 1993033 | Bender Hat | mago | 5 |  |
| 1011404 | Bloodsoaked Dragon Sword | guerreiro | 5 |  |
| 1012404 | Crescent Star Bow | arqueiro | 5 |  |
| 1013404 | Soul Collector Dragon Staff | mago | 5 |  |
| 1030404 | Exorcist Cap | todas | 5 |  |
| 2128301 | Dismal Weapon | todas | 0 |  |
| 2128303 | Dismal Helmet | todas | 0 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1011403 | Magic Slayer Broadsword | guerreiro | 3 |  |
| 1012403 | Ancient Battle Bow | arqueiro | 3 |  |
| 1013403 | Phantom Shadow Staff | mago | 3 |  |
| 1030403 | Phantasmal Helmet | todas | 3 |  |
| 1070403 | Hoarfrost Ring | todas | 3 |  |

## 9105 The Badlands(Nightmare) (Lv 45, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129400 | Lvl. 40 Legendary Stone | todas | 0 |  |
| 1991034 | Crotian Armor | guerreiro | 5 |  |
| 1991036 | Crotian Brooch | guerreiro | 5 |  |
| 1992034 | Aerial Armor | arqueiro | 5 |  |
| 1992036 | Aerial Brooch | arqueiro | 5 |  |
| 1993034 | Bender Robe | mago | 5 |  |
| 1993036 | Bender Brooch | mago | 5 |  |
| 1041404 | Sacred Defender Armor | guerreiro | 5 |  |
| 1042404 | Dragon's Rage | arqueiro | 5 |  |
| 1043404 | Prophet's Vestment | mago | 5 |  |
| 1060404 | Black Dragon Heart | todas | 5 |  |
| 2128302 | Dismal Armor | todas | 0 |  |
| 2128304 | Dismal Necklace | todas | 0 |  |
| 2128301 | Dismal Weapon | todas | 0 |  |
| 2128303 | Dismal Helmet | todas | 0 |  |
| 2129003 | Lvl. 3 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1041403 | Imperial Knight Armor | guerreiro | 3 |  |
| 1042403 | Oracle Light Armor | arqueiro | 3 |  |
| 1043403 | Sunton Seer Robe | mago | 3 |  |
| 1060403 | Manadon's Pendant | todas | 3 |  |
| 1080403 | Twilight Talisman | guerreiro/arqueiro | 3 |  |
| 1080413 | Ice Queen Talisman | mago | 3 |  |

## 9106 Garden of Death(Nightmare) (Lv 50, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129500 | Lvl. 50 Legendary Stone | todas | 0 |  |
| 1991061 | Titan Sword | guerreiro | 5 |  |
| 1991063 | Titan Helmet | guerreiro | 5 |  |
| 1992061 | Harpy Bow | arqueiro | 5 |  |
| 1992063 | Harpy Cap | arqueiro | 5 |  |
| 1993061 | Magister Staff | mago | 5 |  |
| 1993063 | Magister Hat | mago | 5 |  |
| 1011504 | Heart Breaker Cursed Sword. | guerreiro | 5 |  |
| 1012504 | Barathrum's Bow | arqueiro | 5 |  |
| 1013504 | Necromancer's Staff | mago | 5 |  |
| 1030504 | Banshee Feather Cap | todas | 5 |  |
| 2128401 | Mystic Weapon | todas | 0 |  |
| 2128403 | Mystic Hat | todas | 0 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1011503 | Dakan Crystal Sword | guerreiro | 3 |  |
| 1012503 | Cursed Crystalan Bow | arqueiro | 3 |  |
| 1013503 | Fire Idol Staff | mago | 3 |  |
| 1030503 | Undead Helmet | todas | 3 |  |
| 1070503 | Fallen Celestial Band | todas | 3 |  |

## 9107 Tarraton's Liar(Nightmare) (Lv 55, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129500 | Lvl. 50 Legendary Stone | todas | 0 |  |
| 1991064 | Titan Armor | guerreiro | 5 |  |
| 1991066 | Titan Brooch | guerreiro | 5 |  |
| 1992064 | Harpy Armor | arqueiro | 5 |  |
| 1992066 | Harpy Brooch | arqueiro | 5 |  |
| 1993064 | Magister Robe | mago | 5 |  |
| 1993066 | Magister Brooch | mago | 5 |  |
| 1041504 | Black Hole Ultimate Armor | guerreiro | 5 |  |
| 1042504 | Dragonus Blood Armor | arqueiro | 5 |  |
| 1043504 | Spellbinder's Robe | mago | 5 |  |
| 1060504 | Galene Brooch | todas | 5 |  |
| 2128402 | Mystic Armor | todas | 0 |  |
| 2128404 | Mystic Necklace | todas | 0 |  |
| 2128401 | Mystic Weapon | todas | 0 |  |
| 2128403 | Mystic Hat | todas | 0 |  |
| 2129004 | Lvl. 4 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1041503 | Azure Armor | guerreiro | 3 |  |
| 1042503 | Syr Light Armor | arqueiro | 3 |  |
| 1043503 | Warlock Exile's Robe | mago | 3 |  |
| 1060503 | Manadon's Pendant | todas | 3 |  |
| 1080503 | Duskan Talisman | guerreiro/arqueiro | 3 |  |
| 1080513 | Elemental Storm Talisman | mago | 3 |  |

## 9108 Moonevil Den(Nightmare) (Lv 60, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129600 | Lvl. 60 Legendary Stone | todas | 0 |  |
| 1991081 | Wyvern Sword | guerreiro | 5 |  |
| 1991083 | Wyvern Helmet | guerreiro | 5 |  |
| 1992081 | Elven Crossbow | arqueiro | 5 |  |
| 1992083 | Elven Cap | arqueiro | 5 |  |
| 1993081 | Sage Staff | mago | 5 |  |
| 1993083 | Sage Hat | mago | 5 |  |
| 1011604 | God Slayer Sword | guerreiro | 5 |  |
| 1012604 | Heart Crossbow | arqueiro | 5 |  |
| 1013604 | Burning Sun Staff | mago | 5 |  |
| 1030604 | Bloody Wolf Helmet | todas | 5 |  |
| 2128501 | Ancient Weapon | todas | 0 |  |
| 2128503 | Ancient Helmet | todas | 0 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1011603 | Soulrip Hexed Sword | guerreiro | 3 |  |
| 1012603 | Hexed Crossbow | arqueiro | 3 |  |
| 1013603 | Cosmic Beast's Staff | mago | 3 |  |
| 1030603 | Lava Helmet | todas | 3 |  |
| 1070603 | Green Dragon Ring | todas | 3 |  |

## 9109 Demon Temple(Nightmare) (Lv 65, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129600 | Lvl. 60 Legendary Stone | todas | 0 |  |
| 1991084 | Wyvern Armor | guerreiro | 5 |  |
| 1991086 | Wyvern Brooch | guerreiro | 5 |  |
| 1992084 | Elven Armor | arqueiro | 5 |  |
| 1992086 | Elven Brooch | arqueiro | 5 |  |
| 1993084 | Sage Robe | mago | 5 |  |
| 1993086 | Sage Brooch | mago | 5 |  |
| 1041604 | Fallen Armor | guerreiro | 5 |  |
| 1042604 | Glory Armor | arqueiro | 5 |  |
| 1043604 | Star Spirit Armor | mago | 5 |  |
| 1060604 | Enchanted Brooch | todas | 5 |  |
| 2128502 | Ancient Armor | todas | 0 |  |
| 2128504 | Ancient Necklace | todas | 0 |  |
| 2128501 | Ancient Weapon | todas | 0 |  |
| 2128503 | Ancient Helmet | todas | 0 |  |
| 2129005 | Lvl. 5 Crystaloid | todas | 0 |  |
| 2040105 | Lvl. 5 Luck Stone | todas | 0 |  |
| 1041603 | Apostle Armor | guerreiro | 3 |  |
| 1042603 | Heavy Leather Armor | arqueiro | 3 |  |
| 1043603 | Sniper's Light Armor | mago | 3 |  |
| 1060603 | Arcane Necklace | todas | 3 |  |
| 1080603 | Giant Bear Jewel | guerreiro/arqueiro | 3 |  |
| 1080613 | Jewel of Yaros | mago | 3 |  |

## 9110 Samsara(Nightmare) (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129700 | Lvl. 70 Legendary Stone | todas | 0 |  |
| 2129701 | Lvl. 70 Legendary Weapon Shard | todas | 0 |  |
| 2129703 | Lvl. 70 Legendary Helmet Shard | todas | 0 |  |
| 2129704 | Lvl. 70 Legendary Armor Shard | todas | 0 |  |
| 2129706 | Lvl. 70 Legendary Necklace Shard | todas | 0 |  |
| 1991091 | Apollo's Sword | guerreiro | 5 |  |
| 1991093 | Apollo's Helmet | guerreiro | 5 |  |
| 1992091 | Angel's Crossbow | arqueiro | 5 |  |
| 1992093 | Angel's Cap | arqueiro | 5 |  |
| 1993091 | Ethereal Staff | mago | 5 |  |
| 1993093 | Ethereal Hat | mago | 5 |  |
| 1011704 | Skyrender | guerreiro | 5 |  |
| 1012704 | The Eliminator | arqueiro | 5 |  |
| 1013704 | Fabled Holy Staff | mago | 5 |  |
| 1030704 | Dragonscale Helmet | todas | 5 |  |
| 2128601 | Archaic Weapon | todas | 0 |  |
| 2128603 | Archaic Helmet | todas | 0 |  |
| 2129006 | Lvl. 6 Crystaloid | todas | 0 |  |
| 2040106 | Lvl. 6 Luck Stone | todas | 0 |  |
| 1011703 | Emerald Terror | guerreiro | 3 |  |
| 1012703 | Succubus' Crossbow | arqueiro | 3 |  |
| 1013703 | Old Cabala Staff | mago | 3 |  |
| 1030703 | Devil's Helmet | todas | 3 |  |
| 1070703 | Tauren Skull Ring | todas | 3 |  |

## 9111 Lych's Lair(Nightmare) (Lv 70, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129700 | Lvl. 70 Legendary Stone | todas | 0 |  |
| 2129701 | Lvl. 70 Legendary Weapon Shard | todas | 0 |  |
| 2129703 | Lvl. 70 Legendary Helmet Shard | todas | 0 |  |
| 2129704 | Lvl. 70 Legendary Armor Shard | todas | 0 |  |
| 2129706 | Lvl. 70 Legendary Necklace Shard | todas | 0 |  |
| 1991094 | Apollo's Armor | guerreiro | 5 |  |
| 1991096 | Apollo's Brooch | guerreiro | 5 |  |
| 1992094 | Angel's Armor | arqueiro | 5 |  |
| 1992096 | Angel's Brooch | arqueiro | 5 |  |
| 1993094 | Ethereal Robe | mago | 5 |  |
| 1993096 | Ethereal Brooch | mago | 5 |  |
| 1041704 | Divine Armor | guerreiro | 5 |  |
| 1042704 | Angelic Armor | arqueiro | 5 |  |
| 1043704 | Atonement Robe | mago | 5 |  |
| 1060704 | Brooch of Trials | todas | 5 |  |
| 2128602 | Archaic Armor | todas | 0 |  |
| 2128604 | Archaic Necklace | todas | 0 |  |
| 2129006 | Lvl. 6 Crystaloid | todas | 0 |  |
| 2040106 | Lvl. 6 Luck Stone | todas | 0 |  |
| 1041703 | Chaos Armor | guerreiro | 3 |  |
| 1042703 | Dragon Blood Armor | arqueiro | 3 |  |
| 1043703 | Oblivion Robe | mago | 3 |  |
| 1060703 | Dancer's Necklace | todas | 3 |  |
| 1080703 | Vortex Medallion | guerreiro/arqueiro | 3 |  |
| 1080713 | Jewel of Secrets | mago | 3 |  |

## 9112 Nirvana (Nightmare) (Lv 80, grupo (4))

| Item | Nome | Classe | Atributos | Visto em |
|---|---|---|---|---|
| 2129800 | Lvl. 80 Legendary Stone | todas | 0 |  |
| 2040107 | Lvl. 7 Luck Stone | todas | 0 |  |
| 1041803 | Royal Knight Armor | guerreiro | 3 |  |
| 1042803 | Forsaken Leather Armor | arqueiro | 3 |  |
| 1043803 | Serpent’s Cursed Robe | mago | 3 |  |
| 1060803 | Ancient Gem Necklace | todas | 3 |  |
| 1080803 | Broken Eagle Eye | guerreiro/arqueiro | 3 |  |
| 1080813 | Endless Blessing Stone | mago | 3 |  |
