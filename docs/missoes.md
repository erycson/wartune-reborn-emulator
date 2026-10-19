# Missões: como o servidor conta o progresso

Missões são `QuestTemps` (título, recompensa, janela) com uma ou mais linhas em `QuestCondictionInfos` (condições). Fontes do que está aqui: `data/overlay/xml/tempinfos.xml`, o cliente decompilado (`TaskTemplate.as`, `SpaceArmyViewHelper.as`, `SpaceDialogFrame.as`, `TaskMobilePhoneView.as`, `DesktopManager.as`) e as capturas. Código: `src/wartune_server/game/rules.py`, `handlers/player.py` (5012 e 5014), `builders/player.py` (112).

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
- **Consumo de bolsa**: a entrega tira da mochila o `Para1` de cada condição de bolsa (`rules.goods_to_take`). Item de missão (`SonType` 210, como o 2100001) sai inteiro: (visto) replay #1609, a pilha do 2100001 foi de 10 para zero ao entregar a 90, cuja condição pede 8. Os demais tiram só `Para2` (o 2125010, `SonType` 201, da 9): (dedução) a captura não cobre esse caso; se o oficial tirar tudo, muda uma linha em `goods_to_take`. Testes: `test_entrega_gasta_so_a_quantidade_pedida_fora_do_item_de_missao` e `test_entrega_de_item_comum_deixa_o_resto_na_bolsa`.
- **Mochila**: a conferência é feita numa cópia, depois de tirar o que a entrega consome (`bag.fits`: casa livre ou pilha do mesmo item com espaço). Se a recompensa não couber, aviso 111 "Inventory Full" e recusa sem consumir nada. (dedução) A captura EN não tem mochila cheia na entrega: o texto é o do `language.txt` inglês na chave `ConsortiaCaseCellClickMediator.command01`, a mesma do "Çantanız Dolu" turco que se usava.

### Ordem da entrega

(visto) captura EN, as 19 entregas (10 a 130): #210-#218, #482-#507, #1569-#1576, #2077-#2085, #2242-#2265. A captura turca (replay #208-#657) tem a mesma ordem.

