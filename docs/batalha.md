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
  inimigos, herói do jogador (a iniciativa real não foi decifrada).
- A primeira ação sai no quadro 100. Do mesmo lado, uma ação começa 12 quadros depois da
  anterior. Troca de lado e rodada nova vêm 9 quadros depois do fim da animação anterior.
- O herói espera a ordem do 10008 sem prazo e golpeia 25 quadros depois dela (o guia pausa no meio
  da luta para ensinar a 30811; golpear sozinho poderia acabar a luta antes). Em modo automático
  usa a primeira skill que o SP permite.
- `frameNum = ActionTempInfo.FrameNum + 5`; `damages` agrupado por alvo, `AttackTimes` entradas
  por alvo; `sp`/`spAdded` pelo `Cost` da skill (só o herói do jogador gasta SP); `attackMillis`
  em `YYYY-MM-DD hh:mm:ss`.
- O 154 sai 90 quadros depois do último golpe.

## Alvos e dano

`SkillTempInfo.AcceptObject` 3 acerta todos os inimigos; o resto acerta um (o de menor
`livingId`). Curas e buffs de NPC (4 e 5) ficam de fora da rotação por enquanto. A fórmula de dano
do oficial é desconhecida: o golpe usa `ataque × Parameter1 / 100 + Parameter2`, com 65% para o
lado do jogador (mata os soldados do tutorial com um golpe, como na captura) e 30–40% para os
inimigos (os 6–19 de dano observados). No PvE o lado do jogador nunca cai abaixo de 1 de vida: as
batalhas do tutorial são vitórias roteirizadas, e uma derrota no chefe deixaria o guia preso.
No PvP ele morre de verdade (abaixo).

## Regras que travam o cliente em silêncio

- O herói do jogador no 157 precisa de `userId == playerId`; senão a batalha nunca começa.
- `mapTempId` tem de existir em `MapInfo`; `tempId` de heróis e soldados nos templates.
- Todo 153 com o `battleId` do 157 e `livingId` existente; cabeçalho com `extend2 = 0`.
- 154 antes do 4103.

## PvP (`spec["pvp"]`)

- O lado do jogador morre de verdade; o dano é o mesmo para os dois lados (30–40% do bruto, mais
  `damageImprove` % depois do 4361).
- Herói NPC do lado 2: antes do golpe vai um 75 com `heroIndexId` dele, skill e alvos (o cliente
  só põe o ícone da skill sobre ele; `castTime` não é usado).
- Herói do jogador em modo manual: sem ordem em 112 quadros (4,5 s) age sozinho.
- A spec aceita `attack` e `defaultSkill` nos heróis e pets (cópia de jogador, robô, pet), fora do
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
