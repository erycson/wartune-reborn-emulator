# Batalha

O servidor simula tudo; o cliente só toca as ações que recebe e espera o fim. Implementação em
`game/battle.py` (uma `asyncio.Task` por batalha, cancelada se o jogador cair).

## Pacotes

| sentido | código | mensagem | quando |
|---|---|---|---|
| S→C | 157 | `BattlePrepareMsg` | monta a batalha: soldados, heróis, cooldowns |
| C→S | 10010 | `BattleReqMsg` | guia pausa (pode vir antes do 10007) → 69 `{type:1, order:0}` |
| C→S | 10007 | `LoadOverMsg` | cliente carregou |
| S→C | 156 | `BattleStartMsg {frame:0, mainType, countDown:60000}` | depois do 10007, sem pausa ativa |
| C→S | 10022 | `BattleReqMsg` | guia retoma |
| C→S | 10008 | `UseSkillMsg {heroId = livingId, skillId}` | jogador escolhe a skill → 75 `HeroOrderMsg` (result 0/1 e alvos) |
| C→S | 10020 | `AttackModeMsg {mode}` | 1 automático, 2 manual; sem resposta |
| S→C | 153 | `AttackOrderMsg` | uma ação, no quadro em que acontece |
| S→C | 154 | `PrepareOverMsg` | fim: animação de vitória (`calcType 3`) dos sobreviventes vencedores |
| S→C | 4103 | `BattleReportMsg` | resultado, EXP, `battleScene` (3 campanha, 1 cidade) |

Na campanha, depois do 154 vêm 3, 4103, 83 (EXP), 150, 100, 140, 131 e 128 (nó derrotado, com
`uuId` novo e `sonType`), e os nós liberados pela vitória.

## Relógio e turnos

- Quadros de 40 ms (25 fps), começando em 0 no 156, calculados pelo relógio (`time.monotonic`),
  não pela soma dos `sleep` (no Windows o `sleep` anda de 15,6 ms). A pausa congela o relógio;
  pausa antes do 156 não conta.
- `153.frame = execFrame = quadro atual`. Mandar adiantado faz o cliente saltar o relógio.
- Rodadas: cada unidade viva age uma vez (`curturn` conta por unidade). Ordem: aliados NPC,
  inimigos, herói do jogador (a iniciativa real não foi decifrada, ver Dano).
- A primeira ação sai no quadro 100. Do mesmo lado, uma ação começa 12 quadros depois da
  anterior. Troca de lado e rodada nova vêm 9 quadros depois do fim da animação anterior.
- O herói usa a ordem do 10008 que chegou até a vez dele e golpeia 25 quadros depois dela. Sem ordem
  na vez dele, dá o golpe básico (`defaultSkill`, 30000 na maga) **(visto)** tutorial_en #152, #271,
  #274 sem 10008, e #1657 a #1704 sempre 30000 com fúria sobrando; a ordem recusada também vira golpe
  básico (#279 → #281). O guia que ensina a 30811 pausa a luta (10010), e a pausa congela o relógio.
  Em modo automático usa a primeira skill que o SP permite.
- `frameNum = ActionTempInfo.FrameNum + 5`; `damages` agrupado por alvo, `AttackTimes` entradas
  por alvo; `sp`/`spAdded` pelo `Cost` da skill (só o herói do jogador gasta SP); `attackMillis`
  em `YYYY-MM-DD hh:mm:ss`.
- O 154 sai 90 quadros depois do último golpe.

## Alvos

`SkillTempInfo.AcceptObject` 3 acerta todos os inimigos, 4 o próprio; o resto acerta um (o de menor
`livingId`). Cura (`Parameter1` 0 e `Parameter2` < 0) vai no aliado com menos vida proporcional
(**dedução**). Confuso (buffer 38) acerta qualquer um vivo, até aliado (**dedução**). Só com
`spec["undying"]` o lado do jogador nunca cai abaixo de 1 de vida: nas lutas roteirizadas do tutorial (as de
`content/tutorial.json`) **(visto)** tutorial_en #144-#540, nenhuma unidade dele a 0, e uma derrota no chefe do
guia o deixaria preso; e no chefe do mundo até o golpe `killTurn` (`handlers/worldboss.battle_spec`). Nessas
duas as tropas também não morrem. Nas outras ele morre e pode perder **(visto)** #1466 (o herói na masmorra 1021),
#1657 (os três no castelo-robô, mapa 993) e #1930.

Tropas mortas: no fim da luta ficam `ceil(vida que sobrou nas pilhas × 100 / Live)` tropas; as outras saem e a
reserva do castelo completa o exército **(visto)** #1466 -> #1511 (162 Lancers, Live 323, 238 de vida: 88 mortos,
reserva 738 -> 650, exército 162 de novo) e #1657 -> #1764 (as 172, 150 com 0 no #1760, reserva 640 -> 468). Na
cidade externa vai o 150 sem as mortas, o 4103 e o 150 e o 100 já repostos. A pedreira não perde tropa **(visto)**
#1930 -> #2065 (morreram os três, reserva 468 igual), nem a luta roteirizada; arena e chefe do mundo também não
(sem captura de perda: ficam como estavam).

