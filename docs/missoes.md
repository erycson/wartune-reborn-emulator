# Missões: como o servidor conta o progresso

Missões são `QuestTemps` (título, recompensa, janela) com uma ou mais linhas em `QuestCondictionInfos` (condições). Fontes do que está aqui: `data/templates/tempinfos.xml` (inglês), o cliente decompilado (`TaskTemplate.as`, `SpaceArmyViewHelper.as`, `SpaceDialogFrame.as`, `TaskMobilePhoneView.as`, `DesktopManager.as`) e as capturas. Código: `src/wartune_server/game/rules.py`, `handlers/player.py` (5012 e 5014), `builders/player.py` (112).

## Fluxo no servidor

1. **Aceite (5012)**: `quest_add` chama `rules.accept_quest`, que confere o que o cliente confere antes de aceitar (`TaskManage.isAvailableTask`, em `rules.can_accept`): janela `StartDate`..`EndDate`, `NeedMinLevel`..`NeedMaxLevel`, `IsLeague` (exige guilda) e `PreQuestId` (lista com vírgula é E; pré-requisito que não existe nos dados é ignorado). Missão já aberta não reabre. Repetível (`IsRepeat`) concluída reabre na mesma linha, só quando o dia do jogo mudou (o dia vira às 5h, como `checkInRepeatTime`). Depois roda as condições de tutorial (23), de prédio (2) e de estado (bolsa, mapa da cidade, símbolos). Missões de conversa (85) são conferidas aqui também. O aceite devolve também as missões que ele mudou (tutorial, prédio, estado): o 5012 grava e manda o 112 de todas, não só da aceita.
2. **Progresso**: cada ação chama `rules.quest_event(snap, templates, tipo, para1, valor)`. Em cada missão aberta, cada linha com `CondictionType == tipo` e `Para1` igual (0 = qualquer) avança o contador da sua posição. Depois grava e manda o 112.
3. **Conclusão (5014)**: `quest_finish` atualiza o estado (mapa, símbolos, social) e `rules.quest_done(snap, templates, q, agora)` confere. Se alguma condição não bate, responde o 112 com o progresso atual (`isComplete` falso, sem 52). Se bate, confere se a recompensa cabe depois de tirar o que a entrega consome, consome, paga a recompensa (`rules.pay_quest_rewards`), grava tudo de uma vez e manda os pacotes na ordem do oficial inglês (seção "Ordem da entrega" abaixo).
4. **Missão que nasce com o personagem**: `services/characters.starting_quests` (missão de tutorial, tipo 23, sem pré-requisito e com `NeedMinLevel` 1: nos dados só a 10) é gravada no registro, com `addDate` = hora da criação. (visto) captura EN #81: a 10 vem no 112 do login com `addDate` 18:21:49, antes do primeiro login do socket (18:24:23), e o cliente nunca manda o 5012 dela. As outras missões têm `addDate` = hora do aceite (a 30 nasce no mesmo segundo do `completedDate` da 10, #213/#224). Personagem antigo sem a 10 continua recebendo pelo 5012 do cliente (`IsAuto`).

## Várias condições (condition_1..4)

- Cada linha de `QuestCondictionInfos` é uma condição. A N-ésima linha, na ordem do XML, é o `condition_N` do 112 (`builders/player.quest_info`).
- O cliente faz o mesmo (visto no cliente: `TaskTemplate.addConditionList` monta a lista na ordem do arquivo; `checkCount(cond, idx)` lê `taskInfo["condition" + (idx + 1)]`; `isCompleted` só fica pronto quando todas as linhas estão prontas). Por isso o servidor também conclui só com todas.
- Sete missões têm mais de uma linha: 8 e 13 (4 linhas tipo 27), 240 (3 tipo 25), 450 e 730 (2 tipo 25), 680 (3 tipo 28) e 764 (tipo 3 e tipo 10). Nenhuma passa de 4 linhas (teste em `tests/game/test_missoes_condicoes.py`).
- Contadores: `quests.progress` (condition_1) e `progress_2`, `progress_3`, `progress_4` (migração `0022_progresso_das_condicoes_da_missao`). Antes só o primeiro contador existia e `templates.get` devolvia só a primeira linha: a 764, por exemplo, concluía só com o recrutamento e ignorava o nível da tropa.

## Como cada tipo é contado

