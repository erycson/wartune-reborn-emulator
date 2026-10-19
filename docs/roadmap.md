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

- [x] Pacotes extras do login oficial conferidos com a captura em inglês; os que não vão (100 vazio, 4900, 4590) e o porquê em [sequencia-login.md](sequencia-login.md)
- [x] Prédios do castelo, tecnologia, filas, aceleração com ledger, produção, cobrança, fazenda, árvore, caixa por tempo e offline ([castelo.md](castelo.md)); fazenda de amigo, fruto da árvore e população ocupada pendentes
- [x] Tutorial completo: mapas 10001/10002, batalhas, missões 10–45, baú e equipar, chefe da cidade externa ([tutorial.md](tutorial.md))
- [x] Batalha PvE em tempo real ([batalha.md](batalha.md))
- [x] Herói e exército: tropas, skills, talento, runas, montaria, estrelas, destino, dragão, cartas e pets ([heroi-exercito.md](heroi-exercito.md))
- [ ] **Validar o tutorial no cliente**
- Fórmulas reais de dano, iniciativa e poder de combate
- [x] Cidade externa: grade, andar, voltar, ataque extra, mudar o castelo, gancho, passe e mapa do tesouro ([cidade-externa.md](cidade-externa.md))
- Cidade externa de verdade: terras selvagens, castelos vizinhos, outros jogadores (o que falta está em [cidade-externa.md](cidade-externa.md))
- [x] Mochila, uso de itens, lojas (comum, moda, poção, misteriosa), forja e moda, com registro de elmas no `cash_ledger` ([itens.md](itens.md))
- Títulos (4484: lista vazia até haver conquistas), patrulha dos monstros (4122)

## Multiplayer

Levantamento e ordem em [multiplayer.md](multiplayer.md).

- [x] Chat: mundo, cena, privado, guilda, cornetas pagas ([chat.md](chat.md)); canal de time recusado
- [x] Social: amigos, lista negra, correio, troca de nome, casamento sem cerimônia ([social.md](social.md))
- [x] Salas PvE e times livres (em memória): criar, entrar, expulsar, passar o dono, sair (por ora e de vez), convite só a amigo, recusa de convite de time; campanha da sala, varredura, torre e pedágio com progresso ficam parciais ([salas-campanha.md](salas-campanha.md))
- [x] Mercado entre jogadores: anunciar, lances, preço fixo, cancelar, busca; sem captura, regras de tela deduzidas ([mercado.md](mercado.md))
- [x] Cidade do céu: ver outros jogadores andando ([mundo-compartilhado.md](mundo-compartilhado.md)); relogin espera a sessão anterior
- [x] Cidade do céu, fatia 2: nós (4601), posição gravada, visual (149), entrada e volta da ilha dos pets. Também: garagem de veículos, conta e segurança ([diversos.md](diversos.md))
- [x] Minas de ouro com refresh de 12 h por jogador ([cidade-externa.md](cidade-externa.md))
- [x] Atividades (SumActive: login, online, devoção e contadores por ação), assinatura, leed, VIP, recompensas e minigames ([eventos.md](eventos.md)); tipos que dependem de outros sistemas listados lá
- [x] Chefe do mundo: agenda, luta com vida compartilhada, ranking, reviver e prêmios pelo correio ([boss-eventos.md](boss-eventos.md)); conferir com captura
- [x] Coliseu contra robôs e cópias de jogadores, ranking e recompensas ([pvp.md](pvp.md))
- [x] Torneio de fadas: formação, desafio com os pets gravados, pontos, recompensas e encerrar já com VIP ([pvp.md](pvp.md)); pets que o jogador ganha são do sistema de pets
- [x] Guilda: criar, entrar, cargos, contribuição, melhorias, habilidades, mercado, bênção, baú ([guilda.md](guilda.md))
- [ ] Senhores, campo de batalha, mina de ametista: respondem como fechados
- [ ] Boss de guilda (altar), terra secreta, guerra de guildas: falta o mapa de campanha
- [ ] Ataque a castelo: 9506 compra tentativas, nada as gasta
- O que falta em cada sistema: [pendencias.md](pendencias.md)
