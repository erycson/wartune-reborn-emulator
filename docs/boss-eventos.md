# Boss e eventos

Visão geral e legenda em [multiplayer.md](multiplayer.md). Há captura só da agenda (4182 em
`login.json` e `replay_packets.json`); da batalha do chefe não há nenhuma.

## Boss mundial *(cliente)*

### Templates

- **`CampaignInfo` com `Types=1`:**
  - 5001 "Kızıl Gözlü Kurt": nível 20, 11:00–12:00.
  - 5003 "Ejderha Kemiği": 21:35–22:35.
  - O cliente trata os mapas 5000–5100 como boss.
- **Heróis do boss:** `GameHeroTempInfo` 2002 "Kızıl Gözlü Kurt" e 2003 "Ejderha Kemiği",
  `HeroType=3`, `Grades=50`, `Live=2000000`, `Attack=20000`, `MagicAttack=20000`, `ForceHit=705`,
  `AI` 20041/20061, `DefaultSkill` 50041/50128. Os ids 2002/2003 de `PawnTempInfos` são tropas comuns (`Live` 400),
  não o chefe.
  - **Ligação campanha -> herói: só por nome** (5001 e 2002, 5003 e 2003). Nenhuma coluna liga os
    dois. *(dedução)*
  - O `Live` é o HP cheio do chefe. O cliente só recebe `totalHp` no 4174.
- **Buff do chefe:** `CampaignBufferTemps` `Types=4`, 401–420 (+5% a +100% de atributos, só na
  batalha do chefe, grade máxima 20). Os 701–720 "Moral Lv. N" são `Types=7` (ataque +500 a +10000,
  grade 1 a 20, ícone `/buff_worldboss.png`), outro buff: a compra (8470) usa só o `Types=4`
  (`WorldBossBuyBuffModel.BUFFER_TYPE = 4`). Quem dá a moral não está no cliente. **precisa de captura**.
- **Mapas:** `MapInfos` 5001 e 5003 ("Dünya BOSS", `MapFileId` = id, `BattleGround` 11, 1600x1700).
  `MapInfos` 5002 tem o mesmo nome mas não tem linha em `Campaigns`: não entra na agenda.
- **Prêmios:** nenhuma linha de `RewardTemps`, `RewardGoods`, `CampaignData` ou `MapNodeInfos` cita
  5001, 5003, 2002 ou 2003. A tabela de prêmios do chefe não está nos templates.
- **Preços em `ConfigInfo`:**
  - `WorldBoss_Buffer_*_Price=5`
  - `WorldBoss_Replacement_Price=30` (dublê)
  - `Live_Pay=2`: lido pela `RiverView` tipo 1, mas o botão de reviver só existe no altar (tipo 2)
  - `Live_Fight_Pay=3`: entrar na luta agora (o botão do chefe)

### Agenda

**Quem decide é o servidor.** O horário do template só aparece no texto "fechado".

- O cliente manda **8271** (vazio) no login. O servidor responde com o **4182**
  `WorldBossStateMsg{worldBossInfo[]{campaignId, state}}`, só com os chefes de `Campaigns`
  `Types=1` (5001 e 5003).
- Significado de `state`: 0 = aberto (de `OpenTime` até `StopTime`), 1 = ainda não abriu hoje,
  2 = encerrado. *(visto)* `login.json #120`: 5001=2, 5003=1.
  - O 0 vem do cliente (`WorldBossManager`, `state == 0`). Nenhuma captura mostra o 0 no 4182: só 1 e 2.
  - O 0 = aberto aparece no 4248 (mesmo `WorldBossStateMsg`): *(visto)* `login.json #121` (20:06
    UTC+3) tem 4001–4009=2, **4010=0** (janela 20:00–20:25) e 4011–4013=1.
  - Na mesma mensagem há um 3: *(visto)* `replay_packets.json #103` (12:20) tem 4002=3 (janela
    12:00–12:25). Aos 6 min da janela é 0, aos 20 min é 3: talvez "entrada encerrada, luta em
    andamento". *(dedução)* Para o chefe o 3 não aparece em captura e não é mandado.
