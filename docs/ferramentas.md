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
`AcceptProtocolType.as`. Gera `protocol/data/opcodes.json` (1061 opcodes) e [packets.md](packets.md).

## `tools/decode_pcap.py`

Decifra as capturas do Wireshark do oficial (`D:\wartune\server-relayll pcaps\*.pcapng`, uma por
sistema) para o formato do `replay_packets.json`, que o `dump_capture.py` lê. Remonta cada fluxo TCP
da porta 5000 pela sequência. As capturas começam no meio da sessão, sem o 20001 com a chave, então
a chave é recuperada pelo cabeçalho: cada byte dela só evolui com o texto cifrado, e o cabeçalho tem
bytes conhecidos (magic, tamanho, `extend1` quase sempre 0). Uma chave só vale se o checksum de três
pacotes seguidos bater; num segmento perdido, ressincroniza. Quase todas só têm o lado servidor→
cliente; os pedidos do cliente saem do código decompilado. A saída fica em `captures/` (fora do git:
tem dados do jogador da captura).

```
uv run python tools/decode_pcap.py "D:/wartune/server-relay/all pcaps/"*.pcapng -o captures
uv run python tools/dump_capture.py captures/kader_sistemi.json
```

## `tools/export_captures.py`

Exporta as sessões HTTP capturadas no Fiddler (só status 200, sem chunked e sem Content-Encoding)
para `data/overlay/` (586 arquivos). Esse diretório inclui o `client/config.xml` oficial usado como
modelo e o `xml/tempinfos.xml` (zlib). Fica fora do git, então rode o script depois de clonar:
`uv run python tools/export_captures.py D:/wartune/server-relay/loginprotokol/raw D:/wartune/server-relay/testraconu/raw`.

## `tools/build_cdn_overrides.py`

Monta `D:\xampp\htdocs\wartune-reborn\cdn`: copia de `data/overlay` e do `public` do relay os
arquivos que faltam no CDN completo ou que têm conteúdo diferente (os `.png` de código, por exemplo),
e ignora o que não é asset (páginas, scripts, respostas de endpoints).

Depois ela ajusta os módulos de código (`N.png`, que começam com `road7` + md5):

* **Enchimento**: os `.png` do relay trazem ~20 MB de zeros depois do tag End do SWF. O Flash
  ignora isso; é a única diferença entre o `2.png` (que o Ruffle carrega) e o `8.png` (`NewbieModule is not defined` no fim do
  login). A ferramenta recomprime o SWF sem o enchimento e atualiza `ui/zh_cn/size.xml`, porque o
  `ModuleLoader` recusa o módulo quando o tamanho difere em 3000 bytes ou mais.
* **MD5**: o `ModuleLoader` compara os bytes 5..37 do arquivo com `resouececheck.sq` e descarta
  o módulo **sem erro** se não baterem. Os módulos que só existem no CDN completo (6, 7, 9, 12–14,
  17, 18) são de outro build, então a lista recebe o md5 embutido em cada arquivo.

## Capturas de referência

`tests/fixtures/pcap_samples.json` traz até 3 amostras por opcode de uma sessão oficial
(333 pacotes, 194 opcodes). Para ver uma mensagem real:

```python
from wartune_server.protocol.registry import MessageRegistry, Direction
r = MessageRegistry.load_default()
r.decode(150, Direction.SERVER_TO_CLIENT, bytes.fromhex(amostra["body"]))
```
