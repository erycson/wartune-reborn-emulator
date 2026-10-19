# Castelo, prédios, tecnologia, produção, fazenda, caixa por tempo e recompensa offline

Fontes: *(visto)* = captura do oficial (`captures/*.json`); *(cliente)* = AS3 decompilado em
`D:/wartune/decompiled` (`m2/scripts/managers/BuildingSocketOutManager.as`,
`yishi/manager/BuildingManager.as`, `m2/scripts/farm/`, `yishi/manager/WaterManager.as`,
`managers/BoxSocketOutManager.as`, `yishi/view/frame/HookRewardFrame.as`); *(dedução)* = regra
nossa onde nem captura nem cliente dizem. Código: `game/castle.py`, `game/farm.py`,
`game/timebox.py`, `game/handlers/castle.py`, `game/handlers/farm.py`, `game/handlers/rewards.py`.

## Modelo

- **Upgrade é imediato** *(visto)*: o 4130 já sai com o template novo; a fila fica ocupada
  `UpgradeTime` segundos (`remainTime = begin + needTime - agora`).
- **Filas** (`build_orders`) *(visto)*: tipo 1 prédio, 2 tecnologia (MasterType 13/14), 3 cobrança
  de ouro. Números do oficial: 1 = prédio (nasce no 8281), 2 = cobrança, 3 = tecnologia; fila
  comprada = maior + 1. Limite de 2 filas de prédio (`BuildingModel.buildOrderLimit`) *(cliente)*.
  O login completa as que faltam (`castle.ensure`).
- **Produção** *(visto, login.json)*: ouro/hora = Property1 do conselho (901) + mina (101) +
  Σ tecnologias de ouro (MasterType 13) `EffectTempInfos[Property1].Property1 × nível`. Teto =
  Property2 do depósito (301), 10000 sem depósito. Acumulada sob demanda (`settle`), guardando a
  fração de hora; ouro de outras fontes pode passar do teto e aí a produção para. População máxima
  = Property2 da casa (1201). Cristais começam em 1000. Teto do armazém e população máxima sobem com
  os pergaminhos 2010501 (efeito 2008) e 2010801 (2005) enquanto durarem (`game/buffs.py`, ver itens.md).
- **Diamante** (`point`) e **diamante vinculado** (`gift_token`): todo débito/crédito passa por
  `services/ledger.py` e grava uma linha em `cash_ledger` na mesma transação.
- **Fazenda** (`farm_lands` + colunas `farm_*`/`tree_*` em `castles`): só terras plantadas têm
  linha. 3 terras abertas (`FarmModel.DEFAULT_OPEN_LAND`).
- **Caixa por tempo / offline** (colunas `box_*`, `offline_*` em `characters`): o tempo online do
  dia é acumulado a cada 5019 e na saída (`GameSession.on_disconnect`); a saída grava a hora para
  o tempo offline do próximo login.

## Opcodes