1. 112 do progresso (`isComplete` falso), **só** quando a missão tem condição de tipo 23, 2 ou 10 (`rules.PROGRESS_BEFORE_FINISH`). Nos tipos 3, 7, 8, 14, 26, 27 e 32 o oficial não manda (52 #700, 60 #834, 70 #1129, 110 #2242...).
2. 115 do que a entrega gasta (bolsa: 90 #1570, 102 #2079).
3. 3 já com o bit da missão no `questSite`, mas antes da recompensa (gp e strategy antigos).
4. 112 concluída (`condition` da bolsa em 0; tipo 3 guarda a soma: 52 = 900, 110 = 460).
5. 3 só com a `RewardStrategy` paga, quando há (90 #1573, 101 #2183); o EXP vem no 3 seguinte.
6. 109 quando a recompensa tem ouro ou cristal.
7. 150 **só** quando sobe de nível (50, 52, 60, 80, 90, 100, 102 não mandam).
8. 3 com tudo pago.
9. 115 dos itens ganhos (45 #489, 110 #2250).
10. 111 "Received: <nome> x<n>" de cada item (#504, #2262).
11. 52.
12. 83 "Received 3,000 EXP " (vírgula de milhar e espaço no fim) e o 83 de cada item com o mesmo texto do 111.

Na subida de nível da entrega (`player.push_level`, (visto) replay #625-#628 e tutorial_en): o exército completa com
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

- Verificado (cliente: `checkPlayerGrades`): `thane.grades >= Para2`. Não usa Para1 e não é "Ödül Al": esse título é só da missão 7. Os 30 tipos 1 são quase todos "Lv.N" (11 Lv.20, 12 Lv.30, 905 Lv.35, 752 e seguintes Lv.40 a Lv.80).
- Servidor: `quest_done` compara `snap.character.grades >= Para2` na conclusão. Não grava progresso e não precisa de hook no `add_gp`, porque o nível do personagem é o estado real.
- Missão 7 ("Yılbaşı Gecesi", Para2 = 1): antes concluível por quem mandasse 5012 e 5014, porque o servidor não conferia a janela. Agora o aceite confere a janela (`rules.can_accept`): `StartDate` e `EndDate` são 2000-01-01, então o 5012 é recusado, como o cliente, que a esconde. O evento de 2012 não é mais dado.
- Teste: `test_nivel_do_jogador_conclui_pelo_nivel_de_agora` (missão 11, nível 19 recusa, 20 conclui).

### Tipo 39: entrar no segundo dia

- Verificado (cliente: `checkSencondLogin`): o dia do aceite é diferente do dia atual.
- Servidor: `quest_done` compara a data UTC de `added_at` com a data UTC de agora (o `addDate` do 112 sai em UTC). Vale no próximo 5014, então um relogin já conta sem código extra.
- Dedução: o cliente compara o dia local. Se o fuso importar, trocar por um fuso fixo.
- Missão 5 ("2. Giriş", 50000 de ouro). Teste: `test_segundo_dia_de_login_conclui_missao_5`.

### Tipo 85: falar com o NPC

- Verificado (cliente): o diálogo de NPC é local (`SpaceDialogFrame`). Ao chegar na última página, o cliente aceita a missão (5012, `requestAcceptTask`) e marca `finishStory`, sem pacote para o fim do diálogo.
- Verificado (cliente): clicar num nó manda o 8692 (`SimplePropertyMsg`, `param1` = nó), exceto quando `MasterType == 1` (`SpaceArmyViewHelper.nodeTrigger` só dispara `SELECT_NODE`, sem pacote).
- Para1 = 0 e Para4 = `"10000,nó"` (mapa e nó do NPC). Exemplo: missão 361 (Tina) = `10000,2`; missão 174 (Jesi) = `10000,9`.
- Servidor: o 8692 perto do nó (`space.talk`) marca as missões abertas com esse alvo; o aceite (5012) perto do nó marca as recém aceitas. Perto = `_near` do 8692 (alcance do nó + 5).
- Limite (cliente: `TaskManage.requestCanAcceptTask`, `SpaceDialogFrame.storyTaskNextStep`): as 10 missões de conversa têm `IsAuto = true`, então o cliente costuma aceitá-las sozinho logo depois da anterior, longe do NPC; o 5012 do último passo do diálogo só sai se a missão ainda não estava aceita. Para NPC de patrulha (MasterType 1: 174 e 191 Jesi, 175 Muhafız, 301 Rona) nenhum pacote chega ao servidor na conversa, então essas missões ficam travadas na conclusão (já eram antes). Falta decidir: confiar no 5014 para esses quatro ou achar outro sinal.
- Ponytail: o servidor não vê o fim do diálogo. Conta o clique ou o aceite perto do nó, que são as ações reais que ele recebe.
- Capturas: não há 8692 de conversa. O único 8692 visto é um teleporte (`peri_adasi_tp.json`, nó 5). A ordem 8692 e 5012 vem só do cliente (código, não captura).
- Teste: `test_falar_com_npc_conta_no_aceite_perto_do_no` e `test_falar_com_npc_pelo_8692_so_perto_e_nao_com_quem_anda`.

### Masmorra Kurt İni (tipos 14, 25, 26, 27 e 31)

Ligados em `handlers/campaign.py` (`_battle_over`, `_dungeon_loot`, `_map_finished`) e em `rules.py`. Só a campanha 1001 tem nós e lutas no servidor. O resto da lista está na seção "Missões bloqueadas para as masmorras 1002+", abaixo.

- **Para1 em lista** (tipos 14 e 26, 17 missões: 760, 783, 784, 842, 843, 844, 845, 893, 894, 895, 896, 901, 902, 903, 904, 923, 924): `rules.para1_ids` separa por vírgula, e 0 = qualquer. Antes, `update_state_quests` fazia `int(Para1)` em toda linha, e `int("9004,9104")` derrubava o aceite da 760 (teste `test_para1_em_lista_nao_derruba_o_aceite`).
- **Tipo 14 (campanha passada)**: `Para1` = `CampaignId`. Quando um mapa da 1001 acaba (`_map_finished`: no 1011, todo o grupo de lobos caído e sem `param4`; no 1021, o chefe 102109 morto), vale `quest_event(14, 1001, 1)`. Não soma: a condição é 1 por campanha. (visto) replay: relatório de campanha 137 em #1215, 135 em #1221, 112 com `cond_1` = 1 em #1222 e 4165 em #1223 (missão 70).
- **Tipo 26 (chefe)**: `Para1` = template do chefe (`GameHeroTemp`, 1011 = 'Çene'), `Para3` = campanha. Cada chefe do lado 2 da batalha vencida vale `quest_event(26, heroTempId, 1)`. Casa pelo template, não pelo mapa: o chefe 102109 tem `heroTempId` 1011, e a missão 80 pede 1011 (teste `test_26_chefe_pelo_template_e_nao_pelo_mapa`).
- **Tipo 25 (matar soldados)**: cada soldado do lado 2 da batalha vencida soma pelo `tempId` (`PAWN_KILL_CONDITION`). A 1001 tem o soldado 2011 do lado 2, mas nenhuma missão de 25 aponta para ela. (dedução) conta todos os soldados do lado 2 da spec, não os que o jogador viu cair.
- **Tipo 27 (bolsa)**: `goods_count` soma as pilhas do item na bolsa (`BagType.BAG`; item fora da bolsa não conta, teste `test_27_nao_conta_item_que_nao_esta_na_bolsa`). Na entrega (5014), `rules.goods_to_take` tira o item de missão (SonType 210, como o 2100001) inteiro; os demais tiram só o `Para2`. (visto) replay #1609: 115 com a posição esvaziada antes do 112 de conclusão da 90 (#1611), e a pilha tinha 10, enquanto o `Para2` pede 8. Tirar a pilha inteira segue o replay. (dedução) para item comum, tirar só o `Para2` não foi confirmado: a captura não cobre esse caso. Uma segunda entrega ainda não foi vista.
- **RewardStrategy**: o 5014 agora paga `RewardStrategy` (antes era ignorada). A 90 dá 1000 de Ruh (template). (visto) PlayerMsg 3 sobe `strategy` 100000 → 101000 entre #1610 e #1612, com o 112 da 90 em #1611. O chefe 102109 dá +72 (4103 #1711, `strategyBonus` 72; `strategy` 101000 → 101072 entre #1613 e #1710).
- **Tipo 31 (cena solo)**: `Para1` = `Campaigns.Capacity`. A 1001 tem capacidade 1, e cada fim de mapa dela vale `quest_event(31, 1, 1)`. A 313 pede `Para2` 3 ("herhangi bir haritayı [3 kez] geç"): fecha no servidor depois de duas partidas (dedução: cada mapa conta), mas o cliente só a oferece com a pré 310 concluída, e a 310 é do tipo 26 da campanha 1007 (sem nós). A 371 pede capacidade 2 (grupo) e não fecha com a 1001. (visto) captura `savasa_baskin_ve_elmas_ile_hizlandirma.json` #12 mostra progresso 1 em 313.

- **Pilha do drop**: o drop do nó entra por `bag.fits` + `bag.add` (como o 5006 e a loja), então o Kurt Dişi (MaxCount 9999, overlay) fica numa pilha só. (visto) replay: id 58470972 no pos 6, com 2, 4, 7 e 10 (#1360, #1442, #1520, #1578). Antes (commit 0475383) cada drop criava um item novo.
- **Şans Taşı (desvio)**: o oficial põe o item num baú: 4103 com `baseItem` 2040101 e `signId` (#1355), pick-up C>S 5129 com o mesmo `signId` (#1332) e 115 no pos 7 (#1386). Aqui o item sai direto no 115 da luta, e o 4103 não traz `baseItem` nem `signId` (um 5129 solto responde 4268). Mesmo item e quantidade; sem o baú.
- **Ordem do fim de mapa**: 137, 4151, 83, 135, 112 (missão 70), 4165, 150, 150, 140 (#1215-#1226). O 20 de #1218 (resposta ao 5038) não faz parte do `_dungeon_end`: sai como resposta a cada 5038.
- **Entrega (5014)**: o cliente manda o 5014 só com a missão concluída no cliente (`TaskTraceItem.checkTaskComplete`, `TaskFrameII` e `CompleteTaskTip`). O servidor não conclui e responde o 112 com o progresso atual (ver Recusa na seção de entrega).
- **Guia depois da 70**: 5185 (30111) responde 60 {30111, index 2, type 0} e 5017 responde 1 (#1254, #1257), com o herói do replay (nível 7, `30711,30811`, 1 ponto de skill). Teste `test_guia_depois_da_70_aprende_a_skill_e_avanca_o_novice`. O 8235 (leed, 5 sites) responde 4150 no replay (#1275-#1279), sem teste.

### Tipo 8: atacar castelo-robô

- Verificado (cliente): `CityInfoFrame` manda o 5160 com a posição do castelo, e a missão 100 procura o robô em (44,22) (m8, alvo 80_3).
- Servidor: `_castle_over` (handlers/outer_city.py) conta `quest_event(8, 1, 1)` na vitória. Para1 1 = vitória: 100 e 411 têm Para1 0 (qualquer), 765 tem 1.
- Dedução: a luta é a da mina (sem captura de castelo) e o ataque gasta o contador do dia. Ouro saqueado: sem fonte, sai 0.
- Premissa de desenho: o robô conta como alvo de tipo 8. Pelo dado, 100 e 411 pedem Para1 0 (qualquer alvo) e 765 pede Para1 1 (vitória), e a vitória no robô manda `quest_event(8, 1, 1)` (`_castle_over`). O texto da 100 fala em 'castelos dos jogadores próximos', e o guia 80_3 aponta para o robô. Se o desenho exigir castelo de jogador, o servidor deixa de contar o robô, e aí 100, 411 e 765 voltam a trava (falta PvP).
- Teste: `test_ataque_ao_castelo_robo_conta_a_missao_8_e_gasta_o_ataque`. Detalhes em [cidade-externa.md](cidade-externa.md).

### Tipos que não foram ligados

- **8 (Ocak Yağmala)**: ligado ao castelo-robô (seção *Tipo 8* acima). O `5160` ataca mina livre contra o guarda (isso é ocupar, tipo 7), e mina já ocupada é recusada. O robô recusa quem tem 18 níveis ou mais (`_attack_robot`, a mesma regra do cliente). Falta o PvP contra castelo de jogador: `8488` não tem alvo, e a 765 precisa dele acima de 17 níveis.
- **32 (Kaynak Topla)**: `Para1` é o item (2100022 Kereste, 2100023 Mor Kristal, 2100024 Bakır, `SonType` 210). Contagem na bolsa (`checkGoodsCount`), já ligada (`rules.goods_count`, só BAG; tabela: sim). Nenhum código do servidor cria esses itens (grep vazio em `src`). A coleta do espaço (8733) e a do tutorial (8699) não são implementadas. A coleta de campanha (5032 cmd 2, `CollectionAction`) é outra rota, e a entrada 8258 com a 6001 (Maden Ocağı, Types 2) é recusada com aviso, sem layout nem captura. Falta a fonte, que mexe em `items.py` e `drops.py`, fora do meu grupo.
- **33 (Hızlı Giriş Kullan)**: cliente (`checkClientLogin`) lê `DesktopManager.isDesktop`, um valor que a página manda pelo `ExternalInterface` (`IsDesktop`). Nenhum pacote avisa isso, e o `LoginReqMsg` só tem `playerId`, `key` e `ekeys`. Falta decidir como o servidor sabe que o cliente é o desktop.
- **48 (cadastro de celular)**: existe no template (missão 816), mas o servidor não tem nada de celular. O cliente manda `8524` (`CheckSend`, "já preencheu o celular?") e `8352` (`UserPin`, código do SMS), e nenhum handler responde. Falta: os dois handlers, guardar o número e um provedor de SMS.

## Desbloqueio (revisão 2026-10-17, revisor)

Nenhuma missão foi desbloqueada nesta revisão. O que impede cada grupo de bolsa, com a fonte:

- **Fechadas pela janela** (`EndDate` no passado): 8, 9, 13, 14, 15, 19, 770 e 771. O cliente recusa o aceite em `TaskManage.checkIsAchieved` (`TaskManage.as:340-349`: agora maior que `EndDate`), e `rules.can_accept` faz o mesmo. A 770 e a 771 têm `StartDate` igual a `EndDate` (2000-01-01), então a janela é vazia. Sem missão aberta, o item da condição não precisa de fonte.
- **846 a 856 (208012, Koyu Kristal)**: janela aberta (2000 a 2050), `IsLeague` e `IsRepeat`. Falta fonte servida para 208012. Busca por número isolado em todo o tempinfos e grep em `src` (sem nenhuma referência):
  - ShopTempInfos 755 (ShopType 7) e 810 (ShopType 10): têm `Score` 18 e `LordsScore` 1 (moeda de pontuação, não verificada no cliente). Todas as colunas de preço que o servidor cobra são 0, então `shop.price` devolve `None` e o 5154 recusa (`NO_ITEM`).
  - ActiveTempInfos 11 (Deneme Kulesi, `DropList`): `handlers/tower.py` só responde o info da torre (`tower_info`), sem progresso e sem recompensa.
  - FishTemplateInfos 1004 (`RewardId`): `minigames.fishing` manda pool vazio, então não há pesca.
  - Drop da cena de guilda (texto da 846: "Birlik ek sahnesinden [Koyu Kristal] toplayın"): não há tabela de drop nos dados e não há código de drop de cena no servidor.
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
| 1 | Seviyeyi Geliştir | 1 / 1; 1 / 20; 1 / 30 | 30 (7, 11, 12, 752, 772, 773, ...) | `checkPlayerGrades` | sim | rules.quest_done (PLAYER_LEVEL_CONDITION), nível lido na conclusão | nada: ligado. A missão 7 'Yılbaşı Gecesi' (P2=1) deixou de ser aceitável: a janela (2000-01-01) está fechada, como no cliente. | eu |
| 2 | Meclisi Geliştir | 901 / 2; 402 / 2; 1201 / 3 | 38 (51, 81, 82, 181, 182, 225, ...) | `checkBuildingOrTecGrades` | sim | rules.update_building_quests (castle.py:115, accept_quest) | — | outra equipe |
| 3 | Asker Çağır | 1 / 200; 2 / 100; 3 / 200 | 5 (52, 110, 764, 785, 786) | `checkCount` | sim | army.py:92 quest_event RECRUIT (soma) | — | outra equipe |
| 7 | Altın Ocağını İşgal Et | 2006 / 2 | 2 (60, 282) | `checkWilanCount` | sim | outer_city.py:266 quest_event OCCUPY (soma) | — | outra equipe |
| 8 | Ocak Yağmala | 0 / 1; 0 / 2; 1 / 1 | 3 (100, 411, 765) | `checkCount` | parcial | outer_city: `_castle_over` (handlers/outer_city.py), vitória contra o castelo-robô (Para1 1) | só o castelo-robô: PvP contra castelo de jogador segue sem alvo (8488). 765 precisa de PvP acima de 17 níveis. 411 presa pela 410. 100 fecha pelo robô, que conta pelo dado (seção *Tipo 8*). 765 é diária, não re-aceita (rules.py:282) e exige guilda (IsLeague). Ouro saqueado sem fonte. | eu |
| 10 | Mızraklı Askeri Geliştir | 1 / 3; 3 / 5 | 2 (101, 764) | `checkPawnGrades` | sim | army.py:178 quest_event PAWN_LEVEL (maior valor) | — | outra equipe |
| 12 | Bekleme Süresini Kaldır | 1 / 1; 1 / 3; 1 / 7 | 3 (111, 112, 113) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 14 | Vahşiler Düzlüğünü Geç | 1005 / 1; 1002 / 1; 1001 / 1 | 39 (21, 70, 120, 130, 250, 350, ...) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`, `_map_finished`); rules.quest_event (CAMPAIGN_CONDITION) | só a campanha 1001 tem nós no servidor. As outras 38 missões pedem campanhas 1002+ ou 9000+ (lista abaixo) | eu |
| 16 | Arena Savaşına katıl | 1 / 3; 1 / 5 | 2 (421, 422) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 17 | Bir Ekipmanı 3 Lv’ye Güçlendir | 2 / 1 | 1 (121) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 18 | Değerli Taş İşle | 1 / 1 | 1 (281) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 19 | Değerli Taş Birleştir | 0 / 1 | 1 (311) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 20 | Arkadaşına Enerji Doldur | 0 / 2; 1 / 2 | 4 (22, 260, 261, 271) | `checkCount` | sim | handlers/farm.py (15017) | Para1 exato: 1 a própria árvore, 0 a de amigo | castelo.md |
| 21 | Arkadaş Ekle | 0 / 1 | 1 (200) | `checkFriendsCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 22 | Birliğe Katıl/Birlik kur | 0 / 1 | 1 (220) | `checkJoinConsortia` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 23 | Avcıyı Öldür | 13000 / 1; 11600 / 1; 17000 / 1 | 7 (10, 20, 30, 40, 45, 50, ...) | `checkAttack` | sim | rules.update_novice_quests (campaign.py:506, accept_quest) | — | outra equipe |
| 25 | Ölümsüz Askerleri Öldür | 2041 / 4; 2042 / 3; 2043 / 2 | 34 (240, 450, 480, 490, 510, 560, ...) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`); rules.quest_event (PAWN_KILL_CONDITION) | conta por soldado do lado 2 da batalha. A 1001 tem o 2011, mas nenhuma missão de 25 aponta para ela. As 34 missões são de campanhas 1004 a 1602 (sem nós) | eu |
| 26 | Kurt Çenesini Öldür | 1011 / 1; 1031 / 1; 1041 / 1 | 30 (80, 210, 230, 280, 310, 470, ...) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`); rules.quest_event (HERO_KILL_CONDITION) | o chefe da 1001 (102109, template 1011) conta na 80. Os chefes de campanhas 1002+ e o da ilha dos pets (921) não têm gatilho | eu |
| 27 | “Yeni” Kelimesini Topla | 2125006 / 1; 2125007 / 1; 2125008 / 1 | 15 (8, 9, 13, 14, 90, 190, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte: vários itens das condições (2100003, 2100004, 2100006, 2100008, 2100009, 2100013) não têm fonte nos dados (só ItemTempInfo e a condição); a contagem não depende disso. A 90 fecha com 2100001 da 1001. Na 1001, 14 missões de 27 pedem itens sem fonte (lista abaixo) | eu |
| 28 | Kayıp Taş Topla | 2125011 / 3; 2100005 / 1; 2100007 / 1 | 12 (17, 300, 370, 460, 500, 540, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte: 2100005 e 2100007 não têm fonte nos dados; a contagem não depende disso | eu |
| 29 | Birlik Katkısı | 0 / 10; 0 / 50; 0 / 150 | 4 (221, 222, 223, 224) | `checkConsortiaOffer` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 30 | Birlik Bereketi | 0 / 1 | 1 (241) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 31 | Tek Kişilik Sahneden Geç | 1 / 3; 2 / 1 | 2 (313, 371) | `checkCount` | parcial | handlers/campaign.py (`_dungeon_loot`, fim de mapa); rules.quest_event (SOLO_CONDITION) | conta cena com capacidade = Para1 só na 1001 (capacidade 1). 313 fecha no servidor (`Para2` 3), mas a pré 310 bloqueia. 371 (capacidade 2) não tem cena | eu |
| 32 | Kereste Topla | 2100022 / 20; 2100024 / 10; 2100023 / 10 | 7 (55, 102, 140, 170, 171, 172, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), mesmo caminho da 27 | fonte: a pedreira 6001 (Resource Quarry), pela captura inglesa: 8258 entra, 5032 `cmd:2` colhe Wood x2/x3, 8699 luta dá Wood x18 ([salas-campanha.md](salas-campanha.md)). Coleta no espaço (8733) não é implementada | eu |
| 33 | Hızlı Giriş Kullan | 0 / 1 | 2 (1, 150) | `checkClientLogin` | não | — | sinal de cliente desktop: o cliente lê DesktopManager.isDesktop (JS da página, ExternalInterface 'IsDesktop') e nenhum pacote manda isso (LoginReqMsg só tem playerId, key e ekeys). Decisão de protocolo. | eu |
| 34 | Asker Modunu Ayarla | 0 / 1 | 1 (160) | `checkSortPawn` | sim | army.py:286 quest_event FORMATION (soma) | — | outra equipe |
| 35 | Meydan Oku | 1 / 3; 1 / 5; 1 / 1 | 3 (2, 4, 188) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 36 | Kader | 1 / 1; 0 / 1 | 2 (3, 622) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 37 | Özgürlük Otlağına Gir | 0 / 1; 0 / 2; 0 / 3 | 5 (173, 390, 580, 787, 826) | `checkMapId` | sim | update_state_quests (MAP_CONDITION, checkMapId); já estava no HEAD | — | outra equipe |
| 38 | Yeraltı Labirentine Katıl | 8001 / 2 | 1 (6) | `checkMazeRecord` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 39 | İkinci Gün Oyuna Giriş Yap | 0 / 1 | 1 (5) | `checkSencondLogin` | sim | rules.quest_done (LOGIN_DAY_CONDITION), dia UTC | nada: ligado. Compara o dia UTC do aceite com o de agora; o cliente usa o dia local (getDate). Se o fuso importar, trocar por um fuso fixo. | eu |
| 40 | Dünya Boss’a Katıl | 0 / 10; 0 / 1 | 2 (759, 761) | `checkCount` | sim | handlers/worldboss.py (fim da luta) | 1 por luta (dedução) | boss-eventos.md |
| 41 | Biriktirilmiş Zarar | 0 / 50000 | 1 (762) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 42 | Altın Topla | 0 / 1 | 1 (763) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 44 | Savaş Alanına Katıl | 0 / 1 | 2 (758, 766) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 45 | Savaş Alanında Düşman Öldür | 0 / 70; 0 / 2 | 2 (16, 767) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 46 | Ekipman Parçala | 0 / 1 | 1 (768) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 47 | Ekipman Arıt | 0 / 1 | 1 (769) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 48 | Cep Numaranı ve Onay Kodunu Gir | 0 / 1 | 1 (816) | `checkCount` | não | — | o servidor não tem nada de celular: o cliente manda 8524 (CheckSend) e 8352 (UserPin, código SMS) e nenhum handler responde. Falta: os dois handlers, guardar o número e um provedor de SMS. | eu |
| 49 | Koyu Kristal | 208012 / 6 a 36 (846 a 856); 2125012 / 5 (15); 2125013 / 50 (19); 2127001 / 10 (770); 2129001 / 5 (771) | 15 (15, 19, 770, 771, 846 a 856) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte (número isolado em todo o tempinfos): 208012 só em ShopTempInfos 755/810 (preço em Score/LordsScore, que `shop.price` não cobra), ActiveTempInfos 11 (Deneme Kulesi, sem recompensa no `tower.py`) e FishTemplateInfos 1004 (pesca fechada): nenhuma servida, então 846 a 856 travam (ver "Desbloqueio"). 2125013 sem fonte; 2125012 só como QuestGoods de outra missão; 2127001 na loja 149 (1 GiftToken; sem campo de bloqueio) e receita (só ingrediente); a contagem não depende disso | eu |
| 50 | Savaş Alanı Zaferi | 0 / 1 | 2 (18, 818) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 51 | Birlik Seviyesi | 1 / 2; 2 / 2 | 2 (819, 820) | `checkConsortuaGrade` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 52 | Asker Özelliği Aydınlat | 0 / 2 | 1 (821) | `checkCount` | sim | army.py:247 quest_event COMPREHEND (soma) | — | outra equipe |
| 53 | Kader Topu Kilitle | 0 / 1 | 1 (623) | `checkCount` | sim | stars.py:316 quest_event LOCK_QUEST (soma) | — | outra equipe |
| 56 | İhale | 0 / 1 | 1 (825) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 57 | Bereket Ruleti | 0 / 1 | 1 (857) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 58 | Şeytan Damgası | 0 / 1 | 1 (858) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 59 | Çiftlikte Ürün Ek | 0 / 1 | 2 (262, 859) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 60 | Çiftliğini Topla | 0 / 2; 1 / 2 | 4 (263, 266, 860, 861) | `checkCount` | sim | handlers/farm.py (op 4 e 5) | Para1 exato: 0 colher a própria, 1 roubar de amigo | castelo.md |
| 61 | Böcek Temizle | 1 / 2 | 2 (267, 862) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 63 | Devotion (Emek Oranı) | 0 / 20 | 1 (863, diária `IsRepeat`) | `checkCount` | sim: maior total de devoção do dia (`LEVEL_CONDITIONS`) | `handlers/events.leed_gain`/`devotion_quests` (ganhos e 1º login do dia) | aceite nasce com 0 mesmo com devoção já ganha (visto, tutorial_en #3199); só o próximo ganho grava o total. Reabre no dia do jogo seguinte (`_repeat_ok`) | — |
| 64 | Simya | 0 / 3 | 1 (184) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 65 | Ruh Topla | 0 / 3 | 1 (185) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 66 | Dünya BOSS'ta Hemen Savaş | 0 / 3 | 1 (183) | `checkCount` | sim | handlers/worldboss.py (8264 pago) | 1 por reviver pago | boss-eventos.md |
| 71 | Binek Eğitimi | 0 / 1 | 1 (753) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 74 | Deneme Kulesine Gir | 0 / 1 | 1 (799) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 76 | Saldırma Sembolünü Öğren | 2 / 1; 1 / 1 | 2 (906, 907) | `checkRuneStudy` | sim | update_state_quests (RUNE_STUDY); já estava no HEAD | — | outra equipe |
| 77 | Ufak Sembol Taşını Birleştir | 3020010 / 5; 0 / 10; 3020004 / 20 | 3 (186, 908, 909) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 78 | Sembol Geliştir | 0 / 3; 5 / 150; 0 / 5 | 6 (910, 911, 916, 917, 918, 919) | `checkRuneGrade` | sim | update_state_quests (RUNE_GRADE, LEVEL_CONDITIONS); já estava no HEAD | — | outra equipe |
| 79 | Top Arabası Etkinliği | 0 / 1; 3001 / 1 | 2 (912, 914) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 80 | Top Arabası Zaferi | 0 / 1; 3001 / 1 | 2 (913, 915) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 85 | Jesi İle Konuş | 0 / 1 | 10 (174, 175, 191, 229, 272, 283, ...) | `checkFinishPetStory` | parcial | space.py talk (8692) e player.py quest_add (aceite), perto do nó | parcial: MasterType 61 (Tina 361, Asina 229, Lili 272, Larry 283, Anna 922, Badin 933) conta no 8692 e no aceite perto do nó. Patrulha (MasterType 1: Jesi 174/191, Koruma 175, Rona 301): o cliente não manda 8692; só conta no aceite se a posição do modelo estiver perto (não validado). O servidor não vê o fim do diálogo. | eu |
| 86 | Altın Ocağı Savaşına Katıl | 0 / 1 | 1 (503) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 87 | Peri Turnuvasına Katıl | 0 / 1 | 1 (504) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 89 | Hazine Harita Kazısına Katıl | 0 / 1 | 1 (925) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 90 | Direnç Kristali Mozaiği Yap | 0 / 1 | 1 (926) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 91 | Define Avı | 0 / 1 | 1 (930) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 93 | Gökyüzü Yolunda Zafer Kazan | 0 / 1 | 1 (932) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |

## Missões bloqueadas para as masmorras 1002+

Lista calculada do `tempinfos.xml` do overlay: missões com condição 8, 14, 25, 26, 27 ou 31 que a masmorra 1001 não cumpre. Total: 119 missões. Fecham com a 1001: 70, 80 e 90. A 313 fecha no servidor, mas a pré 310 a deixa travada.

Para as masmorras 1002+ destravarem uma missão, precisam de nós e lutas (`content/dungeon_<id>.json`, a partir de captura; `tools/extract_dungeon.py` só serve à 1001 hoje), do fim de mapa com o grupo caído e dos drops. Sem captura dos nós, nenhuma dessas missões fecha.

- **14, campanha sem nós (38)**: 21 (1005), 120 e 130 (1002), 250 (1005), 350 (9000), 380 (1101), 410 (1102), 430 (1103), 440 (1104), 530 (9002), 650 (9003), 720 (1205), 754 (9104), 760 (9004 e 9104), 784 (9005 e 9105), 801 (1302), 803 (1304), 805 (1306), 807 (1308), 828 (1402), 830 (1404), 832 (1406), 843 (9006 e 9106), 845 (9007 e 9107), 879 a 885 (1501 a 1507), 894 (9008 e 9108), 896 (9009 e 9109), 897 (1601), 898 (1602), 902 (9010 e 9110), 904 (9011 e 9111), 924 (9012 e 9112).
- **26, chefe de campanha sem nós (29)**: 210 (1003), 230 (1004), 280 (1006), 310 (1007), 470 (1105), 550 (1107), 590 (1201), 620 (1202), 660 (1204), 670 (1203), 740 (1207), 750 (1206), 783 (9005), 800 (1301), 802 (1303), 804 (1305), 806 (1307), 827 (1401), 829 (1403), 831 (1405), 833 (1407), 842 (9006), 844 (9007), 893 (9008), 895 (9009), 901 (9010), 903 (9011), 923 (9012). A 921 (`Para3` 0, chefe 20010 da ilha dos pets) entra aqui também: a ilha tem dados em `petisland.json`, mas o servidor não emite a condição 26 nela.
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
- **Login**: o login manda só as missões abertas (`handlers/login.py:216`, `not q.completed`), então a repetível concluída não aparece lá. Quando o cliente a re-oferece (IsAuto, depois do `RepeatInterval`), o 5012 a reabre na mesma linha (`accept_quest`). A captura citada no código (login.json #89) mostra a 241 aberta com `completedDate` antigo e o bit do `states` ligado. O bit fica ligado (`ever_completed`), mas a missão não vai no login: diferença de exibição, em aberto.
- **Sem migração nova**: a entrega não guarda estado pendente, então nada muda no banco.
- **5017 (passo do novice)**: o cliente só manda valor positivo e múltiplo de 100 (cliente: `sendSaveProcess`, m8). A ordem crescente vem do guia (`newbie.xml`). O replay tem 29 avanços positivos, de 100 a 1500, de 11000 a 25500, e um pedido repetido (22800 duas vezes), que o servidor ignora (visto). O teto de 3500 é o maior salto do guia, de 28500 para 32000 (dedução: não há captura de salto maior). O painel de depuração do cliente (m8, `QVKZDKIyIBJ.as`, `__onSaveClick`) manda o id digitado sem esse teto: se ele existir em produção, o servidor recusa saltos acima de 3500 (não verificado).
- **Revisão**: as linhas de [missoes-revisao.md](missoes-revisao.md) marcadas com "Revisão 2026-10-17" dizem o que mudou por missão.
- **Mudança de comportamento (5014)**: `RewardStrategy` agora é paga na entrega, antes ignorada. São 20 missões com valor (a 90 dá 1000 de Ruh; o total no template é 875000). Conferido no replay para a 90 (PlayerMsg 3, #1610 → #1612).
- **Mudança de comportamento (aceite)**: `Para1` em lista (17 missões, tipos 14 e 26) não derruba mais o aceite (`rules.para1_ids`).
- **Mudança de comportamento (missões 70, 80, 90)**: as três fecham jogando a 1001 do começo ao fim (teste `test_missoes_70_80_90_fecham_jogando_a_1001_do_comeco_ao_fim`). A 70 vira concluída, e o guia 24007 (c12(70)) libera o guia de habilidade 24000. Verificado até o 5017 (teste do guia); o 8235 (leed) não tem teste.