## Dano

`damage()` em `game/battle.py`; coeficientes em `game_settings.battle_formula` (migração 0039,
[configuracao.md](configuracao.md#fórmula-de-dano)).

- Golpe = `max((A - D) × 0,5, A × 0,1) × Parameter1/100 + Parameter2`, ±8%, dividido pelos
  `AttackTimes`. **(visto)** tutorial_en, os 153 contra os atributos do 150 e dos templates: maga
  nível 1 (MAtk 20) com Lightning Bolt (102% + 15) dá 25; Lancer (64) contra Def 66 dá 5–6 (o piso
  de 10%); 10102 (84) com a skill 11 (150%) contra PDef 44 dá 28–30. Testes em `test_batalha.py`.
- `CountWay` 2 usa `MagicAttack`/`MagicDefence`; 1 e 3, os físicos (**visto**: as skills da maga).
- Crítico: `extraData & 1` (cliente `DannyAction`), ×1,5 (**dedução**, poucos golpes). Bloqueio:
  `parry`, ×0,75 (**dedução**). Chance `1 - 0,9995^ForceHit` e `1 - 0,9995^Parry`
  **(internet)** https://breezewiki.discard.no/wartune/wiki/Statistics.
- O dano da tropa não cresce com o tamanho da pilha (**visto**: o mesmo golpe com pilhas diferentes).
- Atributos: herói do jogador = `HeroStats.total` (o mesmo do 150); NPC = colunas do template
  (`Attack`, `Defence`, ...), depois `stats` da spec, depois `attack` da spec (os dois ataques).
- Iniciativa: **sem dado**. #727 e #782 têm as mesmas unidades e ordens diferentes; a ordem fica:
  aliados NPC, inimigos, herói do jogador.

## Tropa, passivas, runas e destino

- A tropa do jogador (`outer_city.army_soldiers`, de `rules.battle_pawn`) troca as pilhas de tropa
  do lado 1 da spec, só onde a spec já tem pilhas (**dedução**: nas lutas roteirizadas sem tropa os
  `livingId` são outros). Vida da pilha = `Live × quantidade / 100`, dividida com o arredondamento
  para cima na primeira (**visto** 523 → 262/261).
- Skills passivas (`UseWay` 2) viram `HeroMsg.buffers` no 157 (**visto** #1466: 30111, `curTurn` -1)
  e não entram nos cooldowns nem na rotação. Talento: passivas do `talent_script` (`MasterType` 10);
  destino: a linha de `SkillTempInfos` com `SonType` = tipo e `Grades` = grau (**dedução**).
- Runas: `RuneTempInfos.SkillTemplateId` é uma skill ativa, entra no `skillId` e só se usa uma vez
  por batalha (**dedução**).
- Dragão e cartas: **precisa de captura** (o buffer das cartas, 3040/3041, não está nos templates; o
  dragão não tem tabela de skill).

## Buffers e controle

`SkillTempInfo.BufferIds` (com a chance do texto, "50% chance"; sem texto, sempre: **dedução**) aplica
linhas de `SkillBufferTempInfos`. `BufferMsg` no 153 de quem age e dos alvos.

- Ciclo **(visto)** #1484–#1493 (60023, Chomp): entra com `curTurn = ValidCount`, `seeType` 0; cada
  ação de quem carrega desconta 1 e o efeito age (sangra antes do golpe, `seeType` 1); em 0 sai com
  `seeType` 2. Passiva permanente começa em -1 e desce (-2, -3...).
- `AttackWay` (cliente `BufferEffectiveType`): 1 ao agir, 2 ao levar dano, 3 ao causar, 4 na hora.
- 30111 (Fúria): +1 de SP por golpe dado, entrada `damageType` 9 com o total em `leftValue`
  (**visto** #3136).
- `AttackType` lidos: 1/3 ataque, 2/4 defesa, 5/33 vida, 6 fúria, 15 dano recebido, 16/17 crítico,
  20/40 dano causado, 28/29 ignora defesa. Controle: 19 atordoado e 101 desmaio não agem (cliente
  trata 19 como "restrito"); 38 confuso; 39 amnésia (só o golpe básico). `RejectType` do
  `GameHeroTemp` = tipos a que o herói é imune.
- Atordoado perde a vez sem 153 e o turno do controle conta (**dedução**; **precisa de captura**).
- Selo sagrado (100): **sem dado**, ignorado.

## Captura que falta

- Uma luta com atordoamento num inimigo (skill com "Stunned", ex. buffer 41): ver se a vez perdida
  manda 153 e como desce o `curTurn`.
- Batalha com cartas de poder equipadas e com dragão: 157 (buffers do herói) e 4902.
- Golpes críticos e bloqueados em quantidade (multiplicadores e chances); um guerreiro ou caçador no
  150 (o ×1,05 do `MagicAttack` no poder de combate só foi visto na maga).
- Skills com chance de buffer (quantas vezes entra); Selo sagrado; pets numa luta normal.
## Regras que travam o cliente em silêncio

- O herói do jogador no 157 precisa de `userId == playerId`; senão a batalha nunca começa.
- `mapTempId` tem de existir em `MapInfo`; `tempId` de heróis e soldados nos templates.
- Todo 153 com o `battleId` do 157 e `livingId` existente; cabeçalho com `extend2 = 0`.
- 154 antes do 4103.

## PvP (`spec["pvp"]`)

- O lado do jogador morre de verdade; o dano é a mesma fórmula, mais `damageImprove` % depois do 4361.
- Herói NPC do lado 2: antes do golpe vai um 75 com `heroIndexId` dele, skill e alvos (o cliente
  só põe o ícone da skill sobre ele; `castTime` não é usado).
- Herói do jogador em modo manual: espera a ordem até 112 quadros (4,5 s) e então dá o golpe básico
  (#1667, quadro 111).
- A spec aceita `stats`, `attack` e `defaultSkill` nos heróis e pets (cópia de jogador, robô, pet), fora do
  protobuf (`ParseDict(ignore_unknown_fields=True)`).
- Batalha só de pets (battleType 35): `pets` no 157, sem herói do jogador; o cliente manda o 10007
  e não deixa dar ordens. Sem um pet com `userId` do jogador no lado dele a batalha não
  inicializa. `notice`/`damageImprove` na spec: no quadro `notice` vai o 4361
  `{countDown 60000, damageImprove}` (no cliente o aumento é cumulativo; vai um só).
- `finish()`: resolve o resto sem esperar nem mandar 153 (8727).
- A cena para onde o cliente volta depende do `battleType` (16 e 35 voltam à cena anterior e
  reabrem o coliseu/torneio); `battleScene` (7 coliseu, 19 torneio) só decide a dica de pós-luta.
- 154: `calcType 3` para os vencedores vivos; o cliente faz a animação dos outros do mesmo lado.

## Outros pacotes de batalha (`handlers/battle.py`)

| C>S | Resposta |
|---|---|
| 10018 `LoadOverMsg` | igual ao 10007 (quem entra como reforço, `useWay != 0`) |
| 10016 `AttackModeMsg` | 77 com a postura (2 ataque, 1 defesa); sem efeito no dano |
| 10499, 10507, 10509 `BattleItemMsg` | 158 `result 1`: não há itens, provas nem skill de casal; o cliente libera a barra |
| 8985 `BattleViewMsg` | 4804 `param7 true` (a batalha acabou): não há batalhas para assistir |
| 10015, 10497, 10516, 8282, 10003 | nada (log): o cliente não espera resposta. QTE (bônus não modelado); 10497 e 10003 são código morto no cliente; 10516 é skill do filho; 8282 é estatística de combo (o 8283, tirar buff de pergaminho, está em itens.md) |
