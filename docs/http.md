# HTTP

Implementação: `src/wartune_server/http/app.py`. Todas as respostas vão sem compressão. O relay só
funcionava no projector depois que parou de mandar gzip para quem não pedia.

## Endpoints do jogo

| Rota | Quem chama | Entrada | Resposta |
|---|---|---|---|
| `GET /client/config.xml` | Loading | — | modelo oficial com hosts, porta, site e chave RSA trocados |
| `GET/POST /loginselectlist` | Loading | `username`, `site` | `<Result><Item ID Active NickName/></Result>` |
| `POST /login`, `/login2` | LoginQueue | `p` (RSA+Base64), `site`, `playfb`, `p2`, `client` | `<Result value message userId Address Port/>` |
| `GET/POST /visualizeregister` | MainFigureView | `userid`, `username`, `nickname`, `sex`, `camp`, `icon`, `site`, `key` | `<Result value="true" type="0"/>` ou `value="false"` com `message` |
| `POST /updateplayernovice` | Loading / NewbieSPHelper | `op` (0 lê, 1 grava), `userid`, `noviceprocess`, `key` | inteiro: o `noviceProcess` atual |
| `* /flashversionservlet` | StartupResourcesLoader | — | `true` |

Regras que o cliente impõe:

* **login**: a resposta precisa ter `@message`, e `@userId` diferente de 0 e `@value` diferente de `"false"`. Um `@message` com `|` faz o cliente entrar em fila de espera.
* **visualizeregister** é carregado pelo `LoaderManagerII` tipo 7 (bytes crus lidos como XML). O cliente aceita `type` 0 ou 3. Com `value="false"`, mostra o `message` na tela de criação.
* `key` em `visualizeregister` e `updateplayernovice` é o `md5(tempPassword)` do login. O servidor confere se ele pertence ao `userid`.

### Ícone, classe e sexo

A tela de criação manda `icon` a partir do índice do papel escolhido (1→1, 2→4, 3→3, 4→6, 5→2, 6→5).
O mesmo número é o `job`/`pic` do `PlayerMsg` e o `TemplateId` em `GameHeroTemp`:

| icon/job | Herói |
|---:|---|
| 1 | guerreiro (masc.) |
| 2 | arqueiro (masc.) |
| 3 | mago (masc.) |
| 4 | guerreira (fem.) |
| 5 | arqueira (fem.) |
| 6 | maga (fem.) |

## Portal

| Rota | Entrada | Resposta |
|---|---|---|
| `GET /`, `/play` | — | launcher (login, URL para o projector, botão do Ruffle) |
| `POST /api/register` | `username` (3–32 caracteres `[A-Za-z0-9_.-]`), `password` (≥ 6) | `{ok, username}` |
| `POST /api/login` | `username`, `password` | `{ok, flashvars, swf_url, socket_port, websocket_port}` |

As senhas são guardadas com scrypt.

## Arquivos estáticos

Qualquer outro `GET` procura o arquivo em `WARTUNE_ASSET_DIRS`, na ordem:
1. `data/overlay` (respostas capturadas do servidor oficial, geradas por `tools/export_captures.py`);
2. `D:/wartune/server-relay/public` (os SWFs e PNGs do relay, que foram validados contra a captura);
3. `D:/xampp/htdocs/wartune-cdn` (o CDN completo, com mapas, equipamentos, ícones etc.).

Caminhos com `..` que escapam da pasta retornam 404.

## PHP / Apache

Se quiser um site em PHP (XAMPP), use-o para o portal e para os assets estáticos. Os endpoints
acima continuam no Python, porque dependem da sessão de login em memória. Para emitir um
ticket, o PHP insere uma linha em `play_tickets` (`token`, `account_id`, `server_id`,
`created_at` e `expires_at`, em UTC) e monta as flashvars.
