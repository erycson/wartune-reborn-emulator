# Roteiro de captura no oficial

O que gravar no servidor oficial inglês para trocar as **deduções** do servidor por dado visto. Como capturar:
[captura-oficial-en.md](captura-oficial-en.md) (pktmon na porta 5002, `tools/decode_pcap.py --port 5002`). Cada item
diz o que fazer no jogo e o que o pacote resolve; o detalhe está no doc do sistema (link).

Ordem sugerida: o que dá numa conta nova primeiro, depois o que pede nível, VIP ou amigos.

O que hoje só tem fonte turca (e o que capturar no inglês para trocar): [fontes-turcas.md](fontes-turcas.md).

## Numa sessão comum (conta nova ou baixa)

| Fazer no jogo | Resolve | Doc |
|---|---|---|
| Subir de nível numa **batalha**, masmorra, coliseu ou fazenda, com o castelo já aberto | ordem 139/100/150/4640 fora da entrega de missão | [cidade-externa.md](cidade-externa.md) |
| Subir de nível com o **exército vazio** e soldados no castelo | tipo de tropa que completa o exército | [cidade-externa.md](cidade-externa.md) |
| Lutar muito: **críticos e bloqueios** à vista | multiplicadores ×1,5 / ×0,75 e chances | [batalha.md](batalha.md) |
| **Atordoar** um inimigo (skill com "Stunned") | se a vez perdida manda 153 e como o `curTurn` desce | [batalha.md](batalha.md) |
| Skills com chance de buffer, Selo sagrado (100), pets numa luta normal | chance do buffer, efeitos | [batalha.md](batalha.md) |
| Abrir o **150** de um guerreiro ou caçador (logar com um) | o ×1,05 do poder de combate fora da maga | [batalha.md](batalha.md) |
| Colher na **própria fazenda**, entregar uma tarefa do painel (Bounty), atacar o chefe do mundo — cada um como 1º do dia | onde sai o 4152 dos leeds 25, 24 e 18 | [eventos.md](eventos.md) |
| Passar o mouse em "Enter the Altar of Ennoblement" no painel de devoção | qual sistema é o leed 22 | [eventos.md](eventos.md) |
| Usar uma **Power Potion** (2013501), gravar o 5006 inteiro; depois tirar o buff (8283) | pacotes e ordem da poção de atributo | [itens.md](itens.md) |
| Terminar uma etapa solo com o **Bonus EXP Scroll** (2013002) ativo | `totalGp` e `propJoin` do 137 | [itens.md](itens.md) |
| Gastar diamante na **loja** e no VIP | se outros gastos também disparam o leed 15 | [eventos.md](eventos.md) |
| Pegar prêmio de uma atividade de soma tipo 1 (gastar Balens) e tipo 10 (troca); depois de uma alquimia ou luta no Sylph Arena, ver se vem 4476 sozinho | respostas do 8586 e se o 4476 é empurrado | [eventos.md](eventos.md) |

## Itens com validade

| Fazer no jogo | Resolve | Doc |
|---|---|---|
| Comprar uma **medalha de 7 dias** na loja de honra; deixar uma vencer na mochila e outra vestida; gravar o login seguinte e o 8346 | se o oficial avisa (83/111/correio) ao vencer | [itens.md](itens.md) |

## Com VIP

| Fazer no jogo | Resolve | Doc |
|---|---|---|
| Logar com **VIP 3+** e gravar o 4152 do login; de novo quando o VIP for comprado ou vencer | devoção do VIP | [eventos.md](eventos.md) |
| Abrir o **chat mundial** com VIP (de preferência em dois níveis VIP): 8705 → 4500 (`paraInt1`) | cornetas grátis do VIP (`vip_bugle_bonus`) | [chat.md](chat.md) |

## Com amigos (fazenda)

| Fazer no jogo | Resolve | Doc |
|---|---|---|
| **Roubar** uma terra madura na fazenda de amigo | quantidade (hoje 10%, internet) e pacotes | [castelo.md](castelo.md) |
| Tirar **verme/erva** na fazenda de amigo | resposta | [castelo.md](castelo.md) |
| Regar o mesmo amigo **duas vezes** no dia; regar depois de bater os 200 de EXP do dia | recusas | [castelo.md](castelo.md) |
| Regar amigos com **graus de amizade** diferentes | tabela do grau (hoje dedução: 1 + gp/10) | [social.md](social.md) |
| Com o dono **online**, um amigo regar a árvore ou roubar | o que o dono recebe | [castelo.md](castelo.md) |

## Cartas de poder e dragão

| Fazer no jogo | Resolve | Doc |
|---|---|---|
| Subir as cartas de uma coleção (9505 op 1) e gravar o 4905 a cada subida | graus dos degraus 2 e 3 do bônus de coleção | [heroi-exercito.md](heroi-exercito.md) |
| Lutar com **cartas de poder** e **dragão** equipados: 157 e 4902 | buffer 3040/3041 e skill do dragão na batalha | [batalha.md](batalha.md) |

## Minigames (só nos dias em que o oficial abre)

| Fazer no jogo | Resolve | Doc |
|---|---|---|
| **Fundo normal**: comprar um nível, resgatar o 1º tier, abrir depois do fim do resgate | janela e estados | [eventos.md](eventos.md) |
| **Árvore dourada**: botão do topo; ativar 1x e 10x com e sem varinha; baú de ativações; vender e tirar do armazém; 4825 de um servidor com andares; ativar no dia seguinte | pesos, andares, "uma vez por dia" | [eventos.md](eventos.md) |
| **Quiz** (9501): uma rodada inteira (4907–4910) | perguntas, respostas, agenda | [eventos.md](eventos.md) |
| **Estrada dourada** (9520–9522): abrir (4933) e jogar o dado nos 3 modos (4934) e o refresh | tabela das casas | [eventos.md](eventos.md) |
| **Pesca** (9507), **caça ao tesouro** (9502), **minério** (9645): abrir e jogar uma vez cada | regras e prêmios | [eventos.md](eventos.md) |
| Loteria, caça-níquel, cadeiras, caixa de ano novo, história, sorteio de grupo: jogar uma vez quando abrir | template e configuração | [eventos.md](eventos.md) |

## Sistemas inteiros sem fonte

Precisam de captura antes de qualquer código ([pendencias.md](pendencias.md)): mapas das atividades de guilda (altar
7601, terra secreta 7501, guerra 4501), exércitos de outros jogadores no mapa (169/4167/4168) e ataque a castelo de
jogador (5160/8488), lordes e campo de batalha, montaria (estrelas, refino, voo), vocação depois do tipo 102.