- **Fuso UTC+3.** Duas capturas batem: o 4182 de `replay_packets.json` (pacotes 78 -> 102, 12:20
  local, 09:20 UTC) mandou 5001=2 e 5003=1 (em UTC, 5001 daria 1), e o de `login.json #120`
  (20:06 local) também 5001=2 e 5003=1. Código: `game/worldboss.py` (`GAME_TZ`).
- O cliente guarda todo `Types>=1` menos 5 e 9, e derruba com um `campaignId` fora desse
  dicionário: o 4182 nunca leva outro id.
- O 4182 só sai como resposta ao 8271. Não há tarefa periódica no servidor, então quem já está
  logado não vê o chefe abrir até relogar. *(dedução)*
  - O oficial empurra a mudança: *(visto)* `replay_packets.json #619`, 12:25:04, 4248 sem pedido e
    só com o id que mudou (4002=2) no fim da janela. Para o 4182 não há captura do empurrão.
    ponytail: sem tarefa periódica; quando o chefe tiver mapa, mandar `{campaignId, state}` no
    `OpenTime`/`StopTime` para todos online.
- O **4248** é o mesmo formato para o campo de batalha (4001–4013) e já sai no login
  (`warfield.login`).
- O **4381** `{campaignId, leftTime}` é o aviso de pré-carregamento antes de abrir. É opcional;
  não é mandado.

### Mapa do chefe *(dado verificado no espelho local da CDN, só leitura)*

- `maps/5001/5001.maps` e `maps/5003/5003.maps` existem no espelho (`D:\xampp\htdocs\wartune-cdn\maps`).
  Decodificados (AMF3, mesmo decodificador de `memory/campaign-nodes-in-maps-files`), trazem só
  decoração: 5001 tem 1756 objetos com `campaign: null` e 5003 tem 2047; nenhum dos dois tem objeto
  com `campaign` preenchido. Nenhum dos 13 mapas com nós é o do chefe.
- Então o **nó do chefe** (`campDataId`, `nodeId`, `masterType`, `sonType`, `heroTempId`,
  `BattleType`) não está no arquivo e não está em `CampaignData`. Em masmorra o nó também vem do
  banco do oficial. **precisa de captura**: o 130 (lista de nós) do mapa 5001 numa entrada real.
- Atacar um nó: o cliente anda até ele e manda **5125** `CampaignReqMsg{paraInt1=nodeId}`
  (`CampaignArmyViewHelper` -> `MapSocketOuterManager.sendCampaignArrive`). É o mesmo caminho do
  tutorial. Sem o nó do chefe no servidor não há o que atacar.

### Pedidos C>S

Handlers em `game/handlers/worldboss.py`. Recusa = 111 (aviso no meio da tela) e nada cobrado.

| Opcode | Nome | Corpo | Servidor | Fonte |
|---|---|---|---|---|
| 8271 | `C_WORLDBOSS_STATE` | vazio | 4182 com a agenda de hoje | *(visto)* captura; *(cliente)* `WorldBossManager.setup` |
| 8258 | `C_WORLD_BOSS_CMD` | `WorldBossMsg{param1=campanha}` | 111 com o motivo: id fora do template, janela fechada, nível abaixo de `MinLevel` (20), em batalha ou em campanha. Se tudo passa, 111 de "mapa não pronto". Nunca 125 | *(cliente)* `WorldBossSocketOutManager.sendWorldBossCmd` (5 s entre pedidos no cliente) |
| 8259 | `C_WORLD_BOSS_REQ` | `WorldBossMsg{mapId}` | nada (log) | *(cliente)* `reqWorldBossCmd` existe, mas nenhum arquivo o chama |
| 8264 | `C_WORLDBOSS_PLAYER_LIVE` | `PayTypeMsg{payType}` | 111, sem cobrança | *(cliente)* `WorldBossRiverMediator` → `RiverView()` tipo 1: entrar na luta com `Live_Fight_Pay`=3; payType 0 = vinculado primeiro, 1 = só diamante (como `cash.split`) |
| 8470 | `C_WORLDBOSS_BUFFER` | `WorldBossBufferMsg{op=2, type}` | 111, sem cobrança | *(cliente)* `buyWorldBossBufferWithPointOrGiftToken` → `MapSocketOuterManager`; `type` 2 = vinculado, 1 = só diamante; preço `WorldBoss_Buffer_Diamond_Price` / `WorldBoss_Buffer_Gift_Price` = 5 |
| 8535 | `C_CANCEL_TRANS` | vazio | nada (log). Cancela o transporte do jogador morto no mapa de PvP do chefe, que não existe aqui. O cliente não espera resposta | *(cliente)* `SocketSendManager.sendCancelTransport` |

