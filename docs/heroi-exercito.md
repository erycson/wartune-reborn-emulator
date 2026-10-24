# Herói e exército

Tropas, skills, talento, runas, montaria, estrelas (kader), destino, alma do dragão, cartas de poder
e pets. Fonte de cada resposta: *(visto)* = captura oficial, *(cliente)* = código do cliente
(inglês: `D:/xampp/htdocs/wartune/decomp/2/scripts`), *(dedução)* = sem captura nem código, marcado `ponytail:`.
As capturas só têm pacotes S>C; os campos dos pedidos vêm do cliente.

Código: `game/handlers/army.py`, `hero.py`, `stars.py`, `systems.py`, `pets.py`; regras puras em
`game/rules.py`; mensagens em `game/builders/army.py` e `builders/login.py`.
Testes: `tests/game/test_heroi_exercito.py`.

## Estado

| Tabela | O que guarda |
|---|---|
| `pawns` | uma linha por tipo de tropa: castelo, exército, especialidade, bênção, posição |
| `stars` | estrelas: sacola (0 temporária, 1 mochila, 2 equipadas), posição, grau, EXP, trava |
| `pets` | pets: pontos, aptidões, batalha, skills, atalhos, ordem |
| `player_systems` | uma linha por personagem: montaria, destino, dragão, cristais/moeda das estrelas, cartas, vagas de pet |
| `heroes` (colunas novas) | talento, runas, segundo conjunto de skills |

Migração: `0003_tropas_estrelas_pets_e_sistemas_do_heroi` (quem integrar renumera, se outro ramo
também criou uma 0003). `CharacterService.snapshot` cria `player_systems` em memória quando falta;
ela é gravada no primeiro `save` que a inclui.

## Vida do herói e poções

