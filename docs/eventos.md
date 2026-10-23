# Eventos, atividades, recompensas, VIP e minigames

Handlers em `game/handlers/events.py` (atividades, assinatura, leed, guia de 7 dias),
`vip.py` (VIP, contrato do rei, alquimia, alma, loja do teste), `offer.py` (painel de recompensas
e anel) e `minigames.py` (o resto). Fonte de cada regra: *(visto)* = captura oficial, *(cliente)* =
código decompilado, *(dedução)* = nenhum dos dois mostra, escolha nossa.

## Estado no banco

- **`event_states`** `(character_id, key, value, text, updated_at)`, única por `(character_id, key)`.
  Toda marca/contador de personagem é uma linha. `game/events.py`: `state` cria, `peek` lê,
  `daily` zera se a última mudança foi em outro dia (UTC, o relógio do `sysCurtime`).
  Chaves: `login`, `relogin`, `sign`, `leed:<id>`, `leedbox`, `serven`, `sum:<active>[:<pacote>]`,
  `vip` (value = vipGp, text = fim), `vipgift:next` (text = próxima liberação do presente),
  `vip:type` (value = `vipType`), `vipwheel` (text = JSON das posições já tiradas), `king:<id>` (text = fim),
  `king:fetch`, `alchemy`, `soul`, `offer:list` (JSON das 4 vagas), `offer:task`, `offer:free`,
  `offer:count`, `ring`, `fund:novice`, `fund:novice:get:<times>`.
- **`cash_ledger`** `(character_id, delta_point, delta_gift_token, balance_point,
  balance_gift_token, reason, ref, gm, created_at)`: todo gasto de diamante passa por
  `services/ledger.spend`, que devolve a linha para entrar na **mesma** `save` do que foi comprado.
  `gm` fica nulo (reservado para ajuste manual).
- Migração `0003_estado_de_eventos_e_livro_caixa_de_`.

## Concessão de recompensa