**Dependências (por que cada recusa):**
- **Mapa do chefe.** O `.maps` de 5001/5003 existe, mas não tem nó (ver *Mapa do chefe*). Sem o nó
  do chefe não há alvo para o 125 nem para o 5125. **precisa de captura** da entrada (8258 -> 125 ->
  130) para montar o nó.
- **Batalha compartilhada.** O 157 com `battleType 17`, o boss com `type==3`
  (`BattleModel.getWorldBoss`), herói 2002/2003 (vida 2 000 000). Não há captura da luta nem do
  que encerra a batalha de cada jogador. Falta: 4174 (HP global), 4435, 4203 e 4369.
- **Morte e entrada paga.** O 4175 de morte nasce na batalha do chefe. Sem o servidor saber que o
  jogador morreu, o 8264 é recusado. Quando a batalha existir: contar a morte, cobrar
  `Live_Fight_Pay` (3, com a regra de vinculado do payType) e mandar o 4175 de volta. Não há
  botão de reviver pago no chefe: `Live_Pay` (2) não tem uso no cliente do chefe.
- **Buff.** Só se compra dentro do mapa do chefe, e o efeito só vale na batalha
  (`CampaignBufferTemps` `Types=4`, 401–420, grade máxima 20). O cliente lê o nível atual pelo
  4165 (`bufferTempId`, `leftTime`) e pelo 4174 (`bufferGrade`). Duração e reset não estão no
  cliente nem em captura, então nada é gravado.
- **Altar de guilda.** O 8264 também é o reviver do altar (`RiverView` tipo 2, paga
  `AltarLive_Offer` = 50 de contribuição). Quem fizer o mapa do altar separa pelo mapa do jogador;
  a recusa atual vale para os dois.
- **Pedido de info (8259).** Sem chamador no cliente: nada a responder.

### Batalha compartilhada

**Entrada**
- O cliente manda **8258** `WorldBossMsg{param1=campaignId}`.
- A resposta deve ser a mesma entrada de campanha que já temos, no mapa 5001 *(dedução)*.

**HP global**
- O servidor faz broadcast do **4174** `WorldBossInfoMsg` com:
  - `curHp`, `totalHp`
  - `woundInfo[]{userId, nickName, wound, job}`
  - `myWound`, diferente para cada destinatário
  - `currentMillis`
  - `bufferGrade`
- O cliente monta sozinho o top 10 a partir do `woundInfo`.

**Na batalha**
- O 157 vai com `battleType 17` e o boss com `type==3` (`BattleModel.getWorldBoss`).
- O **4435** ajusta a barra de HP.
- Não se sabe o que encerra a batalha de cada jogador. Provavelmente é tempo ou a morte dele: o
  boss sobrevive à batalha individual.

**Morte e reviver**
- O **4175** `PlayerStateListMsg{playerState[]{armyId, state:1, leftTime ms}}` avisa a morte. A
  contagem é de uns 20 s.
- Entrar na luta pagando (botão da `RiverView` tipo 1): o cliente manda **8264** `PayTypeMsg`.

**Extras**
- Buff: 8470.
- Dublê: 8526, com as respostas 4424 e 4423. Recusado em `handlers/dungeon.py` (sem cobrança; preço
  `WorldBoss_Replacement_Price` = 30). Nas pastas decompiladas nada chama `sendBuyStunmanFor`: a tela
  `worldboss.BuyAvatarFrame` não está lá, então o lugar da compra não foi confirmado. *(dedução)*

### Fim

- **4203** `WorldBossReportMsg{order, gold, strengy, totalWound}`: posição, ouro e Ruh.
- **4369**: marcos de dano acumulado.
- As recompensas são definidas pelo servidor.

## Regras pela Internet (pesquisa de 2026-10-18)

