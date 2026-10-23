# Plano: fechar todas as pendências

Ordem pedida pelo dono (2026-10-23): nada fica sem implementação. Dado que falta sai, nesta ordem, de
1. cliente (`decompiled/`), 2. replay/capturas, 3. internet, 4. inventado. O inventado leva
`# TODO(inventado): <o quê>` no código (`grep -rn "TODO(inventado)" src`) e entra na lista do fim de
[pendencias.md](pendencias.md). Regras tiradas de evidência real seguem como `(dedução)`; atalhos de engenharia
(busca linear, lock, agendador de 60 s) seguem `ponytail:`.

Status: `[ ]` a fazer, `[x]` feito (commit), `[~]` em andamento. Fonte: C cliente, R replay, I internet, X inventado.

## 1. Contrato do rei e VIP
- [x] Varredura/Blitz 8528 de campanha (Free Blitz 5). Labirinto: junto do progresso do labirinto (seção 4)
- [x] Rest House / Altar of Ennoblement (estátuas, tiques, aceleração, Lord of Time 4, leed 22)
- [ ] PK na Rest House (8525/4421, BattleType 19)
- [x] Buff 7 (+10% nas masmorras, Catacombs, Necropolis) na batalha
- [x] Power of Healing: o 83 com contrato → marcar TODO(inventado)
- [ ] VIP: montaria exclusiva, missões diárias VIP, baús de masmorra VIP, privilégios 7 e 8 (VipPrivilegeFrame)
- [ ] Cota de cornetas VIP (vip_bugle_bonus)
- [ ] vipGp diário (Vip_DailyAddGp por dia), vencimento do VIP avisando a guilda, vipType 1

## 2. Gravar outro personagem (offline)
- [ ] serviço para mudar snapshot de outro jogador (online ou offline)
- [ ] presente de VIP (8513), de contrato (8540), da loja (`receiveId`), entrega pelo correio na compra
- [ ] mochila cheia na loja → correio (resultado 12)

## 3. Restos da captura oficial_20261023
- [ ] Tesouro tipo 22 (battleType 3, guardas 6014)
- [ ] Minas no mapa global (nomes "Autaric Plains(x,y)")
- [ ] Alvo aleatório na batalha (oráculo KNOWN_EXTRA)
- [ ] Títulos 4484 / 8597 (conquistas)

## 4. Itens e loja
- [ ] Refino da forja: peso por nível
- [ ] Avaliação de moda 8781 e composição 8594
- [x] randomSkill (RandomSkillCount) em itens novos e recompensas
- [ ] Teto diário de Beden/EXP de itens
- [ ] Lojas pagas com pontuação (lordes, guerra de guildas, cristal de fada, volta de jogador)
- [ ] Progresso do labirinto (andar e recorde) para a loja 4 e o tower

## 5. Minigames e eventos
- [ ] Quiz 9501, estrada dourada 9520-9522, pesca/caça/minério 9507/9502/9645
- [ ] Loteria, caça-níquel, cadeiras, caixa de ano novo, história, sorteio de grupo
- [ ] Recuperar EXP 9503 (participação do dia por sistema)
- [ ] Troca da sorte 9610; labirinto de gemas: nível, ajuda de amigo, ranking semanal
- [ ] 8518 contadores do painel; quadro 8291/8298/8729; SumActive tipos em status 3
- [ ] Devoção: 13, 22, 23, 27, 28

## 6. Chefe do mundo
- [ ] buff 8470 e dublê 8526; 4435; vida pelo nível; 8264 do altar da guilda

## 7. Salas e masmorras
- [ ] persistência de times; gasto da entrada multi
- [ ] 1001: 5180, cartas pagas, recusa sem Beden, missões, progresso salvo, chance da carta
- [ ] Pandora: recompensa; 5121; 5038 de todos os mapas
- [ ] Torre 8297/8300/8296 com progresso; guarda de batalha 8742 (gemas); pedágio 8752-8755
- [ ] 5027, 8740

## 8. Cidade externa
- [ ] exércitos alheios (169/4167/4168), 5160 contra castelo/exército de jogador, 8488, 5004 (feito: terras/minas do
  mundo, robôs, castelos NPC "Köy")
- [ ] monstros: prêmio, luta em equipe; mapa do tesouro 8744; passe 8636/8637; ametista 30000; 8699, 8745, 8535

## 9. Mercado
- [ ] mascote no leilão; cartas oficiais; ordenação 8450/8457; reempilhar; validade do correio

## 10. Guilda
- [ ] altar 7601, terra secreta 7501, guerra 4501, entre servidores 4601; rankings/add_to_box
- [ ] bênção: tabela e x10; eleição com relógio; 8335 recrutamento; prêmio da bênção ao sair

