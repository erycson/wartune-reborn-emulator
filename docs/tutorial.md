# Tutorial (campanha de treino)

Personagem novo com `noviceProcess < 19000` (o padrão; `WARTUNE_SKIP_TUTORIAL=true` pula) começa na campanha de
treino: dois mapas, 10001 e 10002 ("Ryan Yolu"), com cinco batalhas, um baú com a arma da
classe, a Dinah como escolta e, no fim, a batalha do chefe na cidade externa para retomar o
castelo. Tudo foi reproduzido da captura oficial (`server-relay/replay_packets.json`, pacotes
116 a 580).

## De onde vem o conteúdo

O `tempinfos.xml` não tem os nós, as tropas inimigas nem as falas do tutorial: o servidor oficial
os tinha no banco dele. O `tools/extract_tutorial.py` tira isso da captura, sem nada do jogador
(ids, nome, herói), e grava `src/wartune_server/content/tutorial.json`:

| chave | conteúdo |
|---|---|
| `maps` | por mapa, o ponto de partida e os `CampaignNodeMsg` do 127 |
| `battles` | por `campDataId` (e `8251` para o chefe): tipo, mapa, soldados, heróis NPC, posição do herói do jogador, EXP |
| `plots` | os diálogos 138 na ordem em que aparecem, com o apelido do jogador trocado por `{nick}` |

Cada nó tem dois ids. O de execução (`nodeId`, 9544…) vai nos pacotes 127, 128, 4105, 4122 e
4124. O do template (`campDataId`, 1000101…) é o que o cliente manda em 5125, 8196 e 5032.

## Fluxo

| cliente | servidor | onde |
|---|---|---|
| 5127 `{type:1}` | 125 `{createdType:1}`, 140, 21, 127, 130, (4124 no mapa 10002), 143 `MOVIE_MAP_NAME` | `campaign_training` |
| 5124 rota (px) | nada; guarda a posição (px / 20) | `sync_pos` |
| 8196 num monstro agressivo | 4105 `NPCChaseMsg` | `node_lock` |
| 5125 num nó | depende do nó (tabela abaixo) | `arrive` |
| 5032 (fim de diálogo) | depende de quantos 5032 aquele nó já recebeu | `callback` |
| 5017 `noviceProcess` | (112 se uma missão cumpriu a condição), 3, 1; no 14000 o portal aparece | `novice` |
| 5012 / 5014 | aceitar / entregar missão (ver Missões) | `handlers/player.py` |
| 5005 | equipar ou trocar item: 3, 150, 115 (origem), 115 (destino) | `bag_move` |
| 5006 num pacote (SonType 298) | 115 (posição vazia), 150, (109), 115 com os itens novos, 111/83 "Kazanılan:…", 3. Troca o pacote pelo `GradeDrop` `DropId=Property1` numa transação; moedas negativas: -100 ouro, -300 Ruh (`strategy`), -400 elmas (`point`), -500 bağlı elmas (`gift_token`). Recusa se faltar nível (`NeedGrades`), espaço (42) ou se o drop tiver algo desconhecido | `use_item` |
| 5035 `{state:4}` | 4382 com a EXP da última batalha | `client_state` |
| 5015 / 20008 / 5167 | 109 / 4234 / 64 | `handlers/player.py` |

Roteiro dos nós (constantes no topo de `game/handlers/campaign.py`):

| nó | evento |
|---|---|
| 1000103, 1000104 (Huntera) | chegada: batalha |
| 1000110 (gatilho) | chegada: diálogo 0. 1º 5032: câmera na Tina, o urso pisca, diálogo 1. 2º 5032: o jogador anda até `param4` e o gatilho some |
| 1000106 (urso) | chegada: diálogo 2. 5032 com o urso de pé: batalha; vitória: 1000109 aparece. 5032 com o urso derrotado (no 15300): a Tina passa a seguir |
| 1000108 (portal) | aparece no `noviceProcess` 14000. Chegada: 4208 e mapa 10002 (`createdType:3`) |
| 1000202 (baú) | chegada: arma da classe (`param3`, índice `job-1`) com o atributo sorteado `DefaultSkill`, 115, 111, 128, 150 |
| 1000203 (urso) | chegada: batalha tipo 18 com a Tina |
| 1000208 (gatilho) | chegada: o jogador anda até `param4` com a câmera |
| 1000205 (Brutal Bloodhoof) | chegada: diálogo 3. 5032: batalha. Vitória: saída 1000206 e 1000207 aparecem |
| 1000206 (saída) | chegada: 4165, 150, 140, 134. O cliente vai para a cidade externa |

Cidade externa (`handlers/outer_city.py`): 9525 → 4938; 8201 → 4129 (o próprio castelo) e 169;
8251 → batalha do chefe (tipo 15, mapa 1); 8747 → 4382; 8281 → 109, 109, 100, 4130, 104.

