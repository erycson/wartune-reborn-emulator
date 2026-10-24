# Checklist: servidor 100% pelo cliente inglês

Regra: o cliente inglês (S134, `D:\xampp\htdocs\wartune\decomp`) e a captura inglesa (`captures/tutorial_en.json`)
mandam. O turco só ajuda quando o inglês não tem a resposta. Cada item é conferido no cliente inglês antes de
ser marcado. Ordem de trabalho: de cima para baixo, um item por vez.

## 0. Base

- [x] `.proto` e `opcodes.json` gerados do cliente inglês (`decomp/2`, `m3`..`m18`, `Loading`); `ShopMainRspMsg.flag` (4238) bate com a captura
- [x] 8301 (`PlayerNodeStateMsg`) como caso especial do `scan_opcodes.py` (o envio passa `param1:Message`)
- [x] READMEs e `ferramentas.md` apontam para o cliente e o espelho inglês; aviso de não rodar `build_cdn_overrides.py` no espelho
- [x] Espelho: 11 páginas "403 Forbidden" do nginx salvas como arquivo, retiradas (ficaram no rascunho da sessão)

## 1. Correções da revisão por sistema (cliente inglês × servidor)

Preenchido com os achados da revisão de cada sistema.

- [x] Itens, mochila, lojas, forja, moda, mercado
- [x] Social, chat, correio, casamento, guilda
- [x] Castelo, fazenda, cidade externa, minas, veículos
- [x] Herói, exército, pets, estrelas, montaria, cartas, batalha
- [x] Eventos, VIP, minigames, labirinto de gemas, ofertas
- [x] Login, HTTP, tutorial, missões, campanhas, salas, chefe do mundo, PvP, cidade do céu

## 2. Configuração

- [x] Fuso do jogo: UTC padrão, configurável (`WARTUNE_GAME_TIMEZONE` no `.env`); testes sem o fuso turco
- [x] Limite diário de compra do leilão configurável (`game_settings`)

## 3. Opcodes que o cliente inglês envia e o servidor não trata

- [x] 5028 `U_C_CAMPAIGN_ROOM_INVITE` (convidar para a sala)
- [x] 5034 `U_C_CAMPAIGN_ROOM_EDIT` (editar sala)
- [x] 5036 `U_C_PLAYER_READY_STATE` (pronto)
- [x] 5037 `U_C_ROOM_STATE` (estado da sala)
- [x] 8344 `C_ROOM_PWDCHANGE` (senha da sala, `RoomEditMsg`)
- [x] 8296 `C_ENTER_TOWER` (`EnterTowerInfoMsg`): entra no andar (`game/maze.py`, `handlers/tower.py`)
- [x] 8299 `C_TOWER_RESET` (`TowerInfoReqMsg`)
- [x] 8599 `C_CHECK_WARFIELD_COUNT` (`CampaignReqMsg`): fechado com o campo de batalha (`pvp.md`)
- [x] 8610 `C_VEHICLE_LEAVE_CAMPAIGN`
- [x] 8615 `C_VEHICLE_MOVE` (`VehicleMoveMsg`)
- [x] 8616 `C_VEHICLE_ATTACK` (`VehicleAttackReqMsg`)
- [x] 8617 `C_VEHICLE_PICK_PROP` (`VehiclePickPropMsg`): 8610/8615-8617 da cena VEHICLE, feitos com a batalha (m17, `diversos.md`)

## 4. Respostas que o cliente inglês escuta (conferir se o servidor manda quando deve)

- [x] 49 renomear guilda · 4170 busca de jogador · 4161 lista de convite da sala · 4192 sala individual falhou
  - 49 e 4170 já iam; 4161 é a resposta do 5027 (aba Hall do `RoomInviteFrame`, agora feito); 4192: o `CampaignInfoView.__createFailHandler` é vazio, nada a mandar