## 11. Herói, pets, montaria
- [ ] fusão de pets 117-119; crescimento/skills/treino/resistência
- [ ] montaria: estrelas, rei, loja, refino, voo (8529, 8843); vocação 8643; destino 2100/2200
- [ ] cartas de poder na batalha; dragão; posição em salas e teleporte 8277/8278/8326

## 12. Castelo e fazenda
- [ ] pets da fazenda 15044 ops 10-16; offline x1,5/x2 8287; 8255, 8562 trégua; bônus de guilda no rendimento

## 13. PvP
- [ ] lordes 8710-8721, lordes casados 8975-8981, campo de guerra 8332-8338, campo de minas 8633, 8635

## 14. Social e protocolo
- [ ] canal de time (6); opcode 2 do tutorial; 150 ×2; 363/364; 4156 maxPage; 4544; 4248 state 2; ENEMY_CAST_MS por skill

## 15. `ponytail:` do código
- [ ] classificar os 138: comportamento faltando (implementar), dado inventado (TODO(inventado)), atalho (fica)

## Notas de pesquisa (cliente) para os itens abertos

### Rest House / Altar of Ennoblement (gancho): devolve estamina, não EXP
- Entrar: 8258 `WorldBossMsg.param1` = 7001..7009 (Campaigns Types 3, MapInfo 1500x900, nível 1-50). Mapa 7000-7100 =
  sala do gancho (`WorldBossHelper`). 4204 `maxCount` decide "Full" (`curCount >= maxCount/2`).
- Estátua: nó `types` 111 (`PosType.HOOK_NODE`); clique = 5033; o servidor responde 29 `CampaignConfirmMsg`
  (`type` fora de {0,2,3,4,5,6,10..14,17,21,22}, ex. 7) que abre `HookAlertFrame`; "Begin" = 5033 `paraBool1` true.
- Estado: 4199 (`leftWeay`, na entrada, antes da view), 4206 `PlayerHangupStateListMsg{armyId,state>0}` (desenha
  `images/hook/<state>.png`), 4200 (início/fim: `isStartHangup`, `addWeay`), 4235 a cada tique (+1, `addWeay` 1).
  Tempo na tela = `leftWeay` × 120 s. 8292 cancela (guarda o que falta), 8293 `payType` acelera:
  `min(leftWeay, 200 - weary)` Balens (1 por estamina); grátis com contrato 4 (o cliente manda `payType` 0).
  Sair: 5025. PK: 8525 op 1/2/3, S>C 4421, BattleType 19. Abre no nível 21 (`OpenGradesII.HOOK`), prédio 150401.
- `DataResetMsg` tem `hangupCount` (2) e `leftHangupWeary` (6); o cliente não lê. Teto diário: sem fonte (inventar).
- Textos ingleses: `map.campaign.view.ui.HookTimeView.chatData.msg` "Restored 1 Stamina through cultivation.";
  HookAlertFrame title "Divine Statue", text "Welcome to the land of ancient spirits! Here you can receive bonus
  Stamina, would you like to get started?".

### VIP (VipPrerogativeTempInfo) ainda abertos
- 1 CASTLE_VIEW: `BaseCastleMsg.vipCastleView` (16) = para1 (1, VIP9 2) no 4153 e nos castelos do mapa; 17 = vipType.
- 7 kyanite no saque de castelo: +para1 cristais ao atacante na vitória (só servidor).
- 11 astro 1 clique: 8269 `StarRandReqMsg.site` -1 → VIP 4+, repete captura (ouro) até 16 na lista temporária ou
  acabar o ouro, vende as brancas; responde 4180.
- 12 missões VIP: `QuestTempInfo.TemplateType` 3 (21, 22, 863); o cliente pede pelo 5012 até sem VIP: o servidor
  recusa sem VIP.
- 15 honra no campo de batalha: perda × (100 - para1)% (4269 `WarMovieMsg.geste`), depende do campo de batalha.
- 17 bênção em 1 clique (guilda 5145 `param1`): VIP 6+; o valor de "todas" não está no decompilado.
- 18 pular luta de fadas: 8727 com VIP 3+ (já feito em arena.py).
- 19 montaria VIP: `MountTempInfo` MountType 3 = 1116 "Panda Guardian"; VIP + nível 40 → avatar no 4427 e 4610
  `param7` true; VIP vencido → 4610 false e tira a montaria.
- 20 baú VIP na masmorra: nenhum campo no cliente (inferência: carta a mais no 135 para VIP).
