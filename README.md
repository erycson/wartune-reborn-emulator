# wartune-server

Servidor de jogo em Python (asyncio) para o cliente Flash do **Legend Online / Wartune** (7Road).
Ele substitui o relay em Node (`D:\wartune\server-relay`), que só reenviava pacotes capturados.
Aqui cada pacote é montado a partir do banco de dados e dos templates do jogo.

## Rodando

```powershell
uv sync
uv run python tools/export_captures.py      # uma vez: gera data/overlay (config.xml, tempinfos.xml...)
uv run wartune-server account create maga segredo1
uv run wartune-server run
```

Abra `http://127.0.0.1:8080/` e entre com a conta. O launcher mostra a URL do `Loading.swf`
para colar no **Flash Player projector** (File → Open) e também tem um botão para jogar pelo Ruffle.

A configuração vem de variáveis `WARTUNE_*` ou do arquivo `.env`; veja [docs/configuracao.md](docs/configuracao.md).

## Testes

```powershell
uv run pytest            # inclui um cliente falso que vai do login HTTP até o LoginState
uv run ruff check src tests
uv run mypy src
```

## Documentação

Comece por [docs/README.md](docs/README.md).
