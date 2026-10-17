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
inimigos (os 6–19 de dano observados). O lado do jogador nunca cai abaixo de 1 de vida: todas as
batalhas daqui são do tutorial, que na captura são vitórias roteirizadas, e uma derrota no chefe
deixaria o guia preso.

## Regras que travam o cliente em silêncio

- O herói do jogador no 157 precisa de `userId == playerId`; senão a batalha nunca começa.
- `mapTempId` tem de existir em `MapInfo`; `tempId` de heróis e soldados nos templates.
- Todo 153 com o `battleId` do 157 e `livingId` existente; cabeçalho com `extend2 = 0`.
- 154 antes do 4103.
