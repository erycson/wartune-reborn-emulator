# wartune-server

Servidor de jogo em Python (asyncio) para o cliente Flash do **Legend Online / Wartune** (7Road).
Ele substitui o relay em Node (`D:\wartune\server-relay`), que só reenviava pacotes capturados.
Aqui cada pacote é montado a partir do banco de dados e dos templates do jogo.

## Rodando

Nada real vai para o git (banco, templates da 7road, capturas, chave): tudo é gerado do zero pelos comandos abaixo.

O jogo tem três partes:

| Parte | Onde | Papel |
|---|---|---|
| **servidor do jogo** (este projeto) | Python, portas 8080/5000/5001/843 | socket do jogo e endpoints HTTP do `Loading.swf` |
| **portal** | PHP em `D:\xampp\htdocs\wartune-reborn\portal` | contas, lista de servidores, ticket, `config.xml` |
| **CDN** | Apache em `D:\xampp\htdocs\wartune-reborn\cdn`, link para o espelho inglês `D:\xampp\htdocs\wartune\mirror\res134-bmclas-sq.7road.net` | SWFs, imagens, `language.txt` |

```powershell
uv sync
uv run wartune-server templates update   # baixa o tempinfos.xml da CDN (WARTUNE_TEMPLATES_URL) e importa no banco
uv run wartune-server run                # migrações criam tabelas e conteúdo; a chave RSA é gerada se faltar
```

Abra `http://127.0.0.1:8090/wartune-reborn/`, crie a conta e escolha o servidor. A página de jogar
mostra a URL do `Loading.swf` para o **Flash Player projector** (File → Open) e tem um botão
para jogar pelo Ruffle.

O CDN e o site do jogo são o espelho do oficial inglês (S134), baixado por
`D:\xampp\htdocs\wartune\download.php`. Para baixar o que o cliente pediu e o espelho não tem
(404 no Apache): `uv run python tools/fetch_missing.py`. As ferramentas da CDN turca antiga estão em
`consulta/legado-turco/` (fora do git).

A configuração vem de variáveis `WARTUNE_*` ou do arquivo `.env`; veja [docs/configuracao.md](docs/configuracao.md).

## Testes

```powershell
uv run pytest            # inclui um cliente falso que vai do login HTTP até o LoginState
uv run ruff check src tests
uv run mypy src
```

## Documentação

Comece por [docs/README.md](docs/README.md).
