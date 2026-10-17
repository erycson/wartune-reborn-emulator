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
  `vip` (value = vipGp, text = fim), `vipgift` (semana ISO), `king:<id>` (text = fim),
  `king:fetch`, `alchemy`, `soul`, `offer:list` (JSON das 4 vagas), `offer:task`, `offer:free`,
  `offer:count`, `ring`, `fund:novice`, `fund:novice:get:<times>`.
- **`cash_ledger`** `(character_id, delta_point, delta_gift_token, balance_point,
  balance_gift_token, reason, ref, gm, created_at)`: todo gasto de diamante passa por
  `services/ledger.spend`, que devolve a linha para entrar na **mesma** `save` do que foi comprado.
  `gm` fica nulo (reservado para ajuste manual).
- Migração `0003_estado_de_eventos_e_livro_caixa_de_`.

## Concessão de recompensa

`game/rewards.py`: `can_grant` (TemplateId existe, quantidades > 0, cabe na mochila de 42),
`grant` (moedas negativas -100 ouro, -300 Ruh, -400 diamante, -500 vinculado, -700 EXP; itens com
`DefaultSkill`), `text` (`Kazanılan:...` nos dois estilos do oficial), `take_one` (consome 1 item).
O 5006 da mochila usa o mesmo código. Depois de gravar, `handlers/player.granted` manda 3, 150
(EXP), 109 (ouro), 115 (itens) e 83.

- ponytail: -600 "Kristal" não existe no banco; é aceito e descartado (fora do texto).

## Atividades (SumActive) e login

Definições do operador em **`data/events.json`** (`config.events_file`): `dataStamp` (subir quando
mudar) e `actives[]` com GUIDs, datas, pacotes, itens e condições. Vêm preenchidos o login de 7
dias (tipo 13, itens da captura) e o presente online (tipo 14: 10 min, depois 30 min x3; o -600 da
captura virou -500).

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4475 em páginas de 10 + 4476 no 8586 tipo 1 | (visto) login.json #63-69 |
| 8586 type 1 | 4476 com `status` 1/2/3 e `countDown` (tipo 14) | (visto) |
| 8586 type 2 | valida status=1 e mochila; ordem 111, 4476 parcial, 83, 4476 completo, 3, 109, 115 | (visto) online_odul… #38-46 |
| 8266 | assina o dia: bit `1 << (dias_do_mês - dia)` em `signSite`; `SignDrop` ao chegar num `Times`; 4177 | (cliente) DayGuideCatecory |
| 8496 | dia `index` do login acumulado (`ReloginDrops.Times`), exige `index <= dias logados`; 3 com `reloginProcess` | (cliente) |
| 8749 | guia de 7 dias: dia alcançado, tarefas do dia feitas, `ServenLeadRewards`; 4638 | (visto) login.json #93 |
| 8234, 8322 | só devolvem 4152 (nenhuma tela manda; o progresso vem do servidor) | (cliente) |
| 8235 | baú `site` 1..5 da atividade diária (10/40/60/80/100 pontos), `LeedDrop`; 4150 | (cliente) |
| 8518 | 4412 vazio (contadores do painel do dia) | (cliente) |

- Cliente: `FunnyManager`. Atividade com `stopTime` passado é descartada; o cache só troca quando
  `dataStamp` sobe. O oficial mandou 5 páginas, 53 atividades, `dataStamp 264`.
- `activeType` vistos: 1 gasto diário, 10 troca, **13 login**, **14 presente online**
  (`conditionValue` = segundos), 15 primeira recarga, 18 montaria, 27 anfiteatro, 28 campo de
  batalha, 35 fadas.
- Tipo 13 conta dias de login (primeiro login do dia); tipo 14 soma segundos online desde o
  último resgate (zera a cada presente, gravado na desconexão e no resgate).
- Outros `activeType` ficam "ainda não" (3): cada um depende do sistema dele (recarga, troca,
  montaria...).
- Leed: só o login (1) e o chat no mundo (16) contam. **Dependência:** os outros sistemas chamam
  `events.leed_done(s, template_id)` quando a ação acontece.
- Guia de 7 dias: só tarefas `SimpleTasks` tipo 4 (nível) e 22 (poder de combate) são verificadas.

