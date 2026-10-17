# Boss e eventos

Visão geral e legenda em [multiplayer.md](multiplayer.md). Não há captura de boss mundial.

## Boss mundial *(cliente)*

### Templates

- **`CampaignInfo` com `Types=1`:**
  - 5001 "Kızıl Gözlü Kurt": nível 20, 11:00–12:00.
  - 5003 "Ejderha Kemiği": 21:35–22:35.
  - O cliente trata os mapas 5000–5100 como boss.
- **Heróis do boss:** `GameHeroTempInfo` 2002/2003, `HeroType=3`. O HP total é definido pelo
  servidor.
- **Moral:** `CampaignBufferTempInfo` 701–710 "Moral Lv.N".
- **Preços em `ConfigInfo`:**
  - `WorldBoss_Buffer_*_Price=5`
  - `WorldBoss_Replacement_Price=30` (dublê)
  - `Live_Pay=2` (reviver)
  - `Live_Fight_Pay=3`

### Agenda

**Quem decide é o servidor.** O horário do template só aparece no texto "fechado".

- O cliente manda **8271**. O servidor responde com o **4182**
  `WorldBossStateMsg{worldBossInfo[]{campaignId, state}}`.
- Significado de `state`: 0 = aberto, 1 = ainda não abriu hoje, 2 = encerrado. *(visto)*
  `login.json #120`: 5001=2, 5003=1.
- O **4248** é o mesmo formato para o campo de batalha (4009–4013).
- **Nunca mandar `campaignId` fora do template:** o cliente quebra.
- O **4381** `{campaignId, leftTime}` é o aviso de pré-carregamento antes de abrir. É opcional.

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
- Reviver pagando: o cliente manda **8264** `PayTypeMsg`.

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
3. **Boss mundial:**
   - agenda em asyncio com broadcast do 4182;
   - HP global por campanha;
   - 4174, 4175 e 4203.
4. **Guilda e altar.**
