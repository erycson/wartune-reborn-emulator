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
  `offer:count`, `ring`.
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