- [x] 86 fortalecer · 89 compor · 4258 refino sorteado · 4260 decompor · 4368 refino aplicado · 4558 reforço de equipamento de mascote (8644) · 4487 moda (compor)
  - tipos conferidos com o `opcodes.json`; o 4558 espera o equipamento de mascote (m14, seção 5) e o 4487 a regra da composição de moda (não está no cliente)
- [x] 106 colher árvore · 146 colheita · 4189 colheita da árvore · 4190 amigos que podem regar (`farm.py`)
- [x] 125 criar campanha · 4474 nós NPC do veículo · 4513/4514/4517–4525 campanha de veículos
  - o 125 vai na entrada das masmorras (5039) e da batalha de veículos; 4474/4513/4514/4517–4525 feitos com o m17

## 5. Telas novas do cliente inglês (556 classes que o turco não tinha)

Cada módulo: ler as classes inteiras, listar o que a tela pede ao servidor e o que lê, implementar o que faltar.

- [x] m6 guilda (73): janelas da guilda, recrutamento, permissões, renomear, transferir, subir nível, e-mail da guilda
  - feitos: eventos em partes `|` pelo tipo (migração 0046), eleição (`isVotingman` = candidato, `votingTime` da própria linha, estados 3/4), VIP na lista de membros (online), nome de 4 a 10 e renomear grátis com "!", candidatura velha devolve o 40, baú com 10 por membro, armazém (bolsa 6), `gradeOrder`, custo de sair pagando (`Consortia_ClearCD_Point`), bênção trocando o prêmio pendente
  - precisa captura: bênção ×10, manutenção semanal sem riqueza, acelerar (`ceil(t/600)` × 4 no cliente), anúncio de recrutamento, mapas do altar do demônio/terra secreta, guerra entre servidores, `isReceived` do baú
- [x] m7 leilão (49), fazenda (15), rega e árvore do casamento (11)
  - feitos: a troca por pontos da misteriosa (ShopType 7) não é vendida sem pontos (`shop.price`); as ops de mascote da fazenda recusadas não mandam mais o 4387 de terra de plantio; custo de atualizar a misteriosa (45) corrigido no `itens.md`
  - precisa captura: cultivo e guarda de mascote na fazenda (ops 12–16), pontos ganhos na misteriosa, texto do registro da rega (145), compradores da sorte (4470), árvore do casal (chance de praga, valor do cultivo)
  - leilão: itens revisados (8448–8457, `docs/mercado.md`); venda de Sylph feita (8448 `sellType` 2, item −900 com o pet no `property1`, `pets.held`, 5022 para a lista de pets, cancelar; migração 0049). Falta um jeito de ganhar pet livre
- [x] m9 salas PvE/PvP e listas (40), lordes e lordes casados (29), casamento: renda, qualidade, sala, pedido (25), veículos/daimon (14), labirinto e ordem (5), gancho (2)
  - feitos: `roomState` 1 nas salas, 8465 → 4370 (sala clicada, busca e entrada rápida com `roomId` 0), filtro do 5026 pela campanha, 8295 com as 9 salas do gancho (7001–7009, sem o TypeError do `HookItem`), aba 1 do labirinto = 8101, convite rápido 8353 (corneta + link da sala no canal mundo)
  - precisa captura: recusa do 8465 (sala inexistente) e do 5039, campanha em grupo com 2 jogadores, mapa do gancho, PvP em equipe, formato oficial do 8353, sala de casamento; sala de veículo feita com o m17
  - casamento: 357 `MarriageDataMsg` e o 4657 completo (satisfação, aliança op 12, missões 8774, jogo do coração 8802, sala 8760 com 4662/4673/4674/4672); relatório da revisão em `consulta/revisoes/relatorio_casamento.md` (fora do git), seção "Não implementado"
- [x] m12 amigos, achar amigo, IM, chat em grupo (37)
  - feitos: 4455 do VIP para a guilda online (`vip_changed`), aviso do grupo no direito 3 do 8544
  - precisa captura: 4246 (convites da barra) × 84, pedido de amizade com o alvo offline, presente de rosa (SonType 217), resposta automática do IM
