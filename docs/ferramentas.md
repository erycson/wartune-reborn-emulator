# Ferramentas e fontes

## Cliente decompilado

A referência é o cliente **inglês** (Wartune Reborn S134), o mesmo que o portal serve (`wartune-reborn/cdn` e
`wartune-reborn/game` são links para o espelho em `D:\xampp\htdocs\wartune\mirror`).

* O FFDec está em `D:\xampp\htdocs\wartune\ferramentas\ffdec` e roda com o JRE portátil de `D:\xampp\htdocs\wartune\ferramentas\jdk-21.0.12.1+1-jre`.
* Os módulos de código (`2.png`, `3.png`… `18.png` do CDN são SWFs embaralhados) são desembaralhados com
  `python -I D:\xampp\htdocs\wartune\desembaralhar.py <N.png> <saida.swf>` e decompilados em
  `D:\xampp\htdocs\wartune\decomp\2\scripts` (código principal: 648 classes de protobuf) e `decomp\m3`..`m18\scripts`.
  O módulo Loading (login, criação de personagem) está em `decomp\Loading\scripts`.
* Legado: o cliente turco do relay em `D:\wartune\decompiled\m{2,3,4,5,8,10,11,15,16}\scripts`. Não é referência; das
  classes em comum, 690 mudaram no inglês, e o inglês tem 556 classes que o turco não tinha (módulos 6, 7, 9,
  12–14, 17 e 18).

## `tools/as3_to_proto.py`

Gera `proto/wartune.proto` e `proto/message_index.json` a partir das classes protobuf AS3. Ele lê os
`readFromSlice`, entende os três formatos do `switch` (deslocamento −1, 0 e −2) e falha se uma classe
tiver `case`s mas o `switch` não for reconhecido. Os dois geradores recebem as mesmas pastas do cliente inglês:

```powershell
$E = 'D:/xampp/htdocs/wartune/decomp'
$R = @("$E/2/scripts") + (3..18 | ForEach-Object { "$E/m$_/scripts" }) + @("$E/Loading/scripts")
uv run python tools/as3_to_proto.py @R
uv run python tools/scan_opcodes.py @R
```

Depois de gerar o `.proto`:

```
uv run python -m grpc_tools.protoc -Iproto --python_out=src/wartune_server/protocol/messages \
    --pyi_out=src/wartune_server/protocol/messages proto/wartune.proto
```

## `tools/scan_opcodes.py`

Varre os listeners `"SLGSocketEvent" + N` (seguindo um nível de delegação) e os `new PackageOut(N)`,
resolve o tipo protobuf de cada lado e dá nome aos opcodes com `ProtocolType.as` e
`AcceptProtocolType.as`. Gera `protocol/data/opcodes.json` (1061 opcodes) e [packets.md](packets.md).

## `tools/decode_pcap.py`

Decifra as capturas do oficial: a inglesa (`tutorial-en.pcapng`, porta 5002, ver
[captura-oficial-en.md](captura-oficial-en.md)) e as turcas antigas (`D:\wartune\server-relay\all pcaps\*.pcapng`, uma por
sistema) para o formato do `replay_packets.json`, que o `dump_capture.py` lê. Remonta cada fluxo TCP
da porta 5000 pela sequência. As capturas começam no meio da sessão, sem o 20001 com a chave, então
a chave é recuperada pelo cabeçalho: cada byte dela só evolui com o texto cifrado, e o cabeçalho tem
bytes conhecidos (magic, tamanho, `extend1` quase sempre 0). Uma chave só vale se o checksum de três
pacotes seguidos bater; num segmento perdido, ressincroniza. Quase todas só têm o lado servidor→
cliente; os pedidos do cliente saem do código decompilado. A saída fica em `captures/` (fora do git:
tem dados do jogador da captura).

```
uv run python tools/decode_pcap.py D:/wartune/server-relay/tutorial-en.pcapng --port 5002 -o captures
uv run python tools/decode_pcap.py "D:/wartune/server-relay/all pcaps/"*.pcapng -o captures   # turcas
uv run python tools/dump_capture.py captures/kader_sistemi.json
```

## `tools/extract_vehicle_map.py`

Lê o `maps/<id>/<id>.titles` do espelho da CDN (objeto AMF3 dinâmico com zlib, chave `"x_y"`, o `mapTielsData` do
cliente) e grava `data/vehicle_map_<id>.json`: os tiles andáveis (valor > 0 e diferente de 2,
`VehicleModel.getWalkable`) e as marcas (valor 3), onde a batalha de veículos põe os tanques e as caixas. Sem o
arquivo, a partida anda sem conferir os tiles (aviso no log).

```
uv run python tools/extract_vehicle_map.py <espelho>/res134-bmclas-sq.7road.net/maps/3001/3001.titles
```

## Legado da CDN turca

`export_captures.py` e `build_cdn_overrides.py` (com `cdn_stubs`, o teste e o `data/overlay`) foram para
`consulta/legado-turco/` (fora do git), com a explicação de como montavam a CDN turca. A CDN ativa é o espelho
inglês (res134) completado pelo `tools/fetch_missing.py`.

## `tools/fetch_missing.py`

O `wartune-cdn` foi montado das capturas, então só tem o que o jogador capturado (job 6, mago,
sexo 0) carregou: faltam os assets de outras classes e sexos (corpo padrão de batalha, efeitos de
skill, figura de level-up...). O CDN oficial inglês (`res134-bmclas-sq.7road.net`) está no ar; o turco
(`res114lortr.creaction-network.com:8080`) é legado. A ferramenta lê os 404 do
`access.log` do Apache e baixa os originais para o `wartune-cdn`, sem alterar nada. Rode depois de
jogar com uma classe nova:

```
uv run python tools/fetch_missing.py                     # 404s do log
uv run python tools/fetch_missing.py equip/x/1.swf ...   # caminhos avulsos
```

Um 403/404 no oficial quer dizer que o arquivo também não existe lá (as capas `*_default_body_cloak`
do guerreiro, por exemplo) e o cliente funciona sem ele. Não gere nem altere assets: se falta algo,
o arquivo certo está no oficial.

## Capturas de referência

`tests/fixtures/pcap_samples.json` traz até 3 amostras por opcode da captura inglesa
(`captures/tutorial_en.json`), mais as turcas dos 8 opcodes que ela não tem (430 pacotes, 234 opcodes;
lista em `tests/protocol/test_messages_against_pcap.py`). Para ver uma mensagem real:

```python
from wartune_server.protocol.registry import MessageRegistry, Direction
r = MessageRegistry.load_default()
r.decode(150, Direction.SERVER_TO_CLIENT, bytes.fromhex(amostra["body"]))
```