## VIP e contrato do rei

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4410 `VipInfoMsg`, 4434 com os 7 contratos | (visto) login.json #107, #15 |
| 8513 | `days` 31/93/186 por `One/Three/Six_MonthPoint` (298/868/1588), só diamante; renova somando; 3, 4410, 4416 | (cliente) OpenSelfView |
| 8505 | presente semanal `VipDrop.site` = nível VIP; `isTakeGift` = pode resgatar; `takeGiftDate` = próxima segunda | (cliente) VipGiftItem |
| 8519, 8521 | 4414 vazio sempre (o 8521 põe máscara que só sai no 4414) | (cliente) VIPManager |
| 8756 | só registro (atendimento QQ) | (cliente) |
| 8540 | compra `ids` (`NeedPoint` cada; os seis por `All_KingContract`=338), só diamante, renova somando 31 dias; `__use` com o contrato 6 ativa o 7 (30 min) uma vez por dia; 3 + 4434 | (cliente) KingContractFrame |

- Nível VIP: `UpGradeTempInfos` `Types=4` (Data = vipGp acumulado).
- ponytail: o vipGp do período (`Vip_DailyAddGp` x dias) entra todo na compra.
- ponytail: presentear VIP/contrato a um amigo é recusado (exige gravar outro personagem).
- `vipType` vai 0 (o 1 só muda o ícone; regra desconhecida).

## Alquimia, alma e loja do teste

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4224 e 4372 | (visto) login.json #9, #10 |
| 8320 / 8466 | estado (4224 / 4372) | (cliente) |
| 8321 | custo `min((usos+1)*2, 40)` diamantes (só `point`); ouro = Meclis(901).Property1 x 10 + Altın Ocağı(101).Property1 x 5; 20 usos + privilégio VIP 8 | (cliente) AlchemyFrame |
| 8467 | mesmo custo; alma = nível Kışla(402) x `RefiningSoul_ArmyHouseMut` + nível Ev(1201) x `RefiningSoul_PeopleMut`; nível mínimo `RefiningSoul_Grades`; `RefiningSoul_Count` + privilégio VIP 9 | (cliente) + (visto) #10 |
| 8582 | recusa sem cobrar e devolve a loja 4468 (`TrialSkill`) | (cliente) TrailShopItem |

- **Dependência (8582):** o mapa do teste (andar, buffs na batalha) não existe no servidor.

## Painel de recompensas e anel

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| login | 4360 `rewardCount 0`, 4198 da tarefa aceita, 4616 + 4614 do anel | (visto) login.json #48, #56-58 |
| 8290 | `isButton` falso: sorteia se não há lista ou passou 30 min; verdadeiro: 2 grátis por dia, depois 2 diamantes (`payType` 0 aceita vinculado); 4197 | (cliente) OfferRewardModel/OfferTimeView |
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

Todo C>S da lista tem handler. Os que o servidor não joga respondem o estado fechado que o cliente
mostra (ícone escondido, tela vazia), sem travar. Só o **fundo novato** é real.

