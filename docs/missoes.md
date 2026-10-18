# Missões: como o servidor conta o progresso

Missões são `QuestTemps` (título, recompensa, janela) com uma ou mais linhas em `QuestCondictionInfos` (condições). Fontes do que está aqui: `data/overlay/xml/tempinfos.xml`, o cliente decompilado (`TaskTemplate.as`, `SpaceArmyViewHelper.as`, `SpaceDialogFrame.as`, `TaskMobilePhoneView.as`, `DesktopManager.as`) e as capturas. Código: `src/wartune_server/game/rules.py`, `handlers/player.py` (5012 e 5014), `builders/player.py` (112).

## Fluxo no servidor

1. **Aceite (5012)**: `quest_add` chama `rules.accept_quest`, que confere o que o cliente confere antes de aceitar (`TaskManage.isAvailableTask`, em `rules.can_accept`): janela `StartDate`..`EndDate`, `NeedMinLevel`..`NeedMaxLevel`, `IsLeague` (exige guilda) e `PreQuestId` (lista com vírgula é E; pré-requisito que não existe nos dados é ignorado). Missão já aberta não reabre. Repetível (`IsRepeat`) concluída reabre na mesma linha, só quando o dia do jogo mudou (o dia vira às 5h, como `checkInRepeatTime`). Depois roda as condições de tutorial (23), de prédio (2) e de estado (bolsa, mapa da cidade, símbolos). Missões de conversa (85) são conferidas aqui também.
2. **Progresso**: cada ação chama `rules.quest_event(snap, templates, tipo, para1, valor)`. Em cada missão aberta, cada linha com `CondictionType == tipo` e `Para1` igual (0 = qualquer) avança o contador da sua posição. Depois grava e manda o 112.
3. **Conclusão (5014)**: `quest_finish` atualiza o estado de bolsa e `rules.quest_done(snap, templates, q, agora)` confere. Se alguma condição não bate, responde o 112 com o progresso atual (`isComplete` falso, sem 52). Se bate, confere a mochila, manda o 112 do progresso, consome os itens das condições de bolsa, paga a recompensa (`rules.pay_quest_rewards`) e manda 3, 112 (concluída), 83, 150, 3, 115 (itens) e 52. Detalhes em "Entrega (5014)" abaixo.

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
- **Bolsa (quantidade atual)**: tipos 27, 28, 32 e 49. No cliente é `checkGoodsCount`, a quantidade do item `Para1` na bolsa `>= Para2`. O servidor conta a quantidade atual do item na mochila (`rules.goods_count`, só `BagType.BAG`, como `GoodsManager.countGoods`) no aceite, a cada mudança de estado e na entrega. Na entrega, a condição consome o item (abaixo).
- **Estado de mapa e de símbolo (37, 76, 77, 78)**: `update_state_quests` julga pelo que já existe (`checkMapId`, `checkRuneStudy`, `checkRuneGrade`), então quem aceita depois do fato já nasce com o progresso.

## Entrega (5014)

- **Reavaliação**: os três caminhos do cliente que mandam o 5014 (`TaskFrameII.as:590`, `TaskTraceItem.as:583`, `CompleteTaskTip.as:115`) só agem com `isCompleted` local. Por isso o servidor reavalia no 5014 e conclui quando a condição bate, sem guardar "entrega pendente".
- **Recusa**: sem a condição, o 5014 responde o 112 com o progresso atual (`condition_N` = quantidade atual), `isComplete` falso e sem 52. Antes a resposta era silêncio, e o botão de entrega ficava sem retorno.
- **Consumo de bolsa**: a entrega tira da mochila todas as unidades do `Para1` de cada condição de bolsa (`rules.goods_to_take`). Observado uma vez (visto): replay #1609, a pilha do 2100001 foi de 10 para zero ao entregar a 90, cuja condição pede 8. Se a regra oficial for tirar só `Para2`, a captura contradiz (sobrariam 2). A dúvida fica aberta.
- **Mochila**: conta os espaços que a própria entrega libera (as pilhas consumidas). Se não couber a recompensa, aviso 111 "Çantanız dolu." e recusa sem consumir nada.
- **Sem linha de condição**: a missão não conclui (`quest_done` devolve falso). Nenhuma missão dos dados está assim; o caso existe para id inexistente.

