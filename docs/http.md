# HTTP

Implementação: `src/wartune_server/http/app.py`. Só os endpoints dinâmicos que o cliente chama em
`REQUEST_PATH`; o `config.xml`, o portal e os arquivos estáticos são do portal PHP e do Apache. Todas as respostas vão sem compressão. O relay só
funcionava no projector depois que parou de mandar gzip para quem não pedia.

## Endpoints do jogo

| Rota | Quem chama | Entrada | Resposta |
|---|---|---|---|
| `GET /crossdomain.xml` | Flash | — | libera o SWF vindo do Apache (outra porta = outra origem) |
| `POST /maillist` | EmailManager | `userId`, `mailId`, `reqType`, `key` | `<Result value="true"/>` em **zlib** (o cliente faz `ByteArray.uncompress`); `<Info .../>` por correio ([social.md](social.md#correio)); `key` da sessão do próprio `userId` |
| `GET/POST /nicknamecheck` | RenameView | `nickname` | `xml_result` true = nome livre (antes do 8345) |
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

## Portal (PHP)

Fica em `D:\xampp\htdocs\wartune-reborn\portal` (`http://127.0.0.1:8090/wartune-reborn/portal/`):

| Página | O quê |
|---|---|
| `index.php` | entrar / criar conta (senha com `password_hash`); lista os servidores de `game_servers`, com status online (teste no socket) e o personagem da conta em cada um |
| `play.php?server=N` | emite o ticket e mostra a URL do `Loading.swf` (projector) e o botão do Ruffle |
| `client-config.php?server=N` | `config.xml` do servidor N, a partir do modelo oficial: `REQUEST_PATH` → HTTP do jogo, `ResourcePath`/`TEMPLATE_PATH` → CDN, `SocktPath`, `NODE site` e `RSAKey` vindos de `game_servers` |

## CDN

`D:\xampp\htdocs\wartune-reborn\cdn` contém só os arquivos que diferem do CDN completo ou que
faltam nele (gerada por `tools/build_cdn_overrides.py`). O `.htaccess` resolve, na ordem:

1. a própria pasta (respostas oficiais capturadas e os `.png` de código do relay);
2. o CDN completo em `/wartune-cdn/`;
3. `cdn/client/`, porque o cliente pede arquivos relativos ao `Loading.swf`, que no oficial ficava em `/client/` (ex.: `resouececheck.sq`, a lista de MD5 sem a qual os SWFs cifrados não abrem).

Arquivos que o cliente pede e o CDN não tem (`xml/version.xml`, `xml/resource.xml`) saem de
`tools/cdn_stubs`. No 404, o Flash entrega um corpo vazio e segue; o Ruffle entrega o HTML do Apache,
e o `StartupResourcesLoader` quebra com `XML parser failure`.
