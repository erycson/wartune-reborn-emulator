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

## Atividades ("Sıcak Etkinlik", SumActive)

Cliente: `m2/scripts/managers/FunnyManager.as`. *(visto)* `login.json` #63–69 e
`online_odul_sicak_etkinlik_giris_odulu_toplama_takas_ve_binek_upgrade.json` #38–89.

### Descoberta no login

1. O servidor manda **4475** `SumActivesMsg{actives[], dataStamp, curPage, maxPage}` em páginas.
   No oficial foram 5 páginas com 53 atividades e `dataStamp 264`.
   - **Atividade:** `activeId` (GUID), datas, título e texto, `activeType`, `startTime`/`stopTime`.
   - **Pacotes:** `packages[]{packageId (GUID), items[], conditions[]{conditionId,
     conditionValue}}`.
2. Com todas as páginas recebidas, o cliente manda **8586** `{type:1}`.
3. O servidor responde com o **4476** `SumActiveDataMsg`, o progresso do jogador:
   `datas[]{activeId, packdata[]{packId, status, countDown, getCount}}`.
   - `status`: 1 = pode resgatar, 2 = já resgatado, 3 = ainda não.

### Regras do cliente

- Atividade com `stopTime` no passado é descartada.
- O cache só é trocado quando `dataStamp` aumenta: subir o número sempre que as definições
  mudarem.
- Itens negativos são moedas, como no GradeDrop: -100 ouro, -300 Ruh.

### Resgate

O cliente manda **8586** `{type:2, activeId, packageId, count}`. A resposta do oficial é:

1. 111 "Hediye Paketi başarıyla alındı"
2. 4476 só com a atividade que mudou
3. 83 "Kazanılan:…"
4. 4476 completo
5. 3, 109 e 115

### Tipos de atividade

| activeType | atividade |
|---|---|
| 1 | gasto diário |
| 10 | troca |
| 13 | **login** |
| 14 | **presente online** (`conditionValue` = segundos de jogo; `countDown` = o que falta) |
| 15 | primeira recarga |
| 18 | montaria |
| 27 | anfiteatro |
| 28 | campo de batalha |
| 35 | fadas |

### Quem define o quê

Toda a definição (GUIDs, datas, itens, condições) é do **operador**: nada disso está no tempinfos.
No nosso servidor vira um JSON de configuração, e o progresso de cada jogador vai para o banco.

## Assinatura, login acumulado, caixa por tempo *(cliente)*

- **Assinatura:**
  - o cliente manda **8266** sem corpo;
  - o servidor responde **4177** `PlayerSignRspMsg{signDate, signTimes, signSite}`;
  - template `SignDropInfo` (Times 2/5/10/17/26);
  - o estado inicial vai no `PlayerMsg`.
- **Login acumulado:**
  - o cliente manda **8496** `TakeLoginReward{index}`;
  - o estado fica em `PlayerMsg.reloginProcess` (bitmask) e `reloginCount`;
  - template `ReloginDrop`;
  - a resposta provável é o `PlayerMsg` (3).
- **Caixa por tempo:**
  - o servidor manda **4** `BoxBoxMsg`;
  - o cliente manda **5019** `{operate, time}`;
  - template `TimeDropInfo`.
- **Atividade diária ("leed"):**
  - o servidor manda 4152 e 4150;
  - o cliente manda 8235 para resgatar;
  - templates `LeedTempInfo` e `LeedDropInfo`.

## Prioridade

1. **Login sem quebrar os painéis:**
   - 4182 com 5001/5003, com estados coerentes com a hora;
   - 4248;
   - 4475 com `maxPage=1`;
   - 4476 ao receber o 8586 tipo 1.
2. **Resgate de atividades** dos tipos 13 e 14, com as definições em JSON.
3. **Assinatura e login acumulado.**
4. **Boss mundial:**
   - agenda em asyncio com broadcast do 4182;
   - HP global por campanha;
   - 4174, 4175 e 4203.
5. **Guilda e altar.**
