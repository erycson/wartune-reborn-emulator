# Plano: fechar todas as pendências

Ordem pedida pelo dono (2026-10-23): nada fica sem implementação. Dado que falta sai, nesta ordem, de
1. cliente (`decompiled/`), 2. replay/capturas, 3. internet, 4. inventado. O inventado leva
`# TODO(inventado): <o quê>` no código (`grep -rn "TODO(inventado)" src`) e entra na lista do fim de
[pendencias.md](pendencias.md). Regras tiradas de evidência real seguem como `(dedução)`; atalhos de engenharia
(busca linear, lock, agendador de 60 s) seguem `ponytail:`.

Status: `[ ]` a fazer, `[x]` feito (commit), `[~]` em andamento. Fonte: C cliente, R replay, I internet, X inventado.

## 1. Contrato do rei e VIP
- [ ] Varredura/Blitz 8528 + progresso de campanha (MopupManager; custos ConfigInfos) → Free Blitz (5)
- [ ] Gancho / Altar of Ennoblement: ganho offline (HookContorler/HookFrame) → Lord of Time (4), leed 22
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
- [ ] randomSkill (RandomSkillCount) em itens novos e recompensas
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
- [ ] exércitos alheios (169/4167/4168), terras selvagens, robôs, castelos Köy, 5160 contra castelo/exército, 8488, 5004
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
- [ ] pets da fazenda 15044 ops 10-16; offline x1,5/x2 8287; 8255, 8562 trégua, 5179; bônus de guilda no rendimento

## 13. PvP
- [ ] lordes 8710-8721, lordes casados 8975-8981, campo de guerra 8332-8338, campo de minas 8633, 8635

## 14. Social e protocolo
- [ ] canal de time (6); opcode 2 do tutorial; 150 ×2; 363/364; 4156 maxPage; 4544; 4248 state 2; ENEMY_CAST_MS por skill

## 15. `ponytail:` do código
- [ ] classificar os 138: comportamento faltando (implementar), dado inventado (TODO(inventado)), atalho (fica)
