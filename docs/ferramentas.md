# Ferramentas e fontes

## Cliente decompilado

* O FFDec está em `D:\xampp\htdocs\wartune-cdn\_tools\ffdec-26.2.1\ffdec.jar` e roda com o JRE portátil de `D:\wartune\tools\jdk-21.0.12.1+1-jre`.
* Os módulos do relay (`2.png`, `3.png`… são SWFs) foram decompilados em `D:\wartune\decompiled\m{2,3,4,5,8,10,11,15,16}\scripts`. O **m2** é o código principal: 2600 classes, 648 delas de protobuf.
* O módulo Loading (login, criação de personagem) está em `D:\wartune\server-relay\decoded client\Loading\scripts`.
* Use as versões do relay, não as do CDN: os `.png` com código no CDN são diferentes, e os do relay foram validados contra a captura.

## `tools/as3_to_proto.py`

Gera `proto/wartune.proto` e `proto/message_index.json` a partir das classes protobuf AS3. Ele lê os
`readFromSlice`, entende os três formatos do `switch` (deslocamento −1, 0 e −2) e falha se uma classe
tiver `case`s mas o `switch` não for reconhecido. Depois de gerar o `.proto`:

```
uv run python -m grpc_tools.protoc -Iproto --python_out=src/wartune_server/protocol/messages \
    --pyi_out=src/wartune_server/protocol/messages proto/wartune.proto
```

## `tools/scan_opcodes.py`

Varre os listeners `"SLGSocketEvent" + N` (seguindo um nível de delegação) e os `new PackageOut(N)`,
resolve o tipo protobuf de cada lado e dá nome aos opcodes com `ProtocolType.as` e
`AcceptProtocolType.as`. Gera `protocol/data/opcodes.json` (1055 opcodes) e [packets.md](packets.md).

## `tools/export_captures.py`

Exporta as sessões HTTP capturadas no Fiddler (só status 200, sem chunked e sem Content-Encoding)
para `data/overlay/` (586 arquivos). Esse diretório inclui o `client/config.xml` oficial usado como
modelo e o `xml/tempinfos.xml` (zlib). Fica fora do git, então rode o script depois de clonar.

## Capturas de referência

`tests/fixtures/pcap_samples.json` traz até 3 amostras por opcode de uma sessão oficial
(333 pacotes, 194 opcodes). Para ver uma mensagem real:

```python
from wartune_server.protocol.registry import MessageRegistry, Direction
r = MessageRegistry.load_default()
r.decode(150, Direction.SERVER_TO_CLIENT, bytes.fromhex(amostra["body"]))
```