## Recompensas (5014)

- **Paga** (`rules.pay_quest_rewards`, como `TaskRewardViewII._rewardList`): EXP `RewardPlayGP` (com o bônus diário `(nível - NeedMinLevel) * 500` quando `TemplateType` é 1), ouro `RewardGold`, `RewardStrategy` (ruh, `Character.strategy`), `RewardCrystal` (`Character.crystals`), `RewardPlayerOffer` (oferta do personagem), `RewardConsortiaOffer` (oferta da guilda, creditada na guilda do jogador; sem guilda não há onde pôr) e os `QuestGoods`.
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

### Tipos que não foram ligados

- **8 (Ocak Yağmala)**: missão 100 pede atacar cidade inimiga (`P1 = 0`, `P2 = 1`), 411 pede 2 ataques a cidade de jogador, e 765 é diária com `P1 = 1`. O servidor não tem ataque PvP a castelo: `8488` não tem alvo e só registra. O `5160` ataca mina livre contra o guarda (isso é ocupar, tipo 7), e mina já ocupada é recusada. Falta o ataque PvP a castelo.
- **32 (Kaynak Topla)**: `Para1` é o item (2100022 Kereste, 2100023 Mor Kristal, 2100024 Bakır, `SonType` 210). Contagem na bolsa (`checkGoodsCount`). Nenhum código do servidor cria esses itens (grep vazio em `src`). A coleta do espaço (8733) e a do tutorial (8699) não são implementadas. Depois de haver fonte, a avaliação é pela bolsa, o que mexe em `items.py` e `drops.py`, fora do meu grupo.
- **33 (Hızlı Giriş Kullan)**: cliente (`checkClientLogin`) lê `DesktopManager.isDesktop`, um valor que a página manda pelo `ExternalInterface` (`IsDesktop`). Nenhum pacote avisa isso, e o `LoginReqMsg` só tem `playerId`, `key` e `ekeys`. Falta decidir como o servidor sabe que o cliente é o desktop.
- **48 (cadastro de celular)**: existe no template (missão 816), mas o servidor não tem nada de celular. O cliente manda `8524` (`CheckSend`, "já preencheu o celular?") e `8352` (`UserPin`, código do SMS), e nenhum handler responde. Falta: os dois handlers, guardar o número e um provedor de SMS.

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
| 8 | Ocak Yağmala | 0 / 1; 0 / 2; 1 / 1 | 3 (100, 411, 765) | `checkCount` | não | — | PvP contra castelo: 8488 não tem alvo (outer_city.pvp_army só registra) e 5160 só ataca mina livre contra o guarda (isso é ocupar, tipo 7). 100 pede cidade inimiga, 411 pede 2 ataques a cidade de jogador, 765 é diária com P1=1. | eu |
| 10 | Mızraklı Askeri Geliştir | 1 / 3; 3 / 5 | 2 (101, 764) | `checkPawnGrades` | sim | army.py:178 quest_event PAWN_LEVEL (maior valor) | — | outra equipe |
| 12 | Bekleme Süresini Kaldır | 1 / 1; 1 / 3; 1 / 7 | 3 (111, 112, 113) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 14 | Vahşiler Düzlüğünü Geç | 1005 / 1; 1002 / 1; 1001 / 1 | 39 (21, 70, 120, 130, 250, 350, ...) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 16 | Arena Savaşına katıl | 1 / 3; 1 / 5 | 2 (421, 422) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 17 | Bir Ekipmanı 3 Lv’ye Güçlendir | 2 / 1 | 1 (121) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 18 | Değerli Taş İşle | 1 / 1 | 1 (281) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 19 | Değerli Taş Birleştir | 0 / 1 | 1 (311) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 20 | Arkadaşına Enerji Doldur | 0 / 2; 1 / 2 | 4 (22, 260, 261, 271) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 21 | Arkadaş Ekle | 0 / 1 | 1 (200) | `checkFriendsCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 22 | Birliğe Katıl/Birlik kur | 0 / 1 | 1 (220) | `checkJoinConsortia` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 23 | Avcıyı Öldür | 13000 / 1; 11600 / 1; 17000 / 1 | 7 (10, 20, 30, 40, 45, 50, ...) | `checkAttack` | sim | rules.update_novice_quests (campaign.py:506, accept_quest) | — | outra equipe |
| 25 | Ölümsüz Askerleri Öldür | 2041 / 4; 2042 / 3; 2043 / 2 | 34 (240, 450, 480, 490, 510, 560, ...) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 26 | Kurt Çenesini Öldür | 1011 / 1; 1031 / 1; 1041 / 1 | 30 (80, 210, 230, 280, 310, 470, ...) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 27 | “Yeni” Kelimesini Topla | 2125006 / 1; 2125007 / 1; 2125008 / 1 | 15 (8, 9, 13, 14, 90, 190, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte: vários itens das condições (2100001, 2100003, 2100004, 2100006, 2100008, 2100009, 2100013) não têm fonte nos dados (só ItemTempInfo e a condição); a contagem não depende disso | eu |
| 28 | Kayıp Taş Topla | 2125011 / 3; 2100005 / 1; 2100007 / 1 | 12 (17, 300, 370, 460, 500, 540, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte: 2100005 e 2100007 não têm fonte nos dados; a contagem não depende disso | eu |
| 29 | Birlik Katkısı | 0 / 10; 0 / 50; 0 / 150 | 4 (221, 222, 223, 224) | `checkConsortiaOffer` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 30 | Birlik Bereketi | 0 / 1 | 1 (241) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 31 | Tek Kişilik Sahneden Geç | 1 / 3; 2 / 1 | 2 (313, 371) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 32 | Kereste Topla | 2100022 / 20; 2100024 / 10; 2100023 / 10 | 7 (55, 102, 140, 170, 171, 172, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), mesmo caminho da 27 | fonte dos recursos 2100022/23/24: nenhum código do servidor cria esses itens (grep vazio em src); coleta no espaço (8733) e no tutorial (8699) não é implementada | eu |
| 33 | Hızlı Giriş Kullan | 0 / 1 | 2 (1, 150) | `checkClientLogin` | não | — | sinal de cliente desktop: o cliente lê DesktopManager.isDesktop (JS da página, ExternalInterface 'IsDesktop') e nenhum pacote manda isso (LoginReqMsg só tem playerId, key e ekeys). Decisão de protocolo. | eu |
| 34 | Asker Modunu Ayarla | 0 / 1 | 1 (160) | `checkSortPawn` | sim | army.py:286 quest_event FORMATION (soma) | — | outra equipe |
| 35 | Meydan Oku | 1 / 3; 1 / 5; 1 / 1 | 3 (2, 4, 188) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 36 | Kader | 1 / 1; 0 / 1 | 2 (3, 622) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 37 | Özgürlük Otlağına Gir | 0 / 1; 0 / 2; 0 / 3 | 5 (173, 390, 580, 787, 826) | `checkMapId` | sim | update_state_quests (MAP_CONDITION, checkMapId); já estava no HEAD | — | outra equipe |
| 38 | Yeraltı Labirentine Katıl | 8001 / 2 | 1 (6) | `checkMazeRecord` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 39 | İkinci Gün Oyuna Giriş Yap | 0 / 1 | 1 (5) | `checkSencondLogin` | sim | rules.quest_done (LOGIN_DAY_CONDITION), dia UTC | nada: ligado. Compara o dia UTC do aceite com o de agora; o cliente usa o dia local (getDate). Se o fuso importar, trocar por um fuso fixo. | eu |
| 40 | Dünya Boss’a Katıl | 0 / 10; 0 / 1 | 2 (759, 761) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 41 | Biriktirilmiş Zarar | 0 / 50000 | 1 (762) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 42 | Altın Topla | 0 / 1 | 1 (763) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 44 | Savaş Alanına Katıl | 0 / 1 | 2 (758, 766) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 45 | Savaş Alanında Düşman Öldür | 0 / 70; 0 / 2 | 2 (16, 767) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 46 | Ekipman Parçala | 0 / 1 | 1 (768) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 47 | Ekipman Arıt | 0 / 1 | 1 (769) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 48 | Cep Numaranı ve Onay Kodunu Gir | 0 / 1 | 1 (816) | `checkCount` | não | — | o servidor não tem nada de celular: o cliente manda 8524 (CheckSend) e 8352 (UserPin, código SMS) e nenhum handler responde. Falta: os dois handlers, guardar o número e um provedor de SMS. | eu |
| 49 | Koyu Kristal | 2125012 / 5; 2125013 / 50; 2127001 / 10 | 15 (15, 19, 770, 771, 846, 847, ...) | `checkGoodsCount` | sim | rules.goods_count (só BAG), update_state_quests (GOODS_CONDITIONS), quest_done; a entrega consome (5014) | fonte: 2125013 não tem fonte nos dados; 2125012 só aparece como recompensa de missão; 2127001 tem loja e receita (ComposeTempInfo); a contagem não depende disso | eu |
| 50 | Savaş Alanı Zaferi | 0 / 1 | 2 (18, 818) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 51 | Birlik Seviyesi | 1 / 2; 2 / 2 | 2 (819, 820) | `checkConsortuaGrade` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 52 | Asker Özelliği Aydınlat | 0 / 2 | 1 (821) | `checkCount` | sim | army.py:247 quest_event COMPREHEND (soma) | — | outra equipe |
| 53 | Kader Topu Kilitle | 0 / 1 | 1 (623) | `checkCount` | sim | stars.py:316 quest_event LOCK_QUEST (soma) | — | outra equipe |
| 56 | İhale | 0 / 1 | 1 (825) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 57 | Bereket Ruleti | 0 / 1 | 1 (857) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 58 | Şeytan Damgası | 0 / 1 | 1 (858) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 59 | Çiftlikte Ürün Ek | 0 / 1 | 2 (262, 859) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 60 | Çiftliğini Topla | 0 / 2; 1 / 2 | 4 (263, 266, 860, 861) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 61 | Böcek Temizle | 1 / 2 | 2 (267, 862) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 63 | Emek Oranı | 0 / 20 | 1 (863) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 64 | Simya | 0 / 3 | 1 (184) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 65 | Ruh Topla | 0 / 3 | 1 (185) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
| 66 | Dünya BOSS'ta Hemen Savaş | 0 / 3 | 1 (183) | `checkCount` | não | — | não contado; não verificado neste trabalho | outra equipe |
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

## Notas para o integrador

- **Migração**: o branch já mesclou o milestone-1; a `0022_progresso_das_condicoes_da_missao.py` desce da `0021_copias_de_campanha_em_grupo.py` (uma head só).
- **Assinatura**: `rules.quest_done(snap, templates, q, now)` agora exige `now`. Chamador novo em outra equipe precisa passar o relógio.
- **Mudança de comportamento intencional**: a missão 764 (recrutar 200 do tipo 3 e tropa do tipo 10 no nível 5) passou a exigir as duas linhas. Antes concluía só com o recrutamento.
- **Junção no worktree**: `data\overlay` é uma junção para `D:\wartune\servidor\data\overlay`. Antes de apagar o worktree, desfazer só a junção pelo gerenciador de links do Windows, nunca por exclusão recursiva, que pode atravessar a junção e apagar a pasta real.
- **Tipos de outra equipe**: as colunas "Contado" e "Onde" das linhas "outra equipe" refletem o código deste branch, então o integrador deve conferir essas linhas depois da mescla.
- **Aceite e entrega (2026-10-17)**: o 5012 agora recusa o que o cliente também recusa (janela, nível, guilda, pré-requisito, repetição). Missões dos dados que estão vencidas ou com pré-requisito deixaram de nascer pelo 5012. Nos testes, 11, 5, 361, 906, 910, 390 e 173 entram abertas direto na sessão, ou com o pré-requisito concluído (`_done`), porque nos dados estão vencidas ou têm pré-requisito. O teste de conversa no aceite usa a 922 (a 361 venceu em 2000).
- **Login**: missão repetível concluída continua aparecendo como concluída no login (`repeatFinish` 1). O oficial a mostra aberta com `completedDate`. Não espelhado; fica em aberto.
- **Sem migração nova**: a entrega não guarda estado pendente, então nada muda no banco.
- **Revisão**: as linhas de [missoes-revisao.md](missoes-revisao.md) marcadas com "Revisão 2026-10-17" dizem o que mudou por missão.