# Multiplayer: visão geral

Levantamento do que o cliente espera do servidor quando há mais de um jogador. Cada parte tem o
seu documento:

| Parte | Conteúdo |
|---|---|
| [chat.md](chat.md) | Canais, envio, privado, amigos, correio, guilda |
| [mundo-compartilhado.md](mundo-compartilhado.md) | Cidade do céu (ver outros andando), cidade externa e mapa-múndi, times e salas de grupo |
| [pvp.md](pvp.md) | Coliseu (desafio), torneio de fadas, mina de ouro, ataque a castelo |
| [boss-eventos.md](boss-eventos.md) | Boss mundial e de guilda, atividades (SumActive), assinatura, login acumulado, presente online |

## O que é fato e o que é dedução

- **Nenhuma captura turca tem pacotes C>S** (a inglesa, `tutorial_en.json`, tem). As turcas só guardam o que o
  servidor mandou.
  Todo formato de pedido do cliente nestes documentos vem do código decompilado
  (`D:/wartune/decompiled`) e está marcado como *(cliente)*.
- **Nenhuma captura tem chat entre jogadores, time ou sala com 2 jogadores, ataque a castelo ou
  boss mundial.** Esses fluxos são *(dedução)*: montados do código do cliente e do formato das
  mensagens.
- O que tem índice de captura (`inglesa #2126`; turco: `login.json #131`) foi *(visto)*.

Correções em relação aos nomes dos arquivos de captura:

- `savasa_baskin_ve_elmas_ile_hizlandirma.json` é **varredura de campanha** (4425
  `CampaignSweepRsp`), sem batalha. Não é ataque a castelo.
- `cevre_altin_madeni_savasi.json` é PvE contra a guarnição NPC de uma mina sem dono (como a inglesa #723-#754).

## Armadilhas do cliente

- **4182** (estado do boss) com um `campaignId` que não está em `CampaignInfo` derruba o cliente
  (acesso a nulo em `WorldBossManager`).
- **4594** (movimento na cidade do céu) é ignorado para quem não foi apresentado antes por um
  **4597**. O oficial manda 4597 e logo depois um 4594 com a posição.
- **ChatChannelMsg**: o cliente grava `vipType` na tag 24 mas lê da **26**. O servidor manda na 26
  (o nosso `.proto` já está assim).
- **4595** força a cena SPACE no cliente. Só mandar depois do tutorial.
- Mensagem privada (4231) de quem não está na lista de amigos fica guardada até o cliente receber
  o **4256** que ele pede com **15038**.

## Base comum no servidor

- `OnlinePlayers` (`game/session.py`) é o registro de quem está conectado neste processo.
  `broadcast(code, msg)` manda para todos; `Connection.send` em conexão fechando só descarta,
  então mandar para uma sessão saindo é seguro.
- Os outros jogadores são sempre montados a partir do snapshot em memória da sessão deles (online)
  ou do banco (offline, para PvP).
- ponytail: um processo por servidor, tudo em memória. Vários processos para o mesmo servidor de
  jogo exigiriam um barramento (Redis pub/sub), o que só faz sentido com muita gente.

## Ordem de implementação

1. **Chat**: mundo (8198), cena (15005 canal 8), privado (15023), info de quem mandou (15038).
   Valida nível, tamanho, intervalo e tira as tags HTML. Só precisa do `broadcast`.
2. **Cidade do céu**: 4595/4597/4594/4607 e o 8690 de movimento. Junto, o login passa a esperar a
   sessão anterior terminar antes de carregar o snapshot (relogin não duplica item nem anuncia
   saída por engano).
3. **Coliseu** contra robôs e cópias de outros jogadores. Exige que o lado do jogador possa perder
   na batalha (`battle.py` hoje não deixa).
4. **Atividades (SumActive)**: login e presente online, definidas pelo operador em JSON.
5. **Boss mundial**: agenda, HP global, ranking de dano.
6. Amigos de verdade (lista, pedido, online/offline), times, mina de ouro, torneio de fadas.
7. Guilda, boss de guilda, ataque a castelo (sem captura nenhuma: capturar antes, se der).
