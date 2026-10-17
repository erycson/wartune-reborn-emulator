# Boss e eventos

Visão geral e legenda em [multiplayer.md](multiplayer.md). Há captura só da agenda (4182 em
`login.json` e `replay_packets.json`); da batalha do chefe não há nenhuma.

## Boss mundial *(cliente)*

### Templates

- **`CampaignInfo` com `Types=1`:**
  - 5001 "Kızıl Gözlü Kurt": nível 20, 11:00–12:00.
  - 5003 "Ejderha Kemiği": 21:35–22:35.
  - O cliente trata os mapas 5000–5100 como boss.
- **Heróis do boss:** `GameHeroTempInfo` 2002/2003, `HeroType=3`. O HP total é definido pelo
  servidor.
- **Buff do chefe:** `CampaignBufferTemps` `Types=4`, 401–420 (+5% a +100% de atributos, só na
  batalha do chefe). Os 701–710 "Moral Lv.N" são `Types=7` (ataque +500 a +5000), outro buff.
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
- **Fuso UTC+3.** A captura do 4182 (`replay_packets.json`, pacotes 78 -> 102) saiu às 12:20 local
  (09:20 UTC) e mandou 5001=2 e 5003=1. Em UTC, 5001 daria 1. Código: `game/worldboss.py`
  (`GAME_TZ`).
- O cliente guarda todo `Types>=1` menos 5 e 9, e derruba com um `campaignId` fora desse
  dicionário: o 4182 nunca leva outro id.
- O 4182 só sai como resposta ao 8271. Não há tarefa periódica no servidor, então quem já está
  logado não vê o chefe abrir até relogar. *(dedução)*
- O **4248** é o mesmo formato para o campo de batalha (4009–4013) e já sai no login
  (`warfield.login`).
- O **4381** `{campaignId, leftTime}` é o aviso de pré-carregamento antes de abrir. É opcional;
  não é mandado.

### Pedidos C>S

Handlers em `game/handlers/worldboss.py`. Recusa = 111 (aviso no meio da tela) e nada cobrado.

| Opcode | Nome | Corpo | Servidor | Fonte |
|---|---|---|---|---|
| 8271 | `C_WORLDBOSS_STATE` | vazio | 4182 com a agenda de hoje | *(visto)* captura; *(cliente)* `WorldBossManager.setup` |
| 8258 | `C_WORLD_BOSS_CMD` | `WorldBossMsg{param1=campanha}` | 111 com o motivo: id fora do template, janela fechada, nível abaixo de `MinLevel` (20), em batalha ou em campanha. Se tudo passa, 111 de "mapa não pronto". Nunca 125 | *(cliente)* `WorldBossSocketOutManager.sendWorldBossCmd` (5 s entre pedidos no cliente) |
| 8259 | `C_WORLD_BOSS_REQ` | `WorldBossMsg{mapId}` | nada (log) | *(cliente)* `reqWorldBossCmd` existe, mas nenhum arquivo o chama |
| 8264 | `C_WORLDBOSS_PLAYER_LIVE` | `PayTypeMsg{payType}` | 111, sem cobrança | *(cliente)* `WorldBossRiverMediator` → `RiverView()` tipo 1: entrar na luta com `Live_Fight_Pay`=3; payType 0 = vinculado primeiro, 1 = só diamante (como `cash.split`) |
| 8470 | `C_WORLDBOSS_BUFFER` | `WorldBossBufferMsg{op=2, type}` | 111, sem cobrança | *(cliente)* `buyWorldBossBufferWithPointOrGiftToken` → `MapSocketOuterManager`; `type` 2 = vinculado, 1 = só diamante; preço `WorldBoss_Buffer_Diamond_Price` / `WorldBoss_Buffer_Gift_Price` = 5 |

**Dependências (por que cada recusa):**
- **Mapa do chefe.** `Campaigns` 5001/5003 não têm `CampaignData` nos templates, e esses mapas
  não estão entre os 13 com nós (memória `campaign-nodes-in-maps-files`). Sem o mapa não há 125
  nem nós. Falta: aceitar o 8258.
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
- Dublê: 8526, com as respostas 4424 e 4423.

### Fim

- **4203** `WorldBossReportMsg{order, gold, strengy, totalWound}`: posição, ouro e Ruh.
- **4369**: marcos de dano acumulado.
- As recompensas são definidas pelo servidor.

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
4. **Guilda e altar.**
