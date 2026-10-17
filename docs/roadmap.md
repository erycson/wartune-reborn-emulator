# Roadmap

## Marco 1: conta nova chega ao castelo

- [x] Protocolo: cifra, cabeçalho, framing, 693 mensagens validadas contra a captura
- [x] Banco: contas, tickets, servidores, personagens (um por conta em cada servidor), heróis e castelos
- [x] HTTP: config.xml, loginselectlist, login (RSA), visualizeregister, updateplayernovice, portal e launcher
- [x] Socket: 20001 com troca de chave, 8224 com os 10 pacotes da carga inicial, LoginState
- [x] Logs em arquivo (`server.log` e `packets.log`)
- [x] Teste ponta a ponta com cliente falso
- [ ] **Validar no Flash Player projector**. É o próximo passo: abrir pelo launcher e acompanhar `logs/packets.log`

## Próximos

- Pacotes extras do login oficial (4434, 83, 100, 4224, 4900, 4922, 4590 e as respostas a 8320/8466/8530/8218/8209/8625/8322), conforme o cliente pedir
- Prédios do castelo (`BuildingInfoListMsg` a partir de `BuildingTempInfos`) e produção de recursos
- Bolsa e itens, missões
- Tutorial (`noviceProcess < 19000`): 5127 e a campanha de treino (125/140/21/127/130/143)
- Batalhas
- Alembic, quando a primeira coluna existente mudar
