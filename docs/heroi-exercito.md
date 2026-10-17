# Herói e exército

Tropas, skills, talento, runas, montaria, estrelas (kader), destino, alma do dragão, cartas de poder
e pets. Fonte de cada resposta: *(visto)* = captura oficial, *(cliente)* = código do cliente
(`D:/wartune/decompiled/m2/scripts`), *(dedução)* = sem captura nem código, marcado `ponytail:`.
As capturas só têm pacotes S>C; os campos dos pedidos vêm do cliente.

Código: `game/handlers/army.py`, `hero.py`, `stars.py`, `systems.py`, `pets.py`; regras puras em
`game/rules.py`; mensagens em `game/builders/army.py` e `builders/login.py`.
Testes: `tests/game/test_heroi_exercito.py`.

## Estado

| Tabela | O que guarda |
|---|---|
| `pawns` | uma linha por tipo de tropa: castelo, exército, especialidade, bênção, posição |
| `stars` | estrelas: sacola (0 temporária, 1 mochila, 2 equipadas), posição, grau, EXP, trava |
| `pets` | pets: pontos, aptidões, batalha, skills, atalhos, ordem |
| `player_systems` | uma linha por personagem: montaria, destino, dragão, cristais/moeda das estrelas, cartas, vagas de pet |
| `heroes` (colunas novas) | talento, runas, segundo conjunto de skills |

Migração: `0003_tropas_estrelas_pets_e_sistemas_do_heroi` (quem integrar renumera, se outro ramo
também criou uma 0003). `CharacterService.snapshot` cria `player_systems` em memória quando falta;
ela é gravada no primeiro `save` que a inclui.

## Atributos do herói

`rules.leader_stats` = herói + equipamentos + **estrelas equipadas** (coluna × grau) + **montaria**
(template + 5 × grau de cada atributo, UpGrade Types 18; bate com o login: 1610 de EXP = 65 de força).
Talento, runas, destino, dragão e cartas são skills/buffs nos templates, não atributo fixo.

**Para a batalha:** `rules.battle_pawn(snap, templates) -> (linha de PawnTempInfos, quantidade) | None`
devolve a tropa que luta com o herói. Os atributos de cada soldado são as colunas Attack, Defence,
MagicAttack, MagicDefence, Live, ForceHit e Parry do template (o mesmo que vai em `pawnLive`).
O `battle.py` ainda não lê.

## Opcodes