## Retomada

O cliente só grava o `noviceProcess` em pontos de retomada (`newbie.xml`, nós `a24`). Ao reentrar,
o 5127 escolhe o mapa (10002 a partir de 15500) e `CampaignMap.enter` recoloca os nós como
estavam naquele ponto (`RESUME` em `game/campaign.py`); o guia do cliente continua dali. Por
isso as reações ao 5032 dependem do estado do nó, não de quantos 5032 vieram (a contagem recomeça
ao relogar), e o baú não dá a arma de novo se ela já está na mochila.

| `noviceProcess` | mapa | já mudou |
|---|---|---|
| ≥ 11400 | 10001 | 1000103 derrotado |
| ≥ 12000 | 10001 | 1000104 derrotado |
| ≥ 13500 | 10001 | gatilho 1000110 usado, 1000106 derrotado, 1000109 visível |
| ≥ 14000 | 10001 | portal 1000108 visível |
| ≥ 15300 | 10001 e 10002 | a Tina segue o jogador (4124 ao entrar) |
| ≥ 16700 | 10002 | baú 1000202 aberto |
| ≥ 17500 | 10002 | 1000203 derrotado |
| ≥ 18500 | 10002 | gatilho 1000208 usado, 1000205 derrotado, 1000206/1000207 visíveis |

## Missões

Quem aceita as missões é o cliente (5012), sozinho, depois do 112 do login: ele checa
`NeedMinLevel` contra o nível do herói, que vem do `SimpleHeroInfoMsg.grade` no 150. Esse campo
precisa ir com o nível real: com `grade: 0` (o `complete()` preenchia) nenhuma missão fica
disponível e o guia do `newbie.xml` trava no 12000 (o passo 12005 espera a missão 10).

Tabela `quests`. As do tutorial têm condição tipo 23 (`QuestConditionInfo`): cumprida quando o
`noviceProcess` passa de `Para1` (10: 11600, 30: 13000, 40: 17000, 45: 18000, 50: 19000). O 5017
só avança: múltiplo de 100, para a frente, salto de até 3500 (o maior do newbie.xml; de 0, até 11000 no primeiro passo;
`rules.novice_step_ok`). O 5014 entrega a recompensa do `QuestTempInfo` (EXP, ouro, ruh, cristal e
ofertas), os itens da classe e consome os itens das condições de bolsa. Manda 112, 3,
112, (109), 83, 150, 3, (115, 111, 83 por item), 52. Se a condição ainda não bate, responde só o 112
com o progresso. As concluídas formam o bitmap
`questSite`/`states`: bit `id-1`, byte `(id-1)/8`, bit menos significativo primeiro.

## Nível e atributos

EXP do jogador pela tabela `UpGradeTempInfo Types=3` (`Data` = EXP do nível anterior até este,
acumulada: 3000, 7000, 12000…); o líder sobe junto. O mago ganha por nível inteligência +3,
agilidade +1, liderança +10, físico +1 (`GROWTH` em `game/rules.py`; guerreiro e caçador são um
palpite espelhado). Os derivados (`HeroStats.of`) batem com a captura nos níveis 1, 3 e 5, com e
sem arma:

| atributo | fórmula |
|---|---|
| ataque físico | 4 × força |
| defesa física | físico + 3 × (nível − 1) |
| ataque mágico | 4 × inteligência (+ `MagicAttack` dos itens no total) |
| defesa mágica | inteligência + físico + 3 × (nível − 1) − 1 |
| vida | `Live` do template + 20 × físico + 10 × nível |
| liderança do exército | liderança |

Os atributos dos itens equipados e o atributo sorteado (`SkillPropertyTempInfo`, ex.: 70302
"Zeka+2") entram nos atributos antes das fórmulas; os bônus fixos (`Attack`, `MagicAttack`…) só
no total. O poder de combate ainda é aproximado (bate no nível 1).

## Testes

- `tests/game/test_tutorial.py`: cliente falso nos trechos principais (primeira batalha, missão
  com subida de nível, portal, baú e equipar, mapa 10002 até o castelo, retomada).
- `tests/game/test_tutorial_oracle.py`: reenvia ao servidor todos os pacotes do cliente da
  captura (116 a 580) e compara quantas respostas de cada opcode saem. Fora: golpes da batalha,
  sistemas que não existem aqui (atividades, títulos, moda, patrulha dos monstros) e duas
  respostas deixadas de lado de propósito.

## Para testar no cliente

```
uv run wartune-server character novice <id> 0
```

e reinicie o servidor. Com `noviceProcess` 0 o cliente faz o começo do guia e o 5127 abre o mapa
10001.
