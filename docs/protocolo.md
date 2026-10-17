# Protocolo do socket

Fonte: `ByteSocket`, `PackageIn`/`PackageOut` e `SocketSendManager` do cliente decompilado
(`D:\wartune\decompiled\m2`). Implementação: `src/wartune_server/protocol/`.

## Cabeçalho (20 bytes, big-endian)

| Offset | Tipo | Campo |
|---:|---|---|
| 0 | int16 | magic = **29099** (`0x71AB`) |
| 2 | uint16 | tamanho total (cabeçalho + corpo) |
| 4 | int16 | checksum |
| 6 | int16 | código (opcode); acima de `0x7FFF` vai como negativo |
| 8 | int32 | clientId (o `playerId` depois do login) |
| 12 | int32 | extend1 |
| 16 | int32 | extend2 |
| 20 | … | corpo: protobuf (proto2) |

`checksum = (119 + soma(bytes[6:])) & 0x7F7F`, calculado sobre o pacote **em claro**.

## Cifra (XOR com estado)

A chave tem 8 bytes, e a padrão é `[174, 191, 86, 120, 171, 205, 239, 241]`. Cada direção tem
a sua chave, e ela avança a cada byte. A chave continua de um pacote para o outro, mas o índice
`i` recomeça em 0 a cada pacote:

```
out[0] = in[0] ^ key[0]
para i >= 1:
    key[i % 8] = ((key[i % 8] + out[i-1]) ^ i) & 0xFF
    out[i]     = ((in[i] ^ key[i % 8]) + out[i-1]) & 0xFF
```

Na decifragem o papel de `out[i-1]` é feito pelo byte cifrado anterior. Como o estado avança,
só pode existir **um escritor por conexão** (veja [arquitetura.md](arquitetura.md)). O decoder
espia o cabeçalho sem avançar a chave (`StreamCipher.peek`) e só decifra quando o pacote inteiro chegou.

## Troca de chave no login

`SocketSendManager.loginCmd`:

1. O cliente chama `resetKey()`, que volta para a chave padrão.
2. Envia **20001** `LoginReqMsg{key, ekeys[8 aleatórios]}` ainda com a chave padrão.
3. Logo depois chama `setKey(ekeys)` nas **duas** direções.

No servidor, o handler do 20001 chama `Connection.rekey(ekeys)` antes de responder qualquer coisa.
Isso troca a chave de recebimento na hora (o leitor está entre dois pacotes) e põe a troca da
chave de envio na fila do escritor. O teste `test_key_switch_between_packets_in_same_chunk` cobre
o caso em que o 20001 e o pacote seguinte chegam no mesmo bloco TCP.

## Corpo (protobuf)

As classes AS3 (netease `as3-protobuf`) foram convertidas em `proto/wartune.proto` (693 mensagens)
por `tools/as3_to_proto.py`, que lê os `readFromSlice`. O `writeToBuffer` dessas classes tem tags
repetidas e não serve como fonte. O arquivo Python gerado fica em `protocol/messages/wartune_pb2.py`.

A geração foi validada byte a byte: `tests/protocol/test_messages_against_pcap.py` decodifica e
recodifica 333 pacotes reais (194 opcodes) e exige zero campos desconhecidos.

Nomes repetidos entre pacotes AS3 ganham prefixo do pacote, como `ArmyArmyMsg` e `BattleArmyMsg`.

## Policy file

O Flash pede `<policy-file-request/>\0` na porta 843 ou, se ela falhar, na própria porta do jogo.
As duas respondem com um `cross-domain-policy` liberando todas as portas.

## Observações para os próximos marcos

* Pacotes de campanha e veículo levam um contador (o `ByteSocket.send` verifica o `param2`).
* A FSM do `ByteSocket` foi ignorada, porque não afeta o que trafega na rede.