### Tropas

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 5155 recrutar | 109, 112 (missões), 109, 100, 111 | visto (relay #643) | ouro = ⌈n·GoldConsume·(100−Property4 do quartel)/100⌉; quartel ≥ NeedBuilding; população da casa (1201) |
| 5156 pôr no exército | 150, 93, 100 | visto | um slot; total ≤ liderança (ConatArmy) |
| 5157 dispensar | 100, 109 | dedução | |
| 5158 evoluir | 3, 116, 150, 109 (+112) | visto | Ruh de UpGrade Types 1; quartel ≥ nível seguinte; nível < herói − 3 |
| 8580 trocar tipo | 3, 116, 116, 150 | cliente | 200 diamantes (payType 3 = vinculado) ou 2M de Ruh |
| 8455 compreender | 3, 116 (+112) | cliente | 1M de Ruh; sorteio por TakeRandom; bênção Types 16 (dedução) |
| 8456 salvar especialidade | 116, 150 | cliente | |
| 8276 formação | 150 (+112, missão 34) | visto | |
| 8277 / 8278 formação de campanha | 4186 | cliente | só a posição do próprio herói (dedução: salas) |
| 8326 teleporte | 4237, 3 / 4263 | cliente | 100 de energia ou 100 diamantes; posição não persiste (depende da cidade externa) |
| 8328 posição do exército | 4241 | cliente | |

### Herói, skills, talento, runas

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 5185 aprender skill/talento | 150, 60 | visto (#1175) | pontos = nível/2 − graus gastos; talento por TalentTempInfos |
| 5184 resetar skills | 61, 150 (+3) | cliente | grátis abaixo do 25 |
| 5187 subir talento | 4430, 4431, 3, 109 | cliente | ouro e EXP do jogador (dedução: desconta gp e totalGp) |
| 8479 abrir 2º conjunto | 150, 3 | cliente | Second_SkillPoint diamantes |
| 8480 trocar conjunto | 150 | cliente | |
| 5170 redistribuir atributos | 150 | cliente | os pontos são automáticos por nível: sem efeito |
| 5018 caixa de novato | — | cliente | o cliente nunca chama: só log |
| 8548 luta de guerra de guildas | — | cliente | depende de GvG: só log |
| 8605 runas | 115, 4495, 150 (op 3: só 4495) | cliente | op 1 aprende (livro SonType 302), 2 sobe (item 3020010 = 50 EXP, ou 2 diamantes), 3 equipa (2 espaços no 40) |

### Estrelas (kader) — `stars.py`, captura `kader_sistemi.json`

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 8269 sortear | 109, 3, 4180 | visto | cristais 4000/5000/6000/8000/10000 de ouro; 1 grátis por dia; cristal usado apaga (o 0 nunca); -1 = rápido (≥ 20000 de ouro). **Chances e abertura do próximo cristal: dedução** |
| 8268 recolher | 109 + 4179 (vendidas, bagType −1), 4178 + 4179 (recolhidas), 3 | visto | lixo (Profile 1) vende por SellGold; fonte de energia (6) vira StarPoint (dedução) |
| 8267 mover/equipar/devorar | 4178 (+150) | visto | equipadas: min(8, nível/10), sem repetir MasterType; `eat` = destino devora a movida |
| 8331 compor | 109, 4479 (temporária) / 4178 (mochila) | visto | devora tudo que não está travado; EXP = SellGp + graus + gp; tabela por Profile (Types 9-13, 22), grau máx. 10 |
| 8330 travar | 4180 / 4178 (+112) | cliente | missão 53 |
| 8270 comprar espaço | 3 | cliente | (comprados/4 + 1) × 100 diamantes; 1 espaço por compra (dedução) |
| 8325 virada do dia | 3 | cliente | renova o sorteio grátis |
| 8341 loja | 4178, 3 | cliente | preço = StarPoint do template |
| 8224 `star` | 4178, 4180 | visto (login #51-52) | |

### Montaria, destino, dragão, cartas — `systems.py`

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 8530 lista | 4427, 4426 | visto (login #11-12) | soulScore = soma de SoulScore |
| 8529 op 1 treinar | 115, 3, 150, 4426 | visto | `propertyType` 0 força, 2 int., 5 físico, 1 agilidade (PropertyInfo); `param1` unidades de comida 208017 ou Mount_Point diamantes; 10 de EXP cada; teto = grau levelMax |
| 8529 op 2 montar | 4426, 150 | cliente | precisa possuir |
| 8529 op 5 ver de outro | 4459 | cliente | só jogador online |
| 8529 demais ops | — | **parcial** | estrela/bênção, rei, loja, refino, voo: UI não descompilada |
| 8843 evento de montaria | — | **parcial** | sem captura |
| 8628 destino | 4544 | visto (login #34) | abre no 55 com os tipos 2000 e 3000; 2100/2200: não sabemos abrir |
| 8626 treinar destino | 115, 4544 | cliente | pedras SonType 307; **1 EXP por pedra: dedução**; graus por Types 26 (acumulado) |
| 8627 roda | 4545, 115 (+3) | cliente | Fate_FreeCount grátis, depois 10, 20, 30… e 300 do 30º; prêmios 1/2/3/4/10 pedras com pesos das fatias (dedução) |
| 8642 dragão | 4555 | visto (login #37) | abre no 40 |
| 8641 alimentar | 115, 4555 | cliente | item SonType 319, 1 EXP; Types 101 por grau; grau máx. pelo nível (40→1 … 80→5) |
| 8643 transferência | 4556, 4557 | cliente | grau 5 → tipo 102; **vocação: parcial** |
| 9505 cartas | 4905 | visto (login #76) | op 1 sobe (Types 29+Profile), 2 ativa todas, 3 reenvia; buf = BufId + grau − 1. **Cartas/EXP vêm das batalhas (4902): parcial** |
| 8224 `powcardInfo` | 4905 | visto | |

### Pets — `pets.py`

| C>S | Resposta | Fonte | Regra |
|---|---|---|---|
| 8621 op 2 pontos | 4540 | cliente | soma ≤ pontos livres (**5 por nível: dedução**) |
| 8621 op 3 zerar | 4540, 3 | cliente | pet_reset_att diamantes |
| 8621 op 9 / 10 batalha / descanso | 4540 | cliente | um pet na batalha |
| 8621 op 11 atalhos | 4540 | dedução | string em `petName` |
| 8621 op 12 vaga | 4540, 3 | cliente | add_pet_count por compra; base 3 (login: petCount 6) |
| 8621 op 14 topo | 4540 | cliente | |
| 8621 op 13 compor (um pet) | 4540, 115, 109 | cliente + template | receita de `PetComponseInfos` com `Pet2Types` 0 casa com (`PetType`, `NeedGrade` = tier, `Quality` = estrela) do template do pet; o template passa a ser o do resultado; gasta `NeedItemTempId*` e `NeedGold`. Nível, EXP, pontos, aptidões, skills e qualidade ficam (**dedução**). 24 de 28 receitas; 19, 26, 29 e 32 dão tipos 117–119, sem template: recusadas |
| 8621 op 15 fusão de dois pets | — | template | as 6 receitas dão tipos 117–119 e pedem itens (2125126, 2125127, 2125128, 2125130, 2125134) que não estão em `ItemTempInfos`: sem resposta (log) |
| 8621 ops 1, 4–8 | — | **sem dado** | devorar (1), crescimento (4), skills (5), sacrifício (6), aptidão (7), resistência (8). Tabelas que existem: `UpGradeTempInfos` tipo 25 (EXP por nível), tipos 27/29/107 (EXP de qualidade), `PetTempInfos.PowerApt` (mín,máx). Falta o ganho por item ou ação, que o cliente não informa |
| 8702 pets de outro | 4608 | cliente | só jogador online |
| login (8224 `army`) | 4540 | visto (login #30) | só quando há pet |

Atributos derivados do pet (força etc. = template + pontos + nível × aptidão/100) e o HP são
aproximação: o cliente não calcula e a captura não fecha com fórmula simples.

## Carga do login

Enviados: 100 (tropas, no `user`), 150 com `mountTempId` e o pet em batalha (`petTempId`, `petQuqlity`, `petName`, como no login #5), 4540 (flag `army`, só com pet), 4178 + 4180 (`star`), 4905 (`powcardInfo`); 4427/4426, 4544 e 4555 respondem aos pedidos 8530, 8628 e 8642 que o cliente faz sozinho. O sorteio grátis das estrelas vira às 5h e é recalculado em toda leitura (`rules.refresh_star_day`), então quem estava offline no 8325 não perde.

Não enviados: 4495 do login (#40 é `{opType 0, opResult false, count 0}`; o `ArmyManager.__runeOperateHandler` não faz nada com isso) e 4902 (bônus das cartas por campType na batalha; o `MagicCardManager` só guarda — depende da batalha).

## Dependências

- Ganhar montaria, pet e cartas: uso de item / missões / batalha (outros módulos).
- Batalha: ler `rules.battle_pawn` e os buffs de talento, runas, destino e cartas.
- Cidade externa: posição do teleporte (8326).
- `castle_yield` usa `rules.population` (sobrepõe com o módulo do castelo).
