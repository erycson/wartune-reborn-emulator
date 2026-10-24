# Boss e eventos

Visão geral e legenda em [multiplayer.md](multiplayer.md). Há captura só da agenda (4182 na
inglesa #103); da batalha do chefe não há nenhuma.

## Boss mundial *(cliente)*

### Templates (inglês, `data/templates/tempinfos.xml`)

- **`CampaignInfo` com `Types=1`:** 5001 "Bloodfang" (11:35–12:35) e 5003 "Redoga Drake" (21:00–22:00),
  `MinLevel` 20, `Capacity` 10000. O cliente trata os mapas 5000–5100 como chefe (`WorldBossHelper`).
- **Herói do chefe:** o cliente usa o **2001 "Ragnoch"** nos mapas 5001 e 5003 e o 2002 no 5002
  (`PreLoadWorldBoss.as:32-45`). Isso vira lei, contra a ligação por nome (5001 Bloodfang = 2002,
  5003 Redoga = 2003). Os três têm `HeroType=3`, `Grades=50`, `Live=2000000`, `Attack=20000`, `Captain=3`
  e `ResPath` boss016/boss004/boss020B. Os ids 2001–2003 de `PawnTempInfos` são tropas comuns.
- **Mapas:** `MapInfos` 5001 e 5003 ("World BOSS", `BattleGround` 11, 1600x1700). `checkFogMap` ignora
  a névoa nesses mapas.
- **Moral:** `CampaignBufferTemps` 701–720 "Moral Lv. N" (`Types=7`, ataque +500 a +10000). O texto do
  cliente (`WoundInfoView.buffTip`) diz que sobe a cada 500 mil do maior dano.
- **Buff comprado** (`Types=4`, 401–420, 8470): removido no Patch 5.5 (internet); fica recusado.
- **Prêmios:** os templates não têm tabela de prêmios do chefe. Estão na config do banco (ver abaixo).
- **`ConfigInfo`:** `Live_Fight_Pay=15` (reviver e voltar à luta, 8264), `Live_Pay=10` (sem botão no
  chefe), `WorldBoss_Replacement_Price=30` (dublê).

### Agenda

- O cliente manda **8271** (vazio) no login. O servidor responde com o **4182**
  `WorldBossStateMsg{worldBossInfo[]{campaignId, state}}` só com 5001 e 5003. Um id fora dos chefes
  derruba o cliente.
- `state`: 0 = aberto, 1 = ainda não abriu hoje, 2 = encerrado. *(visto)* inglesa #103: 5001=2, 5003=1.
  O 8258 só passa no cliente com `worldbossState` ligado, e só o 4182 com 0 liga.
- **O servidor empurra a mudança:** no relógio (20008, ~60 s) cada sessão recebe o 4182 de novo quando um
  estado muda (abriu, fechou ou o chefe morreu). Um chefe morto na janela de hoje aparece como 2.
- Fuso do jogo: `game_timezone`. Código: `game/worldboss.py`.
- O **4381** (pré-carregamento) não é mandado.

### Implementação (`game/boss_fight.py`, `game/handlers/worldboss.py`)

**Config no banco (migração 0031).** `world_bosses` tem uma linha por chefe com a fonte de cada valor em
`source`: herói, `sonType` do avatar, posição do nó e do jogador, vida inicial e mínima, regra de
crescimento (morto em menos de `fast_seconds`: +`grow_pct`%; não morto: −`shrink_pct`%, sem passar de
`min_hp`), `kill_turn` (6), `revive_seconds` (30), `damage_per_gold` (5), `battle_cap` (10M) e o último
golpe (1,5M de ouro). `world_boss_rewards` tem o top 10 da classe (300k/270k/240k/180k de ouro e daru) e os
degraus da fração do dano (0,3%/0,5%/0,8%: 60k/120k/180k). Os números vêm da Internet.

**Estado.** `world_boss_fights` guarda uma linha por janela (vida cheia, quem matou e quando, `settled`,
`next_hp`) e `world_boss_wounds` o dano de cada personagem. A vida atual é a vida cheia menos a soma dos
danos. Em memória fica o `Pool` da janela aberta (`ctx.bosses`). Um restart perde só as lutas em curso.

**Entrar (8258).** Valida id, janela, nível 20 e se o jogador está fora de batalha ou campanha, e se o
chefe ainda está vivo. Resposta: 125, **4369** (os 3 degraus, antes da view; o cliente só tem
`core.WorldBossReward1..3`), 21 (todos no mapa), 127, 130, 4174 e, se o jogador estiver morto, 4175. Quem
já está no mapa recebe o 21 de quem entrou.

O nó tem `nodeId` 1 e `campDataId` = campanha × 100 + 1, e copia o modelo do chefe da masmorra
(102109): `masterType` 41, `heroTempId` 2001, `resource` 1. O avatar `swf/npc/<sonType>.bswf` (2145) é
dedução.

**Atacar (5125).** Luta com `battleType` 17. O chefe é herói `type` 3, `livingId` 4, com a vida que resta
(`maxHp` = cheia). Ao lado do jogador vão as tropas e o herói.
- **Concorrência:** a vida do chefe na luta é um `SharedHp`. Antes de cada ação ela vem do pool, e o dano
  nele passa pelo pool dentro do próprio golpe (`Battle._act`, sem await). Assim, dois golpes nunca
  levam a mesma vida, e só um zera o pool: esse é o último golpe.
- A moral soma `bufferGrade × 500` a cada golpe do lado do jogador.
- O jogador não morre até o `kill_turn`-ésimo golpe do chefe, que mata o lado inteiro.
- **Fim da luta:**
  - ouro e daru = dano da luta ÷ 5 (teto de 10M), gravados junto com o dano;
  - o jogador recebe 3, 4103 (`goldBonus`/`strategyBonus`), 150 e 140;
  - o 4174 vai a todos no mapa, cada um com o seu `myWound`.

**Morte.** Quem perde fica morto 30 s. O 4175 (`state` 1, `leftTime` em ms) vai a todos no mapa, e o
jogador revive sozinho com um 4175 `state` 0. Enquanto estiver morto, o 5125 só devolve o 4175.
O **8264** revive na hora, cobrando `Live_Fight_Pay`: com payType 0 gasta primeiro o vinculado, com 1
só diamante.

**Missões.** Tipo 40 ("Participate in a World BOSS Battle": 759 ×10, 761 ×1) conta 1 no fim de cada luta no
chefe (*dedução*: luta e não entrada; com entrada, a 759 pediria 10 entradas). Tipo 66 (183 "Spend Balens to begin
the battle instantly ... 3 times") conta 1 em cada 8264 pago com sucesso. As duas mandam o 112 e gravam junto.

**Sair (5025 ou desconexão).** O 22 `CampaignExitMsg` vai a todos no mapa, inclusive a quem sai
(`exitBack`).

**Fim da janela (chefe morto ou `StopTime`).** É pago uma vez só, sob o lock do pool.
- Os prêmios do fim vão pelo **correio do jogo** e somam (guia da Koram), só com o chefe morto
  ("Defeating the World Boss earns", help do cliente): Ares Prize (top 10 da classe, `job % 3`), Warrior Prize
  (o maior degrau da fração do dano) e Lucky Prize (o último golpe). No `StopTime` com o chefe vivo, só o ouro e
  o Daru de cada golpe.
- Na mesma transação gravam-se `settled`, `next_hp` e o dano de todos.
- Quem está no mapa recebe o **4203** (posição, ouro, daru e dano total) e o 22. Quem está em luta recebe
  os dois no fim dela.
- O relógio (20008, uma vez por minuto no servidor) paga as janelas que passaram do `StopTime`,
  inclusive as que ficaram no banco sem pagamento depois de um restart.

**Fora do escopo:** o buff comprado (8470, removido no 5.5) e o dublê (8526) continuam recusados, e o
4435 (barra de HP na luta) não é mandado. A vida do chefe não acompanha o nível dos jogadores: cresce ou
cai conforme a última janela.

## Regras pela Internet (pesquisa de 2026-10-18)

Tudo aqui é *(internet)*; o help do cliente (`worldboss.view.BaseHelpFrame.helpText`) confirma ouro e Daru por
golpe, "HP e tropas não se esgotam", e, só para o chefe derrotado, o Lucky Prize (último golpe), o Ares Prize (top 10 de dano
por classe) e o Warrior Prize (0,3%/0,5%/0,8% do dano total). Wiki: https://wartune.fandom.com/wiki/World_BOSS (lida pela `api.php`, revisões
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
  conta.
- **Último golpe**: 1 000 000 de ouro (`?oldid=5206`) → 1,2-1,3M → 1,7M (`?oldid=12788`); "varies based on
  World Boss' total health (e.g. 1.5 million or 1.7 million gold)" (wiki atual); título Mortal Blow (HP +340).
- **Top 10 por classe**: 360k/300k/240k/180k (do 4º ao 10º) em nov/2013 (`?oldid=18253`), depois
  300k/270k/240k/180k, de ouro e daru. Antes: top 3 com 200k+200k (`?oldid=5206`).
- **Por % do dano**: 0,3%/0,5%/0,8% → 60k/180k/360k (`?oldid=18143`) ou 60k/120k/180k (`?oldid=19424`);
  servidores antigos: 1% → 360k. Removido no Patch 5.5.
- **Prêmios somam?** Conflito: "you only receive one prize, whichever is best" (`?oldid=13462`) contra "Players
  can acquire Beating Reward as well as other rewards" (Koram). Prêmios vão por correio (Koram).
- **Fim**: a masmorra fecha quando o tempo acaba ou o chefe morre, e todos voltam para a cidade. Sem chefe morto,
  não há prêmio do fim (help do cliente). Participantes: "like 300-500 people" (Doly world-boss-last-hits).

## Captura que falta

Cada item diz o que gravar no `captures/` (ou no relay) e o que fazer no jogo. Todos com um
personagem de nível 20 ou mais, sem batalha e sem campanha abertas, no horário da janela
(fuso do jogo). Os pacotes esperados estão entre parênteses.

1. **Estado aberto da agenda.** Entrar entre 11:35 e 12:35 (ou 21:00–22:00) e logar. Gravar o 4182
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
7. **Fim.** Deixar a janela fechar (depois de 12:35) com a sessão aberta. Gravar 4203
   (`order`, `gold`, `strengy`, `totalWound`) e 4369 (marcos de dano e estado de cada um).
8. **Ranking com dois jogadores.** Dois personagens no mesmo chefe, cada um com dano. Gravar os dois
   4174 para confirmar a ordem do `woundInfo` e o `myWound` de cada um.

O servidor já faz tudo isso (ver *Implementação*), com o que falta das capturas tirado do cliente e da
Internet; as capturas confirmariam o nó, a ordem dos pacotes e os números.

## Boss de guilda

A guilda está pronta ([guilda.md](guilda.md)); o altar abre (8541 -> 4436 para os membros, estado
no 164/4138), mas a entrada (8542) é recusada: falta o mapa de campanha 7601 com as ondas.

- **7601 "Celestial Altar"** (`MapName` "Divine Altar") é a defesa do altar:
  - abertura: o servidor manda o 4436;
  - entrada: o cliente manda o 8542;
  - relatório: o servidor manda o 4437 (durabilidade, ondas, `hurtOrder`).
- **7501 "Guild Chamber"**: 8537 (`handlers/fam.py`, ver [guilda.md](guilda.md)).

Quem abre é quem tem o direito 3 (só o chefe), com a guilda no nível 5, pagando 50000 ou 200000
de riqueza (`Consortia_OpenAltar1_Offer`/`2`); m6 `ConsortiaSocektSendManager.sendOpenDemon`.

## Atividades, assinatura, login acumulado, leed, VIP, recompensas e minigames

Implementados: regras, opcodes e dependências em [eventos.md](eventos.md).

## Prioridade

1. **Login sem quebrar os painéis:**
   - 4182 com 5001/5003, com estados coerentes com a hora;
   - 4248;
   - 4475 em páginas (as 41 do oficial e as do operador: [eventos.md](eventos.md));
   - 4476 ao receber o 8586 tipo 1.
2. Resgate de atividades (13 e 14), assinatura e login acumulado: feito ([eventos.md](eventos.md)).
3. **Boss mundial:** agenda (8271 -> 4182) e recusas (8258, 8264, 8470) prontos. Falta o mapa
   do chefe (ver as dependências acima): entrada, HP global (4174), morte (4175) e relatório (4203).
   As capturas que faltam estão em *Captura que falta*.
4. **Guilda e altar.**