`game/rewards.py`: `can_grant` (TemplateId existe, quantidades > 0, cabe na mochila de 42),
`grant` (moedas negativas -100 ouro, -300 Daru, -400 diamante, -500 vinculado, -700 EXP; itens com
`DefaultSkill`), `text` (`Received: ...` nos dois estilos do oficial inglês: "Received: 50,000 Gold, Moderate HP Pack
x1", #2110, e "Received: Bound Balens x 10,Daru x 10000,...", #2772), `take_one` (consome 1 item).
O 5006 da mochila usa o mesmo código. Depois de gravar, `handlers/player.granted` manda 3, 150
(EXP), 109 (ouro), 115 (itens) e 83.

- ponytail: -600 "Kyanite" não existe no banco; é aceito e descartado (fora do texto).

## Atividades (SumActive) e login

Definições do operador em **`data/events.json`** (`config.events_file`): `dataStamp` (subir quando
mudar) e `actives[]` com GUIDs, datas, pacotes, itens e condições. Vêm preenchidos o Login Bonus
(tipo 13, os dois pacotes do "10/15 Login Bonus I" da inglesa #60) e o presente online (tipo 14: 10 min, depois
30 min x3; o -600 da captura virou -500; só turco: login.json), os dois sem fim (2099: o painel mostra a contagem
até lá, "Countdown: 26732 Day"), e depois **as 41 atividades do oficial inglês** (#60-#67, GUIDs, textos, pacotes e
datas de 2026-10-01 a 2026-11-04, iguais byte a byte: `test_atividades_troca`). Passado 2026-11-04 só sobram as
duas do operador: novas atividades entram no arquivo com outras datas e o `dataStamp` sobe.

- Pacote: `condition` = `[conditionId, conditionValue, conditionBak, Bak2, Bak3, Bak4]` (zeros do fim podem
  faltar); `items` = `[TemplateId, quantidade]` ou `[TemplateId, quantidade, templateType]`; `templateType` 4 é o
  custo da troca (aparece no pacote, não é dado); `limit` = trocas por jogador no tipo 10 (o `getCount` do 4476 #68
  no personagem novo: 1, 10 ou 200; ausente = sem limite).
- O painel recebe **toda atividade que ainda não acabou**, também as que vão começar (#60, às 10-18, já manda as de
  10-22 a 10-31; o cliente só descarta `stopTime` passado, `FunnyManager.__funnyTemHandler`, e mostra a data de
  início no lugar da contagem, `FunnyBagView.setRemainTime`). Antes do `beginDate` todo pacote vai 3 e o resgate é
  recusado; contadores só somam nas que já começaram.
- Os testes usam um catálogo fixo (`tests/fixtures/events.json`, as duas do operador), não o do operador.

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4475 em páginas de até 12.000 bytes e logo o 4476 de todas, sem pedido; outro 4476 no 8586 tipo 1 | (visto) tutorial_en #60-#68, #76 |
| ganho de item | 4476 de todas logo depois do 115 que dá item (missão, carta, drop, caixa, presente VIP); mover, vestir e gastar não mandam | (visto) tutorial_en: 26 dos 61 115 (#352, #490, #1112, #2927, #3268) |
| 8586 type 1 | 4476 com `status` 1/2/3 e `countDown` (tipo 14) | (visto) |
| 8586 type 2 | valida status=1 e mochila; ordem 3, 109, 115, 4476 de todas, 111, 4476 só desta, 83 | (visto) tutorial_en #2753-#2772 |
| 8266 | assina o dia: bit `1 << (dias_do_mês - dia)` em `signSite`; `SignDrop` ao chegar num `Times`; 4177 | (cliente) DayGuideCatecory |
| 8496 | dia `index` do login acumulado (`ReloginDrops.Times`), exige `index <= dias logados`; 3 com `reloginProcess` | (cliente) |
| 8749 | guia de 7 dias: dia alcançado (contado da conclusão da missão 130), tarefas do dia feitas, `ServenLeadRewards`; 4638 | (visto) login.json #93 (só turco: a inglesa não tem 8749) |
| login, 5014 (130) | 4638 só depois de concluir a missão 130 (`beginTime` = conclusão dela) | (visto) tutorial_en #3187-#3193 |
| volta da campanha | 4638 de novo (o oficial manda logo depois do 4152 e mais 5 cópias iguais depois do 83; aqui um, depois do 83) | (visto) oficial_encantar #694-#706 |
| qualquer pedido | 4638 de novo se uma tarefa ou prêmio mudou desde o último (o cliente nunca pede o painel: `GuideTaskManager` só escuta o 4638); só fora de campanha e batalha | (dedução) |
| login | 4247 com os eventos de EXP em curso (`exp_rate_events`), logo depois do 4686; multiplicador não aplicado (o EXP das capturas já inclui o evento) | (visto) tutorial_en #44-#46 |
| 5019 | baú online: conta só depois do 1º 5019; resgate zera; 109 (ou 3), 115, 111, 4250, 4, 83 "Received: ...", 83 "Reward retrieval successful!" | (visto) tutorial_en #1594-#1598, #2097-#2114 |
| 8234, 8322 | só devolvem 4152 (o 8322 vem do login com `templateId` 1, como oficial_encantar #25/#52; o 8234 nenhuma tela manda; o progresso vem do servidor) | (cliente), (visto) |
| 8235 | baú `site` 1..5 da atividade diária (10/40/60/80/100 pontos), `LeedDrop`; 4150 | (cliente) |
| 8518 | 4412 vazio (contadores do painel do dia) | (cliente) |

- Cliente: `FunnyManager`. Atividade com `stopTime` passado é descartada; o cache só troca quando
  `dataStamp` sobe. O oficial inglês mandou 4 páginas, 41 atividades, `dataStamp 3` (#60-#67).
- `activeType` vistos (inglesa #60-#67): 1 gasto diário, 10 troca, **13 login**, 15 primeira recarga, 18 montaria,
  27 anfiteatro, 28 campo de batalha, e 11, 12, 22, 46-48, 58, 59, 100, 101, 107, 109, 111, 118; **14 presente
  online** (`conditionValue` = segundos) e 35 fadas só no turco (login.json).
- Tipo 13 (Login Bonus): um resgate por dia de cada pacote ("Claim them once everyday."); condição 14 valor 1 =
  todos ("During the event, non-VIP players can check-in", `FunnyBagData` title14), 2 = só VIP (title15). Na
  inglesa o normal vem 1 já no login (#68) e o VIP fica 3 até a conta virar VIP (#3268); o VIP pega os dois. Tipo
  14 soma segundos online desde o último resgate (zera a cada presente, gravado na desconexão e no resgate).
- Contadores por ação (`game/events.py` `count`, estado `sum:<activeId>`; o 4476 leva o contador em `value`):
  21 Gold Alchemy (8321), 22 Daru Alchemy (8467), 26 desafio do coliseu (8253, no início), 108 giro do destino
  (8627, por giro), 109 fusão do destino (8626, por carta) e 110 Sylph Arena (fim da luta de fadas). 12 =
  devoção do dia (soma dos `Num` dos leeds de hoje, condição 13). Diário (zera no dia do jogo): 12, 14, 108, 109
  e 110, pelos textos "today" do cliente (`funny.FunnyRightView`); 21, 22 e 26 contam o período todo (texto sem
  "today": **dedução**). O resgate do diário marca o dia; o do período, o período.
- Troca (tipo 10, `getway` 2, condição 11): vale (1) com `conditionValue` do item `conditionBak` na mochila e
  limite sobrando; 8586 tipo 2 com `count` (o `FunnyMutiFrame` escolhe; `count` × custo, `count` × itens); o
  `getCount` do 4476 = trocas que ainda cabem (0 = sem limite), e com o limite usado o pacote vai 2 (pego); estado `sum:<active>:<pacote>` =
  trocas feitas no período. Resposta: 115 do que saiu, depois a do resgate (3, 109, 115, 4476, 111, 4476 desta, 83).
  **Dedução**: a inglesa não troca nada; o significado do `getCount` vem do cliente (`FunnyBagItem`, `mutiMaxNum`).
- Gasto (tipo 1 "Spending Bonus", condição 9): soma os **Balens** (não os vinculados) que caíram em qualquer
  pedido, no mesmo ponto do leed 15 (`GameSession.on_packet`); conta o período (cada uma dura um dia na inglesa).
  **Dedução**: sem captura de gasto em inglês; "Spend" no texto.
- `activeCharge` do 4476 vai 0: a inglesa #68 manda 1 em parte das trocas e de outras sem regra visível (o cliente
  só o lê no tipo 4, `regressionActiveCost`).
- Outros `activeType` ficam "ainda não" (3), cada um **depende de** um sistema: 15 recarga de Balens
  (cash), 18 cultivo de montaria, 2 montaria, 5 refino, 7 honra, 9 recarga, 11 moda, 19 selo de alma,
  20 astrologia, 23 recompensa, 24 mistério, 25 runa, 27 anfiteatro, 28 campo de batalha, 100-102 runas e cartas,
  105 torre do rei, 106/107 roda, 111 campo minado, 112 pesca, 113 trilhas, 118 labirinto. O 4476 sai no pedido
  (8586 tipo 1), no login e depois de cada 115 de ganho (acima); **precisa de captura**: se o oficial também empurra
  quando um contador sobe sem item.
- 8586 tipo 2 da inglesa #2753 (pacote do "10/15 Login Bonus I") é o mesmo resgate; a recusa vinha só dos GUIDs do
  catálogo do operador, diferentes dos oficiais (o oráculo do tutorial troca pelos nossos).
- Leed = **devoção** (dayGuide "Daily devotion"; `totalNum` do 4152 = soma dos `Num` dos `LeedTemp` completos no
  dia; zera na virada do dia do jogo, `ev.daily`). Contam: login 1 (1º login do dia), 4 "Complete a solo dungeon"
  (saída do mapa do tutorial, tutorial_en #521, e fim de etapa de campanha com `Capacity` 1), 5 (fim de etapa com
  `Capacity` > 1, dedução), 9 (ocupar mina, #748), 10 "Plunder another player" (5160 no castelo-robô, já no ataque,
  #1649), 12 (bênção da guilda, 5145), 16 (chat no mundo), 19 (desafio do coliseu, 8253), 20 (entrega de missão
  `TemplateType` 1 "Daily"). Um sistema novo chama `events.leed_done(s, template_id)` (ou `leed_gain`, sem await, e
  grava depois). Ganchos do resto da `LeedTemp` (não existe o 26):

  | Leed | Título | Gancho | Fonte |
  |---|---|---|---|
  | 8 | Contribute to your Guild | doação 5144 (`guild/upgrades.contribute`), depois do 111 | *(visto)* só turco: birlik_katkisi #10-#11 |
  | 15 | Consume Balens/Bound Balens | `GameSession.on_packet`: depois de **qualquer** pedido em que diamante ou vinculado caiu (pega todos os `ledger.pay/spend`, a guilda inclusive) | *(visto)* só turco: a aceleração paga 5172 chama antes do 111/102 (replay #1289-#1294: o 83 "Your devotion level has increased to 25." é este); yeralti_labirenti #7-#8 (giftToken 6 → 5 e o 4152); sem contraexemplo: a aceleração paga da savasa_baskin (gift 5 → 0, sem 4152 do 15) já está com total 37, depois do labirinto (22); a inglesa não gasta diamante |
  | 17 | Capture an Astral | sorteio de estrela 8269, antes do 4180 | *(visto)* só turco: kader_sistemi #4-#7 |
  | 18 | Fight a World BOSS | `worldboss.boss_attack`, já no ataque (como o 10) | *(dedução)* pelo título |
  | 24 | Complete Bounty Quest | entrega do painel de recompensas 8291 | *(dedução)* pelo título (PassCount 5) |
  | 25 | Harvest from your own farm | colheita 15044 op 4 (só a própria fazenda existe) | *(dedução)* pelo título |
  | 33 | Spin the Blessing Wheel | **bênção do seminário** 8489, antes do 4391 | *(visto)* só turco: city_city_upgrade #139-#140; a "Blessing Wheel Percentage" das notícias (internet) é essa % |
  | 13 | Participate in a group arena fight | **depende de** arena em grupo (não existe) | — |
  | 22 | Enter the Altar of Ennoblement | **depende de** um sistema que não se sabe qual é (o tooltip `tipData22` está no language, que não temos); talvez o altar da guilda 7601, recusado | — |
  | 23 | Enter Forgotten Catacombs | **depende de** entrar no labirinto (Crypt, 8001/8101; hoje só o 4205 de informação) | (internet) https://wartune.fandom.com/wiki/Glossary |
  | 27 | Enter Battleground | **depende de** campo de batalha (`warfield.py`, fechado) | — |
  | 28 | Enter the Spire | **depende de** Spire do Hall of Heroes (mapa de torre não existe) | (internet) https://wartune.fandom.com/wiki/Hall_of_Heroes |

  A ordem: o oficial manda o 83 do total mais para o fim da resposta; aqui ele vai junto do 4152.
- Ganho (visto tutorial_en #521-#522, #748-#753, #1649-#1652): 4152 **só com o leed que mudou** (a lista completa só
  no login, #50, do maior `TemplateId` para o menor), 83 canal 3 "Your devotion level has increased to N." quando o
  total sobe (no login, logo depois do PlayerMsg, #16) e o 112 das missões tipo 63 (863). O oficial manda o 83 depois
  dos 140 seguintes; aqui vai logo depois do 4152. (dedução) passos do meio de `PassCount` > 1 não mandam 83.
- VIP: o `totalNum` soma o `para1` do `VipPrerogativeTempInfos` **tipo 2 "Devotion Bonus"** do nível VIP ativo
  (0, 0, 10, 10, 20, 20, 30, 30, 40 do VIP 1 ao 9). *(cliente)* `DayGuideCatecory.finishList` põe a linha "VIP login"
  (`templateId` -1, já completa) com VIP 3+ ativo, o mesmo nível em que o tipo 2 sai do 0; `VIPModel.VIP_ACTIVE` = 2.
  A dica da linha (`ProjectItem`, `vipActivePrivilege`) lê o tipo 9, que nesta tempinfos é a alquimia de Daru: o
  número da dica sai errado, o total não. Sem captura com VIP 3+ (a inglesa só tem VIP 1). Sem prêmio por nível de
  devoção além dos baús (8235).
- Guia de 7 dias: `SimpleTasks.Type` = `GuideTaskType` do cliente; o sentido dos IParam vem do `Detail` em inglês
  (IParam5 é só o nível que mostra a tarefa, `GuideTaskItem`). `events._task_done`:

  | Tipo | Tarefas | Conferido | Fonte |
  |---|---|---|---|
  | 1 ARMY_LEVEL | 1 | alguma tropa com `PawnTempInfos.Level` >= IP1 | (dedução) Detail |
  | 2 GUILD_SKILL | 2, 14 | IP1 habilidades da guilda (`skill_*`) no nível IP2 | (dedução) Detail "3 Guild skills reach Lvl. 3" |
  | 3 PERSONAL_SKILL | 3 | alguma tecnologia (prédio MasterType 13/14) no nível IP1 | (cliente) abre o SeminaryFrame |
  | 4, 22 | 4, 26 | nível do herói; poder de combate | (dedução) Detail |
  | 5 USE_STAR | 5 | IP1 estrelas equipadas com `Profile` >= IP2 (3 = rara) | (dedução) Detail |
  | 6 USE_EQUIPMENT | 6 | IP1 peças vestidas com `NeedGrades` >= IP3 | (dedução) Detail |
  | 7 STRENGTHEN_EQU | 7, 13 | item encantado a IP3, `NeedGrades` >= IP1 e `Profile` >= IP2 (5 = [Legendary]) | (dedução) Detail |
  | 8 PASS_TOWER | 8 | recorde do Forgotten Catacombs (`maxIndex`) >= IP1: **nunca**, o labirinto não guarda progresso | — |
  | 9 STAR_LEVEL | 9 | estrela equipada no grau IP1 | (dedução) Detail |
  | 10 INLAY_STONE | 10, 15 | IP1 pedras (SonType 205) de nível IP2+ engastadas; nível = `TemplateId % 100` | (visto) tempinfos: as 96 |
  | 11, 17 | 11, 21 | runa aprendida; runa com `RuneGrade` >= IP2 | (dedução) Detail |
  | 12, 20 | 12, 23 | montaria possuída; nível da montaria (Beast Soul Lvl, `MountInfo.grade`) | (dedução) Detail |
  | 13 PASS_CAMPAIGN | 16, 20, 28 | `campaign_rank:<IP1>` existe (gravado no fim da campanha) | (dedução) |
  | 14 GUILD_DEVOTE | 17 | `consortia_total_offer` >= IP1 | (dedução) Detail |
  | 15 STAR_VALUE | 18 | "Astral Value" = EXP das estrelas equipadas / 10 | (cliente) StarModel.getStarPow, HoroscopeFrame |
  | 16 SOUL_IMPORT_PARVAT | 19 | `store_grade` >= IP1 | (cliente) FightingManager: SOUL = jewelGrades = storeGrade |
  | 18, 19 | — | talento; ter mascote | (dedução) Detail |
  | 21 HONOUR_SOLDIER | 25, 27 | honra (`geste`) >= `Para` do título Private (AppellInfos 8, 2000) | (cliente) thane.honer = geste |
  | 23 ENTER_CAMPAIGN | 29 | **nunca**: The Spire (8201) não tem entrada no servidor | — |

  Sem conteúdo no servidor (só 1001, 1002 e 6001 têm mapa): as masmorras MP 9004/9104/9105 (tarefas 16, 20, 28) e
  o Spire; e o labirinto (tarefa 8). Precisam de captura desses sistemas, não do guia.

### Captura que falta (devoção)

- Personagem com **VIP 3+** ativo: gravar o login (4152 completo) para conferir que o `totalNum` já vem com o
  "Devotion Bonus" (+10 no VIP 3) e se o 4152 muda na hora em que o VIP é comprado ou vence.
- Atacar o chefe do mundo, entregar uma tarefa do painel de recompensas (Bounty) e colher na própria fazenda,
  cada um no 1º do dia: gravar onde sai o 4152 dos leeds 18, 24 e 25 (no ataque ou no fim? em toda entrega?).
- Abrir o painel de devoção com o mouse sobre "Enter the Altar of Ennoblement" (leed 22) para saber o sistema.

## VIP e contrato do rei

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4410 `VipInfoMsg`, 4434 só com os contratos já comprados (conta sem contrato = vazio) | (visto) tutorial_en #96 (4410), #10-#11 (4434 vazio); 4434 com contrato só turco: login.json #107 |
| 8513 | `days` 31/93/186 por `One/Three/Six_MonthPoint` (298/868/1588), só Balens livres; renova somando; 3, 4410, 4416. O inglês não manda (os botões abrem a página de pagamento; a tela do amigo não é criada): fica para o GM e os testes | (cliente) OpenSelfView, VIPFrame |
| 8505 | presente semanal `VipDrop.site` = nível VIP; 115, 111, 4410, 4539, 83 ("Received: ..."); de novo na segunda da semana seguinte (semana começa no domingo, *dedução*: um ponto só); repetido sem resposta | (visto) tutorial_en #3266-#3282 |
| 5006 (2031201) | cartão VIP de teste: `Property3` horas somadas ao fim; 115, 111 "Your VIP service has been extended N hours; new expiration date is AAAA-MM-DD.", 4410 `vipType` 2, 3 | (visto) tutorial_en #3259-#3263 |
| 8521 | abre/atualiza a roleta: zera o tabuleiro, 4414 com os 18 prêmios (`vip_wheel_prizes`), `leftCount` 8, `needVipItem` 1; sem VIP 4414 vazio | (visto) #3325 |
| 8519 | gira gastando VIP Token (208015): o giro k custa k (`game_settings.vip_wheel_costs`); `opType` 1 gira enquanto houver fichas; prêmio sorteado entre os que faltam pelo `vip_wheel_prizes.weight` (0035, padrão 1 = uniforme; peso 0 nunca sai; só pesos 0 sobrando = giro recusado; `vip.wheel_pick`); 115, 109, 3, 4415 (`openIndex` = abertos agora, `takeItem` = todos); recusa = 4415 sem `isStart` | (visto) #3331-#3335 |
| 8756 | só registro (atendimento QQ) | (cliente) |
| 8540 | compra `ids` (`NeedPoint` cada; os seis por `All_KingContract`=1295), só diamante, renova somando 31 dias; `__use` com o contrato 6 ativa o 7 (30 min) uma vez por dia; 3 + 4434 | (cliente) KingContractFrame |

- Contrato do rei = "Spirit Covenant" na tela inglesa (os seis por 1295, `All_KingContract`). Efeitos
  (`KingContracts`, `events.has_contract`):
  - 1 Pocket Market: só o cliente (abre o mercado de qualquer lugar).
  - 2 Bounty Helper: a tarefa do painel de recompensas termina na hora (`offer.py`, `PASS_CONTRACT`).
  - 3 Power of Healing: a vida do herói enche sem gastar a reserva das poções (`rules.heal_hero`,
    `HEALING_CONTRACT`; *dedução*: o 83 "Used HP pack to restore HP." continua indo).
  - 4 Lord of Time: **depende de** o gancho (Altar of Ennoblement) existir; hoje não há aceleração para cobrar.
  - 5 Free Blitz: a varredura de campanha não cobra ouro nas rodadas nem a aceleração (`sweep.free`).
  - 6 Attribute Boost: dá o buff 7 (30 min, uma vez por dia, "Retrieve Buff"): +10% de atributos, vida e tropa nas lutas de masmorra (`Campaigns.Types` 0 e 4; `campaign.boosted`).
- Nível VIP: `UpGradeTempInfos` `Types=4` (Data = vipGp acumulado).
- ponytail: o vipGp do período (`Vip_DailyAddGp` x dias) entra todo na compra.
- ponytail: presentear VIP/contrato a um amigo é recusado (exige gravar outro personagem).
- `vipType` vai 0, ou 2 depois do cartão de teste (o 1 só muda o ícone; regra desconhecida).
- ponytail: preço de "atualizar" a roleta e probabilidades dos prêmios não estão na captura (os pesos são do dono:
  [configuracao.md](configuracao.md#chances-dos-sorteios)).

## Anúncios agendados (`game/announcements.py`)

Tabela **`scheduled_announcements`** (migração 0035): uma linha por mensagem, `times` (`HH:MM,HH:MM`, hora do jogo,
`WARTUNE_GAME_TIMEZONE`), `weekdays` (ISO `1,2,..`, 1 = segunda; vazio = todo dia), `channel`, `user_type`,
`is_center_tip`, `text`, `active`. No horário, todos os jogadores online recebem um **83** com `otherId` -1 e `name`
vazio, como o oficial (#3029/#3030). Mesmo horário: na ordem do `id`. Como editar: [configuracao.md](configuracao.md#anúncios-agendados).

- Relógio: o 20008 de qualquer jogador (~60 s). `Announcer.tick` solta os horários em `(última conferência, agora]`,
  uma vez só por servidor (`GameContext.announcer`), também cruzando a meia-noite.
- Horário perdido há mais de 2 min (`LATE`) não sai atrasado (ninguém online por horas não despeja tudo de uma vez);
  um restart perde os do tempo em que o servidor ficou fora (não persiste: é só um aviso).
- **Defend Sylph Atoll** (semeado, `name` `sylph_atoll`):

| horário padrão | texto | `isCenterTip` | fonte |
|---|---|---|---|
| 00:55, 03:55, …, 21:55 | `Sylph Atoll echoes, “Humans, how foolish you are!”` + 36 espaços | sim | (visto) #3029 |
| idem, logo depois | `Defend Sylph Atoll event is starting soon. Sylphs here have hidden themselves.` | não | (visto) #3030 |
| ~~01:00~~ | `Defend Sylph Atoll event has started.` | não | **desativado** (0057): dedução trocada pelo texto visto |
| ~~01:30~~ | `Defend Sylph Atoll event has ended` | não | **desativado** (0057): a janela é de 1 h |

  **Os horários são escolha do dono** (configuráveis). O padrão segue o help do cliente
  (`PetBossInfoView.boss.helpContent`: "Every day from 01:00, the Sylph Atoll attacks every 3 hours") e a captura:
  #3029 saiu às 18:55 (entre os 4234 de 18:55:01 e 18:56:02), antes do ataque das 19:00. Os 5 min de antecedência são
  dedução. A abertura e o fechamento não são anúncios agendados: saem com o 4686 (abaixo).

### Defend Sylph Atoll: a janela (`game/pet_defend.py`, `handlers/pet_defend.py`)

| o quê | regra | fonte |
|---|---|---|
| horas | `ConfigInfos.pet_island_defend_hour` (1,4,7,…,22), no fuso do jogo; o cliente conta com a mesma config | (visto) #43, #866, #2337: 07:00-08:00 e 10:00-11:00 PDT |
| duração e andar | `game_settings.pet_island_defend` (0057): `duration` 3600, `floors` [20001] sorteado por janela; `bossId` = 5100 + andar | (visto) 1 h, andares 20002/20004 com 5102/5104; só o 20001 tem nós aqui |
| login | 4686 com os sete campos; `peace*` = vitórias com prêmio hoje (`pet_defend:*`, dia do jogo) | (visto) tutorial_en #44, oficial_encantar #43 |
| abre/fecha | no 20008 de cada um: 4686 **sem** `peace*` (o cliente só troca os contadores se vierem os três) + 83 canal 12: abre `Defend Sylph Atoll has opened. Warriors, …` (centro); fecha `Sylphs' anger has subsided. …` (centro) e `Defend Sylph Atoll is over. …` | (visto) #866-#868, #2337-#2338 |
| monstros | nós `masterType` 1003 do 20001 (37 avançados 7511x, 37 sofisticados 7512x, 4 do chefe 5101) chegam DONE (8) no 127; na janela do andar ficam NORMAL (no 127 de quem entra e em 128 no 20008 de quem já está lá); fora dela voltam a 8. O vencido some só para quem venceu | (dedução) nós da captura turca + `PosType.PET_BOSS_MONSTER` |
| luta | 5125 no nó: battleType 6 (nó de campanha) contra o herói do nó com a vida do template; 4103, 150, 100, 140/131 e o 128 DONE (ou NORMAL na derrota) | (dedução) sem captura de luta |
| prêmio | vitória conta em `pet_defend:middle/high/boss` (dia do jogo) até `pet_island_defend_reward_count` (20, 10, 1); dentro do teto, `game_settings.pet_island_defend.rewards` (Sylph Crystalloid 2100038 x2 / x5 / x20 + Sylph Equipment Shard Pack 2060489 no chefe) com 115, 4476, 111 e 83 | (inventado) itens; teto do `ConfigInfos` |
| fúria | por janela, do andar: +`pet_island_defend_rage_add` (2 avançado, 5 sofisticado), até `pet_island_defend_boss_rage` (100); 4686 novo a todos (com `peace*` só para quem lutou). Cheia: os nós do chefe aparecem a todos no andar. Só em memória (`GameContext.pet_rage`, `shortcut`) | (cliente) `PetBossInfoView`; ajuda "the Lord appears after enough kills" |
| chefe | luta individual contra 510x com a vida inteira (a janela não divide a vida como o chefe do mundo); sem ranking do grupo (`PetBossSortView`, sem captura) | (dedução) |

## Alquimia, alma e loja do teste

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4224 e 4372 | (visto) login.json #9, #10 (turco; a inglesa não responde o 8320/8466 de #17-#18) |
| 8320 / 8466 | estado (4224 / 4372) | (cliente) |
| 8321 | custo 0 no 1º uso do dia, depois `min(40 + 10 x usos, 200)` Balens não vinculados (só `point`); ouro = Town Hall(901).Property1 x 10 + Gold Refinery(101).Property1 x 5; 20 usos + privilégio VIP 8 | (cliente) AlchemyFrame |
| 8467 | mesmo custo; alma = nível Barracks(402) x `RefiningSoul_ArmyHouseMut` + nível Cottage(1201) x `RefiningSoul_PeopleMut` (500 cada, como o SoulMakeFrame); nível mínimo `RefiningSoul_Grades`; `RefiningSoul_Count` + privilégio VIP 9 | (cliente) + (visto) login.json #10 (só turco) |
| 8582 | recusa sem cobrar e devolve a loja 4468 (`TrialSkill`) | (cliente) TrailShopItem |

- **Dependência (8582):** o mapa do teste (andar, buffs na batalha) não existe no servidor.

## Painel de recompensas e anel

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4360 `rewardCount 0`, 4198 da tarefa aceita, 4616 + 4614 do anel | (visto) tutorial_en #46 (4360), #53 (4616), #54 (4198 vazio); 4198 com tarefa e 4614 só turco: login.json #56-58 |
| 8290 | `isButton` falso: sorteia se não há lista ou passou 30 min; verdadeiro: 2 grátis por dia, depois 10 Balens (`REFRESH_REWARD_NEEDPAY`; `payType` 0 aceita vinculado); 4197 | (cliente) OfferRewardModel/OfferTimeView |
| 8288 | aceita a vaga `rewardId` (uma por vez, 20 por dia, nível 14+); 4198 + 4197 | (cliente) OfferTaskItem |
| 8289 | desiste: 4198 com `isComplete` (é como o cliente tira da lista) e a vaga volta a 1 | (dedução) |
| 8291 | `isPass` com o contrato 2 ativo termina: EXP/ouro = `RewardPlayGP`/`RewardGold` x qualidade x nível (5 = x6); 4198, 4197, 3, 150, 109, 83 | (cliente) OfferTaskItem |
| 8298 | só registro | (cliente) |
| 8731 | 4616 (anéis hoje) + 4614 (anel atual) | (cliente) RingTaskManager |
| 8732 | sorteia anel `RewardTemps` tipo 1 do nível (35+, até 200 por dia) | (cliente) |
| 8730 | termina na hora: 1x item 2131021 ou 35 diamantes; prêmio `RewardGold/Strategy/PlayGP` + `RewardGoods` do passo | (cliente) TaskFrameII |
| 8729 | só devolve o estado | (cliente) |

- Vagas: 4, sorteio por `Rands` entre `RewardTemps` tipo 0 do nível.
- ponytail: pesos da qualidade (40/30/15/10/5) e o prêmio do anel sem multiplicador são escolha nossa.
- **Dependência (8291 sem passe, 8298, 8729):** as condições (`RewardCondictionInfos`: capturar
  NPC = batalha, missões, enviar mensagem...) precisam que os outros sistemas avisem o progresso.

## Minigames (`handlers/minigames.py`)

Todo C>S da lista tem handler. Reais: **fundo novato** (8751), **fundo normal** (8703), **árvore dourada** (8604,
`handlers/gold_tree.py`) e **labirinto de gemas** (9508, 9509, 9513, 9516, 9517). Os que o servidor não joga
respondem o estado fechado que o cliente mostra (ícone escondido, tela vazia), sem travar. 9510 e 9515 (ajuda de
amigo do labirinto) recusam sem efeito. Calendário (quando cada um abre): `game_settings`, do operador
([configuracao.md](configuracao.md#calendário-dos-minigames)); sem a linha, fechado.

**Fundo normal (8703, 4612)**: o mesmo código do novato (`Fund` em `minigames.py`), com a regra do cliente para
o normal. Banco: `game_settings.normal_fund` (0038) = o 4612 do tutorial_en #86 ("钻石矿脉", Diamond Vein: níveis
1000/2000/10000 diamantes, 5 tiers um por dia).
- `activeType` *(visto #86 = 1 dentro da compra)*: 1 entre `setStartDate` e `setEndDate`; 2 dali até `getEndDate`
  *(dedução: o cliente só resgata com 2, `getCanGetGift`)*; 0 fora (o botão some).
- Compra: nível 11 (`FundManager.getShowBtn`), uma vez por edição, só diamante (`point`), só na janela de compra
  *(dedução: o cliente não confere a data)*. `cash_ledger` `reason` `fund_normal`.
- Tier: *(cliente)* `FundRewardItem`: libera quando `sysCurtime >= getStartDate + interval` minutos; aqui também só
  até o `getEndDate`.
- Estado por edição: `fund:normal:<activeId>` e `fund:normal:<activeId>:get:<vez>` (edição nova = todos compram de
  novo). Login: 4612 sempre que há a linha (#86 manda já no nível 1).
- `title`/`description` vieram em chinês; o cliente não mostra nenhum dos dois: vão em inglês (tradução nossa).

**Árvore dourada ("Sacred Gold Tree", 8604)**: no cliente é a "garrafa" (`BottleManager`). Banco:
`game_settings.gold_tree` (0038) = o 295 do tutorial_en #72 (70 itens, 5 baús de vezes, 5 de andar, fim). Preço:
`Bottle_Price` do template inglês = **65|650|3250** (1/10/50 vezes).

| opType (`BottleOpMsg`) | o que faz | resposta | fonte |
|---|---|---|---|
| 4 (botão do topo) | abre a tela (nível 11, dentro da edição) | 4825, 4497 sorte, 4526 `openView` | (cliente) `TopToolsBar`, `BottleModel.isOpenFrame` |
| 0 (`alterType` 1/2/3) | ativa 1/10/50 vezes: varinhas (208022) primeiro se `stickFirst` 0, uma por vez; o resto em diamante (`point`) | 3, 115 (varinhas e bolsa 22), 4497 `passType` 1, 4526 `alterBottle`, 4825 se pegou andar, 4497 `passType` 2 a todos se saiu item raro | (cliente) `BottleFrame.openCall` |
| 3 | atualiza depois da animação | 4825, 4526 | (cliente) |
| 5 (`alterType` = vezes) | baú de vezes: `count >= param`, uma vez; marca "1" no `treeStatus` (índice na ordem do `param`) | 3/115 (prêmio na mochila), 4526 | (cliente) `BottleBottomIntergalBoxView` |
| 6 (`alterType` = andar) | baú de andar: só o dono, uma vez (`state` 1) | prêmio, 4825 | (cliente) `BottleIntergalBoxView` |
| 1 | vende o armazém (`GoodsHelp.getSellGold`, como o 5007) | 115, 109 | (cliente) `BottleStorageFrame` |
| 2 | armazém -> mochila, só se couber tudo | 115 | (cliente) `BottleStorageFrame` |
| 5005 22 -> 1 | clique numa pilha do armazém | 115 | (cliente) `BottleBagCellClickMediator` |

- Armazém = bolsa 22 (`BagType.BOTTLE`): com mais de 8×5 pilhas o cliente não ativa *(cliente)*, mas não confere se
  o sorteio cabe (a tela passa a 8×7); aqui cabem até 40 + 50 pilhas *(dedução)*. O login manda as pilhas da bolsa
  22 com as outras (o 115 do login leva todas as bolsas).
- Andares ("Lucky Level", help do `language.txt`): total de ativações do servidor na edição = soma do
  `goldtree:<id>` de cada personagem (lido uma vez, `EventStateRepository.by_prefix`, e mantido em `ctx.gold_tree`).
  O andar fica com quem fez a ativação que chegou nele *(dedução)*: linha `goldtree:<id>:floor:<andar>` no dono.
- Linhas da sorte (4497 `passType` 2) no formato do #71 (links de jogador e item); raro = `isNewItems`
  *(dedução: as 3 linhas do #71 são de itens com isNewItems, um deles com isShow falso)*; as 20 últimas, em memória
  *(ponytail: somem no restart)*. A linha própria (`passType` 1) usa o mesmo texto *(dedução)*.
- Sorteio: com reposição, pelo peso de cada item (`drops[i][4]`, padrão 1 = uniforme; *dedução*). O `BottleItems` do
  tempinfos (58 linhas) não é lido pelo cliente: vale a lista do 295.
- Início da edição: *dedução* (o 295 só traz o `endTime`, 2026-10-18 23:59:59 no Pacífico). "Uma vez por dia" do help
  não está implementado (não se sabe o quê).
- Login: 4497 (sorte) e 295, nessa ordem (#71-#72), sempre que há a linha.

**Fundo novato (8751, 4640)** — banco: `game_settings.novice_fund` (migração 0033, valores do oficial
inglês tutorial_en #639/#2784: custos 500/5000/30000). 4640 no login só a partir do nível `openGrades` (6).
- `opType` 0 = estado (4640); 1 = compra o nível `opParam` (1..3): nível 11+ do personagem, uma vez,
  só diamante (`point`, como o `FundBuyItem` confere), `ledger.spend` com `reason` `fund_novice`.
- 2 = resgata o tier `opParam` (= `times`, 1..5): `grades >= interval` (no ramo do fundo novato o
  cliente usa o "intervalo" como nível), uma vez por tier. Diamante de volta entra no `cash_ledger`
  (`record_cash`, entrada) na mesma gravação do prêmio.
- Total mostrado (`itemInfos`) = soma dos tiers; **não é pago na compra** (conferido: nível 1 soma
  -500:100 e -400:200, bate com `itemInfos`).
- Janela: `endDate` 2099 (ponytail: a janela oficial não está na captura). Sem janela de compra.
- Estado: `fund:novice` (value = nível, text = data da compra); `fund:novice:get:<times>` (marca de tier).
- Login: 4640 (mesmo da tutorial_en #639); recebe `login_push` de `events.login_push`.

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| 8751 | fundo novato, real (acima) | (visto) tutorial_en #639, #2783-#2784 + (cliente) FundManager, FundBuyItem, FundRewardItem |
| 8703 | fundo normal, real (acima) | (visto) tutorial_en #86 + (cliente) FundManager, FundRewardItem |
| 9503 | 4912 vazio sempre; resgate recusado. Fórmula de custo para quando houver contagem: `itemCost = num*ItemCount`, `goldCost = num*Gold`, `goldReward = itemReward*GoldPercent/ItemPercent` (conferida nos sonTypes 1, 2 e 4 da login.json #54, só turco) | (visto) tutorial_en #51 (vazio) + (cliente) ExpBackManager |
| 8534 | 4428 vazio (igual ao login, tutorial_en #57) | (visto) |
| login | 4461 do Recharge Gift Pack (`game_settings.rebate`, 0055) na janela; fora dela `id` vazio esconde o botão | (visto) oficial_encantar #61; tutorial_en #59 (vazio) |
| 8574 `RebateOpMsg` | `op` 1: 4463 `{id, userid, point, type, packagestates}` com `point` = Balens recarregados na janela (`cash_ledger` `reason='recharge'`, gravado pelo portal); `op` 2 `packageid`: resgata quando `point` >= o do pacote e ainda não resgatado (itens e 4463 de novo). Fora da janela: 4461 vazio | (visto) oficial_encantar #62 (op 1), #76 (4463); (cliente) `FeedBackManager`, `FeedBackItem`; (dedução) o resgate, sem amostra |
| 8629, 8630, 8634, 8638, 8748 | sem resposta (nunca 4546 nem 4550) | (cliente) TimeStoryFrame, TopToolsBar, SinglePass, LotteryManager |
| 8639 / 8640 | 4554 / 4553 vazios (corneta sem item) | (cliente) SinglePassManager |
| 8722 / 8723 | 4543 vazio: botão só com `isIn360Agent` (plataforma 360) | (cliente) Bag360Manager |
| 8750 | 4637 `isOpen` falso | (cliente) LotteryManager |
| 8866 | 4745 zerado | (cliente) ExchargeRankManager |
| 9602 | 345 zerado | (cliente) CrossCostController |
| 8994 | 4811 lista vazia | (cliente) StoreSocketOutManager |
| 9500 | 4901 `open` falso | (visto) tutorial_en #87 |
| 9501 | 4908 `sysState` 0 | (cliente) AnswerManager |
| 9502 | 4914 `op` 1, `seekCount` 0, `seekNodeList` presente e vazio | (cliente) TreasureHuntControler |
| 9507 | 4916 e 4918 vazios | (cliente) FishManager |
| 9508 | 4922 com o tabuleiro (real, abaixo) | (visto) só turco: av_askeri #1, login da replay #10; (cliente) GemMazeManager |
| 9509 | troca: cascata, 4923 por passo e 4924 (real, abaixo) | (visto) só turco: av_askeri #5-#56; (cliente) GemMazeView |
| 9510 | ajuda de amigo: recusa com 4924 (sem amigos; o 4925 nunca sai) | (cliente) GemMazeManager |
| 9513 | caixa de tesouro: 4928 com o `boxMark` novo e a caixa (real, abaixo) | (cliente) GemMazeManager, GemMazeBoxView |
| 9515 | resposta de ajuda: só registra | (cliente) GemMazeManager |
| 9516 | compra de movimentos: 4927 (real, abaixo) | (cliente) GemMazeManager, GemMazeFrame |
| 9517 | receber tudo: bolsa 24 vai para a mochila, 111 "Reward retrieval successful!" (texto inglês do baú online, #2114) | (visto) só turco: av_askeri #60-#62 |
| 9521, 9522 | sem resposta | (cliente) |
| 9520 | 300 (fecha o quadro; só o GoldRoadManager escuta) | (cliente) GoldRoadManager |
| 9523 | 4936 `leadExtractTimes` 0 | (cliente) FunnyControler |
| 9550 | 4980 lista vazia | (cliente) InfoTipsManager |
| 9610 `LuckExchangeOpMsg` | é a troca (`exchangeId` x `exchangeCount`), não um pedido: sem edição vigente, recusa só no log. As listas (363, 364) vão vazias no login, sem pedido | (cliente) LuckyExchangeManager + (visto) tutorial_en #88, #102 |
| 9638 | 414 `param7` falso; 415 vazio (obrigatório se a tela abrir) | (visto) tutorial_en #112 (414); 415 só turco: login #127 |
| 8604 | árvore dourada, real (acima); sem a linha no banco: 295 `open` falso e 4526 `openView` falso | (visto) tutorial_en #71-#72 + (cliente) BottleManager, BottleFrame |
| 9645 `extend1` 35 | minério: 190 fechado | (visto) tutorial_en #109 |
| 9645 `extend1` 38 `SuperSigninCardReqMsg` | super assinatura: `opType` 2 compra (500 Balens livres, nível 6, uma por edição), 3 recebe o dia `date` (estado 1), 4 assina o dia perdido (estado 3, 10 Balens); responde 513 com os 7 estados (0 ainda não, 1 recebe, 2 recebido, 3 perdido). O login manda 4590 (datas da edição) e 514 (preços e prêmios), e o 513 só com cartão; quem está no jogo assina o dia (o 513 vai de novo depois de qualquer pedido quando muda, como na virada da meia-noite) | (visto) oficial_encantar #118-#119 (`game_settings.super_signin`, 0054); regras: `SuperSigninCardFrame`/`Item` e o `language.txt` inglês; (dedução) o 513 de cada operação, sem amostra |

**Labirinto de gemas (9508–9517, real)**: `handlers/gemmaze.py`; a regra da troca e da cascata está em
`game/gemmaze.py`.
- Tabuleiro 5×5 (marca = linha × 5 + coluna; cores 1–5). A troca é entre vizinhas na horizontal ou na
  vertical (cliente: `GemMazeView.isUpon`). Três ou mais iguais em linha ou coluna saem; as de cima descem;
  o topo ganha gemas novas; a cascata repete até não sobrar combinação. *(visto, só turco)* Na captura
  `av_askeri_ve_odul_toplama`, cada uma das 7 trocas tem uma única vizinha que forma a primeira combinação
  e cada cascata (10 passos) bate com a gravidade (`tests/game/test_labirinto_gemas.py`).
- Pontos e EXP: 3 em linha = 10 e 1; 4 = 20 e 2 *(visto, só turco: av_askeri)*. Cinco ou mais segue a mesma conta *(ponytail)*.
- Movimentos: 20 e 5 ajudas no personagem novo *(visto, só turco: replay)*. Cada troca gasta 1, também a sem
  combinação *(ponytail)*. Troca entre gemas que não são vizinhas não gasta e só recebe o 4924.
- Prêmio: cada passo dá um prêmio (`rewardInfo` do 4923) para a bolsa 24 (`BagType.MAZE`, 48 espaços, empilha
  até o `MaxCount`). O 9517 passa a bolsa para a mochila se couber tudo. As buscas por posição (`bag.at`, `bag_item`, arrumar, tirar) filtram `BagType.BAG`, então nenhuma acha item da bolsa 24 (auditado). Itens: 2060008 Lvl. 1 Gem Pack ×1,
  208027 Refinement Lock ×1, 208014 Soul Crystal ×2 *(visto, só turco: o 115 sobe a pilha de 2 em 2 e o
  chat diz "x 2")* (nomes dos `ItemTempInfos`). Sorteio pelos pesos `game_settings.gem_maze_reward_weights`
  (0035, padrão `[1, 1, 1]` = uniforme) *(ponytail: nenhum template liga o prêmio à cor nem ao tamanho)*.
- Caixas (9513/4928): *(cliente)* `GemMazeBoxView`: a caixa `i` (1–5) libera com `score` >= 500, 1000, 2000,
  3500, 6000 e o pedido manda `boxId` = 1, 2, 4, 8, 16; `boxMark` é a soma dos bits das caixas pegas. O
  prêmio é o item `boxesId[i]` (2131035–2131039, Lost Treasure of Antiquity I–V; a dica da caixa é esse item,
  `GemMazeIntergalBoxView`) e vai para a bolsa 24 *(ponytail: a bolsa não foi capturada)*. Sem pontos, caixa
  já pega, bit inválido ou bolsa cheia: 4928 com a marca atual e sem prêmio.
- Renovação na virada do dia do jogo (5h): movimentos voltam a 20 (os comprados também somem), ajudas a 5, pontos
  e caixas zeram; o semanal zera na semana nova (ISO). Tabuleiro, nível e EXP ficam. *(cliente)* `helpContent`:
  "Free and purchased attempts reset daily", "Points and attempts reset daily at 5 A.M.".
- Compra (9516): `Gem_Maze_BuyInfo` = `10,15,99`: 10 movimentos por compra a 15 Balens cada, 150 por compra
  (`buyTimesTips`: "spend 150 Balens to purchase 10"); 99 é o teto (89 + 10, o mesmo limite de 90 do cliente).
  `buyTypes` 2 aceita vinculado (`bugGemMazeTimesUseBind`), 1 só livre. O 4927 só sai quando a compra vale,
  porque o cliente soma 10 ao receber.
- Login: 4922 com o tabuleiro gravado, só se a conta já tem um (*dedução*). A inglesa (personagem novo) não tem 4922 nenhum; o replay (só turco: pacotes 10 e 12, depois do 4900) tem, com o tabuleiro já aberto. Não grava.
- Estado: uma linha `EventState` de chave `gemmaze` com `text` em JSON (tabuleiro, movimentos, ajudas,
  nível, EXP, máximo de EXP, pontos, semanal, caixas pegas, dia da renovação). Abrir sem linha sorteia e
  grava. Cada troca grava tudo
  numa vez, antes dos pacotes do passo (o 4924 sai por último).
- Dedução: tabuleiro novo sem combinação pronta e com ao menos uma jogada; cor de gema nova uniforme.
- *ponytail*: sem subida de nível (a tabela não foi capturada: `curExp` passa de `maxExp`); `scoreOrder` 0
  (sem ranking); `buyTimesLeft` 0.

**Precisa de captura (o que gravar e o que fazer no jogo):**
- Subida de nível: jogar até subir e gravar os 4923 com `gemLevel` e `maxExp` novos. A captura (só turco) só tem o
  nível 0 (30 de EXP) e o nível 5 (150).
- Troca sem combinação: trocar duas gemas que não formam nada e gravar o que o oficial manda (só o 4924,
  um 4923 vazio, ou nada).
- Prêmios: jogar uns 50 passos e gravar os `rewardInfo`, para ver se cor e tamanho decidem o prêmio, e
  os pesos.
- Caixas (9513/4928): juntar 500 pontos, pegar a 1ª caixa e gravar o 9513, o 4928 e o 115 (para ver em
  que bolsa a caixa cai e se o `rewardInfo` é a caixa ou o conteúdo).
- Renovação: abrir o labirinto antes e depois das 5h de uma segunda-feira e gravar os 4922, para ver se o semanal
  zera.
- Ajuda de amigo (9510, 4925, 9515, 4924): convidar um amigo e gravar os dois lados.
- Ranking semanal (`scoreOrder`, `weekScore`): gravar o 4922 de outra semana e de um jogador de topo.
- Bolsa do labirinto cheia (48 itens): gravar o que o oficial manda ao trocar e ao receber tudo.

**Captura que falta — fundo normal e árvore dourada:**
- Fundo normal: comprar um nível dentro da compra e gravar o 8703/4612 (e o 3); voltar no resgate e pegar o 1º
  tier (4612 com `activeType` 2? `logs`?); abrir o fundo depois do `getEndDate` (`activeType` 0 ou 3?).
- Árvore dourada: clicar no botão do topo (8604 op 4) e gravar a resposta inteira (4526? 4825? 4497?); ativar 1x
  e 10x com e sem varinhas (115 da bolsa 22, 4497 `passType` 1, 4526, 3); pegar um baú de vezes (op 5: o prêmio
  vai para a mochila? 4526 `treeStatus`); vender e tirar do armazém (op 1/2); gravar o 4825 de um servidor com
  andares batidos (quem fica com o andar, `state`, `isVip`); ativar no dia seguinte (o que o "once per day" do help
  limita). Tudo isso dá também os pesos, se forem muitas ativações.

**Dependências (sistema fechado, com o motivo e o que capturar):**
- **Quiz (9501):** `HeartTempInfos` são perguntas de personalidade ("which finger will you wear it on?"), sem
  resposta certa em lugar nenhum (`QuestionReplyInfoResolve` é o atendimento, não o quiz). Agenda em conflito: help
  inglês "Monday, Wednesday, Friday 19:30-20:00", template `Dati_Day` 1,3,5,6 às `AnswerQuestionTime` 14:35.
  **Captura que falta**: uma rodada inteira (9501, 4907/4908/4909/4910): o 4909 com `answer` no estado 4 diz qual
  opção valeu; gravar várias perguntas para ver se a certa é fixa ou a mais votada.
- **Pesca (9507):** `FishTemplateInfos` (13 peixes com prêmio) e `Fish_*` (20 tentativas, ajuda 15 diamantes)
  existem; faltam o surgimento e a captura. **Captura que falta**: abrir a pesca (4916 piscina, 4918) e pescar
  algumas vezes (o que o servidor manda por peixe, o 4917/resultado).
- **Caça ao tesouro (9502):** `treasure_*` (refresh 120 diamantes ou 8 itens, cavar já 25) existe; faltam os nós.
  **Captura que falta**: abrir o mapa (4914 com `seekNodeList`) e cavar um nó.
- **Estrada dourada (9520..9522):** `Golden_Road_Batch_Times` 50 e o help ("Normal 1x, Double 2x, Quintuple 5x",
  casas "?", 100 pontos) existem; as casas (4933 `cellInfo`) e o custo de cada dado vêm do servidor. **Captura que
  falta**: abrir (4933) e jogar o dado nos três modos (4934 `CastDiceMsg`), mais o "refresh".
- **Minério (9645):** `MineOfActiveTime`, `Mine_Level`, `FreshManDepositCost` existem; sem tabela de
  recompensa da mineração (op 1/2). **Super assinatura** (9645 `extend1` 38): feita (ver a tabela).
- **Corneta (8638..8640):** `SinglePass_Count` existe; sem item nem tabela do passe.
- **Loteria (8748/8750), caça-níquel (9500), cadeiras (9638), recompensa de grupo (9523), caixa de
  ano novo (8994), história (8629/8630):** sem template nem config no servidor; a captura inglesa só os mostra
  fechados (4637 #107, 4901 #87, 414 #112). O caça-níquel tem regra no help (`slot.slotHelpFrame.describe`: um
  dígito por dia, prêmio no último dia), mas não a tabela de prêmios. **Captura que falta**: cada um num dia em que
  o oficial o abre (o 4637/4901/414 com `true`), abrir a tela e jogar uma vez.
- **360 (8722/8723):** `PrivilegeDrops` existe, mas o cliente só mostra com `isIn360Agent`.
- **Recuperação (9503):** lista vazia porque nenhum sistema conta as atividades perdidas (campanha,
  arena, boss, imposto; `RecoverInfos` tem 10 linhas). **depende de** cada sistema gravar a participação do dia;
  quando houver, a fórmula acima já confere. O tutorial_en #51 manda o 4912 vazio (personagem novo).
- **Troca da sorte (9610):** a inglesa (#88/#102) tem duas edições, uma vencida (2026-10-14) e uma futura
  (2026-10-23), sem as trocas; a sorte atual (`currentLuckValue`) e o que cada troca dá não são conhecidos.

**Alterações em arquivos compartilhados:** `handlers/events.py` (`minigames.login_push` no login)
`domain/models.py` (`BagType.MAZE`, `BagType.BOTTLE`), `handlers/minigames.py` (chama `gemmaze.login_push` e
`gold_tree.login_push`), `handlers/__init__.py` (registro), `game/bag.py` (`side_fits`/`side_add`, bolsas de prêmio
22 e 24), `handlers/items.py` (5005 da bolsa 22 para a mochila), `game/session.py` (`GameContext.gold_tree`) e
`EventStateRepository.by_prefix`. O progresso dos fundos, da árvore e do labirinto usa `event_states`; as regras
vêm da 0033 (novato) e da 0038 (normal, árvore).