- **Contador (soma)**: cada ação soma `valor`. Ex.: 3 (recrutar), 7 (ocupar), 34 (formação), 52, 53.
- **Maior valor**: tipo 10 (nível da tropa), via `LEVEL_CONDITIONS`.
- **Estado, lido na conclusão**: tipo 1 (nível do personagem) e 39 (dia do login). Não gravam progresso; `quest_done` lê o snapshot na hora.
- **Estado, gravado quando muda**: tipo 23 (passo do tutorial, no aceite e quando o guia avança) e tipo 2 (nível do prédio, no aceite e quando o prédio sobe).
- **Conversa**: tipo 85, marcado uma vez quando o jogador fala com o NPC perto dele.
- **Bolsa (quantidade atual)**: tipos 27, 28, 32 e 49. No cliente é `checkGoodsCount`, a quantidade do item `Para1` na bolsa `>= Para2`. O servidor confere a quantidade atual do item na mochila (`rules.goods_count`, só `BagType.BAG`, como `GoodsManager.countGoods`) na entrega, mas não grava no `condition_N`, que fica em 0. (visto) captura EN: a 90 e a 102 só têm 112 com 0 (aceite #1140 e #1800, conclusão #1572 e #2081), e os drops do Worg Tooth (#1276, #1408) não mandam 112. Na entrega, a condição consome o item (abaixo).
- **Tutorial (23)**: no aceite e quando o guia passa do `Para1`, o `condition_N` vira o `Para2` (1, captura EN #205). Na entrega vira o `noviceProcess` de agora (#211: 12000 na 10; #483: 18500 na 45), em `rules.finish_progress`.
- **Estado de mapa e de símbolo (37, 76, 77, 78)**: `update_state_quests` julga pelo que já existe (`checkMapId`, `checkRuneStudy`, `checkRuneGrade`), então quem aceita depois do fato já nasce com o progresso.

## Entrega (5014)

- **Reavaliação**: os três caminhos do cliente que mandam o 5014 (`TaskFrameII.as:590`, `TaskTraceItem.as:583`, `CompleteTaskTip.as:115`) só agem com `isCompleted` local. Por isso o servidor reavalia no 5014 e conclui quando a condição bate, sem guardar "entrega pendente". (visto) captura: 70, 80 e 82 chegam com o contador cumprido e `isComplete` falso no 112, e a conclusão aparece depois do 5014. A ordem entre pacotes S>C e C>S não é confiável (o S>C atrasa de 2 a 110 linhas), então isso é a ordem observada, não prova de causa.
- **Recusa**: sem a condição, o 5014 responde o 112 com o progresso atual (na bolsa, 0), `isComplete` falso e sem 52. Antes a resposta era silêncio, e o botão de entrega ficava sem retorno.
- **Consumo de bolsa**: a entrega tira da mochila o `Para1` de cada condição de bolsa (`rules.goods_to_take`). Item de missão (`SonType` 210, como o 2100001) sai inteiro: (visto) inglesa #1570, a pilha do 2100001 foi de 10 para zero ao entregar a 90, cuja condição pede 8. Os demais tiram só `Para2` (o 2125010, `SonType` 201, da 9): (dedução) a captura não cobre esse caso; se o oficial tirar tudo, muda uma linha em `goods_to_take`. Testes: `test_entrega_gasta_so_a_quantidade_pedida_fora_do_item_de_missao` e `test_entrega_de_item_comum_deixa_o_resto_na_bolsa`.
- **Mochila**: a conferência é feita numa cópia, depois de tirar o que a entrega consome (`bag.fits`: casa livre ou pilha do mesmo item com espaço). Se a recompensa não couber, aviso 111 "Inventory Full" e recusa sem consumir nada. (dedução) A captura EN não tem mochila cheia na entrega: o texto é o do `language.txt` inglês na chave `ConsortiaCaseCellClickMediator.command01`.

### Ordem da entrega

(visto) captura EN, as 19 entregas (10 a 130): #210-#218, #482-#507, #1569-#1576, #2077-#2085, #2242-#2265.

1. 112 do progresso (`isComplete` falso), **só** quando a missão tem condição de tipo 23, 2, 10, 21, 29 ou 51 (`rules.PROGRESS_BEFORE_FINISH`; os três últimos de oficial_20261023-171155-1: 200 #4274, 221 #4978, 819 #5889). Nos tipos 3, 7, 8, 14, 20, 22, 26, 27, 32 e 42 o oficial não manda (52 #700, 60 #834, 70 #1129, 110 #2242; 765, 271, 220, 210, 190, 763 na oficial).
2. 115 do que a entrega gasta (bolsa: 90 #1570, 102 #2079).
3. 3 já com o bit da missão no `questSite`, mas antes da recompensa (gp e strategy antigos).
4. 112 concluída (`condition` da bolsa em 0; tipo 3 guarda a soma: 52 = 900, 110 = 460). O tipo 22 (estar em guilda) nunca conta: `condition_1` 0 na entrada e na entrega (oficial #4218, #4919); `quest_done` confere a guilda na hora.
5. 3 só com a `RewardStrategy` paga, quando há (90 #1573, 101 #2183); o EXP vem no 3 seguinte.
6. 109 quando a recompensa tem ouro ou cristal.
7. 150 **só** quando sobe de nível (50, 52, 60, 80, 90, 100, 102 não mandam).
8. 3 com tudo pago.
9. 115 dos itens ganhos (45 #489, 110 #2250).
10. Um 111 "Received: <nome> x<n>" com todos os itens separados por ", " (#504, #2262; vários itens: oficial #4994 "Received: Moderate Stamina Potion x1, Skeleton Key x1").
11. 4152 do leed 20 quando a missão é diária (`TemplateType` 1; oficial #6042, #7808).
12. 52.
13. 83 "Received 3,000 EXP " (vírgula de milhar e espaço no fim) e o 83 com o mesmo texto do 111.

Na subida de nível da entrega (`player.push_level`, (visto) tutorial_en): o exército completa com
as tropas do castelo até a nova liderança (+10 no mago); com o castelo já criado (8281) vão 139 se o castelo não tem
tropa para completar, 100 (tropas do castelo), o 150 e 4640 quando o nível chega ao `openGrades` do fundo de novato
(6). Fora: 4638 (guia de 7 dias, na missão 130) e 4476/4484 (atividades e títulos).
- **Sem linha de condição**: a missão não conclui (`quest_done` devolve falso). Nenhuma missão dos dados está assim; o caso existe para id inexistente.

## Recompensas (5014)

- **Paga** (`rules.pay_quest_rewards`, como `TaskRewardViewII._rewardList`): EXP `RewardPlayGP` (com o bônus diário `(nível - NeedMinLevel) * 500` quando `TemplateType` é 1), ouro `RewardGold`, `RewardStrategy` (ruh, `Character.strategy`), `RewardCrystal` (`Character.crystals`), `RewardPlayerOffer` (oferta do personagem), `RewardConsortiaOffer` (oferta da guilda, creditada na guilda do jogador; sem guilda não há onde pôr) e os `QuestGoods`, que entram na mochila pelo `bag.add` (empilham até `MaxCount`; equipamento ganha `joins`), não por `pay_quest_rewards`. Ouro ou cristal na recompensa disparam o 109 (`castle_yield`).
- **Não paga**: `RewardMoney` (só a 1, vencida, e a tela não mostra), `RewardHeroGP` e `RewardDower` (0 em todas as linhas).
- Exemplo: 241 (diária, `TemplateType` 1) com nível 28 dá 12000 + (28 - 20) * 500 = 16000 de EXP.

## Tipos ligados nesta rodada (login-diversos-regras)

### Tipo 1: nível do jogador

- Verificado (cliente: `checkPlayerGrades`): `thane.grades >= Para2`. Não usa Para1 e não é "Collect Reward": esse título é só da missão 7. Os 30 tipos 1 são quase todos "Lv.N" (11 Lv.20, 12 Lv.30, 905 Lv.35, 752 e seguintes Lv.40 a Lv.80).
- Servidor: `quest_done` compara `snap.character.grades >= Para2` na conclusão. Não grava progresso e não precisa de hook no `add_gp`, porque o nível do personagem é o estado real.
- Missão 7 ("New Year's Arrival", Para2 = 1): antes concluível por quem mandasse 5012 e 5014, porque o servidor não conferia a janela. Agora o aceite confere a janela (`rules.can_accept`): `StartDate` e `EndDate` são 2000-01-01, então o 5012 é recusado, como o cliente, que a esconde. O evento de 2012 não é mais dado.
- Teste: `test_nivel_do_jogador_conclui_pelo_nivel_de_agora` (missão 11, nível 19 recusa, 20 conclui).

### Tipo 39: entrar no segundo dia

- Verificado (cliente: `checkSencondLogin`): o dia do aceite é diferente do dia atual.
- Servidor: `quest_done` compara a data UTC de `added_at` com a data UTC de agora (o `addDate` do 112 sai em UTC). Vale no próximo 5014, então um relogin já conta sem código extra.
- Dedução: o cliente compara o dia local. Se o fuso importar, trocar por um fuso fixo.
- Missão 5 ("Secondary Login", 50000 de ouro). Teste: `test_segundo_dia_de_login_conclui_missao_5`.

### Tipo 85: falar com o NPC

- Verificado (cliente): o diálogo de NPC é local (`SpaceDialogFrame`). Ao chegar na última página, o cliente aceita a missão (5012, `requestAcceptTask`) e marca `finishStory`, sem pacote para o fim do diálogo.
- Verificado (cliente): clicar num nó manda o 8692 (`SimplePropertyMsg`, `param1` = nó), exceto quando `MasterType == 1` (`SpaceArmyViewHelper.nodeTrigger` só dispara `SELECT_NODE`, sem pacote).
- Para1 = 0 e Para4 = `"10000,nó"` (mapa e nó do NPC). Exemplo: missão 361 (Dinah) = `10000,2`; missão 174 (Priest) = `10000,9`.
- Servidor: o 8692 perto do nó (`space.talk`) marca as missões abertas com esse alvo; o aceite (5012) perto do nó marca as recém aceitas. Perto = `_near` do 8692 (alcance do nó + 5).
- Limite (cliente: `TaskManage.requestCanAcceptTask`, `SpaceDialogFrame.storyTaskNextStep`): as 10 missões de conversa têm `IsAuto = true`, então o cliente costuma aceitá-las sozinho logo depois da anterior, longe do NPC; o 5012 do último passo do diálogo só sai se a missão ainda não estava aceita. Para NPC de patrulha (MasterType 1: 174 e 191 Priest, 175 Guardian, 301 Berdim) nenhum pacote chega ao servidor na conversa, então essas missões ficam travadas na conclusão (já eram antes). Falta decidir: confiar no 5014 para esses quatro ou achar outro sinal.
- Ponytail: o servidor não vê o fim do diálogo. Conta o clique ou o aceite perto do nó, que são as ações reais que ele recebe.
- Capturas: não há 8692 de conversa. O único 8692 visto é um teleporte (só turco: `peri_adasi_tp.json`, nó 5). A ordem 8692 e 5012 vem só do cliente (código, não captura).
- Teste: `test_falar_com_npc_conta_no_aceite_perto_do_no` e `test_falar_com_npc_pelo_8692_so_perto_e_nao_com_quem_anda`.

### Masmorra Worg Lair (tipos 14, 25, 26, 27 e 31)

Ligados em `handlers/campaign.py` (`_battle_over`, `_dungeon_loot`, `_map_finished`) e em `rules.py`. Só a campanha 1001 tem nós e lutas no servidor. O resto da lista está na seção "Missões bloqueadas para as masmorras 1002+", abaixo.

- **Para1 em lista** (tipos 14 e 26, 17 missões: 760, 783, 784, 842, 843, 844, 845, 893, 894, 895, 896, 901, 902, 903, 904, 923, 924): `rules.para1_ids` separa por vírgula, e 0 = qualquer. Antes, `update_state_quests` fazia `int(Para1)` em toda linha, e `int("9004,9104")` derrubava o aceite da 760 (teste `test_para1_em_lista_nao_derruba_o_aceite`).
- **Tipo 14 (campanha passada)**: `Para1` = `CampaignId`. Quando um mapa da 1001 acaba (`_map_finished`: no 1011, todo o grupo de lobos caído e sem `param4`; no 1021, o chefe 102109 morto), vale `quest_event(14, 1001, 1)`. Não soma: a condição é 1 por campanha. (visto) inglesa: relatório de campanha 137 em #1098, 135 em #1102, 112 com `cond_1` = 1 em #1103 e 4165 em #1104 (missão 70).
- **Tipo 26 (chefe)**: `Para1` = template do chefe (`GameHeroTemp`, 1011 = 'Wulfgar'), `Para3` = campanha. Cada chefe do lado 2 da batalha vencida vale `quest_event(26, heroTempId, 1)`. Casa pelo template, não pelo mapa: o chefe 102109 tem `heroTempId` 1011, e a missão 80 pede 1011 (teste `test_26_chefe_pelo_template_e_nao_pelo_mapa`).
- **Tipo 25 (matar soldados)**: cada soldado do lado 2 da batalha vencida soma pelo `tempId` (`PAWN_KILL_CONDITION`). A 1001 tem o soldado 2011 do lado 2, mas nenhuma missão de 25 aponta para ela. (dedução) conta todos os soldados do lado 2 da spec, não os que o jogador viu cair.
- **Tipo 27 (bolsa)**: `goods_count` soma as pilhas do item na bolsa (`BagType.BAG`; item fora da bolsa não conta, teste `test_27_nao_conta_item_que_nao_esta_na_bolsa`). Na entrega (5014), `rules.goods_to_take` tira o item de missão (SonType 210, como o 2100001) inteiro; os demais tiram só o `Para2`. (visto) inglesa #1570: 115 com a posição esvaziada antes do 112 de conclusão da 90 (#1572), e a pilha tinha 10, enquanto o `Para2` pede 8. Tirar a pilha inteira segue a captura. (dedução) para item comum, tirar só o `Para2` não foi confirmado: a captura não cobre esse caso. Uma segunda entrega ainda não foi vista.
- **RewardStrategy**: o 5014 agora paga `RewardStrategy` (antes era ignorada). A 90 dá 1000 de Daru (template). (visto) PlayerMsg 3 sobe `strategy` 88 → 1088 entre a inglesa #1571 e #1573, com o 112 da 90 em #1572. O chefe 102109 dá +72 (só turco: replay 4103 #1711, `strategyBonus` 72; `strategy` 101000 → 101072 entre #1613 e #1710; na inglesa o 4103 #1509 traz 88).
- **Tipo 31 (cena solo)**: `Para1` = `Campaigns.Capacity`. A 1001 tem capacidade 1, e cada fim de mapa dela vale `quest_event(31, 1, 1)`. A 313 pede `Para2` 3 ("Gain passage through any dungeon three times"): fecha no servidor depois de duas partidas (dedução: cada mapa conta), mas o cliente só a oferece com a pré 310 concluída, e a 310 é do tipo 26 da campanha 1007 (sem nós). A 371 pede capacidade 2 (grupo) e não fecha com a 1001. (visto, só turco) captura `savasa_baskin_ve_elmas_ile_hizlandirma.json` #12 mostra progresso 1 em 313.

- **Pilha do drop**: o drop do nó entra por `bag.fits` + `bag.add` (como o 5006 e a loja), então o Worg Tooth (MaxCount 9999, overlay) fica numa pilha só. (visto) inglesa: id 82751 no pos 3, com 2, 4, 7 e 10 (#1205, #1265, #1343, #1397). Antes (commit 0475383) cada drop criava um item novo.
- **Lvl. 1 Luck Stone no baú**: o que não é material (SonType 210) cai num baú: 4103 com `baseItem` e `signId` (inglesa #2910: 1080011; turco: 2040101), e o C>S 5129 com o mesmo `signId` entrega (inglesa #2924-#2939: 115, 4476, 111, 83). Ver [itens.md](itens.md).
- **Ordem do fim de mapa**: 137, 4151, 83, 135, 112 (missão 70), 4165, 150, 150, 140 (inglesa #1098-#1107). O 20 de #1101 (resposta ao 5038) não faz parte do `_dungeon_end`: sai como resposta a cada 5038.
- **Entrega (5014)**: o cliente manda o 5014 só com a missão concluída no cliente (`TaskTraceItem.checkTaskComplete`, `TaskFrameII` e `CompleteTaskTip`). O servidor não conclui e responde o 112 com o progresso atual (ver Recusa na seção de entrega).
- **Guia depois da 70**: 5185 (30111) responde 60 {30111, index 2, type 0} e 5017 responde 1 (inglesa #1141-#1146; a inglesa manda também um 150 antes do 60 e um 3 antes do 1), com o herói do replay (só turco: nível 7, `30711,30811`, 1 ponto de skill). Teste `test_guia_depois_da_70_aprende_a_skill_e_avanca_o_novice`. O 8235 (leed, 5 sites) responde 4150 (inglesa #1561-#1565, com 109, 111 e 83), sem teste.

### Tipo 8: atacar castelo-robô

- Verificado (cliente): `CityInfoFrame` manda o 5160 com a posição do castelo, e a missão 100 procura o robô em (44,22) (m8, alvo 80_3).
- Servidor: `_castle_over` (handlers/outer_city.py) conta `quest_event(8, 1, 1)` na vitória. Para1 1 = vitória: 100 e 411 têm Para1 0 (qualquer), 765 tem 1.
- Dedução: a luta é a da mina (sem captura de castelo) e o ataque gasta o contador do dia. Ouro saqueado: sem fonte, sai 0.
- Premissa de desenho: o robô conta como alvo de tipo 8. Pelo dado, 100 e 411 pedem Para1 0 (qualquer alvo) e 765 pede Para1 1 (vitória), e a vitória no robô manda `quest_event(8, 1, 1)` (`_castle_over`). O texto da 100 fala em 'castelos dos jogadores próximos', e o guia 80_3 aponta para o robô. Se o desenho exigir castelo de jogador, o servidor deixa de contar o robô, e aí 100, 411 e 765 voltam a trava (falta PvP).
- Teste: `test_ataque_ao_castelo_robo_conta_a_missao_8_e_gasta_o_ataque`. Detalhes em [cidade-externa.md](cidade-externa.md).

### Tipos que não foram ligados

- **8 (Plunder a City)**: ligado ao castelo-robô (seção *Tipo 8* acima). O `5160` ataca mina livre contra o guarda (isso é ocupar, tipo 7), e mina já ocupada é recusada. O robô recusa quem tem 18 níveis ou mais (`_attack_robot`, a mesma regra do cliente). Falta o PvP contra castelo de jogador: `8488` não tem alvo, e a 765 precisa dele acima de 17 níveis.
- **32 (Collect Lumber)**: `Para1` é o item (2100022 Wood, 2100023 Amethyst, 2100024 Copper, `SonType` 210). Contagem na bolsa (`checkGoodsCount`), já ligada (`rules.goods_count`, só BAG; tabela: sim). Nenhum código do servidor cria esses itens (grep vazio em `src`). A coleta do espaço (8733) e a do tutorial (8699) não são implementadas. A coleta de campanha (5032 cmd 2, `CollectionAction`) é outra rota, e a entrada 8258 com a 6001 (Resource Quarry, Types 2) é recusada com aviso, sem layout nem captura. Falta a fonte, que mexe em `items.py` e `drops.py`, fora do meu grupo.
- **33 (Login With Mini-client)**: cliente (`checkClientLogin`) lê `DesktopManager.isDesktop`, um valor que a página manda pelo `ExternalInterface` (`IsDesktop`). Nenhum pacote avisa isso, e o `LoginReqMsg` só tem `playerId`, `key` e `ekeys`. Falta decidir como o servidor sabe que o cliente é o desktop.
- **48 (cadastro de celular)**: existe no template (missão 816), mas o servidor não tem nada de celular. O cliente manda `8524` (`CheckSend`, "já preencheu o celular?") e `8352` (`UserPin`, código do SMS), e nenhum handler responde. Falta: os dois handlers, guardar o número e um provedor de SMS.

## Desbloqueio (revisão 2026-10-17, revisor)

Nenhuma missão foi desbloqueada nesta revisão. O que impede cada grupo de bolsa, com a fonte:

- **Fechadas pela janela** (`EndDate` no passado): 8, 9, 13, 14, 15, 19, 770 e 771. O cliente recusa o aceite em `TaskManage.checkIsAchieved` (`TaskManage.as:340-349`: agora maior que `EndDate`), e `rules.can_accept` faz o mesmo. A 770 e a 771 têm `StartDate` igual a `EndDate` (2000-01-01), então a janela é vazia. Sem missão aberta, o item da condição não precisa de fonte.
- **846 a 856 (208012, Koyu Kristal)**: janela aberta (2000 a 2050), `IsLeague` e `IsRepeat`. Falta fonte servida para 208012. Busca por número isolado em todo o tempinfos e grep em `src` (sem nenhuma referência):
  - ShopTempInfos 755 (ShopType 7) e 810 (ShopType 10): têm `Score` 18 e `LordsScore` 1 (moeda de pontuação, não verificada no cliente). Todas as colunas de preço que o servidor cobra são 0, então `shop.price` devolve `None` e o 5154 recusa (`NO_ITEM`).
  - ActiveTempInfos 11 (Deneme Kulesi, `DropList`): `handlers/tower.py` só responde o info da torre (`tower_info`), sem progresso e sem recompensa.
  - FishTemplateInfos 1004 (`RewardId`): `minigames.fishing` manda pool vazio, então não há pesca.
  - Drop da cena de guilda (texto da 846: "Collect [Shadow Crystal] in the multiplayer dungeons"): não há tabela de drop nos dados e não há código de drop de cena no servidor.
  - Nenhum handler lê `Score` ou `LordsScore` para vender (`shop.py:46` só ignora essas lojas), nenhum outro handler atende ShopType 7 ou 10, e nenhum arquivo em `data/` (incluindo o `overlay`) cita 208012 fora do tempinfos.
  - Para desbloquear, o servidor precisa servir uma dessas fontes (moeda de Score na loja, drop na Deneme Kulesi ou drop na cena de guilda). Nada disso foi implementado.
- **2127001 (770)**: a loja 149 (ShopType 1) pede 1 GiftToken por unidade, e `handlers/shop.py` (`charge`) cobra GiftToken. Os campos de bloqueio que `check()` lê estão zerados ou em -1 (`VIP0Count`), então a fonte existe para o servidor. A 770 continua fechada.
- **2129001 (771)**: a loja 474 é ShopType 99 (ofertas da home), que o 5154 recusa. A 771 continua fechada.

## Tabela por CondictionType

- **Nome**: título mais frequente em `CondictionTitle`.
- **Para1 / Para2**: as três combinações mais comuns, com o número de missões e alguns exemplos.
- **Cliente**: função de `TaskTemplate.getProgress` que trata o tipo. `default` conta como feito no cliente (o cliente manda 5014 e o servidor recusa se não contar).
- **Contado**: `sim` quando o servidor avança ou avalia o tipo, `parcial` quando só um caso é coberto, `não` caso contrário.
- **Quem**: `eu` para os tipos deste trabalho, `outra equipe` para o resto. O integrador atualiza esta coluna no fim.

| Tipo | Nome | Para1 / Para2 (mais comuns) | Missões | Cliente (`getProgress`) | Contado | Onde no código | O que falta | Quem |
|---|---|---|---|---|---|---|---|---|
| 1 | Level Up | 1 / 1; 1 / 20; 1 / 30 | 30 (7, 11, 12, 752, 772, 773, ...) | `checkPlayerGrades` | sim | rules.quest_done (PLAYER_LEVEL_CONDITION), nível lido na conclusão | nada: ligado. A missão 7 'New Year's Arrival' (P2=1) deixou de ser aceitável: a janela (2000-01-01) está fechada, como no cliente. | eu |
| 2 | Upgrade your Town Hall | 901 / 2; 402 / 2; 1201 / 3 | 38 (51, 81, 82, 181, 182, 225, ...) | `checkBuildingOrTecGrades` | sim | rules.update_building_quests (castle.py:115, accept_quest) | — | outra equipe |
| 3 | Recruit Lancers | 1 / 200; 2 / 100; 3 / 200 | 5 (52, 110, 764, 785, 786) | `checkCount` | sim | army.py:92 quest_event RECRUIT (soma) | — | outra equipe |
| 7 | Occupy Gold Mines | 2006 / 2 | 2 (60, 282) | `checkWilanCount` | sim | outer_city.py:266 quest_event OCCUPY (soma) | — | outra equipe |
| 8 | Plunder a City | 0 / 1; 0 / 2; 1 / 1 | 3 (100, 411, 765) | `checkCount` | parcial | outer_city: `_castle_over` (handlers/outer_city.py), vitória contra o castelo-robô (Para1 1) | só o castelo-robô: PvP contra castelo de jogador segue sem alvo (8488). 765 precisa de PvP acima de 17 níveis. 411 presa pela 410. 100 fecha pelo robô, que conta pelo dado (seção *Tipo 8*). 765 é diária, não re-aceita (rules.py:282) e exige guilda (IsLeague). Ouro saqueado sem fonte. | eu |
| 10 | Upgrade Lancers | 1 / 3; 3 / 5 | 2 (101, 764) | `checkPawnGrades` | sim | army.py:178 quest_event PAWN_LEVEL (maior valor) | — | outra equipe |
| 12 | Speed Up the Building Construction Cooldown | 1 / 1; 1 / 3; 1 / 7 | 3 (111, 112, 113) | `checkCount` | sim | castle.py ACCELERATE (aceleração de construção) | — | eu |
| 14 | Gain passage through the Orc Plains | 1005 / 1; 1002 / 1; 1001 / 1 | 39 (21, 70, 120, 130, 250, 350, ...) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`, `_map_finished`); rules.quest_event (CAMPAIGN_CONDITION) | só a campanha 1001 tem nós no servidor. As outras 38 missões pedem campanhas 1002+ ou 9000+ (lista abaixo) | eu |
| 16 | Participate in an Arena Challenge | 1 / 3; 1 / 5 | 2 (421, 422) | `checkCount` | sim | arena_grupo._after: fim de cada luta da sala PvP, vitória ou derrota (ARENA_PARTY_CONDITION, Para1 1); 112 depois do 4103 *(visto)* 27/10 #19929 | — | eu |
| 17 | Enchant Weapon/Armor to Level 3 | 2 / 1 | 1 (121) | `checkCount` | sim | forge.py STRENGTHEN (5150), grau > Para1 (MIN_CONDITIONS) | — | eu |
| 18 | Socket a Gem | 1 / 1 | 1 (281) | `checkCount` | sim | forge.py GEM_INLAY (5151) | — | eu |
| 19 | Synthesize a Gem | 0 / 1 | 1 (311) | `checkCount` | sim | forge.py GEM_COMPOSE (5153) | — | eu |
| 20 | Energize a Friend's Tree of Ancients | 0 / 2; 1 / 2 | 4 (22, 260, 261, 271) | `checkCount` | sim | handlers/farm.py (15017) | Para1 exato: 1 a própria árvore, 0 a de amigo | castelo.md |
| 21 | Make a Friend | 0 / 1 | 1 (200) | `checkFriendsCount` | sim | friends.py e rules.social_state_quests (tamanho da lista) | — | eu |
| 22 | Create/Join Guild | 0 / 1 | 1 (220) | `checkJoinConsortia` | sim (estado) | rules.quest_done lê a guilda na entrega; condition_1 fica 0 como no oficial | — | eu |
| 23 | Defeat the Huntera | 13000 / 1; 11600 / 1; 17000 / 1 | 7 (10, 20, 30, 40, 45, 50, ...) | `checkAttack` | sim | rules.update_novice_quests (campaign.py:506, accept_quest) | — | outra equipe |
| 25 | Defeat Undead Warrior | 2041 / 4; 2042 / 3; 2043 / 2 | 34 (240, 450, 480, 490, 510, 560, ...) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`); rules.quest_event (PAWN_KILL_CONDITION) | conta por soldado do lado 2 da batalha. A 1001 tem o 2011, mas nenhuma missão de 25 aponta para ela. As 34 missões são de campanhas 1004 a 1602 (sem nós) | eu |
| 26 | Defeat Wulfgar | 1011 / 1; 1031 / 1; 1041 / 1 | 30 (80, 210, 230, 280, 310, 470, ...) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`); rules.quest_event (HERO_KILL_CONDITION) | o chefe da 1001 (102109, template 1011) conta na 80 e o da 1003 (103207, template 1031) na 210. Os chefes de campanhas 1002+ e o da ilha dos pets (921) não têm gatilho | eu |
| 27 | Collect “新” | 2125006 / 1; 2125007 / 1; 2125008 / 1 | 15 (8, 9, 13, 14, 90, 190, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte: vários itens das condições (2100003, 2100004, 2100006, 2100008, 2100009, 2100013) não têm fonte nos dados (só ItemTempInfo e a condição); a contagem não depende disso. A 90 fecha com 2100001 da 1001. Na 1001, 14 missões de 27 pedem itens sem fonte (lista abaixo) | eu |
| 28 | Collect Forgotten Stones | 2125011 / 3; 2100005 / 1; 2100007 / 1 | 12 (17, 300, 370, 460, 500, 540, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte: 2100005 e 2100007 não têm fonte nos dados; a contagem não depende disso | eu |
| 29 | Guild Contribution | 0 / 10; 0 / 50; 0 / 150 | 4 (221, 222, 223, 224) | `checkConsortiaOffer` | sim | fam.py, upgrades.py e social_state_quests (contribuição total) | — | eu |
| 30 | Guild Blessing | 0 / 1 | 1 (241) | `checkCount` | sim | altar.py (5145) | — | eu |
| 31 | Complete Any Solo Dungeon | 1 / 3; 2 / 1 | 2 (313, 371) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`, fim de mapa); rules.quest_event (SOLO_CONDITION) | conta cena com capacidade = Para1 só na 1001 (capacidade 1). 313 fecha no servidor (`Para2` 3), mas a pré 310 bloqueia. 371 (capacidade 2) não tem cena | eu |
| 32 | Collect Lumber | 2100022 / 20; 2100024 / 10; 2100023 / 10 | 7 (55, 102, 140, 170, 171, 172, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), mesmo caminho da 27 | fonte: a pedreira 6001 (Resource Quarry), pela captura inglesa: 8258 entra, 5032 `cmd:2` colhe Wood x2/x3, 8699 luta dá Wood x18 ([salas-campanha.md](salas-campanha.md)). Coleta no espaço (8733) não é implementada | eu |
| 33 | Login With Mini-client | 0 / 1 | 2 (1, 150) | `checkClientLogin` | não | — | sinal de cliente desktop: o cliente lê DesktopManager.isDesktop (JS da página, ExternalInterface 'IsDesktop') e nenhum pacote manda isso (LoginReqMsg só tem playerId, key e ekeys). Decisão de protocolo. | eu |
| 34 | Adjust Troop Formation | 0 / 1 | 1 (160) | `checkSortPawn` | sim | army.py:286 quest_event FORMATION (soma) | — | outra equipe |
| 35 | Challenge | 1 / 3; 1 / 5; 1 / 1 | 3 (2, 4, 188) | `checkCount` | sim | arena.py QUEST_CHALLENGE (8253) | — | eu |
| 36 | Astro | 1 / 1; 0 / 1 | 2 (3, 622) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 37 | Head to Autaric Plains | 0 / 1; 0 / 2; 0 / 3 | 5 (173, 390, 580, 787, 826) | `checkMapId` | sim | update_state_quests (MAP_CONDITION, checkMapId); já estava no HEAD | — | outra equipe |
| 38 | Battle the Forgotten Catacombs | 8001 / 2 | 1 (6) | `checkMazeRecord` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 39 | Second Login | 0 / 1 | 1 (5) | `checkSencondLogin` | sim | rules.quest_done (LOGIN_DAY_CONDITION), dia UTC | nada: ligado. Compara o dia UTC do aceite com o de agora; o cliente usa o dia local (getDate). Se o fuso importar, trocar por um fuso fixo. | eu |
| 40 | Participate in a World BOSS Battle | 0 / 10; 0 / 1 | 2 (759, 761) | `checkCount` | sim | handlers/worldboss.py (fim da luta) | 1 por luta (dedução) | boss-eventos.md |
| 41 | Total Damage Dealt | 0 / 50000 | 1 (762) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 42 | Levy your town hall | 0 / 1 | 1 (763) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 44 | Participate in a Battleground | 0 / 1 | 2 (758, 766) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 45 | Battleground Kills | 0 / 70; 0 / 2 | 2 (16, 767) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 46 | Recycle a Piece of Equipment | 0 / 1 | 1 (768) | `checkCount` | sim | forge.py RECYCLE (8340) | — | eu |
| 47 | Refine a Piece of Equipment | 0 / 1 | 1 (769) | `checkCount` | sim | forge.py REFINE (8336) | — | eu |
| 48 | Input Your Cell Number and ID Number | 0 / 1 | 1 (816) | `checkCount` | não | — | o servidor não tem nada de celular: o cliente manda 8524 (CheckSend) e 8352 (UserPin, código SMS) e nenhum handler responde. Falta: os dois handlers, guardar o número e um provedor de SMS. | eu |
| 49 | Shadow Crystal | 208012 / 6 a 36 (846 a 856); 2125012 / 5 (15); 2125013 / 50 (19); 2127001 / 10 (770); 2129001 / 5 (771) | 15 (15, 19, 770, 771, 846 a 856) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte (número isolado em todo o tempinfos): 208012 só em ShopTempInfos 755/810 (preço em Score/LordsScore, que `shop.price` não cobra), ActiveTempInfos 11 (Deneme Kulesi, sem recompensa no `tower.py`) e FishTemplateInfos 1004 (pesca fechada): nenhuma servida, então 846 a 856 travam (ver "Desbloqueio"). 2125013 sem fonte; 2125012 só como QuestGoods de outra missão; 2127001 na loja 149 (1 GiftToken; sem campo de bloqueio) e receita (só ingrediente); a contagem não depende disso | eu |
| 50 | Battle Victories | 0 / 1 | 2 (18, 818) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 51 | Guild Level | 1 / 2; 2 / 2 | 2 (819, 820) | `checkConsortuaGrade` | sim | upgrades.py e social_state_quests (GUILD_LEVEL_ATTRS) | — | eu |
| 52 | Gain a Troop Speciality | 0 / 2 | 1 (821) | `checkCount` | sim | army.py:247 quest_event COMPREHEND (soma) | — | outra equipe |
| 53 | Lock an Astral | 0 / 1 | 1 (623) | `checkCount` | sim | stars.py:316 quest_event LOCK_QUEST (soma) | — | outra equipe |
| 56 | Auction | 0 / 1 | 1 (825) | `checkCount` | sim | mall.py SELL_CONDITION (8448) | — | eu |
| 57 | Blessing Wheel | 0 / 1 | 1 (857) | `checkCount` | sim | castle.py SEMINARY_CONDITION (8489) | — | eu |
| 58 | Soul Engraving | 0 / 1 | 1 (858) | `checkCount` | sim | items.use_store (8484), +1 por uso | (visto) 20261101-220132-1 #1970: 112 condition_1 1 depois do 8484; entrega #1974-#1993 pelo 5014 comum | eu |
| 59 | Life on the Farm | 0 / 1 | 2 (262, 859) | `checkCount` | sim | farm.py QUEST_PLANT | — | eu |
| 60 | Harvest from your own farm | 0 / 2; 1 / 2 | 4 (263, 266, 860, 861) | `checkCount` | sim | handlers/farm.py (op 4 e 5) | Para1 exato: 0 colher a própria, 1 roubar de amigo | castelo.md |
| 61 | Pest Extermination | 1 / 2 | 2 (267, 862) | `checkCount` | sim | farm.py QUEST_BUG (só a praga) | — | eu |
| 63 | Devotion | 0 / 20 | 1 (863, diária `IsRepeat`) | `checkCount` | sim: maior total de devoção do dia (`LEVEL_CONDITIONS`) | `handlers/events.leed_gain`/`devotion_quests` (ganhos e 1º login do dia) | aceite nasce com 0 mesmo com devoção já ganha (visto, tutorial_en #3199); só o próximo ganho grava o total. Reabre no dia do jogo seguinte (`_repeat_ok`) | — |
| 64 | Alchemy | 0 / 3 | 1 (184) | `checkCount` | sim | vip.alchemy (8321) ALCHEMY_CONDITION | posição do 112 TODO(inventado) | eu |
| 65 | Daru Alchemy | 0 / 3 | 1 (185) | `checkCount` | sim | vip.soul (8467) DARU_ALCHEMY_CONDITION | posição do 112 TODO(inventado) | eu |
| 66 | Instant Battle with World Boss | 0 / 3 | 1 (183) | `checkCount` | sim | handlers/worldboss.py (8264 pago) | 1 por reviver pago | boss-eventos.md |
| 71 | Train | 0 / 1 | 1 (753) | `checkCount` | sim | systems.py QUEST_MOUNT_TRAIN | — | eu |
| 74 | Enter The Spire | 0 / 1 | 1 (799) | `checkCount` | sim | campaign.py, entrada da Spire que gasta a vez (SPIRE_CONDITION) | posição do 112 TODO(inventado) | eu |
| 76 | Learn Brutality Rune | 2 / 1; 1 / 1 | 2 (906, 907) | `checkRuneStudy` | sim | update_state_quests (RUNE_STUDY); já estava no HEAD | — | outra equipe |
| 77 | Consume Small Runestone | 3020010 / 5; 0 / 10; 3020004 / 20 | 3 (186, 908, 909) | `checkCount` | sim | hero.py RUNE_COMBINE (pedras gastas) | — | eu |
| 78 | Upgrade Rune | 0 / 3; 5 / 150; 0 / 5 | 6 (910, 911, 916, 917, 918, 919) | `checkRuneGrade` | sim | update_state_quests (RUNE_GRADE, LEVEL_CONDITIONS); já estava no HEAD | — | outra equipe |
| 79 | Participate in the Tank Battles | 0 / 1; 3001 / 1 | 2 (912, 914) | `checkCount` | sim | vehicle.match_up (TANK_JOIN_CONDITION, Para1 3001) | posição do 112 TODO(inventado) | eu |
| 80 | Win the Tank Battles | 0 / 1; 3001 / 1 | 2 (913, 915) | `checkCount` | sim | vehicle.settle, quem vence (TANK_WIN_CONDITION; empate conta para os dois) | posição do 112 TODO(inventado) | eu |
| 85 | Talk to the Priest | 0 / 1 | 10 (174, 175, 191, 229, 272, 283, ...) | `checkFinishPetStory` | parcial | space.py talk (8692) e player.py quest_add (aceite), perto do nó | parcial: MasterType 61 (Dinah 361, Asima 229, Lilith 272, Lara 283, Azrael 922, Berdim 933) conta no 8692 e no aceite perto do nó. Patrulha (MasterType 1: Priest 174/191, Guardian 175, Berdim 301): o cliente não manda 8692; só conta no aceite se a posição do modelo estiver perto (não validado). O servidor não vê o fim do diálogo. | eu |
| 86 | Join the Amethyst Rush | 0 / 1 | 1 (503) | `checkCount` | sim | warfield.callback, coleta na pilha da mina (5032 cmd 2) | posição do 112 TODO(inventado) | eu |
| 87 | Join the Sylph Arena | 0 / 1 | 1 (504) | `checkCount` | sim | arena._pet_over (`QUEST_PET_TOURNAMENT`): cada luta do torneio de mascotes conta, ganhando ou não | — | outra equipe |
| 89 | Participate in the Lost Treasure | 0 / 1 | 1 (925) | `checkCount` | sim | treasure.py, 8744 op 3/5 ao entrar na luta (dono e grupo) e reforço 8745 (LOST_TREASURE_CONDITION) | posição do 112 TODO(inventado) | eu |
| 90 | Socket Resistance Crystal | 0 / 1 | 1 (926) | `checkCount` | sim | tower.battleguard_op, 8742 op 2 com gema 101..106 num entalhe (RESIST_CRYSTAL_CONDITION; a Will Crystal não conta) | posição do 112 TODO(inventado) | eu |
| 91 | Go on an Exploration | 0 / 1 | 1 (930) | `checkCount` | sim | treasure_hunt.py, 9502 op 3 (EXPLORE_CONDITION) | 112 antes do 4914 (captura 20261029-121453-1 #452) | eu |
| 93 | Win a Sky Trail Battle | 0 / 1 | 1 (932) | `checkCount` | não | — | TODO(93) em rules.py: Sky Trail (General William) sem sistema identificado; candidato (dedução) SinglePass 8753/8755 (handlers/singlepass.py) | eu |

## Missões bloqueadas para as masmorras 1002+

Lista calculada do `tempinfos.xml` do overlay: missões com condição 8, 14, 25, 26, 27 ou 31 que a masmorra 1001 não cumpre. Total: 119 missões. Fecham com a 1001: 70, 80 e 90. A 313 fecha no servidor, mas a pré 310 a deixa travada.

Para as masmorras 1002+ destravarem uma missão, precisam de nós e lutas (`content/dungeon_<id>.json`, a partir de captura; `tools/extract_dungeon.py` só serve à 1001 hoje), do fim de mapa com o grupo caído e dos drops. Sem captura dos nós, nenhuma dessas missões fecha.

- **14, campanha sem nós (38)**: 21 (1005), 120 e 130 (1002), 250 (1005), 350 (9000), 380 (1101), 410 (1102), 430 (1103), 440 (1104), 530 (9002), 650 (9003), 720 (1205), 754 (9104), 760 (9004 e 9104), 784 (9005 e 9105), 801 (1302), 803 (1304), 805 (1306), 807 (1308), 828 (1402), 830 (1404), 832 (1406), 843 (9006 e 9106), 845 (9007 e 9107), 879 a 885 (1501 a 1507), 894 (9008 e 9108), 896 (9009 e 9109), 897 (1601), 898 (1602), 902 (9010 e 9110), 904 (9011 e 9111), 924 (9012 e 9112).
- **26, chefe de campanha sem nós (28)**: 230 (1004), 280 (1006), 310 (1007), 470 (1105), 550 (1107), 590 (1201), 620 (1202), 660 (1204), 670 (1203), 740 (1207), 750 (1206), 783 (9005), 800 (1301), 802 (1303), 804 (1305), 806 (1307), 827 (1401), 829 (1403), 831 (1405), 833 (1407), 842 (9006), 844 (9007), 893 (9008), 895 (9009), 901 (9010), 903 (9011), 923 (9012). A 921 (`Para3` 0, chefe 20010 da ilha dos pets) entra aqui também: a ilha tem dados em `petisland.json`, mas o servidor não emite a condição 26 nela.
- **25, soldados de campanha sem nós (34)**: 240 (1004), 450 (1103), 480 e 490 (1105), 510 (1106), 560 (1107), 600 (1201), 630 (1202), 700 (1204), 730 (1205), 808 a 815 (1301 a 1308), 835 a 841 (1401 a 1407), 886 a 892 (1501 a 1507), 899 (1601), 900 (1602).
- **8, ataque a castelo (3)**: 100, 411 e 765. Não é de masmorra. O castelo-robô conta a vitória (seção *Tipo 8*): a 100 fecha pelo robô (qualquer alvo), a 411 segue presa pela 410, e a 765 precisa de PvP acima de 17 níveis (`8488` sem alvo).
- **31, cena com capacidade 2 (1)**: 371 (grupo). A 1001 é solo.
- **27, item sem fonte no dado da 1001 (14)**: 8 (2125006 a 2125009), 9 (2125010), 13 (2125001 a 2125004), 14 (2125005), 190 (2100003), 270 (2100004), 360 (2100006), 400 (2100008), 420 (2100009), 520 (2100013), 570 (2100014), 610 (2100015), 640 (2100016), 710 (2100018). Podem ter fonte em outra campanha (não verificado). A condição 27 conta a bolsa, então um drop que der o item liga a missão sem hook novo.

## Notas para o integrador

- **Migração**: o branch já mesclou o milestone-1; a `0022_progresso_das_condicoes_da_missao.py` desce da `0021_copias_de_campanha_em_grupo.py` (uma head só).
- **Assinatura**: `rules.quest_done(snap, templates, q, now)` agora exige `now`. Chamador novo em outra equipe precisa passar o relógio.
- **Mudança de comportamento intencional**: a missão 764 (recrutar 200 do tipo 3 e tropa do tipo 10 no nível 5) passou a exigir as duas linhas. Antes concluía só com o recrutamento.
- **Junção no worktree**: `data\overlay` é uma junção para `D:\wartune\servidor\data\overlay`. Antes de apagar o worktree, desfazer só a junção pelo gerenciador de links do Windows, nunca por exclusão recursiva, que pode atravessar a junção e apagar a pasta real.
- **Tipos de outra equipe**: as colunas "Contado" e "Onde" das linhas "outra equipe" refletem o código deste branch, então o integrador deve conferir essas linhas depois da mescla.
- **Aceite e entrega (2026-10-17)**: o 5012 agora recusa o que o cliente também recusa (janela, nível, guilda, pré-requisito, repetição). Missões dos dados que estão vencidas ou com pré-requisito deixaram de nascer pelo 5012. Nos testes, 11, 5, 361, 906, 910, 390 e 173 entram abertas direto na sessão, ou com o pré-requisito concluído (`_done`), porque nos dados estão vencidas ou têm pré-requisito. O teste de conversa no aceite usa a 922 (a 361 venceu em 2000).
- **Login**: o login manda só as missões abertas (`handlers/login.py:216`, `not q.completed`), então a repetível concluída não aparece lá. Quando o cliente a re-oferece (IsAuto, depois do `RepeatInterval`), o 5012 a reabre na mesma linha (`accept_quest`). A captura citada no código (só turco: login.json #89) mostra a 241 aberta com `completedDate` antigo e o bit do `states` ligado. O bit fica ligado (`ever_completed`), mas a missão não vai no login: diferença de exibição, em aberto.
- **Sem migração nova**: a entrega não guarda estado pendente, então nada muda no banco.
- **5017 (passo do novice)**: o cliente só manda valor positivo e múltiplo de 100 (cliente: `sendSaveProcess`, m8). A ordem crescente vem do guia (`newbie.xml`). A inglesa tem 34 avanços positivos, de 11400 a 28500, e um pedido repetido (22800 duas vezes), que o servidor ignora (visto). (Só turco: o replay tem 29, de 100 a 1500 e de 11000 a 25500.) O teto de 3500 é o maior salto do guia, de 28500 para 32000 (dedução: não há captura de salto maior). O painel de depuração do cliente (m8, `QVKZDKIyIBJ.as`, `__onSaveClick`) manda o id digitado sem esse teto: se ele existir em produção, o servidor recusa saltos acima de 3500 (não verificado).
- **Revisão**: a revisão antiga missão a missão (2026-10-17, cliente turco) está em
  `consulta/revisoes/missoes-revisao.md` (fora do git); as linhas "Revisão 2026-10-17" dizem o que mudou por missão.
- **Mudança de comportamento (5014)**: `RewardStrategy` agora é paga na entrega, antes ignorada. São 20 missões com valor (a 90 dá 1000 de Daru; o total no template é 875000). Conferido na inglesa para a 90 (PlayerMsg 3, #1571 → #1573).
- **Mudança de comportamento (aceite)**: `Para1` em lista (17 missões, tipos 14 e 26) não derruba mais o aceite (`rules.para1_ids`).
- **Mudança de comportamento (missões 70, 80, 90)**: as três fecham jogando a 1001 do começo ao fim (teste `test_missoes_70_80_90_fecham_jogando_a_1001_do_comeco_ao_fim`). A 70 vira concluída, e o guia 24007 (c12(70)) libera o guia de habilidade 24000. Verificado até o 5017 (teste do guia); o 8235 (leed) não tem teste.

## EXP do mundo e EXP descansada

(só turco: transfer_kampi #17-#23, meydan_okuma, peri_turnuvasi) Toda EXP de luta (campanha, coliseu) e de missão passa por
`rules.exp_bonus`: a EXP do mundo é a base × `world_percent`/100 (o turco: 10×) e a descansada é a base + a do mundo, limitada ao
`leaveGp` e descontada dele. O texto vira "Received N EXP (Including W World EXP, R Offline EXP)". O mascote em batalha recebe o
total (`petGpBonus` = `gpBonus`) e o 4540 sai logo depois do 3. O `leaveGp` cresce no login com a EXP offline do `timebox`
(`rules.rest`). Abaixo de `min_grade` nada muda: o inglês (níveis 1-19) tem `leaveGp` 0 e nenhum bônus; o 40 é
`TODO(inventado)`. Configurável em `game_settings.exp_bonus` `{"min_grade", "world_percent"}`.

## Tipos pendentes (até o nível 31)

Verificado nesta rodada: o cliente inglês decompilado (`D:\xampp\htdocs\wartune\decomp`, todos os módulos) não tem nenhuma referência a mini-client nem a celular/verificação (grep `miniclient`, `cellphone`, `bindPhone`, `VerifyCode`). A condição 33 e a 48 não aparecem em nenhum `switch` de `TaskTemplate`. As 4 capturas novas (`x_20261024-191924-1`, `x_20261025-232017-1`, `x_20261026-225632-1`, `x_20261027-152321-1`) não têm texto nem pacote de mini-client. (visto) a 816 (celular, nível 25) é aceita no 5012 em quase todos os lotes, mas nunca recebe 5014 nas capturas.

| Tipo | Missões (nível) | Estado | Gancho |
|---|---|---|---|
| 33 Mini-client | 1 (15), 150 (10) | pendente: sem pacote no cliente nem nas capturas | `MINI_CLIENT_CONDITION` |
| 38 Forgotten Catacombs | 6 (23) | pendente: gancho do dono de campaign | `CATACOMBS_CONDITION` |
| 41 Dano no chefe mundial | 762 (27) | pendente: gancho do dono de worldboss | `WORLDBOSS_DAMAGE_CONDITION` |
| 44 Entrar em battleground | 758, 766 (30) | pendente: sistema inexistente | `BATTLEGROUND_JOIN_CONDITION` |
| 45 Kills em battleground | 16 (30), 767 (30) | pendente: sistema inexistente | `BATTLEGROUND_KILL_CONDITION` |
| 48 Cadastro de celular | 816 (25) | pendente: sem pedido no cliente nem 5014 nas capturas | `PHONE_CONDITION` |
| 50 Vitória em battleground / war camp | 18, 818 (30) | pendente: sistema inexistente | `BATTLEGROUND_WIN_CONDITION` |
| 86 Amethyst Rush | 503 (25) | pendente: gancho em outer_city/mines | `AMETHYST_CONDITION` |

Constantes em `game/rules.py`; teste `test_tipos_sem_gancho_tem_o_numero_do_template` em `tests/game/test_missoes_condicoes.py`.

## Verificação por captura: entregas até o nível 10

Teste: tests/game/test_missoes_capturas.py (códigos S>C da entrega contra o oficial; o estado vem das condições da missão). Oficial: S\q\oficial.md. Personagem de teste no grau 60 (sem subida de nível).

| id | estado | #idx (captura) | motivo |
|---|---|---|---|
| 380 | ok | 14667 | códigos iguais |
| 440 | ok | 18290 | códigos iguais |
| 470 | ok | 1784 | códigos iguais |
| 590 | ok | 8417 | códigos iguais |
| 310, 360, 400, 410, 420, 430, 450, 460, 480, 490, 500, 510, 520, 550, 560, 570, 600, 610 | pendente (xfail) | 8939, 11761, 15035, 17367, 17542, 19336, 20432, 20602, 3001, 3082, 5348, 7537, 7597, 8188, 12626, 12635, 14162, 13701 | falta 83 (texto do EXP) e/ou 115 (consumo de item) |
| 580 | pendente (xfail) | 18069 | oficial não manda resposta; o servidor responde |

## Verificação por captura: entregas até o nível 10 (rodada 2)

Tabela do oficial em tests/game/test_missoes_capturas.py (códigos e textos do 83). Janela do oficial: até o próximo pedido do cliente, mais o 83 "Received N EXP" logo depois dele (S\q\oficial.md). Personagem de teste no grau 39 (abaixo do bônus de EXP do mundo, min_grade 40).

Causas achadas: o 115 de consumo de item e o 83 da EXP já saíam no código (HEAD). As divergências da rodada 1 eram do teste: item criado em memória sem estar no banco, e grau 60 que ligava o bônus de EXP do mundo ("Including World EXP").

| id | estado | #idx | motivo |
|---|---|---|---|
| 360, 380, 410, 420, 440, 450, 460, 470, 500, 510, 520, 550, 560, 590, 600, 610 | ok (16) | #11761, #14667, #17367, #17542, #18290, #20432, #20602, #1784, #5348, #7537, #7597, #8188, #12626, #8417, #14162, #13701 | códigos e textos do 83 iguais |
| 310 | pendente (xfail) | 8939 | recompensa com 4484/111/114/4131/149 de outras áreas |
| 400, 430, 480, 570 | pendente (xfail) | 15035, 19336, 3001, 12635 | oficial sobe de nível depois do 83 (100/150); grau do personagem da captura não se conhece |
| 490 | pendente (xfail) | 3082 | oficial manda 109 antes do 3; causa não confirmada |
| 580 | pendente (xfail) | 18069 | oficial não responde (sem 112 de recusa); causa não confirmada |

## Verificação por captura: entregas até o nível 10 (rodada 3, feat/missoes-2)

Teste: tests/game/test_missoes_capturas.py. Grau do personagem por entrega vem do 3 antes do 5014 (captura). Mapa da missão 580 (condição 37) é o do personagem na entrega (castle.map_id = Para2).

Causas corrigidas no teste (o servidor já estava certo): 490 tinha um 109 do ciclo do castelo antes do 3 (não é entrega); 580 precisa do mapa 3 (a entrega do oficial foi com o personagem no mapa 3) e o oficial paga 25.000 EXP (#18077, depois do 5012 #18076).

| id | estado | #idx | motivo |
|---|---|---|---|
| 360, 380, 410, 420, 440, 450, 460, 470, 490, 500, 510, 520, 550, 560, 580, 590, 600, 610 | ok | ver teste | códigos e textos do 83 iguais |
| 310 | pendente (xfail) | 8939 | recompensa com 4484/111/114/4131/149 de outras áreas |
| 400, 430, 480, 570 | pendente (xfail) | 15035, 19336, 3001, 12635 | subida de nível (100/150): o 3 traz só o grau, não o EXP atual |

Lotes 11 a 31: não feitos nesta rodada.

## Verificação por captura: lote 11 a 20 (feat/missoes-3)

Teste: tests/game/test_missoes_capturas.py (mesma tabela OFICIAL e GRAU, grau e janela do oficial como na rodada 3). Se o oficial traz 150, o EXP do personagem fica logo abaixo do limite do próximo grau (UpGradeTempInfos), para a recompensa forçar a subida.

| id | nível | estado | #idx | motivo |
|---|---|---|---|---|
| 312, 350, 351, 391, 411, 421, 441, 461, 472 | 14 a 20 | ok | 8089, 7778, 8099, 8109, 5586, 20153, 9536, 9546, 9557 | códigos e textos do 83 iguais |
| 412 | 17 | pendente (xfail) | 8996 | subida de nível: servidor reabastece o exército (104/110/152/4130) antes do 150 |
| 223 | 20 | pendente (xfail) | 1759 | pacote inicial 4484/111 e 115 de itens: janela mistura outras áreas |
| 241 | 20 | pendente (xfail) | 1965 | bênção do altar (tipo 30): 109 duplicado e 83 de devoção |
| 271 | 12 | pendente (xfail) | 295 | árvore (tipo 20): 115 e 4476 fora da entrega |
| 313 | 15 | pendente (xfail) | 14068 | tipo 31 (cena com 1 jogador): gancho em campaign.py |
| 371 | 20 | pendente (xfail) | 8821 | tipo 31 (cena com 2 jogadores): 4484/111 do pacote de VIP |
| 422 | 18 | pendente (xfail) | 20591 | arena (tipo 16): gancho em arena.py, 3 duplicado |
| 761 | 20 | pendente (xfail) | 8530 | chefe mundial (tipo 40): gancho em worldboss.py |
| 764 | 20 | pendente (xfail) | 11418 | tipo 3 e 10: depende do exército da captura |
| 765 | 12 | pendente (xfail) | 1946 | atacar cidade (tipo 8): gancho em outer_city.py |
| 768 | 19 | pendente (xfail) | 2274 | reciclagem (tipo 46): gancho em forge.py |
| 769 | 19 | pendente (xfail) | 8028 | refino (tipo 47): gancho em forge.py |
| 400, 430, 480, 570 | 10 | pendente (xfail) | 15035, 19336, 3001, 12635 | subida de nível: exército reabastecido antes do 150 |

Lote 21 a 31: não feito.

## Verificação por captura: lote 21 a 31 (feat/missoes-4)

Teste: tests/game/test_missoes_capturas.py (tabela OFICIAL e GRAU gerada de S\q\lote3.txt, janela e grau como nos lotes anteriores). Os 26 casos do lote estão em xfail (strict), cada um com o motivo na PENDENTES. Nenhum passou nesta rodada.

| id | nível | estado | #idx | motivo (resumo) |
|---|---|---|---|---|
| 3, 6, 224, 370, 390, 501, 502, 503, 530, 551, 581, 621, 623, 681, 711, 721, 731, 751, 758, 759, 762, 766, 767, 818, 846, 847 | 23 a 31 | pendente (xfail) | ver tests/game/test_missoes_capturas.py | prédio (2) sem nível montado; gancho de outro sistema (campanha 38, mapa 37, battleground 44/45, war camp 50, mines 86, worldboss 40/41, stars 53); guilda (22/29/49) sem montagem; janela com 4484/4594 de outras áreas |

Causa de cada um: não diagnosticada individualmente (janela e estado). O motivo é por tipo de condição, não por diferença medida.

### Rodada 5 (missões: subida de nível, prédios, lote 21-31)

O teste agora monta o castelo como no login (`castle.ensure`: filas, prédios do nível, produção), com `novice_process` no `CASTLE_READY` e exército cheio (tropa 10101 com `army_count` acima do limite do líder). Prédio (tipo 2) sobe para o nível da condição (o do castelo, ou um novo se faltar) e vale `rules.update_building_quests`. Grau das entregas novas vem do 3 antes do 5014 na captura (`x_20261024-191924-1` a `x_20261027-152321-1`), conferido nos 12 casos novos.

| id | nível | estado | #idx | motivo (resumo) |
|---|---|---|---|---|
| 501, 502, 551, 581, 681, 711, 721, 731 | 24 a 29 | passa (xfail tirado) | 15323, 15335, 15345, 15355, 20221, 4305, 13191, 487 | prédio (tipo 2) no nível da condição |
| 623 | 25 | passa (xfail tirado) | 20264 | estrela travada (tipo 53): gancho real em `handlers/stars.py:431` (`LOCK_QUEST`) |
| 503 | 25 | passa | 1931 | Amethyst Rush (tipo 86): cada coleta na pilha da mina (`warfield.callback`, 5032 cmd 2); a mina abre fora da janela com o carrinho comum (`test_lote1_contadores`) |
| 400, 412, 430, 480, 570 | 22 a 28 | pendente (xfail) | 15035, 17367, 19336, 3001, 12635 | subida de nível: a fila de cobrança e o exército já estão montados; o 52 e o 83 da EXP mudam de lugar entre as subidas e nenhuma regra separa os casos (saídas no comentário do teste) |
| 6 | 23 | pendente (xfail) | 12125 | catacumbas: gancho em tower.py:172 existe; a janela tem 4484/4426/4476 de recompensa não reproduzida |
| 241 | 20 | pendente (xfail) | 1965 | bênção do altar (gancho altar.py:142): não feito, o teste não chama o handler 5145 |
| 768 | 20 | pendente (xfail) | 2274 | reciclagem (gancho forge.py:560): não feito, o teste não chama o handler 8340 nem põe equipamento na bolsa |

Dos 26 casos do lote, 10 passam (acima: 8 de prédio, 623 e 503). Os outros continuam em xfail, cada um com o motivo na PENDENTES do teste.