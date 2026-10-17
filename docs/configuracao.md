# Configuração, logs e CLI

As opções vêm de variáveis de ambiente com prefixo `WARTUNE_` ou do arquivo `.env` na raiz.
Implementação: `src/wartune_server/config.py`.

| Variável | Padrão | Para quê |
|---|---|---|
| `WARTUNE_DATABASE_URL` | `sqlite+aiosqlite:///data/wartune.db` | veja [banco-de-dados.md](banco-de-dados.md) |
| `WARTUNE_SERVER_ID` | `1` | qual linha de `game_servers` este processo atende |
| `WARTUNE_SERVER_NAME` | `S1 - Local` | vai para o `PlayerMsg.serverName` |
| `WARTUNE_SITE` | `local_0001` | flashvar `site` e `<NODE site>` do config.xml |
| `WARTUNE_BIND_HOST` | `0.0.0.0` | |
| `WARTUNE_PUBLIC_HOST` | `127.0.0.1` | host que o cliente usa (config.xml e resposta do login) |
| `WARTUNE_HTTP_PORT` | `8080` | |
| `WARTUNE_SOCKET_PORT` | `5000` | |
| `WARTUNE_WEBSOCKET_PORT` | `5001` | ponte para o Ruffle |
| `WARTUNE_POLICY_PORT` | `843` | vazio desliga |
| `WARTUNE_RESOURCE_URL` | vazio | CDN dos assets; vazio usa o próprio HTTP |
| `WARTUNE_ASSET_DIRS` | `["data/overlay", "D:/wartune/server-relay/public"]` | JSON |
| `WARTUNE_TEMPLATES_FILE` | `data/overlay/xml/tempinfos.xml` | |
| `WARTUNE_CONFIG_TEMPLATE` | `data/overlay/client/config.xml` | |
| `WARTUNE_RSA_KEY_FILE` | `data/rsa_private.pem` | criado na primeira execução |
| `WARTUNE_SKIP_TUTORIAL` | `true` | `noviceProcess` mínimo de 19000 (cena do castelo) |
| `WARTUNE_LOGIN_TICKET_TTL_SECONDS` | `300` | |
| `WARTUNE_SOCKET_SESSION_TTL_SECONDS` | `120` | prazo entre o login HTTP e o 20001 |
| `WARTUNE_IDLE_TIMEOUT_SECONDS` | `300` | desconecta um socket ocioso |
| `WARTUNE_LOG_DIR` | `logs` | |
| `WARTUNE_LOG_LEVEL` | `INFO` | |
| `WARTUNE_LOG_PACKETS` | `true` | grava `logs/packets.log` |

Para vários servidores, rode um processo por servidor, com `SERVER_ID`, `SITE` e portas
diferentes e o mesmo `DATABASE_URL`.

## CLI

```
uv run wartune-server run                          # sobe o servidor (Ctrl+C encerra com limpeza)
uv run wartune-server db init                      # cria as tabelas
uv run wartune-server account create <user> <senha>
```

## Logs

| Arquivo | Conteúdo |
|---|---|
| `logs/server.log` | JSON por linha: conexões, logins, erros com traceback |
| `logs/packets.log` | `dir` (c2s/s2c), `code`, `nome`, `mensagem`, `tamanho`, `corpo` (protobuf em texto) |

Para seguir um jogador específico: `Select-String '"player": 1' logs\server.log`.
