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

## Campanhas novas

| mapa | campanha | situação |
|---|---|---|
| 1011, 1021 Worg Lair | 1001 | temos (`dungeon_1001.json`, captura turca) |
| 1131→1132, 1141→1142 Baylon Plains | 1002 | **nova**: pares de mapas, relatório (137) e cartas (135) só no segundo |
| 6001 Resource Quarry | 6001 | **nova**: 8258 entra, 5032 `cmd:2` coleta madeira, 8699 luta. Hoje recusada (`handlers/worldboss.py`) e trava a missão 102 |

`tools/extract_dungeon.py` está preso à 1001 e ao turco (`exp_text` termina em "EXP kazanıldı";
em inglês é "Received 630 EXP "). O servidor também: `DUNGEON_CAMPAIGN = 1001`, o 5039 ignora o id
pedido e a mensagem de entrada é turca (oficial: "Entered [Worg Lair] and deducted 20 stamina.").

Fim de masmorra (#2700-#2731): 4382, 3, 137, 4151, 83, 20, 135, 112, 4165, 150×2, 140; carta: 5122 →
115, 26, 83; saída 5180 → 134. 137: notas 1=D … 5=S (prováveis limites `StandardDamage`,
`StandardHurt`, `StandSecond` do CampaignInfo), `totalGp` ≈ BaseGp × 1,05. A 1002 deu 2040102, que
não está no `CampaignInfo.Item`: o sorteio real é do servidor.

Karda (GameHeroTempInfo 1023) tem `RejectType="19,100,38,39"` (19 = imune a atordoamento); o
cliente desenha sozinho. Nossa batalha ainda não tem efeitos de controle.

## Missões (10 → 130, todas na captura)

Recompensas batem com `QuestTempInfo`/`QuestGoods`. Diferenças nossas:
- textos turcos ("EXP kazanıldı", "Kazanılan:", "Çantanız dolu."); oficial: "Received 3,000 EXP ",
  "Received: X x1";
- 112 de progresso antes da entrega só nos tipos 23, 2 e 10; no tipo 23 o `condition_1` vira o
  `noviceProcess`; tipos 27/32 deixam `condition` 0;
- 150 na entrega só quando sobe de nível;
- a missão 10 nasce com o personagem (o oficial nunca recebe 5012 dela);
- diária vista: 863 (tipo 63, VIP, nível 10), aceita pelo cliente.

## Novato, VIP e eventos

| sistema | captura | nós |
|---|---|---|
| baú online (`TimeDrop`, minutos) | contagem começa no 1º 5019 e zera a cada resgate; resgate manda 111, 4250, 4, 83×2 | conta segundos do dia; faltam as notificações |
| EXP +100% | 4247 `rateInfo{rate:100, beginDay, endDay}`: evento do servidor por datas | falta |
| cartão VIP de teste 2031201 (`Property1=12`, 1 h) | 5006 → 111, 4410 `vipType:2` | falta |
| VipInfo no login | `takeGiftDate` = criação | próxima segunda |
| presente semanal VIP (`VipDrop`) | 8505 → 115, 111, 4410, 4539, 83; próximo em 10-26 | igual, falta 4539, data diferente |
| roleta VIP (8521/8519) | 18 prêmios em #3325 (só na captura, sem probabilidades) | 4414 vazio |
| chat World | 111 "Requires character Level of 20" | nível 6 calado; `leed_done` duplicado |
| anúncio Sylph Atoll | 83 canal 12 `isCenterTip` | falta |
| fundo novato (4640) | custos 500/5000/30000 | valores turcos em `data/events.json` |
| guia de 7 dias (4638) | `beginTime` = conclusão da missão 130 | `created_at`, no login |
