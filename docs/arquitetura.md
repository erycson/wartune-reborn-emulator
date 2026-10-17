# Arquitetura

```
src/wartune_server/
  protocol/     bytes <-> Packet: cifra, cabeçalho, framing, registry opcode->protobuf
  net/          transporte (TCP, WebSocket), Connection (leitor/escritor), servidores
  game/         GameSession, router por opcode, handlers e builders de mensagens
  http/         aiohttp: endpoints dinâmicos do Loading.swf (REQUEST_PATH)
  services/     regras de negócio sem rede: login (ticket do portal), personagens, relógio
  domain/       entidades (dataclasses), protocolos de repositório, erros
  persistence/  SQLAlchemy async: schema, repositórios, UnitOfWork
  templates/    tempinfos.xml carregado em memória (heróis, itens, mapas...)
  security/     RSA do login (compatível com o Hurlant do Flash)
  app.py        raiz de composição (monta tudo e sobe os servidores)
  cli.py        run | db init/revision | character novice | templates update
```

As dependências apontam para dentro: `game` e `http` usam `services`, que usam `domain`.
A persistência implementa os `Protocol` de `domain/repositories.py`, então os serviços
não conhecem o SQLAlchemy e os testes trocam o banco por um SQLite temporário.

## Divisão com o portal e o CDN

```
navegador / projector
  ├─ portal PHP  (Apache :8090/wartune-reborn/portal)   contas, ticket, config.xml do servidor
  ├─ CDN         (Apache :8090/wartune-reborn/cdn)      SWFs, imagens, xml/ (TEMPLATE_PATH)
  └─ servidor do jogo (Python)
       ├─ HTTP :8080  REQUEST_PATH: login, visualizeregister, updateplayernovice...
       └─ socket :5000 (ou WebSocket :5001 pelo Ruffle)
```

O portal e o jogo conversam só pelo banco. O portal grava `accounts` e `play_tickets`. O jogo
publica a própria linha em `game_servers` (host, portas e chave RSA), que o portal usa para listar
os servidores e montar o `config.xml` de cada um. Tudo que mexe no estado do jogo (personagem,
sessão do socket) fica no Python.

## Processos e servidores

Cada processo atende **um** servidor de jogo (`WARTUNE_SERVER_ID`). Vários processos
(S1, S2...) podem dividir o mesmo banco. Um processo abre:

| Porta | O quê |
|---|---|
| 8080 | HTTP do jogo: login, criação de personagem, noviceProcess, crossdomain.xml |
| 5000 | socket do jogo (Flash real); também responde ao `<policy-file-request/>` |
| 5001 | ponte WebSocket para o Ruffle (`socketProxy`) |
| 843 | policy server dedicado (opcional; se faltar permissão, ele só avisa) |

## Concorrência por conexão

Tudo é asyncio, numa única thread. Cada conexão tem:

* **Leitor**: a corrotina principal de `Connection.run`. Ela lê bytes, entrega **um pacote por vez**
  (`PacketDecoder.next_packet`) e espera o handler terminar antes de pegar o próximo.
  Isso mantém a ordem do cliente e permite trocar a chave entre dois pacotes que chegaram juntos.
* **Escritor**: uma tarefa que é a única dona da cifra de envio. `send()` só enfileira
  (`asyncio.Queue` com limite) e retorna, então nenhum handler bloqueia na rede.
  A troca de chave também passa por essa fila, para não ultrapassar pacotes que ainda vão
  sair com a chave antiga.
* **Encerramento**: `close()` enfileira o fim. O escritor esvazia a fila e fecha o transporte,
  o que acorda o leitor. Se a fila encher (cliente que não lê), o escritor é cancelado.

Operações bloqueantes ficam fora do loop: a leitura do `tempinfos.xml` (25 MB) e a geração da
chave RSA rodam com `asyncio.to_thread`, e o banco usa drivers async (aiosqlite, asyncmy, asyncpg).

## Caminho de um pacote

```
socket -> Transport.read -> PacketDecoder (decifra, valida cabeçalho/checksum)
       -> Connection._reader_loop -> GameSession.on_packet
       -> MessageRegistry.decode (protobuf C->S) -> router[opcode](sessão, mensagem)
       -> handler chama services / builders -> GameSession.send -> fila -> escritor
       -> StreamCipher.encrypt -> Transport.write
```

Opcodes sem handler aparecem no log e são ignorados. Uma exceção num handler é registrada
no log e não derruba a conexão.

## Adicionando um opcode

1. Veja a mensagem em [packets.md](packets.md) e em `proto/wartune.proto`.
2. Crie (ou edite) um módulo em `game/handlers/`, decore a função com `@router.on(CODIGO)` e importe o módulo em `game/handlers/__init__.py`.
3. Monte as respostas em `game/builders/` usando `complete()`. O servidor oficial manda todos os campos, e no AS3 uma string ausente vira `null`.
4. Escreva um teste. `tests/test_end_to_end.py` tem um cliente falso pronto para isso.

## Logs

* `logs/server.log`: JSON, um evento por linha (rotação de 20 MB × 5).
* `logs/packets.log`: cada pacote nas duas direções, com o protobuf decodificado em texto.
* Console: formato legível.