Tudo aqui é *(internet)*; o help do cliente (`worldboss.view.BaseHelpFrame.helpText`) confirma ouro e Ruh por
golpe, "HP e tropas não se esgotam", o prêmio do último golpe (Şanslı Ödülü), o top 10 de dano e o prêmio por
0,3%/0,5%/0,8% do dano total. Wiki: https://wartune.fandom.com/wiki/World_BOSS (lida pela `api.php`, revisões
`?oldid=`); guia da Koram: http://wartune.koramgame.com/2013/gameguide_0302/8.html; DolyGames:
https://wartune.dolygames.com (posts citados abaixo).

- **Chefes e horários**: Bloodfang, Ragnoch e Redoga Drake, todos Lv50 (`?oldid=4813`: 11:00, 16:00, 22:00).
  Depois do Patch 2.1, 2 por dia (Bloodfang 11:30-12:30, depois 11:35; Redoga 22:00-23:00). Janela de 1 h.
  Aviso "30 minutes before ... every 5 minutes" (Koram). Nível 20+. **Conflito**: o cliente fala em chefe Lv70
  e janela "15:10 - 18:10"; nenhuma fonte cita.
- **Vida**: 76 886 700 (`?oldid=4813`, 2012) → 115 330 078 (`?oldid=8129`, 2013) → ~250 milhões (Doly
  my-best-world-boss-fight) → ~1,16 bi e alternando 1 167M/1 500M (fórum R2 147430, 156752, 2015-16).
  **Escala**: "A Boss' health will increase the quicker a server kills the boss and decrease the longer a
  server takes" (wiki), por chefe; "when the server did manage to kill the WB in under 10 minutes his HP
  would grow for the next time" (Doly reflecting-on-world-boss-in-dec-2016); gamelytic: "The boss' level
  scale with ... the average level of the players on the server". Nenhuma fonte dá a fórmula. Luta normal
  de 12-16 min (Doly 508).
- **Luta**: cada golpe é uma batalha individual; cada um vê no máximo 30 jogadores; o chefe dá 5 golpes e o
  sexto em área mata ("kill you on the sixth one"); "troops and blood volume will not be damaged", sem EXP.
  Morte: 30 s ou reviver pago (35 → 15 Balens; 10 na Fairytale). Patch 7.8 (2018): o chefe fica invencível
  nos primeiros 5 min, e o dano conta para o prêmio.
- **Moral (Inspiration)**: "For every 500,000 points of damage dealt by the top player, every player in the
  battle receives a boost of 500 ... maximum level of 20 ... 10,000,000 damage ... boost of 10,000" (wiki).
