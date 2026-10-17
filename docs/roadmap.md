# Roadmap

## Marco 1: conta nova chega ao castelo

- [x] Protocolo: cifra, cabeçalho, framing, 693 mensagens validadas contra a captura
- [x] Banco: contas, tickets, servidores, personagens (um por conta em cada servidor), heróis e castelos
- [x] HTTP: loginselectlist, login (RSA), visualizeregister, updateplayernovice
- [x] Portal PHP (contas, servidores, ticket, config.xml) e CDN no Apache
- [x] Painel GM: edição, recarga, reset, banimento e históricos ([administracao.md](administracao.md))
- [x] Socket: 20001 com troca de chave, 8224 com os 10 pacotes da carga inicial, LoginState
- [x] Logs em arquivo (`server.log` e `packets.log`)
- [x] Teste ponta a ponta com cliente falso
- [ ] **Validar no Flash Player projector**. É o próximo passo: abrir pelo portal e acompanhar `logs/packets.log`

## Próximos

- Pacotes extras do login oficial (4434, 83, 100, 4224, 4900, 4922, 4590 e as respostas a 8320/8466/8530/8218/8209/8625/8322), conforme o cliente pedir
- Prédios do castelo (`BuildingInfoListMsg` a partir de `BuildingTempInfos`) e produção de recursos
- [x] Tutorial completo: mapas 10001/10002, batalhas, missões 10–45, baú e equipar, chefe da cidade externa ([tutorial.md](tutorial.md))
- [x] Batalha PvE em tempo real ([batalha.md](batalha.md))
- [ ] **Validar o tutorial no cliente**
- Fórmulas reais de dano, iniciativa e poder de combate
- Cidade externa de verdade: terras selvagens, castelos vizinhos, outros jogadores
- Atividades (4476), títulos (4484), moda (8625), patrulha dos monstros (4122)

## Multiplayer

Levantamento e ordem em [multiplayer.md](multiplayer.md).

- [x] Chat: mundo, cena, privado, cornetas pagas ([chat.md](chat.md)); guilda e time depois
- [x] Social: amigos, lista negra, correio, troca de nome, casamento sem cerimônia ([social.md](social.md))
- [x] Cidade do céu: ver outros jogadores andando ([mundo-compartilhado.md](mundo-compartilhado.md)); relogin espera a sessão anterior
- [x] Cidade do céu, fatia 2: nós (4601), posição gravada, visual (149), entrada e volta da ilha dos pets. Também: garagem de veículos, conta e segurança ([diversos.md](diversos.md))
- [ ] Coliseu contra robôs e cópias de jogadores
- [ ] Atividades (SumActive): login e presente online
- [ ] Boss mundial
- [ ] Times, mina de ouro, torneio de fadas
- [x] Coliseu contra robôs e cópias de jogadores, ranking e recompensas ([pvp.md](pvp.md))
- [ ] Torneio de fadas: pronto do lado do PvP, espera o sistema de pets
- [ ] Senhores, campo de batalha, mina de ametista: respondem como fechados
- [ ] Atividades (SumActive): login e presente online
- [ ] Boss mundial
- [ ] Amigos, times, mina de ouro
- [ ] Guilda, boss de guilda, ataque a castelo