**Fundo novato (8751, 4640)** — `data/events.json` > `novice_fund` (valores da captura login.json #94).
- `opType` 0 = estado (4640); 1 = compra o nível `opParam` (1..3): nível 11+ do personagem, uma vez,
  só diamante (`point`, como o `FundBuyItem` confere), `ledger.spend` com `reason` `fund_novice`.
- 2 = resgata o tier `opParam` (= `times`, 1..5): `grades >= interval` (no ramo do fundo novato o
  cliente usa o "intervalo" como nível), uma vez por tier. Diamante de volta entra no `cash_ledger`
  (`record_cash`, entrada) na mesma gravação do prêmio.
- Total mostrado (`itemInfos`) = soma dos tiers; **não é pago na compra** (conferido: nível 1 soma
  -500:100 e -400:200, bate com `itemInfos`).
- Janela: `endDate` 2099 (ponytail: a janela oficial não está na captura). Sem janela de compra.
- Estado: `fund:novice` (value = nível, text = data da compra); `fund:novice:get:<times>` (marca de tier).
- Login: 4640 (mesmo do login #94); recebe `login_push` de `events.login_push`.

| Opcode | Comportamento / resposta | Fonte |
|---|---|---|
| 8751 | fundo novato, real (acima) | (visto) login #94 + (cliente) FundManager, FundBuyItem, FundRewardItem |
| 8703 | 4612 `activeType` 0 (fundo normal fechado) | (cliente) sem captura |
| 9503 | 4912 vazio sempre; resgate recusado. Fórmula de custo para quando houver contagem: `itemCost = num*ItemCount`, `goldCost = num*Gold`, `goldReward = itemReward*GoldPercent/ItemPercent` (conferida nos sonTypes 1, 2 e 4 da captura #54) | (visto) login #54 + (cliente) ExpBackManager |
| 8534 | 4428 vazio (igual ao login #60) | (visto) |
| 8574 | 4461 com `id` vazio (esconde; a captura de 2026-05-18..20 já terminou) | (visto) login #62 |
| 8629, 8630, 8634, 8638, 8748 | sem resposta (nunca 4546 nem 4550) | (cliente) TimeStoryFrame, TopToolsBar, SinglePass, LotteryManager |
| 8639 / 8640 | 4554 / 4553 vazios (corneta sem item) | (cliente) SinglePassManager |
| 8722 / 8723 | 4543 vazio: botão só com `isIn360Agent` (plataforma 360) | (cliente) Bag360Manager |
| 8750 | 4637 `isOpen` falso | (cliente) LotteryManager |
| 8866 | 4745 zerado | (cliente) ExchargeRankManager |
| 9602 | 345 zerado | (cliente) CrossCostController |
| 8994 | 4811 lista vazia | (cliente) StoreSocketOutManager |
| 9500 | 4901 `open` falso | (visto) login #95 |
| 9501 | 4908 `sysState` 0 | (cliente) AnswerManager |
| 9502 | 4914 `op` 1, `seekCount` 0, `seekNodeList` presente e vazio | (cliente) TreasureHuntControler |
| 9507 | 4916 e 4918 vazios | (cliente) FishManager |
| 9508 | 4922 vazio (sem tabuleiro) | (cliente) GemMazeManager |
| 9509, 9510, 9513, 9515, 9516, 9517, 9521, 9522 | sem resposta | (cliente) |
| 9520 | 300 (fecha o quadro; só o GoldRoadManager escuta) | (cliente) GoldRoadManager |
| 9523 | 4936 `leadExtractTimes` 0 | (cliente) FunnyControler |
| 9550 | 4980 lista vazia | (cliente) InfoTipsManager |
| 9610 | 364 e depois 363 vazios (tabela da captura #96 expirou em 2026-05-17) | (visto) login #96 |
| 9638 | 414 `param7` falso; 415 vazio (obrigatório se a tela abrir) | (visto) login #127 |
| 8604 | 295 `open` falso; 4526 `openView` falso (295 sem captura) | (cliente) BottleManager |
| 9645 | 190 e 4590 fechados (o código não diz qual dos dois; os dois fechados é o estado certo) | (visto) login #125, #126 |

**Dependências (sistema fechado, com o motivo):**
- **Garrafa (8604):** `BottleItems` (58 sorteios) e `Bottle_Price` 20|200|1000 existem. Falta o
  armazenamento (opType 1/2 e `UPDATE_BOTTLE_BAG`), o martelo (`_hammerNum`), as tabelas de caixa por
  pontuação e por andar (`score`/`storey` de 295 não estão em lugar nenhum) e os pesos do sorteio.
- **Quiz (9501):** `HeartTempInfos` (perguntas) e `Dati_Day`/`AnswerQuestionTime` existem, mas a
  banca não traz a resposta certa.
- **Pesca (9507):** `FishTemplateInfos` e `Fish_*` existem; faltam as regras de surgimento e captura
  (sem captura de 9507, inventar seria chutar).
- **Labirinto (9508..9517):** `av_askeri_ve_odul_toplama.json` #1/#5 (4922/4923) mostra um tabuleiro oficial, mas não as regras de
  combinação, geração e pontuação. `Gem_Maze_BuyInfo` existe.
- **Caça ao tesouro (9502):** `treasure_*` existe; faltam os nós (posição e nome).
- **Estrada dourada (9520..9522):** `Golden_Road_Batch_Times` existe; sem tabela de células.
- **Minério (9645):** `MineOfActiveTime`, `Mine_Level`, `FreshManDepositCost` existem; sem tabela de
  recompensa da mineração (op 1/2). **Super assinatura** (9645): sem template.
- **Corneta (8638..8640):** `SinglePass_Count` existe; sem item nem tabela do passe.
- **Loteria (8748/8750), caça-níquel (9500), cadeiras (9638), recompensa de grupo (9523), caixa de
  ano novo (8994), história (8629/8630):** sem template nem config no servidor.
- **360 (8722/8723):** `PrivilegeDrops` existe, mas o cliente só mostra com `isIn360Agent`.
- **Recuperação (9503):** lista vazia porque nenhum sistema conta as atividades perdidas (campanha,
  arena, boss, imposto). Quando houver a contagem, a fórmula acima já confere.
- **Troca da sorte (9610):** a captura #96 tinha a tabela, mas expirou; a sorte atual
  (`currentLuckValue`) não é conhecida.
- **Fundo normal (8703):** sem captura do 4612.

**Alterações em arquivos compartilhados:** `data/events.json` (chave `novice_fund`),
`game/events.py` (`EventCatalog.novice_fund`), `handlers/events.py` (`minigames.login_push` no login)
e `handlers/__init__.py` (registro). Sem migração: o estado do fundo usa `event_states`.