| C>S | o que faz | resposta | fonte |
|---|---|---|---|
| 5015 | acumula a produção e grava | 109 CastleYieldMsg | visto |
| 8281 | fim do tutorial na cidade externa: liga a produção e cria a fila 1 | 109, 109, 100, 4130, 104 | visto |
| 8203 | upgrade de prédio/tecnologia (`buildingId` do próprio jogador → `NextGradeTemplateId`). Valida nível máximo (`BUILD_MAX_GRADE`), nível do jogador, `PreTemplateId`, fila livre do tipo e ouro (com a produção pendente) e cristais. Libera `NextTemplateId` (academia → tecnologia nível 0, quartel 2 → casa) e avança missões tipo 2 | 109 (pago), 109 (se rendimento/teto/população mudaram), 151, 4130 (prédio + liberados), 83 "Geliştirilen Seviye: …", 112 se missão mudou | visto (city_city_upgrade_academy_upgrade, teknoloji_upgrade) |
| 8202 | constrói o nível 1 de uma tecnologia que ainda não existe (`sonType`); só MasterType 13/14 | igual ao 8203 | cliente (SeminaryFrameBottomView) |
| 8279 | lista as filas | 4187 BuildOrderList | cliente |
| 8489 | Bênção do seminário (sem corpo). Gasta `Blessing_Cast` cristais (2000 sem o template) e soma `Blessing_Buffer` (10) à bênção, até `Blessing_Max` (200). No teto ou sem cristais, recusa sem cobrar e responde com o valor atual. Conta as bênçãos do dia (`seminary_count`, pela data do `arena.today`), sem limite diário no servidor; `maxCount` fica 0 porque o cliente não lê. | 4391 `BlessingMsg` (`increase`, `usedCount`); 109 com os cristais novos, só quando cobra | cliente (`SeminaryBlessFrame`) |
| 5172 | acelera: 1 diamante por 10 min ou fração (`QueueBar.coolItem`). `index` 1 = só diamante, 2 = vinculado primeiro, 0 = VIP grátis (`vip.free_cool`: VIP ativo e `type` 16 com `para1` != 0, *(cliente)* `VIPModel.vipCoolPrivilege`/`QueueBar`). `orderId` 0 = todas as filas de prédio | 3, 111 "Bekleme Süresi kaldırıldı.", 102 | visto (savasa_baskin_ve_elmas_ile_hizlandirma) |
| 5175 | compra a 2ª fila de prédio: 100 diamantes, `payType` 0 = pode usar vinculado | 3, 104 | cliente |
| 8327 | cobrança de ouro: nível ≥ 14, 5 por dia, fila 3 livre; ouro = 901.P1×6 + 101.P1×3; fila 3 ocupada 1 h | 109, 111, 151 (antes do 4242: a LevyView redesenha nele), 4242 (`leftImpose` = usadas), 83 | visto + cliente |
| 5174 | enche a energia de teleporte até 151101.Property2: (máx − atual)/5 diamantes, `payType` 2 = vinculado | 3, 103 TransInfoMsg | cliente |
| 5173 | sem chamador no cliente; devolve o estado | 103 | cliente |
| 5179 | abandonar terra selvagem: não há terras ainda | 108 vazio | cliente |
| 8562 | cancelar a trégua (buff 2001): não há trégua ainda | 4452 `defenceLefttime` 0 | cliente |
| 8747 | entrar no castelo (já tratado em `outer_city.py`) | 4382 | visto |
| 15044 op 0 | dados da fazenda (própria ou de outro jogador) | 4386 FarmInfoRspMsg | visto (ciftlik) |
| 15044 op 1 | planta: terra aberta e vazia, semente (SonType 216) na bolsa em `bagPos` com o `templateId` certo, `NeedGrades`, uma semente especial (`Property5`) de cada tipo por vez. Amadurece em `Property1 − 1` min e rende 80% do `Property3` se for moeda | 115, 4387 (`opType`, `result` 0) | visto (ciftlik) + cliente |
| 15044 op 2/3 | tira inseto/mato da própria terra quando a praga está ativa (40%/60% e 30%/50% do ciclo); +`FarmCrop_Operate_GP` de EXP da fazenda | 4387 | cliente |
| 15044 op 4 | colhe: madura e viva (`matureTime + Property1` min); ouro bloqueado no teto como no cliente. Rende moeda (-100 ouro, -300 alma, -500 vinculado com ledger, -600 cristal), -700 EXP ou item | 4387 (terra vazia), 109 ou 3, 115 se item | cliente |
| 15044 op 7 | acelera (10 diamantes `Farm_Accelerate_Point`, `payType` 0 = vinculado primeiro): amadurece na hora, uma vez por plantio | 3, 4387 | cliente + dedução |
| 15044 op 8 | limpa a terra | 4387 | cliente |
| 15044 outros | roubar (5), reviver (6), ações em fazenda de amigo, upgrade de terra (9) e pets (10–16): recusados | 4387 `result` 1 na própria fazenda, nada na de amigo | — |
| 15017 | rega a própria árvore a cada 10 min (sem fruto): ouro = nível do dono × 20, EXP da fazenda +1, `waterCount` +1 (o "Enerji + 1" do texto é essa carga da árvore, não a energia de teleporte; (internet) https://wartune.fandom.com/wiki/Tree_of_Ancients). Árvore de amigo: recusada | 109, 83 "Doldurma başarılıAltın + N,Enerji + 1,Çiftlik EXP  + 1", 147 | visto (ciftlik, 2 capturas: 220 no nível 11 e 1.320 na árvore de amigo de nível 66) |
| 5178 | colher a árvore: recusada (o servidor nunca tem fruto). Cliente: `TreeInfo.canPick` exige `fruitCount` > 0; a colheita soma 1 de EXP da fazenda (`FarmModel._expTreePick`). Resposta do oficial: 106 (`U_C_TREE_PICK`, sem handler no cliente) | — | cliente |
| 8219 | árvores dos ids pedidos (o cliente pede a própria ao chegar no nível 11) | 4146 FriendTreeRsp | cliente |
| 8231 | estado das fazendas: o próprio jogador primeiro (`isChargeEnergy` = pode regar a própria), amigos todos falsos | 4190 LoadFarmRsp.friendFarmState | visto (ciftlik) |
| 8565 | invocar a árvore da terra secreta da guilda: sem guilda, nada | — | cliente |
| 5019 | `operate=false`: sincroniza; `operate=true, time=P`: paga o TimeDrop do período P se for o próximo e já houver `P×60` s online hoje | 4 BoxBoxMsg (`time` = último período recebido, `operate` = recebido, `timerun` = segundos online hoje); 115, 109, 3 ao pagar | visto (tut2) + cliente |
| 8287 | EXP offline (`rateCount` 0 = ×1) | 3 PlayerMsg | cliente |
| 8255 | reforço numa batalha em curso num nó do mapa: sem batalha em grupo, nada | — | cliente |

No login: 4154 deriva `propterty1/2` do conselho (cobranças usadas/5) e da casa (população); 4155
com as filas; 152 com o rendimento; 4157 com a fazenda **e** `treeInfo` (sem ela o `myFarm` do
cliente fica nulo e a fazenda quebra); 4195 só se houver EXP offline (a conta nova do oficial não
recebe); PlayerMsg com `timeProcess`/`timeGet`/`timeRun`.

## Pendências e dependências

- **População ocupada** (`curPopulation`) = soldados do exército: 0 até o sistema de tropas existir
  (5155/5156/5158 são de outro agente).
- **Rendimento**: o oficial soma +30/h que não sabemos de onde vem (login.json: 8550 = 8220 dos
  prédios + 300 de tecnologia + 30); sem terras selvagens, guilda e efeitos.
- **Fazenda de amigo** (roubar, reviver, praga, regar árvore de amigo, EXP diária de amigos):
  depende da lista de amigos para validar. Regar a árvore de amigo (15017 com `userId` de outro) tem o que falta: ouro = nível do dono × 20 (visto, 1.320), EXP da fazenda = 1 × grau de amizade (+4 com grau 4; `FarmModel.expByOper`, caso 8; teto `Farm_TodayFromFriend_GP` = 200 por dia) e "Arkadaşlık + 1" (amizade, regra não achada). Sem energia. Falta: quem pode regar (cooldown do dono, limite por amigo), o que o 4158 (`FarmLogRsp`) quer dizer, e gravar o castelo do dono, online ou offline. Captura: `ciftlik.json` linhas 81–87.
- **Árvore**: nenhuma captura tem `fruitCount` > 0 (147, 4190, 4146) nem 5178/106. **Precisa de captura**: regar a própria árvore até `fruitCount` > 0 (147), colher (5178 com `index`) e gravar a resposta (106, 115, 109), depois ver a árvore voltar a 0. Os itens 2160037–2160046 e 2160055 são sementes da fazenda (SonType 216), não o fruto.
- **Upgrade de terra** (op 9) e terras extras: sem sender decompilado; ficam 3 terras.
- **Aceleração da fazenda**: o texto do oficial não está decompilado; aqui amadurece na hora.
- **Offline**: ×1,5 e ×2 custam diamante no oficial, preço desconhecido (recusados); EXP =
  nível × minutos fora, até 8 h *(dedução)*.
- **Caixa por tempo**: o dia vira às 5h no fuso do jogo, como os outros contadores diários.
- **Trégua** (8562) e **terras selvagens** (5179): só confirmam; dependem do mapa-múndi.
- **Árvore da guilda** (8565, resposta 4432) e **reforço** (8255): sistemas de guilda e batalha em grupo.
- **Bênção do seminário**: o `blessingBuff` (o bônus que o cliente mostra) ainda não entra nos atributos do
  personagem. `Blessing_ItemId` (208026) não é usado pelo servidor.
