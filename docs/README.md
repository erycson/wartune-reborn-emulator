# Documentação

| Parte | Conteúdo |
|---|---|
| [arquitetura.md](arquitetura.md) | Camadas, concorrência, como um pacote atravessa o servidor |
| [protocolo.md](protocolo.md) | Cabeçalho, checksum, cifra XOR, troca de chave, protobuf |
| [packets.md](packets.md) | Tabela de todos os opcodes, gerada a partir do cliente |
| [sequencia-login.md](sequencia-login.md) | Do portal até a cena do castelo, passo a passo |
| [tutorial.md](tutorial.md) | Campanha de treino: roteiro dos nós, retomada, missões, nível e atributos |
| [itens.md](itens.md) | Mochila, uso de itens, lojas, forja, moda e o registro de elmas (`cash_ledger`) |
| [heroi-exercito.md](heroi-exercito.md) | Tropas, skills, talento, runas, montaria, estrelas, destino, dragão, cartas e pets |
| [batalha.md](batalha.md) | Batalha simulada no servidor: pacotes, relógio, turnos, dano |
| [castelo.md](castelo.md) | Prédios, tecnologia, filas e aceleração, produção, cobrança de ouro, fazenda, árvore, caixa por tempo e offline |
| [http.md](http.md) | Endpoints HTTP do jogo, portal PHP e CDN |
| [banco-de-dados.md](banco-de-dados.md) | Modelo de dados, várias contas em vários servidores, SQLite/MySQL/Postgres |
| [configuracao.md](configuracao.md) | Variáveis de ambiente, logs e CLI |
| [ferramentas.md](ferramentas.md) | Decompilação, geração do `.proto` e dos opcodes, exportação das capturas |
| [eventos.md](eventos.md) | Atividades, assinatura, leed, VIP, contrato do rei, alquimia, painel de recompensas, anel e minigames |
| [cidade-externa.md](cidade-externa.md) | Cidade externa e mapa-múndi: grade, andar, voltar, ataque extra, mudar o castelo; gancho, passe de progresso e mapa do tesouro |
| [multiplayer.md](multiplayer.md) | Levantamento do multiplayer e ordem de implementação: [chat](chat.md), [mundo compartilhado](mundo-compartilhado.md), [PvP](pvp.md), [boss e eventos](boss-eventos.md) |
| [salas-campanha.md](salas-campanha.md) | Salas PvE, times livres e os pedidos do lote: o que está completo e o que depende de quê |
| [drops-masmorras.md](drops-masmorras.md) | Carta do fim de cada masmorra: itens da `Campaigns.Item`, o que foi visto e o que falta (chances) |
| [fontes-internet.md](fontes-internet.md) | Regras e prêmios achados na Internet (wiki/guias), conferidos página a página |
| [administracao.md](administracao.md) | Painel GM do portal, `/gm/kick` e `/gm/ban`, banimento, históricos de login, cash e itens |
| [diversos.md](diversos.md) | Veículos, anti-vício, senha secundária, captcha, acelerador e os pacotes do login que faltam |
| [social.md](social.md) | Amigos, lista negra, correio (socket + `maillist`), troca de nome, casamento |
| [mercado.md](mercado.md) | Mercado entre jogadores: anunciar, lances, preço fixo, cancelar, busca e encerramento pelo correio |
| [pvp.md](pvp.md) | Coliseu, torneio de fadas e os eventos PvP fechados (Senhores, campo de batalha, mina) |
| [boss-eventos.md](boss-eventos.md) | Chefe do mundo: agenda (4182), recusas de entrada, reviver e buff, e o que falta do mapa do chefe |
| [guilda.md](guilda.md) | Guilda: opcodes, regras do cliente, estado em memória, o que falta (altar, guerra) |
| [roadmap.md](roadmap.md) | O que está pronto e os próximos marcos |
| [pendencias.md](pendencias.md) | O que ainda não é igual ao oficial, por sistema, e todas as simplificações `ponytail:` |