`heroes.hp` (migração 0059) é a vida atual do líder; 0 = cheia. A luta da campanha e da cidade externa começa com
ela (`player_hero`). Depois da luta a vida fica no que sobrou, e a derrota deixa 1 (*visto*
`oficial_20261023-153200-1` #774, sem reserva). Então a reserva das poções (`blood`) completa a vida
(`rules.heal_hero`): 529 em cada derrota (9471 -> 7884), com o 83 "Used HP pack to restore HP." logo depois do
4103. A reserva também cura na compra (5633: 109, 113, 170, 111 "Purchase Successful!", 83; #803-#807), no uso
da poção da mochila (*dedução*) e ao vestir um item que sobe a vida máxima (#2182-#2185: 3, 83, 150; 120 de
reserva). Subir de nível enche a vida de graça (#2132). Abaixo de `game_settings.hero_free_heal_grade` (10) a vida
volta cheia sem reserva: no tutorial o herói chega a 0 e volta cheio, e o cliente (`BaseManager.showAlertTip`) só
avisa da falta de poção a partir do nível 10. Arena, carruagem e ilha dos pets seguem com a vida própria.

## Atributos do herói

`rules.leader_stats` = herói + equipamentos + **estrelas equipadas** (coluna × grau) + **montaria**
(template + 5 × grau de cada atributo, UpGrade Types 18; bate com o login: 1610 de EXP = 65 de força).
Talento, runas, destino, dragão e cartas são skills/buffs nos templates, não atributo fixo.

**Para a batalha:** `rules.battle_pawn(snap, templates) -> (linha de PawnTempInfos, quantidade) | None`
devolve a tropa que luta com o herói. Os atributos de cada soldado são as colunas Attack, Defence,
MagicAttack, MagicDefence, Live, ForceHit e Parry do template (o mesmo que vai em `pawnLive`).
O `battle.py` lê (pilhas, talento, runas e destino: [batalha.md](batalha.md)). Poder de combate (150) = `PhyAttack + PhyDefence + 1,05 × MagicAttack + MagicDefence + ForceHit + Parry + ConatArmy + Live/5`, sem a tropa: **visto** em 20 valores da maga no tutorial_en; o ×1,05 nas outras classes é **dedução**.

## Opcodes

### Tropas

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 5155 recrutar | 109, 112 (missões), 109, 100, 111 | visto (inglesa #653-#659) | ouro = ⌈n·GoldConsume·(100−Property4 do quartel)/100⌉; quartel ≥ NeedBuilding; população da casa (1201) |
| 5156 pôr no exército | 150, 93, 100 | visto | um slot; total ≤ liderança (ConatArmy) |
| 5157 dispensar | 100, 109 | dedução | |
| 5158 evoluir | 3, 116, 150, 109 (+112) | visto | Ruh de UpGrade Types 1; quartel ≥ nível seguinte; nível < herói − 3 |
| 8580 trocar tipo | 3, 116, 116, 150 | cliente | 200 diamantes (payType 3 = vinculado) ou 2M de Ruh |
| 8455 compreender | 3, 116 (+112) | cliente | 1M de Ruh; sorteio por TakeRandom até o grau atual (**dedução**); bênção Types 16 cheia = só especialidades do grau acima, até o 10 (`PawnSpecialAbilityFrame.helpContent` inglês) |
| 8456 salvar especialidade | 116, 150 | cliente | subir de grau zera a bênção ("Blessing levels are reset after each specialty level upgrade") |
| 8276 formação | 150 (+112, missão 34) | visto + cliente | herói e tropa na fileira 1 (frente) ou 3 (trás): `AllocateView` "fightPos must be 1 or 3". Na luta (157) o herói fica no meio da fileira dele (pos 3 + fightPos: 4 ou 6) e as duas pilhas da tropa em cima e embaixo da dela (fightPos e fightPos + 6: 3/9 ou 1/7): tutorial_en #727 (herói 1, tropa 3) e oficial_20261023-171155-1, 25 lutas (herói 3, tropa 1); `outer_city.hero_pos` e `army_soldiers` |
| 8277 / 8278 formação de campanha | 4186 | cliente | só a posição do próprio herói (dedução: salas) |
| 8326 teleporte | 140, 4237, 111 (3 pagando com diamantes) / 4263 | visto | 100 de energia ou 100 diamantes; o exército fica no tile (`handlers/outer_city.py`) |
| 8328 posição do exército | 4241 | cliente | |

### Herói, skills, talento, runas

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 5185 aprender skill/talento | 150, 60 | visto (inglesa #1141-#1143) | pontos = nível/2 − graus gastos; talento por TalentTempInfos |
| 5184 resetar skills | 61, 150 (+3) | cliente | grátis abaixo do 25; talento (type 1) 895 diamantes (`TalentView` inglês) |
| 5187 subir talento | 4430, 4431, 3, 109 | cliente | ouro e EXP do jogador (dedução: desconta gp e totalGp) |
| 8479 abrir 2º conjunto | 150, 3 | cliente | nível 38 (`SkillView`: `grades >= 38`); Second_SkillPoint diamantes (995) |
| 8480 trocar conjunto | 150 | cliente | |
| 5170 redistribuir atributos | 150 | cliente | os pontos são automáticos por nível: sem efeito |
| 5018 caixa de novato | — | cliente | o cliente nunca chama: só log |
| 8548 luta de guerra de guildas | — | cliente | depende de GvG: só log |
| 8605 runas | 115, 4495, 150 (op 3: só 4495) | cliente | op 1 aprende (livro SonType 302), 2 sobe (item 3020010 = 50 EXP, ou diamante: 50 + 10 × usos do dia e 20 EXP, `RuneUpgradeView` inglês; o `count` do 4495 e o `upRuneByPointTimes` do 4202 levam os usos; sem o bônus 2x–20x, **sem dado**), 3 equipa (2 espaços no 40) |

### Estrelas (kader) — `stars.py`, captura `kader_sistemi.json`

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 8269 sortear | 109, 3, 4180 | visto | cristais 4000/5000/6000/8000/10000 de ouro, cada sorteio dá 1–5 StarPoint (`MakeStarView` inglês; o grátis também: **dedução**); 1 grátis por dia; cristal usado apaga (o 0 nunca); -1 = rápido (≥ 20000 de ouro). **Chances e abertura do próximo cristal: dedução** |
| 8268 recolher/vender | 109 + 4179 (vendidas, bagType −1), 4178 + 4179 (recolhidas), 3 | visto + cliente inglês | `dropsite` = posição com `way` 1 recolhe e 2 vende (`StarIconView`); −2 recolhe todas (`StarModel` "Collect all"); −1 vende as de `Profile <= way`, grau 1 e gp 0 (venda rápida); lixo (Profile 1) sempre vende por SellGold; o Energine (6) vai para a mochila e só serve de comida de EXP |
| 8267 mover/equipar/devorar | 4178 (+150) | visto | equipadas: min(8, nível/10), sem repetir MasterType; `eat` = destino devora a movida |
| 8331 compor | 109, 4479 (temporária) / 4178 (mochila) | visto | devora tudo que não está travado nem no grau 10, o Energine também (`HoroscopeFrame`); EXP = SellGp + graus + gp; tabela por Profile (Types 9-13, 22), grau máx. 10 |
| 8330 travar | 4180 / 4178 (+112) | cliente | missão 53 |
| 8270 comprar espaço | 3 | cliente | uma linha de 4: (comprados/4 + 1) × 395 diamantes, até 16 espaços (`StarManager.sendBagCellBuy`, `PlayerStarListView`) |
| 8325 virada do dia | 3 | cliente | renova o sorteio grátis |
| 8341 loja | 4178, 3 | cliente | preço = StarPoint do template |
| 8224 `star` | 4178, 4180 | visto (só turco: login.json #51-52; a inglesa #49 só traz o 4180) | |

### Montaria, destino, dragão, cartas — `systems.py`

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 8530 lista | 4427, 4426 | visto (inglesa #19-#20 só traz o 4427; o 4426 é só turco: login.json #11-12) | soulScore = soma de SoulScore |
| 8529 op 1 treinar | 115, 3, 150, 4426 | visto | `propertyType` 0 força, 2 int., 5 físico, 1 agilidade (PropertyInfo); `param1` unidades: chicotes 208017 primeiro, o resto Mount_Point (35) diamantes cada, `payType` 0 aceita vinculados (`MountsFrame` inglês, `mounts.tips02`); 10 de EXP cada; teto = grau levelMax |
| 8529 op 2 escolher | 4426, 150 | cliente | precisa possuir |
| 8529 op 3 montar/descansar | 150 | cliente inglês | `MountsFrame` Mount (`param1` 1) / Rest (0); descansando o 150 vai com `mountTempId` 0 explícito (`hasMountTempId`); guardado em `events` `mount:rest` |
| 8529 op 5 ver de outro | 4459 | cliente | só jogador online |
| 8529 op 4 ativar | 115, 3, 4427 | cliente inglês | `WildSoulFrame`: só `MountType` 1, 2 e 4 trancadas e com `NeedMountGrade` ≤ Beast Soul Lvl (tabela 19 de `UpGradeTempInfos`: maior `Grades` com `Data` ≤ `mountTotalGp`, `MountInfo.growExp`). Com a carta (`NeedItemId`; o tipo 4 usa `mount_king_active_item` "2131500,1") gasta a carta e vale os dias dela (`Property2`, −1 = permanente); sem a carta, `Property1` Balens, permanente (`payType` 0 aceita vinculados) |
| 8529 op 13 voo | 115, 4427 | cliente inglês | `MountsFrame.notFlyMountBtn`: montaria possuída, `IsFly` 0 e sem voo comprado; gasta 1 Flystone (208131); vai no `AvatarInfoMsg.isBuyFly` |
| 5006 carta de montaria (SonType 218) | 115, 4427 | cliente inglês | `Property1` montaria, `Property2` dias (−1 permanente), `Property3` Beast Soul Lvl. Temporária soma dias; já permanente recusa |
| treino que sobe o Beast Soul Lvl | + 4427 | template | dá a `ActiveObject` dos níveis alcançados (1006 no 2, 2001 no 3) |
| 8529 op 6 estrela | 115, 4679 (+4426, 150 na montaria em uso) | cliente inglês | `MountsPromotionView`: a montaria vai no `propertyType`; `param1` 0 = 1 refino com 1 Mount Hoof (208035), 1 = 10 refinos com 10. Herói nível 70, montaria possuída e permanente, `MountType` ≠ 3 e 4 (`canShowStar`), abaixo da estrela máxima (tamanho do `StarAddition`). Bênção até a próxima estrela: `UpGradeTempInfo` tipo 37 com `TemplateId` = `GradeType` (50, 100, 200, 200, 250); cheia sobe e volta a 0. A estrela soma `StarAddition[estrela − 1]` nos 4 atributos (`rules.mount_stats`). O primeiro refino de quem nunca refinou não gasta Hoof (`firstBless`). Bênção por refino (10) e chance de "Therion's Blessing" (5%, o número que o `getPromotSuccessRate` mostra) são **ponytail**; gravado em `player_systems.mount_stars` (migração 0050) |
| 8529 ops 7–12 | — | **sem tela** | 7 rei: o cliente inglês não tem `MountType` 4, tabela 109 nem o item 2131500, e a lista do rei não tem ouvinte; 8–11 loja: nenhum chamador (o botão abre a loja 1002 comum e fica fora da tela); 12 refino da alma: botão fora da tela, item 208070 e tabelas 144–146 ausentes. O 4426 manda sempre os graus de refino 0: outro valor quebra o `MountsFrame` (falta a tabela 144) |
| 8843 evento de montaria | — | **sem resposta** | `MountActSocketOutManager.sendGetMountActInfo`: corpo vazio, sem chamador e sem código de resposta no cliente inglês |
| 8628 destino | 4544 | visto (inglesa #42, vazio no nível 1; os tipos só turco: login.json #34) | abre no 55 com os tipos 2000 e 3000; 2100/2200: não sabemos abrir |
| 8626 treinar destino | 115, 4544 | cliente | pedras SonType 307; **1 EXP por pedra: dedução**; graus por Types 26 (acumulado) |
| 8627 roda | 4545, 115 (+3) | cliente | Fate_FreeCount grátis, depois 10, 20, 30… e 300 do 30º; prêmios 1/2/3/4/10 pedras com pesos das fatias (dedução) |
| 8642 dragão | 4555 | visto (só turco: login.json #37) | abre no 40 |
| 8641 alimentar | 115, 4555 | cliente | item SonType 319, 1 EXP; Types 101 por grau; grau máx. pelo nível (40→1 … 80→5) |
| 8643 transferência | 4556, 4557 | cliente | grau 5 → tipo 102; **vocação: parcial** |
| 9505 cartas | 4905 | visto (só turco: login.json #76) | op 1 sobe (Types 29+Profile), 2 ativa todas, 3 reenvia; buf = BufId + grau − 1; depois do 4905 vai o 4902. 4903: os buffs do tipo do lugar, na entrada da masmorra (depois do 3: 4902, 150, 4903), vazio na saída e no login. **Cartas/EXP vêm das batalhas: parcial** |
| 4905 `bufInfos` (bônus da coleção) | — | visto + cliente + dedução | 3 degraus por coleção (`MagicCardSlotView`); o degrau k usa `Template{3+k}s` (sonType) e `Property{3+k}` (bufId) da `PowCardSuiteTemInfos`, com `fixvalue`/`percent` da linha. Aceso quando há [cartas, grau mínimo] = `powcard_suite_slots` (game_settings, 0037; padrão 4/1, 4/3, 4/8). Fontes: login.json #76 (só turco; só a 1002, com 4 cartas, tem 40001; as de 3 cartas nada) e o language EN `card.CardSlotView.Notactive0..2` ("4 cards", "3 level 4 cards", "8 level 4 cards"). A leitura dos graus 3 e 8 é **dedução**. O bônus ainda não entra na batalha (`battle.py`) |
| 8224 `powcardInfo` | 4905 | visto | |

### Pets — `pets.py`

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 8621 op 2 pontos | 4540 | cliente | soma ≤ pontos livres (5 por nível: `PetData.remainPoint`) |
| 8621 op 3 zerar | 4540, 3 | cliente | pet_reset_att diamantes |
| 8621 op 9 / 10 batalha / descanso | 4540 | cliente inglês | um pet na batalha; ativar pede o `NeedGrade` do template e nível do pet ≤ herói ("Active Sylph level cannot exceed character level!") e vincula o pet ("Active Sylphs become bound") |
| 8621 op 1 devorar | 4540 (+115 com a pedra; 3, 4152, 83 com Balens) | cliente inglês | `PetSwallowView`: o principal ganha 50% da EXP total do secundário (`value`), ou 100% com `payType` 1 (swallow_fullgp_points 295 Balens), 2 (vinculados primeiro) ou 3 (uma Heritage Stone 208029). Recusa secundário em batalha, com equipamento ou na equipe do Sylph Arena, principal com EXP cheia ou nada a ganhar. O secundário vai com `isDel`; o principal fica vinculado |
| 8621 op 6 sacrifício | 4540, 115, 109 | cliente inglês | `PetShowView.getSacrificeTip`: Sylph Sepulcrum (3040001) pela estrela (`(Quality − 1) / 5 + 1`): 1 → 1, 2 → 2~3, 3+ → 16·10ⁿ⁻³~20·10ⁿ⁻³ (sorteio uniforme, **dedução**). Recusa em batalha, na equipe do Sylph Arena, com equipamento e o último pet ("Cannot sacrifice your last Sylph") |
| 8621 op 11 atalhos | 4540 | dedução | string em `petName` |
| 8621 op 12 vaga | 4540, 3 | cliente inglês | `value` vagas; cada uma min(a + k × b, c) de add_pet_count "100,100,300" (k = já compradas, `PetListView.openPos`); base 6, teto 12 (`PetData.petCarryLimit`) |
| 8621 op 14 topo | 4540 | cliente | |
| 8621 op 13 compor (um pet) | 4540, 115, 109 | cliente + template | receita de `PetComponseInfos` com `Pet2Types` 0 casa com (`PetType`, `NeedGrade` = tier, `Quality` = estrela) do template do pet; o template passa a ser o do resultado; gasta `NeedItemTempId*` e `NeedGold`. Nível, EXP, pontos, aptidões, skills e qualidade ficam (**dedução**). Trava do `PetComposeView.checkCanComposeAndTip`: herói nível 60; NeedGrade 1 de cor 4 ou 5, NeedGrade 2 só cor 5; NeedGrade 3 e o legado 50 não (o `canComposePet` do NeedGrade 50 não tem chamador). A leitura família = template é **dedução**, falta captura. 24 de 28 receitas; 19, 26, 29 e 32 dão tipos 117–119, sem template: recusadas |
| 8621 op 15 fusão de dois pets | — | template | as 6 receitas dão tipos 117–119 e pedem itens (2125126, 2125127, 2125128, 2125130, 2125134) que não estão em `ItemTempInfos`: sem resposta (log) |
| 8621 op 4 avanço | 4540 (+115, 3) | cliente inglês | `PetAdvancedView` (o `trainGrowthRate` é o avanço de qualidade): `value` 1–9999 unidades, `payType` 0 aceita vinculados. Cada unidade dá 10 de EXP de qualidade (`curQualityGp`), 50 com a bênção do Sylph ("EXP x5"; chance de 10% é **ponytail**). Barra até a estrela seguinte: `UpGradeTempInfos` tipo 27 (NeedGrade 1), 29 (2) ou 107 (3), `Data` da estrela `quality + 1`; cheia sobe e o resto fica (**dedução**); sem estrela seguinte: "Blessing full". Gasta Mahra (208023; Adv. Mahra 208045 no NeedGrade 3) primeiro, o resto a 35 Balens (`pet_up_quality` / `pet_up_qualityupgrade`); sem saldo, recusa. Estrela e cor: `tempToQuality`/`tempToStar`; na cor nova vira o template da cor (**dedução**); `growthRate` = `calculateCoeLimit` (`pets.coe_limit`). Vinculado gasto vincula o pet |
| 8621 op 7 encantar | 4540, 115 | cliente inglês | `PetStrengthenView`: `value` Sylph Sepulcrum (3040001; Adv. Sepulcrum 3040002 no NeedGrade 3), sem Balens; cada um melhora uma aptidão sorteada abaixo do teto (`calculateCoeLimit` do máximo de `PowerApt`… na estrela). Quanto sobe (1–10) é **ponytail**. Recusa sem itens ou com as 4 no teto ("Attributes maxed") |
| 8621 op 5 aprender skill | 4540 (+115, 3) | cliente inglês | `PetLearnSkillView`. `value` 1: `skillId` de um livro (SonType 303, `Property1`); com o livro gasta o livro, sem ele paga a loja de livros (`ShopTempInfos` Area 7, Point + GiftToken). `value` 2: sorteio entre as skills dos livros (uniforme, **ponytail**), grátis a cada `pet_learn_random_skill_interval` (480) minutos menos o VIP 205, senão `pet_learn_random_skill` (100) Balens; `lastFreeSkillLearnTime` no 3 (`player_systems.pet_free_skill_at`). Skill do tipo do pet ou 107, `NeedPlayerGrade` até o herói, não aprendida. 5 ativas e 3 passivas; cheio troca uma do mesmo tipo sorteada no mesmo lugar (os `chaSkillIndexs` valem); o `fastKey` leva o SonType de toda ativa |
| 8621 ops 8, 15 | — | **sem tela** | 8 (`trainResistance`) e 15 (`mixDoublePet`) não têm chamador no cliente inglês. Esquecer skill e renomear não usam o 8621 (esquecer não existe no build; renomear é HTTP + AMF `renamePet`) |
| 8726 skills do torneio | 4540 | cliente inglês | `chaSkillIndexs`: 3 índices em `changeSkills` (−1 vazio), sem repetir (`PetChallengeTeamItemView`); gravado em `pets.cha_skills` |
| 8702 pets de outro | 4608 | cliente | só jogador online |
| login (8224 `army`) | 4540 | visto (só turco: login.json #30) | só quando há pet |

Atributos do pet (cliente inglês `PetData`): template + ⌊(nível − 1) × growthRate / 80⌋ + pontos; HP =
MaxHp + ⌊6 × físico × aptidão de físico / 1000⌋ + `bagLiving` (o HP do equipamento de mascote, bolsa 26, ver
[itens.md](itens.md)). O `growthRate` mandado é o gravado; o cliente interpola o da qualidade (`calculateCoeLimit`),
**dedução**.

EXP do pet: `pets.gp` é a total (`totalGp`, `PetData.totalExp`); `curGp` é a de dentro do nível (`curExp`). Tabela
25 de `UpGradeTempInfos`: o `Data` de cada nível é a EXP do anterior até ele (2 = 3000, 3 = 4000…), como a do
jogador. O nível não passa do herói ("A Sylph cannot exceed player's level") e, no teto, a EXP para no `Data` do
próximo (`PetData.isFullExp`).

## Carga do login

Enviados: 100 (tropas, no `user`), 150 com `mountTempId` e o pet em batalha (`petTempId`, `petQuqlity`, `petName`, como no login.json #5, só turco), 4540 (flag `army`, só com pet), 4178 + 4180 (`star`), 4905 (`powcardInfo`); 4427/4426, 4544 e 4555 respondem aos pedidos 8530, 8628 e 8642 que o cliente faz sozinho. O sorteio grátis das estrelas vira às 5h e é recalculado em toda leitura (`rules.refresh_star_day`), então quem estava offline no 8325 não perde.

Não enviados: 4495 do login (só turco: login.json #40 é `{opType 0, opResult false, count 0}`; o `ArmyManager.__runeOperateHandler` não faz nada com isso). O 4902 (`systems.fight_add_msg`) sai antes do 150 do próprio exército de quem tem cartas (`GameSession.send`; só turco: 61 dos 83 150 das capturas, login #3, teknoloji_upgrade #4, envanterden_item_kusanma #2). Sem ele (`cards=False`): o 150 logo depois do 154 da luta, os dois da saída da campanha, o da poção de HP e o da tecnologia de tropa. O valor: por campType (CampaignBufferTemps.Types 800-807), a soma dos buffs das cartas e das coleções com a fórmula do `fighting_capacity`; 608/768/1521 batem exatos. O cliente só mostra na dica do botão das cartas (EquipView, `getFightText`).

## Dependências

- Ganhar montaria, pet e cartas: uso de item / missões / batalha (outros módulos).
- Batalha: dragão e cartas (buffer 3040/3041 sem template): **precisa de captura**.
- **Captura que falta (cartas)**: uma conta com as 4 cartas de uma coleção em graus diferentes (todas no 3+, depois
  todas no 8+ ou 6+): gravar o 4905 depois de cada subida (9505 op 1) para fechar quando o 2º e o 3º degrau acendem.
- `castle_yield` usa `rules.population` (sobrepõe com o módulo do castelo).
