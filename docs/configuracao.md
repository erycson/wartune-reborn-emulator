# Configuração, logs e CLI

As opções vêm de variáveis de ambiente com prefixo `WARTUNE_` ou do arquivo `.env` na raiz.
Implementação: `src/wartune_server/config.py`.

| Variável | Padrão | Para quê |
|---|---|---|
| `WARTUNE_DATABASE_URL` | `sqlite+aiosqlite:///data/wartune.db` | veja [banco-de-dados.md](banco-de-dados.md) |
| `WARTUNE_SERVER_ID` | `1` | qual linha de `game_servers` este processo atende |
| `WARTUNE_SERVER_NAME` | `S1 - Local` | vai para o `PlayerMsg.serverName` |
| `WARTUNE_SITE` | `local_0001` | flashvar `site` e `<NODE site>` do config.xml (publicado em `game_servers`) |
| `WARTUNE_BIND_HOST` | `0.0.0.0` | |
| `WARTUNE_PUBLIC_HOST` | `127.0.0.1` | host que o cliente usa; o portal põe no config.xml (via `game_servers`) |
| `WARTUNE_HTTP_PORT` | `8080` | |
| `WARTUNE_SOCKET_PORT` | `5000` | |
| `WARTUNE_WEBSOCKET_PORT` | `5001` | ponte para o Ruffle |
| `WARTUNE_GAME_TIMEZONE` | `UTC` | fuso do jogo (vai para `game_servers.timezone` e aparece na lista de servidores do portal): horários do chefe do mundo, relógio dos chefes do mapa, `createDate` das minas e a virada do dia do jogo às 5h (`domain/gameday.py`), que zera todos os contadores diários. Nome IANA (com horário de verão, base do pacote `tzdata`) ou fixo (`+03:00`). Padrão UTC; troque no `.env` (modelo em `.env.example`). O oficial inglês segue o Pacífico (internet) https://wartunereborn.wan.com/article/read?aid=8721.html. Os testes rodam em UTC |
| `WARTUNE_POLICY_PORT` | `843` | vazio desliga |
| `WARTUNE_TEMPLATES_FILE` | `data/templates/tempinfos.xml` | cópia local dos templates (inglês, zlib) |
| `WARTUNE_TEMPLATES_URL` | vazio | ex.: `https://cdn.exemplo.com/xml/tempinfos.xml`, usada pelo `templates update` |
| `WARTUNE_RSA_KEY_FILE` | `data/rsa_private.pem` | criado na primeira execução |
| `WARTUNE_SKIP_TUTORIAL` | `false` | faz o tutorial ([tutorial.md](tutorial.md)); `true` mantém o `noviceProcess` em no mínimo 19000 (cena do castelo) |
| `WARTUNE_GM_SECRET` | vazio | segredo do painel GM do portal (`gm_secret` no `config.php`). Liga o `POST /gm/kick` (cabeçalho `X-GM-Secret`, campo `character_id`), que derruba o jogador e só responde depois que a sessão terminou, para o portal editar o banco sem o servidor desfazer. Também liga o `POST /gm/ban` ([administracao.md](administracao.md)). Vazio: as rotas não existem |
| `WARTUNE_SOCKET_SESSION_TTL_SECONDS` | `1800` | sessão do login HTTP sem uso por esse tempo expira (renovada a cada uso: registro, novice, 20001) |
| `WARTUNE_IDLE_TIMEOUT_SECONDS` | `300` | desconecta um socket ocioso |
| `WARTUNE_RANKING_XML_DIR` | vazio | pasta `xml/` do site do jogo (o `TEMPLATE_PATH` do `config.xml`, ex.: `D:/xampp/htdocs/wartune-reborn/game/xml`). Com ela, o servidor grava o `challengeorder.xml` (ranking "Hero Rankings" do coliseu) e o `fight.xml` (ranking de poder), `game/rankings.py`, ao subir e a cada `WARTUNE_RANKING_SECONDS`. Vazio: o site serve o arquivo do espelho (jogadores do oficial). Com vários servidores no mesmo site, só um deve gravar |
| `WARTUNE_RANKING_SECONDS` | `3600` | intervalo da gravação do ranking |
| `WARTUNE_LOG_DIR` | `logs` | |
| `WARTUNE_LOG_LEVEL` | `INFO` | |
| `WARTUNE_LOG_PACKETS` | `true` | grava `logs/packets.log` |

Para vários servidores, rode um processo por servidor, com `SERVER_ID`, `SITE`, `SERVER_NAME`
e portas diferentes e o mesmo `DATABASE_URL`. Cada um se publica em `game_servers` e aparece
sozinho na lista do portal.