- **Buff comprado**: 20 Balens/Vouchers por +5% (até 10x no 1.46; até 20x em dez/2013); removido no Patch 5.5.
- **Dublê**: 30 diamantes, marcado antes de abrir, até 3 lutas, sem prêmios de top e de % (vídeo
  https://www.youtube.com/watch?v=iXbY85obSiQ, V1.50 chinês).
- **Ouro e Daru por golpe**: "ratio of 1:5 ... 100,000 damage ... 20,000 Gold and 20,000 Daru" (wiki); teto de
  10M por luta desde o 7.8 (Doly discussing-world-boss-changes-in-wartune-patch-7-8). O dano do Eudaemon não
  conta. *(dedução)* Ruh do cliente = Daru.
- **Último golpe**: 1 000 000 de ouro (`?oldid=5206`) → 1,2-1,3M → 1,7M (`?oldid=12788`); "varies based on
  World Boss' total health (e.g. 1.5 million or 1.7 million gold)" (wiki atual); título Mortal Blow (HP +340).
- **Top 10 por classe**: 360k/300k/240k/180k (do 4º ao 10º) em nov/2013 (`?oldid=18253`), depois
  300k/270k/240k/180k, de ouro e daru. Antes: top 3 com 200k+200k (`?oldid=5206`).
- **Por % do dano**: 0,3%/0,5%/0,8% → 60k/180k/360k (`?oldid=18143`) ou 60k/120k/180k (`?oldid=19424`);
  servidores antigos: 1% → 360k. Removido no Patch 5.5.
- **Prêmios somam?** Conflito: "you only receive one prize, whichever is best" (`?oldid=13462`) contra "Players
  can acquire Beating Reward as well as other rewards" (Koram). Prêmios vão por correio (Koram).
- **Fim**: a masmorra fecha quando o tempo acaba ou o chefe morre, e todos voltam para a cidade. Sem fonte para
  o último golpe quando o chefe não morre. Participantes: "like 300-500 people" (Doly world-boss-last-hits).

## Captura que falta

Cada item diz o que gravar no `captures/` (ou no relay) e o que fazer no jogo. Todos com um
personagem de nível 20 ou mais, sem batalha e sem campanha abertas, no horário da janela
(UTC+3). Os pacotes esperados estão entre parênteses.

1. **Estado aberto da agenda.** Entrar entre 11:00 e 12:00 (ou 21:35–22:35) e logar. Gravar o 4182
   (esperado: 5001=0 ou 5003=0; hoje só vimos 1 e 2). Confirma o 0 do cliente.
2. **Entrada no chefe.** Clicar no chefe com a janela aberta. Gravar 8258, 125 (mapa 5001 ou
   5003), 130 (lista de nós, com o nó do chefe), 4174 (HP cheio e `woundInfo` vazio), 4182 e 157
   (`battleType` e herói do chefe).
3. **Ataque.** Andar até o nó e atacar. Gravar 5125 (`paraInt1` = nodeId), 157, 153, 156, 154, 4103,
   4174 depois de cada golpe (`curHp`, `woundInfo`, `myWound`), 4435 se o servidor mandar.
4. **Morte e entrada paga.** Morrer no chefe e clicar em entrar pagando (vinculado e diamante).
   Gravar 4175 (`leftTime`), 8264 (`payType` 0 e 1) e a resposta com o saldo.
5. **Buff.** Comprar o buff do chefe (`Types=4`) dentro do mapa (8470 `type` 1 e 2). Gravar 8470 e 4165
   (`bufferTempId`, `leftTime`) e o saldo antes e depois.
6. **Dublê.** Comprar e cancelar o dublê na tela de dublê (`BuyAvatarFrame`, onde ela abrir) (8526 `op` 1 e 2). Gravar 8526, 4424 e 4423.
7. **Fim.** Deixar a janela fechar (depois de 12:00) com a sessão aberta. Gravar 4203
   (`order`, `gold`, `strengy`, `totalWound`) e 4369 (marcos de dano e estado de cada um).
8. **Ranking com dois jogadores.** Dois personagens no mesmo chefe, cada um com dano. Gravar os dois
   4174 para confirmar a ordem do `woundInfo` e o `myWound` de cada um.

Sem essas capturas não há como montar o nó, a batalha compartilhada, a regra do dano, a morte, o
buff com duração e os prêmios. Nada disso é inventado no servidor.

## Boss de guilda

A guilda está pronta ([guilda.md](guilda.md)); o altar abre (8541 -> 4436 para os membros, estado
no 164/4138), mas a entrada (8542) é recusada: falta o mapa de campanha 7601 com as ondas.

- **7601 "Lanetli İbadethane"** é a defesa do altar:
  - abertura: o servidor manda o 4436;
  - entrada: o cliente manda o 8542;
  - relatório: o servidor manda o 4437 (durabilidade, ondas, `hurtOrder`).
- **7501 "Birlik Sırrı"**: 8537.

Quem abre é quem tem o direito 3 (só o chefe), com a guilda no nível 5, pagando 50000 ou 200000
de riqueza (`Consortia_OpenAltar1_Offer`/`2`); m6 `ConsortiaSocektSendManager.sendOpenDemon`.

## Atividades, assinatura, login acumulado, leed, VIP, recompensas e minigames

Implementados: regras, opcodes e dependências em [eventos.md](eventos.md).

## Prioridade

1. **Login sem quebrar os painéis:**
   - 4182 com 5001/5003, com estados coerentes com a hora;
   - 4248;
   - 4475 com `maxPage=1`;
   - 4476 ao receber o 8586 tipo 1.
2. Resgate de atividades (13 e 14), assinatura e login acumulado: feito ([eventos.md](eventos.md)).
3. **Boss mundial:** agenda (8271 -> 4182) e recusas (8258, 8264, 8470) prontos. Falta o mapa
   do chefe (ver as dependências acima): entrada, HP global (4174), morte (4175) e relatório (4203).
   As capturas que faltam estão em *Captura que falta*.
4. **Guilda e altar.**
