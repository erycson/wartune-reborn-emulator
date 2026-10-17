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
- [x] Prédios do castelo, tecnologia, filas, aceleração com ledger, produção, cobrança, fazenda, árvore, caixa por tempo e offline ([castelo.md](castelo.md)); fazenda de amigo, fruto da árvore e população ocupada pendentes
- [x] Tutorial completo: mapas 10001/10002, batalhas, missões 10–45, baú e equipar, chefe da cidade externa ([tutorial.md](tutorial.md))
- [x] Batalha PvE em tempo real ([batalha.md](batalha.md))
- [x] Herói e exército: tropas, skills, talento, runas, montaria, estrelas, destino, dragão, cartas e pets ([heroi-exercito.md](heroi-exercito.md))
- [ ] **Validar o tutorial no cliente**
- Fórmulas reais de dano, iniciativa e poder de combate
- [x] Cidade externa: grade, andar, voltar, ataque extra, mudar o castelo, gancho, passe e mapa do tesouro ([cidade-externa.md](cidade-externa.md))
- Cidade externa de verdade: terras selvagens, castelos vizinhos, outros jogadores (o que falta está em [cidade-externa.md](cidade-externa.md))
- [x] Mochila, uso de itens, lojas (comum, moda, poção, misteriosa), forja e moda, com registro de elmas no `cash_ledger` ([itens.md](itens.md))
- Atividades (4476), títulos (4484: lista vazia até haver conquistas), patrulha dos monstros (4122)

## Multiplayer

Levantamento e ordem em [multiplayer.md](multiplayer.md).

- [x] Chat: mundo, cena, privado, cornetas pagas ([chat.md](chat.md)); guilda e time depois
- [x] Social: amigos, lista negra, correio, troca de nome, casamento sem cerimônia ([social.md](social.md))
- [x] Salas PvE e times livres: criar, entrar, expulsar, passar o dono, convite só a amigo; campanha da sala, varredura, torre e pedágio com progresso ficam parciais ([salas-campanha.md](salas-campanha.md))
- [x] Chat: mundo, cena, privado, guilda ([chat.md](chat.md)); time e cornetas pagas depois
- [x] Cidade do céu: ver outros jogadores andando ([mundo-compartilhado.md](mundo-compartilhado.md)); relogin espera a sessão anterior
- [x] Cidade do céu, fatia 2: nós (4601), posição gravada, visual (149), entrada e volta da ilha dos pets. Também: garagem de veículos, conta e segurança ([diversos.md](diversos.md))
- [ ] Coliseu contra robôs e cópias de jogadores
- [x] Atividades (SumActive), assinatura, leed, VIP, recompensas e minigames ([eventos.md](eventos.md)); condições que dependem de outros sistemas listadas lá
- [ ] Boss mundial: agenda (8271 -> 4182) e recusas prontas; falta o mapa do chefe ([boss-eventos.md](boss-eventos.md))
- [ ] Times, mina de ouro, torneio de fadas
- [x] Coliseu contra robôs e cópias de jogadores, ranking e recompensas ([pvp.md](pvp.md))
- [ ] Torneio de fadas: pronto do lado do PvP, espera o sistema de pets
- [ ] Senhores, campo de batalha, mina de ametista: respondem como fechados
- [ ] Atividades (SumActive): login e presente online
- [ ] Boss mundial: agenda (8271 -> 4182) e recusas prontas; falta o mapa do chefe ([boss-eventos.md](boss-eventos.md))
- [ ] Amigos, times, mina de ouro
- [ ] Guilda, boss de guilda, ataque a castelo
- [ ] Amigos, times, mina de ouro, torneio de fadas
- [x] Guilda: criar, entrar, cargos, contribuição, melhorias, habilidades, mercado, bênção, baú ([guilda.md](guilda.md))
- [ ] Boss de guilda (altar), terra secreta, guerra de guildas: falta o mapa de campanha; ataque a castelo
