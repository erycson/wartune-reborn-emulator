# Captura do oficial inglês (2026-10-18)

Personagem novo (mago, job 3) do tutorial até o nível ~15 no S134 inglês. Gravado com `pktmon`
(porta 5002, IPv6, Flash Player projector) e decifrado com
`uv run python tools/decode_pcap.py D:/wartune/server-relay/tutorial-en.pcapng --port 5002 -o captures`
(3370 pacotes, 988 do cliente). `captures/` fica fora do git. Os `#N` abaixo são linhas de
`tools/dump_capture.py captures/tutorial_en.json`.

Como capturar de novo: pegar a URL em `https://7.wan.com/index/get_game_url/?sid=2574` (logado),
trocar `game.jsp` por `Loading.swf` e abrir no projector; `pktmon filter add -p 5002` e
`pktmon start --capture --pkt-size 0 --file-name <arq>.etl` antes; no fim `pktmon stop` e
`pktmon etl2pcap`. No navegador o oficial roda no Ruffle (WebSocket), que o pktmon não pega.

## Já aplicado

- Tutorial: falas e nomes oficiais (`tools/extract_tutorial.py captures/tutorial_en.json`).
  `roleId` do jogador nas falas = `job`.
- Missões: entrega (5014) na ordem e com os textos do oficial, missão 10 no registro (seção Missões).

## Campanhas (feito)

| mapa | campanha | situação |
|---|---|---|
| 1011, 1021 Worg Lair | 1001 | **feito**: conteúdo inglês no banco (`campaign_contents`, migração 0034) |
| 1131→1132, 1141→1142 Baylon Plains | 1002 | **feito**: etapas em par, portal (125 tipo 3), tumbas, caixa do caçador, Karlan e Karda |
| 6001 Resource Quarry | 6001 | **feito**: 8258 entra, 5125 → 143 COLLECTION, 5032 colhe Wood (115, 111, 83), 8699 luta (Wood x18), 5025 sai. Destrava a missão 102 |

`tools/extract_dungeon.py captures/tutorial_en.json --campaign N` (N = 1001, 1002, 6001) junta cada campanha em
`src/wartune_server/persistence/migrations/versions/0034_campanhas.json`; a migração 0034 grava no banco. O 5039
respeita `paraInt2` (a campanha) e a etapa vem do estado do personagem (`campaign_stage:<id>`). Mensagens em inglês.
Ordens, fórmulas (137, `totalGp`), cartas e o que é dedução: `docs/salas-campanha.md` e `docs/drops-masmorras.md`.

Karda (GameHeroTempInfo 1023) tem `RejectType="19,100,38,39"` (19 = imune a atordoamento); o
cliente desenha sozinho. Nossa batalha ainda não tem efeitos de controle: **só registrado, não implementado**.

## Missões (10 → 130, todas na captura)

