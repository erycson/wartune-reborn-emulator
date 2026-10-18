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
| `WARTUNE_GAME_TIMEZONE` | `America/Los_Angeles` | fuso do jogo: horários do chefe do mundo, relógio dos chefes do mapa e `createDate` das minas. Nome IANA (com horário de verão, base do pacote `tzdata`) ou fixo (`+03:00`). O oficial inglês segue o Pacífico (internet) https://wartunereborn.wan.com/article/read?aid=8721.html; as capturas são do turco (UTC+3), por isso os testes usam `+03:00` |
| `WARTUNE_POLICY_PORT` | `843` | vazio desliga |
| `WARTUNE_TEMPLATES_FILE` | `data/overlay/xml/tempinfos.xml` | cópia local dos templates |
| `WARTUNE_TEMPLATES_URL` | vazio | ex.: `https://cdn.exemplo.com/xml/tempinfos.xml`, usada pelo `templates update` |
| `WARTUNE_RSA_KEY_FILE` | `data/rsa_private.pem` | criado na primeira execução |
| `WARTUNE_SKIP_TUTORIAL` | `false` | faz o tutorial ([tutorial.md](tutorial.md)); `true` mantém o `noviceProcess` em no mínimo 19000 (cena do castelo) |
| `WARTUNE_GM_SECRET` | vazio | segredo do painel GM do portal (`gm_secret` no `config.php`). Liga o `POST /gm/kick` (cabeçalho `X-GM-Secret`, campo `character_id`), que derruba o jogador e só responde depois que a sessão terminou, para o portal editar o banco sem o servidor desfazer. Também liga o `POST /gm/ban` ([administracao.md](administracao.md)). Vazio: as rotas não existem |
| `WARTUNE_SOCKET_SESSION_TTL_SECONDS` | `1800` | sessão do login HTTP sem uso por esse tempo expira (renovada a cada uso: registro, novice, 20001) |
| `WARTUNE_IDLE_TIMEOUT_SECONDS` | `300` | desconecta um socket ocioso |
| `WARTUNE_LOG_DIR` | `logs` | |
| `WARTUNE_LOG_LEVEL` | `INFO` | |
| `WARTUNE_LOG_PACKETS` | `true` | grava `logs/packets.log` |

Para vários servidores, rode um processo por servidor, com `SERVER_ID`, `SITE`, `SERVER_NAME`
e portas diferentes e o mesmo `DATABASE_URL`. Cada um se publica em `game_servers` e aparece
sozinho na lista do portal.

O portal tem a própria configuração em `D:\xampp\htdocs\wartune-reborn\portal\config.php`
(DSN do mesmo banco, URL do portal, URL do CDN e validade do ticket).

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
