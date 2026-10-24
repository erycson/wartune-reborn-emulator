# Castelo, prédios, tecnologia, produção, fazenda, caixa por tempo e recompensa offline

Fontes: *(visto)* = captura do oficial (`captures/*.json`); *(cliente)* = AS3 decompilado do cliente inglês em
`D:\xampp\htdocs\wartune\decomp` (`2/scripts/managers/BuildingSocketOutManager.as`,
`yishi/manager/BuildingManager.as`, `2/scripts/farm/` e `m7/scripts/farm/`, `yishi/manager/WaterManager.as`,
`managers/BoxSocketOutManager.as`, `yishi/view/frame/HookRewardFrame.as`); *(dedução)* = regra
nossa onde nem captura nem cliente dizem. Código: `game/castle.py`, `game/farm.py`,
`game/timebox.py`, `game/handlers/castle.py`, `game/handlers/farm.py`, `game/handlers/rewards.py`.

## Modelo

- **Upgrade é imediato** *(visto)*: o 4130 já sai com o template novo; a fila fica ocupada
  `UpgradeTime` segundos (`remainTime = begin + needTime - agora`).
- **Filas** (`build_orders`) *(visto)*: tipo 1 prédio, 2 tecnologia (MasterType 13/14), 3 cobrança
  de ouro. Números do oficial: 1 = prédio (nasce no 8281), 2 = cobrança, 3 = tecnologia; fila
  comprada = maior + 1. Limite de 2 filas de prédio (`BuildingModel.buildOrderLimit`) *(cliente)*.
  O login completa as que faltam (`castle.ensure`). A de cobrança só nasce no nível 14 *(visto,
  oficial_20261023-171155-1 #5840: 104 {orderId 2, orderType 3} na subida; o 4187 antes do 14 só tem a fila 1)*:
  `push_level` manda o 104, e o 8327 cria a que faltar (subida sem `push_level`). A de tecnologia nasce no login
  *(dedução: nenhuma captura mostra quando)*.
- **Produção** *(visto, login.json, só turco; a inglesa #590-#591 só mostra prédios, sem tecnologia)*: ouro/hora = Property1 do conselho (901) + mina (101) +
  Σ tecnologias de ouro (MasterType 13) `EffectTempInfos[Property1].Property1 × nível`. Teto =
  Property2 do depósito (301), 10000 sem depósito. Acumulada sob demanda (`settle`), guardando a
  fração de hora; ouro de outras fontes pode passar do teto e aí a produção para. População máxima
  = Property2 da casa (1201). Cristais começam em 1000. Teto do armazém e população máxima sobem com
  os pergaminhos 2010501 (efeito 2008) e 2010801 (2005) enquanto durarem (`game/buffs.py`, ver itens.md).
- **Diamante** (`point`) e **diamante vinculado** (`gift_token`): todo débito/crédito passa por
  `services/ledger.py` e grava uma linha em `cash_ledger` na mesma transação.
- **Fazenda** (`farm_lands` + colunas `farm_*`/`tree_*` em `castles`): só terras plantadas têm
  linha. Terras abertas = 3 + grau da fazenda // 5, até 9 (cliente inglês `FarmLandLayer`: a terra p de 3 a 8
  abre no nível (p − 2) × 5, "Additional plot available at Lvl. {0}."; 9 a 11 nunca abrem). `castles.land_grade`
  (0041): nível das terras, 1 a 10.
- **Caixa por tempo / offline** (colunas `box_*`, `offline_*` em `characters`): o tempo desde o último
  resgate é acumulado a cada 5019 e na saída (`GameSession.on_disconnect`); a saída grava a hora para
  o tempo offline do próximo login.

## Opcodes

| C>S | o que faz | resposta | fonte |
|---|---|---|---|
| 5015 | acumula a produção e grava | 109 CastleYieldMsg | visto |
| 8281 | fim do tutorial na cidade externa: liga a produção e cria a fila 1 | 109, 109, 100, 4130, 104 | visto |
| 8203 | upgrade de prédio/tecnologia (`buildingId` do próprio jogador → `NextGradeTemplateId`). Valida nível máximo (`BUILD_MAX_GRADE`), nível do jogador, `PreTemplateId`, fila livre do tipo e ouro (com a produção pendente) e cristais. Libera `NextTemplateId` (academia → tecnologia nível 0, quartel 2 → casa) e avança missões tipo 2 | 109 (pago), na tecnologia de ouro o efeito velho e o novo (110 {`PropertyType1`, ouro do nível}, 109, 152 sem a tecnologia; oficial_20261023-231733-1 #3971-#3978), 109 (se rendimento/teto/população mudaram), 151, 4130 (prédio + liberados), 83 "Town Hall has been upgraded to Lvl. 2", 112 se missão mudou | visto (inglesa #589-#594, #2127-#2132; academia e tecnologia só turco: city_city_upgrade_academy_upgrade, teknoloji_upgrade). Custo e tempo do template de destino conferidos em oficial_encantar #1591-#1595 (Town Hall 7: 700 de ouro, 150 s), #1665-#1669 (Cottage 4: 350, 15 s) e #1676-#1680 (Cottage 5: 450, 25 s); o 4130/4154 só leva `userId`, `buildingId`, `templateId`, `sonType` e `propterty1/2` |
| 8202 | constrói o nível 1 de uma tecnologia que ainda não existe (`sonType`); só MasterType 13/14 | igual ao 8203 | cliente (SeminaryFrameBottomView) |
| 8279 | lista as filas | 4187 BuildOrderList | cliente |
| 8489 | Bênção do seminário (sem corpo). Gasta `Blessing_Cast` cristais (2000 sem o template) e soma `Blessing_Buffer` (10) à bênção, até `Blessing_Max` (200). No teto ou sem cristais, recusa sem cobrar e responde com o valor atual. Conta as bênçãos do dia (`seminary_count`, pela data do `arena.today`), sem limite diário no servidor; `maxCount` fica 0 porque o cliente não lê. | 4391 `BlessingMsg` (`increase`, `usedCount`); 109 com os cristais novos, só quando cobra | cliente (`SeminaryBlessFrame`) |
| 5172 | acelera: 5 diamantes por 10 min ou fração (*(cliente inglês)* `QueueItem`, o clique na barra de filas: `ceil(remainTime/600) * 5`; o turco era ×1. **dedução**: o inglês ficou incoerente, `QueueBar.coolItem`, `BuildingManager.point` e a tela de tecnologia `SeminaryFrameBottomView` ainda mostram ×1; vale o da barra, a única tela alterada). `index` 1 = só diamante, 2 = vinculado primeiro, 0 = VIP grátis (`vip.free_cool`: VIP ativo e `type` 16 com `para1` != 0, *(cliente)* `VIPModel.vipCoolPrivilege`/`QueueBar`). `orderId` 0 = todas as filas de prédio | 3, 111 "Cooldown removed." (texto nosso, sem chave no `language.txt` inglês), 102 | dedução (sem captura inglesa) |
| 5175 | compra a 2ª fila de prédio: 395 diamantes (*(cliente inglês)* `QueueBar.buyQueueItem`, "mainBar.QueueBar.content" com 395; o 100 do alerta é o saldo mínimo), `payType` 0 = pode usar vinculado | 3, 104 | cliente |
| 8327 | cobrança de ouro: nível ≥ 14, 5 por dia, fila 3 livre; ouro = 901.P1×6 + 101.P1×3; fila 3 ocupada 1 h | 109, 111, 151 (antes do 4242: a LevyView redesenha nele), 4242 (`leftImpose` = usadas), 83 | visto + cliente |
| 5174 | enche a energia de teleporte até 151101.Property2: (máx − atual)/5 diamantes, `payType` 2 = vinculado | 3, 103 TransInfoMsg | cliente |
| 5173 | sem chamador no cliente; devolve o estado | 103 | cliente |
| 5179 | desistir da mina (`handlers/outer_city.py`, ver cidade-externa.md *Minas do mundo*) | 108 com a posição, 109, 152 | cliente |
| 8562 | cancelar a trégua (buff 2001): não há trégua ainda | 4452 `defenceLefttime` 0 | cliente |
| 8747 | entrar no castelo (já tratado em `outer_city.py`) | 4382 | visto |
| 15044 op 0 | dados da fazenda (própria ou de outro jogador) | 4386 FarmInfoRspMsg | visto (só turco: ciftlik) |
| 15044 op 1 | planta: terra aberta e vazia, semente (SonType 216) na bolsa em `bagPos` com o `templateId` certo, `NeedGrades`, uma semente especial (`Property5`) de cada tipo por vez. Amadurece em `Property1 − 1` min e rende 80% do `Property3` se for moeda. Terra melhorada (`LandUpTip`): −`FarmCrop_Mature_Percent` (2) % do tempo e +`FarmCrop_Gains_Percent` (3) % da produção por nível acima do 1 (arredondamento: dedução) | 115, 4387 (`opType`, `result` 0) | visto (só turco: ciftlik) + cliente |
| 15044 op 2/3 | tira inseto/mato da própria terra quando a praga está ativa (40%/60% e 30%/50% do ciclo); +`FarmCrop_Operate_GP` de EXP da fazenda | 4387 | cliente |
| 15044 op 4 | colhe: madura e viva (`matureTime + Property1` min); ouro bloqueado no teto como no cliente. Rende moeda (-100 ouro, -300 alma, -500 vinculado com ledger, -600 cristal), -700 EXP ou item | 4387 (terra vazia), 109 ou 3, 115 se item | cliente |
| 15044 op 2/3 (amigo) | tira inseto/mato da terra do amigo; EXP `FarmCrop_Operate_GP` para quem ajuda, dentro do teto do dia `Farm_TodayFromFriend_GP` (200; no teto a ação vale e rende 0, como `expByOper`) | 4387 com o `userId` do dono | cliente |
| 15044 op 5 | rouba da terra madura e viva do amigo (`canBeStolen`): uma vez por ladrão, até 3 ladrões (`MAX_STOLEN_COUNT`), produção ≥ 10; até `Farm_TodayStolen_Count` (200) por dia. Leva `farm_steal_percent` % (10, internet) do `rewardCount`, que sai do dono; grava `stolen_by`. Sem EXP. Missão 60 Para1 1 | 4387 (`stolenCount`, `stolenUsers`), 109/3/115 como a colheita | cliente + internet |
| 15044 op 6 | revive a planta morta do amigo: `matureTime` = agora − 1 min, o resto igual; EXP `FarmCrop_Operate_GP` (teto do dia) | 4387 | visto (só turco: ciftlik #88–#105) |
| 15044 op 7 | acelera (35 Balens `Farm_Accelerate_Point`, `payType` 0 = vinculado primeiro): corta pela metade o que falta, uma vez por plantio ("50% maturity speed-up will consume {0} Balens", `farm.view.FarmOperMenu.accelerateTip`; "already on a speed-up", `hasAccelerateTip`) | 3, 4387 | cliente |
| 15044 op 8 | limpa a terra | 4387 | cliente |
| 15044 op 9 | melhora as terras (`FarmBuildLayer`, `FarmSocketSendManager.sendLandUp`): fazenda no nível 30+ ("Once your farm reaches level 30"), terra até o 10; custo n(n+1)(n+2)/2 + 15 Balens do nível n (18, 27, 45… igual à wiki Farm), `payType` 0 = vinculado primeiro. Falha: só log (um 4387 de falha apagaria a terra 0 no cliente) | 3, 4386 (o 4387 não lê `landGrades`) | cliente |
| 15044 outros | pets (10–16), ops do dono na terra do amigo e qualquer op em quem não é amigo: recusados | 4387 `result` 1 com o `userId` do dono da terra | — |
| 15017 | rega a própria árvore a cada 10 min, 3 vezes por dia (sem fruto): ouro = grau da fazenda do dono × 20 (visto: 20 no grau 1, `oficial_20261023-153200-1` #2228), EXP da fazenda +1, `waterCount` +1; com a carga cheia (`UpGradeTempInfos` tipo 7 no grau da fazenda: 10 no 1, até 30, igual à wiki "9 + level, 30 max") vira `fruitCount` 1 e a rega para (`WaterViewContainer` command03 "Energy is already maxed out.") (o "Enerji + 1" do texto é essa carga da árvore, não a energia de teleporte; (internet) https://wartune.fandom.com/wiki/Tree_of_Ancients) | 109, 146 (`harvestMsg` com as 3 linhas), 83, 147 | visto (só turco: ciftlik #5–#10) + cliente (help: "3 times a day") |
| 15017 `userId` de amigo | rega a árvore do amigo: uma vez por dia por amigo (`relations.tree_day`), até 200 no dia (help EN). Quem rega ganha ouro = grau da fazenda do dono × 20 (visto: 920 na fazenda 46, #2242) e EXP da fazenda = grau de amizade (`expByOper` caso 8, teto do dia); a árvore do dono ganha +1 de carga sem mexer no tempo dele (gravado mesmo offline; cheia vira fruto e não aceita mais rega); a amizade sobe 1 dos dois lados. Missão 20 Para1 0 | 4158 `{playerId, operUserId}`, 109, 147 (a do amigo sem `leftTime`, depois a minha), 165 (`relationGrade`/`relationGp`), 146, 83 "Energize successful, Gold + N, Farm EXP + N, Friendship + 1" | visto (só turco: ciftlik #81–#87) + cliente |
| subida da fazenda | qualquer EXP da fazenda que passa do nível (rega, colheita da árvore, ajuda nas terras): 111, 4386 da própria e 83 "Your farm has been upgraded to level N!", e o 146/4189 seguinte com `isUpGrade` true | *(visto)* oficial_20261023-215937-1 #1277-#1285 (rega do amigo, 2 → 3); nos outros ganhos a posição é *(dedução)* |
| 5178 | colhe a árvore cheia (`TreeInfo.canPick`: a própria, `fruitCount` > 0, `leftPickTime` 0). Rende Daru e Kyanite pelo grau da fazenda (`game_settings` `tree_fruit`, 0041: Daru 3800 + 3800 por nível acima do 1, Kyanite 1000 + 100; internet, wiki Farm) e 1 de EXP da fazenda (`FarmModel._expTreePick`, que o cliente soma no 4189); a carga volta a 0. Espera até a próxima meia-noite do fuso do jogo, não às 5h (`TreeInfo.remainPickTime`): vai em `nextPickTime` e `leftPickTime` | 106 `pickMsg` (a animação mostra até 3 linhas), 4189 `harvestMsg`, 3, 109, 147 | cliente + internet; textos e ordem: dedução |
| 8219 | árvores dos ids pedidos (o cliente pede a própria ao chegar no nível 11) | 4146 FriendTreeRsp | cliente |
| 8231 | estado das fazendas: o próprio jogador primeiro (`isChargeEnergy` = pode regar a própria); para amigo, `isReap` (alguma terra roubável por mim), `isChargeEnergy` (não reguei hoje e cabe no dia), `isRevive`, `isWorm`, `isGrass` pelas terras dele; quem não é amigo vem tudo falso | 4190 LoadFarmRsp.friendFarmState | visto (só turco: ciftlik #3) |
| 8565 | invocar a árvore da terra secreta da guilda: em [guilda.md](guilda.md) (`handlers/fam.py`) | 4432 | cliente |
| 5019 | `operate=false`: sincroniza; `operate=true, time=P`: paga o TimeDrop do período P se for o próximo e já houver `P×60` s online desde o último resgate (a contagem começa no 1º 5019; depois dele conta também o tempo fora, regra em `game_settings.time_box`, 0056) | 4 BoxBoxMsg (`time` = último período recebido, `operate` = recebido, `timerun` = segundos desde o último resgate, 0 no resgate); ao pagar 109 (ou 3), 115, 4476, 111, 4250, 4, 83 ×2 e os 9 4484 de títulos | visto (inglesa #1594, #2109-#2115; oficial_encantar #131, #2683-#2699) + cliente |
| 8287 | EXP offline (`rateCount` 0 = ×1) | 3 PlayerMsg | cliente |
| 8255 | reforço numa batalha em curso num nó do mapa: sem batalha em grupo, nada | — | cliente |

No login: 4154 deriva `propterty1/2` do conselho (cobranças usadas/5) e da casa (população); 4155
com as filas; 152 com o rendimento; 4157 com a fazenda **e** `treeInfo` (sem ela o `myFarm` do
cliente fica nulo e a fazenda quebra); 4195 só se houver EXP offline (a conta nova do oficial não
recebe); PlayerMsg com `timeProcess`/`timeGet`/`timeRun`.

## Pendências e dependências

- **População ocupada** (`curPopulation`) = soldados do exército: 0 até o sistema de tropas existir
  (5155/5156/5158 são de outro agente).
- **Rendimento**: o oficial soma +30/h que não sabemos de onde vem (só turco, login.json: 8550 = 8220 dos
  prédios + 300 de tecnologia + 30); sem terras selvagens, guilda e efeitos.
- ~~**Fazenda de amigo**~~: feita (tabela acima). Quem pode: só amigo (`relation` 1, que já é dos dois lados).
  Contadores do dia no castelo de quem age (`farm_day`, `farm_friend_gp`, `farm_steals`, `tree_water_today`,
  `tree_friend_today`, migração 0037); `todayFromFriendGp`/`todayStolenCount` vão no 4386 da própria fazenda.
  Fontes: limites do cliente (`FarmModel`, `FarmLandInfo.canBeStolen`, `ConfigInfos` e o help EN da fazenda),
  reviver e regar visto (só turco: ciftlik). **dedução / config** (`game_settings`, 0037): roubo de 10% (`farm_steal_percent`,
  internet: só o resumo da busca sobre https://breezewiki.discard.no/wartune/wiki/Farm, a página não abriu); grau de amizade = 1 + pontos // `friend_grade_step` (10; só turco, ciftlik: grau 4 com 34); amizade +1 dos dois
  lados; ouro da rega pelo nível de jogador do dono (o 66 do THoR também era o grau da fazenda); textos 146/83 em
  inglês montados com os termos do language EN. O dono online é mexido no snapshot da sessão dele; offline, pelo banco
  (ponytail: dois ladrões ao mesmo tempo com o dono offline podem se sobrepor).
- **Captura que falta (fazenda de amigo)**: (1) roubar uma terra madura de amigo (15044 op 5): gravar o 4387, o 109/115
  e o 83, para conferir os 10% e o texto; (2) tirar inseto/mato na fazenda de amigo (op 2/3); (3) regar a árvore do
  mesmo amigo duas vezes no dia e regar com o teto de 200 EXP batido, para ver as recusas; (4) a tabela de grau de
  amizade: anotar `relationGp`/`relationGrade` do 165 em vários amigos; (5) com o dono online, ver se ele recebe algo
  (4158 ou 147) quando um amigo rega ou rouba.
- **Árvore**: nenhuma captura tem `fruitCount` > 0 (147, 4190, 4146) nem 5178/106. **Precisa de captura**: regar a própria árvore até `fruitCount` > 0 (147), colher (5178 com `index`) e gravar a resposta (106, 4189, 3, 109), para conferir o Daru e o Kyanite de `tree_fruit`, os textos e se o oficial manda `isFirstFruit`. Os itens 2160037–2160046 e 2160055 são sementes da fazenda (SonType 216), não o fruto.
- **Offline**: ×1,5 e ×2 custam diamante no oficial, preço desconhecido (recusados); EXP =
  nível × minutos fora, até 8 h *(dedução)*.
- **Caixa por tempo**: tempo fora e sem reset diário vêm de uma amostra única (#131); `time_box.count_offline`/`daily_reset` trocam a regra. Depois do 180 o cliente para de pedir (`BoxManager.needCountTime`).
- **Trégua** (8562): só confirma; depende do mapa-múndi.
- **Árvore da guilda** (8565, resposta 4432) e **reforço** (8255): sistemas de guilda e batalha em grupo.
- **Bênção do seminário**: o `blessingBuff` (o bônus que o cliente mostra) ainda não entra nos atributos do
  personagem. `Blessing_ItemId` (208026) não é usado pelo servidor.