- [x] m13 coliseu (7), escolher campanha (7), chefe do mundo e PvP do chefe (8), guerra individual (1)
  - feitos: `forward` negativo quando a posição cai, moda no `avater` do 4169, `challengeorder.xml` e `fight.xml` gerados pelo servidor (`game/rankings.py`, `WARTUNE_RANKING_XML_DIR`)
  - precisa captura: conteúdo das outras campanhas e do modo herói, varredura (8528), dublê do chefe (8526/4422 switch 22), campo de batalha
- [x] m14 pets: equipamento, avançado, atributos, compor, aprender skill, desafio, chefe (75); montarias (11); forja: compor, refino, fortalecer, decompor, trocar, montaria (20); moda (4)
  - montarias: estrela (op 6) feita; 7–12 e 8843 sem tela ou sem dado no cliente inglês (ver `heroi-exercito.md`)
  - pets: avanço (op 4), aprender skill (5), encantar aptidão (7) e a trava do compor feitos (migração 0051); 8 e 15 sem chamador
  - feitos: equipamento de mascote na bolsa 26 (`bag*` no 4540, vincula item e mascote, migração 0047), forja do equipamento de mascote (8644 encantar com bênção, 5153 avanço Types 10 e do herói Types 5, Divinity Soul e Soul Socketing Rod, refino com pedras compradas), EXP do mascote pela tabela 25 (`curGp` dentro do nível, teto no herói), devorar (op 1) e sacrifício (op 6), ativar pede nível e vincula, skills do torneio (8726), recusa do 8340 sem 4260
  - montarias: ativar com a carta ou Balens (op 4), voo com Flystone (op 13), carta de montaria no 5006 (SonType 218, temporária soma dias), Beast Soul Lvl dá a `ActiveObject` (migração 0048)
  - precisa captura: chance da bênção do avanço, ganho do Sepulcrum, sorteio da skill aleatória, bênção e chance da estrela de montaria; chefe da ilha dos Sylphs (o cliente não manda nada: só o 4686 do servidor, com mapa, chefe e fúria que não temos; o login manda fechado); resultado do compor e da avaliação de moda (8594, 8781)
- [x] m17 campanha de veículos (109)
  - feitos: janela pelo `MatchOfVehicleTime` (4512 no relógio), fila solo (8608/8609, 4525) e da sala de veículo (5023 tipo 2, 5039, 5037), entrada (125, 4474, 4517, 4518, 4513), andar no mapa 3001 (`tools/extract_vehicle_map.py`), skills de alvo/área/armadilha/em si, buffs (4522), caixas (8617, 4521), revive geral, chefe aos 300 s (4524), fim (4514) com prêmio uma vez por janela pelo correio e o 4515 (`isFirst`)
  - precisa captura (inventado, `ponytail` em `game/vehicles.py`): dano, pontos, quantas caixas e quais skills, o chefe, tamanho mínimo da partida, quantidades do prêmio e a EXP do tanque
- [x] m18 médico e avisos (5): só HTTP (`crossdomain.xml` e `version.xml` existem no espelho); m8 é o painel de depuração do tutorial e os opcodes dele já têm handler

## 6. Legado turco

- [x] Ferramentas da CDN turca (`export_captures.py`, `build_cdn_overrides.py`) e `data/overlay` fora do repositório (`consulta/legado-turco/`)
- [x] Amostras e citações turcas nos testes e docs: trocar pelo inglês; o que não tiver inglês vira pasta de consulta fora do git
  - amostras do .proto já da inglesa (8 opcodes só turcos); caminhos do cliente turco nos docs → `decomp` inglês; `missoes-revisao.md` (retrato antigo) → `consulta/revisoes/`; as marcas "só turco" que ficam são de dados que a inglesa não tem
- [x] `docs/fontes-turcas.md` revisado item a item

## 7. Revisão final

- [ ] Varredura de novo (`scan_opcodes.py`, cobertura C>S, inventário das classes novas) sem nada faltando
- [ ] Suíte inteira, ruff e mypy