O portal tem a própria configuração em `D:\xampp\htdocs\wartune-reborn\portal\config.php`
(DSN do mesmo banco, URL do portal, URL do CDN e validade do ticket).

## Regras no banco

O servidor lê estas tabelas uma vez, ao subir (`persistence/world_store.py`): **edite o banco e reinicie**.

### Anúncios agendados

`scheduled_announcements` (migração 0035; regras em [eventos.md](eventos.md#anúncios-agendados-gameannouncementspy)):
uma linha por mensagem. `times` = horários do dia na hora do jogo (`WARTUNE_GAME_TIMEZONE`), separados por vírgula;
`weekdays` = dias ISO (`1` segunda … `7` domingo) separados por vírgula, vazio = todo dia; `active` 0 desliga.
Mesmo horário: sai na ordem do `id`. Horário inválido (`25:00`) derruba a subida, de propósito.

```sql
-- Sylph Atoll só às 18:55/19:00/19:30, de sábado e domingo
UPDATE scheduled_announcements SET times = '18:55', weekdays = '6,7' WHERE name = 'sylph_atoll' AND text LIKE 'Sylph Atoll echoes%';
UPDATE scheduled_announcements SET times = '18:55', weekdays = '6,7' WHERE name = 'sylph_atoll' AND text LIKE '%starting soon%';
UPDATE scheduled_announcements SET times = '19:00', weekdays = '6,7' WHERE name = 'sylph_atoll' AND text LIKE '%has started%';
UPDATE scheduled_announcements SET times = '19:30', weekdays = '6,7' WHERE name = 'sylph_atoll' AND text LIKE '%has ended';
-- desligar o fim; anúncio novo no centro da tela
UPDATE scheduled_announcements SET active = 0 WHERE text LIKE '%has ended';
INSERT INTO scheduled_announcements (name, times, channel, user_type, is_center_tip, text)
VALUES ('manutencao', '04:50', 12, 1, 1, 'Server maintenance in 10 minutes.');
```

Os horários do Sylph Atoll são escolha do dono (o padrão vem do help do cliente, ver [eventos.md](eventos.md)).

### Calendário dos minigames

`game_settings` (migração 0038; regras em [eventos.md](eventos.md#minigames-handlersminigamespy)). Datas na hora do
jogo (`WARTUNE_GAME_TIMEZONE`), formato `AAAA-MM-DD hh:mm:ss`. Sem a linha, o evento fica fechado.

| chave | o quê |
|---|---|
| `normal_fund` | fundo normal (8703/4612): `activeId` (trocar = edição nova, todos compram de novo), `setStartDate`/`setEndDate` (compra), `getStartDate`/`getEndDate` (resgate), `levels` (custo e tiers `[minutos depois do getStartDate, vez, [[item, qtd]...]]`). Padrão: a edição da captura (#86), já vencida |
| `gold_tree` | árvore dourada (8604): `id` (trocar = vezes, baús e andares do zero), `startDate`/`endDate`, `minGrades`, `drops` (`[item, qtd, isShow, isNewItems, peso]`), `score` e `storey` (`[param, item, qtd]`). Padrão: a edição da captura (#72), já vencida |

```sql
-- árvore dourada de novo, por uma semana, edição nova
UPDATE game_settings SET value = json_set(value, '$.id', '2026-11-01', '$.startDate', '2026-11-01 00:00:00',
  '$.endDate', '2026-11-07 23:59:59') WHERE key = 'gold_tree';
DELETE FROM game_settings WHERE key = 'normal_fund';  -- sem fundo normal
```

### Chances dos sorteios

Peso = chance relativa (só a proporção importa; 0 = nunca sai). Valores semeados na 0035; sem a linha no banco, o
código usa o mesmo padrão.

| onde | o quê |
|---|---|
| `vip_wheel_prizes.weight` | roleta VIP (8519), por prêmio (`position` = ordem do 4414). Padrão 1 (uniforme) |
| `campaign_cards.weight` | carta do fim da masmorra, por campanha e item (0034; peso = vezes visto). Tudo 0 numa campanha = uniforme |
| `game_settings` `star_weights` | estrelas (8269): `{"<Profile>": [peso no cristal 0, 1, 2, 3, 4]}`; Profile fora do JSON não sai |
| `game_settings` `star_open_next` | chance (0 a 1) de um sorteio de estrela acender o cristal seguinte (0.3) |
| `game_settings` `vehicle_tech` | tecnologia de tanque do 4501 (`NeedGrades` dos veículos 365/915); padrão 218 (visto no inglês; o turco manda 18218), sem regra conhecida |
| `game_settings` `maze` | Forgotten Catacombs (0087, `game/maze.py` `DEFAULT`): `floors`, `gp_per_floor`, `free_enter`/`max_enter`, `drops`, `chest` (fallback dos andares sem baú visto; o do andar 5 é 2050701 x2 + 208009 x2, migração 0097), `chest_every`, `key` (Crypt Key), `revive` (Balens), `sweep_from` |
| `game_settings` `campaign_sweep` | varredura de campanha (0085): `round_gold` por campanha (`{"1007": 6000}`) |
| `game_settings` `gem_maze_reward_weights` | labirinto de gemas, um peso por prêmio na ordem 2060008 x1, 208027 x1, 208014 x2 (`[1, 1, 1]`) |
| `game_settings` `mall_daily_limit` | limite diário de compra no leilão, em diamante, por nível: `{"bands": [[nível abaixo de, limite], ...], "top": limite}`. Sem a linha (padrão, como a ajuda inglesa): sem limite. Recusa com -52 |
| `game_settings` `vip_bugle_bonus` | cornetas pequenas grátis a mais por dia, por nível VIP (índice 0..9; padrão `[0, ...]`, sem fonte, ver chat.md) |
| `game_settings` `gold_tree` → `drops[i][4]` | árvore dourada (8604), por item da lista (0038). Padrão 1 (uniforme) |

```sql
UPDATE vip_wheel_prizes SET weight = 0.2 WHERE position = 4;          -- 500.000 de ouro 5x mais raro
UPDATE game_settings SET value = '[1, 1, 3]' WHERE key = 'gem_maze_reward_weights';
UPDATE game_settings SET value = '0.5' WHERE key = 'star_open_next';
```

### Fazenda, amizade, cartas e árvore (0037, 0041)

| `game_settings` | o quê |
|---|---|
| `farm_steal_percent` | % do `rewardCount` que um amigo leva por roubo (10, internet) |
| `tree_fruit` | colheita da árvore (5178): `{"<grau>": {"daru", "kyanite", "gold"}}` pelo grau da fazenda; migração 0093 com os graus 6 e 10 vistos nas capturas, o resto é reta entre eles (TODO(inventado)) |
| `friend_grade_step` | pontos de amizade por grau: grau = 1 + pontos // passo (10, dedução) |
| `powcard_suite_slots` | degraus do bônus da coleção de cartas: `[[cartas, grau mínimo], ...]` (`[[4, 1], [4, 3], [4, 8]]`) |

Ficam no código (vêm do cliente, dos templates ou da internet): `Rands`/`TakeRandom` dos templates, a roda do
destino (tamanho das fatias no cliente), o reforço (100% → 10%, wiki) e as quedas que já estão no banco
(`world_monster_drops`, `campaign_contents`).

## CLI

```
uv run wartune-server run                          # sobe o servidor (Ctrl+C encerra com limpeza)
uv run wartune-server db init                      # cria o banco ou aplica as migrações
uv run wartune-server db revision "mensagem"        # gera migração depois de mudar schema.py
uv run wartune-server character novice 2 0          # refaz o tutorial do personagem 2
uv run wartune-server templates update [url]       # baixa o tempinfos.xml da CDN (a do cliente); reinicie depois
```

## Logs

| Arquivo | Conteúdo |
|---|---|
| `logs/server.log` | JSON por linha: conexões, logins, erros com traceback |
| `logs/packets.log` | `dir` (c2s/s2c), `code`, `nome`, `mensagem`, `tamanho`, `corpo` (protobuf em texto) |

Para seguir um jogador específico: `Select-String '"player": 1' logs\server.log`.

### Fórmula de dano

`game_settings` `battle_formula` (migração 0039; regras em [batalha.md](batalha.md#dano)): um JSON com os coeficientes
de `game/battle.py` (`FORMULA`); chave ausente usa o padrão do código. `defence_factor` e `floor` (golpe =
`max((A - D) × defence_factor, A × floor) × Parameter1/100 + Parameter2`), `spread` (sorteio ±), `crit_base`/
`block_base` (chance = 1 - base^ForceHit ou ^Parry), `crit_damage`/`block_damage` (multiplicadores).

```sql
UPDATE game_settings SET value = json_set(value, '$.crit_damage', 2.0) WHERE key = 'battle_formula';  -- SQLite
```