Recompensas batem com `QuestTempInfo`/`QuestGoods`. Feito (detalhes em [missoes.md](missoes.md), "Ordem da entrega"):
- [x] textos da entrega e da mochila em inglês: "Received 3,000 EXP " (vírgula e espaço no fim),
  "Received: Lvl. 5 Starter Pack x1", pacote (5006) "Received:  10 Bound Balens, 3,000 Gold, Amethyst Ring x1, ..."
  (#689, do fim para o começo, o -500 com espaço antes), recurso "Received: 2,000 Gold" (dedução) e mochila cheia
  "Inventory Full" (dedução: `language.txt`, a captura não tem);
- [x] 112 de progresso antes da entrega só nos tipos 23, 2 e 10; no tipo 23 o `condition_1` vira o
  `noviceProcess`; bolsa (27/28/32/49) deixa `condition` em 0 sempre (nem no aceite nem nos drops o oficial conta);
- [x] ordem 115 (gasto), 3, 112, 3 (strategy), 109, 150, 3, 115 (ganhos), 111, 52, 83;
- [x] 150 na entrega só quando sobe de nível;
- [x] a missão 10 nasce com o personagem (`addDate` = criação; o oficial nunca recebe 5012 dela);
- [ ] 100 (tropas) e 139 junto da subida de nível: o `add_gp` não manda (vale para toda subida, não só missão);
- [ ] diária 863 (tipo 63 "Devotion", VIP, nível 10): aceita pelo cliente junto da 160 (#3195) com `condition_1` 0,
  embora a devoção do dia já estivesse em 20 (#1652 "Your devotion level has increased to 20."). A fonte é a devoção
  (`dayGuide`: "Receive {1} devotion by ..."), que o servidor não tem; não há entrega dela na captura.

Tipos conferidos nos 21 aceites/entregas: 23 (10, 30, 40, 45, 50), 2 (51, 81, 82), 3 (52 = 900, 110 = 460: soma,
passa do `Para2`), 7 (60 = 2), 14 (70; 120 e 130 pedem a 1002, sem nós aqui), 26 (80), 27 (90), 8 (100, robô),
10 (101 = 3), 32 (102: a fonte é a 6001, recusada), 34 (160, só aceite), 63 (863, só aceite).

Correlações (missão ↔ item ↔ monstro ↔ texto):
- 90 "Collect Worg Teeth" ↔ 2100001 Worg Tooth ↔ Grassland Worgs da Worg Lair (1001): "Received: Worg Tooth x2" (#1276);
  a entrega tira a pilha inteira (#1570);
- 102 "Collect Lumber" ↔ 2100022 Wood (SonType 210) ↔ Resource Quarry (6001, 5032 `cmd:2`): "Received: Wood x2/x3/x18"
  (#1875, #1906, #2061); NPC "Welcome to the Resource Quarry! ..." (#2090);
- 80 "Defeat Wulfgar" ↔ chefe `GameHeroTemp` 1011 da 1001;
- 45 → 2060301 Lvl. 5 Starter Pack (mago) → GradeDrop 90305 → #689 (10 Bound Balens, 3,000 Gold, Amethyst Ring,
  Banshee Plume, Lvl. 10 Starter Pack); 50 → Mana Robe; 110 → 2030401 Bound Balens (10 Pack) x8;
- 90 e 101 pagam `RewardStrategy` (1000 e 2000 de Daru): o 3 dela vem antes do 3 da EXP.

## Novato, VIP e eventos

| sistema | captura | nós |
|---|---|---|
| baú online (`TimeDrop`, minutos) | contagem começa no 1º 5019 e zera a cada resgate; resgate manda 109 (ou 3), 115, 111, 4250, 4, 83×2 | **feito** (`handlers/rewards.py`, `timebox.py`) |
| EXP +100% | 4247 `rateInfo{rate:100, beginDay, endDay}`: evento do servidor por datas | **feito**: tabela `exp_rate_events` (0033), 4247 no login; multiplicador não aplicado (o EXP das capturas já vem com o evento) |
| cartão VIP de teste 2031201 (`Property1=12`, 1 h) | 5006 → 115, 111, 4410 `vipType:2`, 3 | **feito** (`vip.use_trial_card`) |
| VipInfo no login | `takeGiftDate` = criação | **feito** |
| presente semanal VIP (`VipDrop`) | 8505 → 115, 111, 4410, 4539, 83; próximo em 10-26 | **feito**: próxima liberação = segunda da semana seguinte (semana começa no domingo; dedução de um ponto só) |
| roleta VIP (8521/8519) | 18 prêmios em #3325 (só na captura, sem probabilidades) | **feito**: tabela `vip_wheel_prizes`, custo k no giro k (`game_settings.vip_wheel_costs`), sorteio uniforme; preço de "atualizar" desconhecido |
| chat World | 111 "Requires character Level of 20" | **feito**: `game_settings.world_chat_min_grade`; cota grátis de `SMALL_BUGLE_FREE_COUNT`; `leed_done` duplicado removido |
| anúncio Sylph Atoll | 83 canal 12 `isCenterTip` | falta: textos em #3029/#3030, mas `petboss_time` = "全天" não dá horário |
| fundo novato (4640) | custos 500/5000/30000 | **feito**: `game_settings.novice_fund` (inglês), 4640 no login só a partir do nível 6 |
| guia de 7 dias (4638) | `beginTime` = conclusão da missão 130 | **feito**: 4638 no login só depois da 130 e na conclusão dela |

Correlações:
- 2031201 (VIP Trial Card) ↔ texto "Your VIP service has been extended N hours; new expiration date is AAAA-MM-DD." (#3260);
- 208015 (VIP Token, SonType 292) ↔ fichas da roleta: `needVipItem` 1 → 3 e 5 → 2 fichas em dois giros (#3325-#3335);
- `TimeDrop` ↔ texto do baú: "Received: 50,000 Gold, Moderate HP Pack x1", da última linha para a primeira (#2110), e "Reward retrieval successful!";
- comparados, sem mudança (eventos datados do servidor, não do personagem): 4590 `param1` 2059 = botão do
  cartão de super login (2026-10-23 a 10-30, #110); 4612 = "钻石矿脉" `activeType` 1 até 10-18 (#86); 4422 =
  lista de chaves (`switchType` 3031 a partir de 10-26, #89); 4251 = "Level up and get rewards" da abertura
  do servidor (#84). 4475: só os títulos/textos dos tipos 13/14 de `data/events.json` foram para o inglês.
