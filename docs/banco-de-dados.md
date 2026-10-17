# Banco de dados

SQLAlchemy 2 async com mapeamento imperativo: as entidades de `domain/models.py` são dataclasses
puras, e as tabelas ficam em `persistence/schema.py`. Funciona com:

| Banco | URL (`WARTUNE_DATABASE_URL`) |
|---|---|
| SQLite (padrão) | `sqlite+aiosqlite:///data/wartune.db` |
| MySQL / MariaDB | `mysql+asyncmy://usuario:senha@host:3306/wartune` |
| PostgreSQL | `postgresql+asyncpg://usuario:senha@host:5432/wartune` |

No SQLite o servidor liga `foreign_keys`, `journal_mode=WAL` e `busy_timeout`. O schema é criado e
migrado no início ou com `wartune-server db init` (ver Migrações). Todas as datas são gravadas em UTC.

## Modelo

```
accounts 1───* characters *───1 game_servers
   │              │ 1
   │              ├──* heroes
   │              ├──* buildings
   │              ├──* quests
   │              ├──* items
   │              ├──* shop_buys, fashion_books, cash_ledger
   │              ├──1 mystery_shops
   │              └──1 castles
   └──* play_tickets *───1 game_servers
```

Uma **conta** é global, e um **personagem** existe por (conta, servidor). Assim, o mesmo usuário
pode jogar em vários servidores com um personagem diferente em cada um. O `characters.id` é o
`playerId`/`userId` que o cliente vê.

### accounts
| Coluna | Tipo | Notas |
|---|---|---|
| id | int PK | |
| username | varchar(32) único | |
| password_hash | varchar(255) | scrypt |
| created_at, last_login_at | datetime UTC | |
| banned | bool | |

### game_servers
Cada processo grava a própria linha no início: `id` (= `WARTUNE_SERVER_ID`), `name`, `site` (único),
`public_host`, `http_port`, `socket_port` e `opened_at`. A data de abertura é mantida nas
reinicializações e vira o `sysStarTime`.

### play_tickets
`token` (PK), `account_id`, `server_id`, `created_at`, `expires_at`. É emitido pelo portal e
validado no `POST login` para o servidor certo.

### characters
| Coluna | Notas |
|---|---|
| account_id, server_id | únicos juntos: um personagem por conta em cada servidor |
| nickname | NULL até o `visualizeregister`; único por servidor |
| active | falso até a criação na tela de registro |
| sex, camp, job | `job` = ícone = template do herói (1–6) |
| grades, gp, total_gp, gold, point, gift_token, strategy | progresso e moedas (`strategy` = Ruh) |
| weary, weary_limit, novice_process, fighting_capacity, repute, geste, charm | |
| bag_count, rental_bag_until | espaços comprados (5010, de 7 em 7) e fim do aluguel da mochila de 217 (8819) |
| store_grade, store_gp | cristal (8484) |
| appell_id | título em uso |
| created_at, last_login_at | |

### heroes
`character_id`, `template_id`, `nickname`, `grades`, `gp`, os cinco atributos (`power`, `agility`,
`intellect`, `captain`, `physique`) e os pontos distribuídos em cada um (`*_point`), além de
`remain_point`, `skill_point`, `skill_script`, `fast_key`, `fight_pos` e `is_leader`; `hide_fashion`
(5008), `blood` e `blood_id` (reserva de HP das poções).

### castles
Um por personagem: `name`, `map_id`, `pos_x`, `pos_y`, `grade`, `energy` e `state`. A posição vem
de `GridCastlePlacement`, que hoje é uma grade simples no mapa 100000313.

### buildings
`character_id`, `template_id`, `property1`, `property2`. O `template_id` muda a cada nível
(`NextGradeTemplateId`). Posição, nome e arte vêm do `BuildingTempInfos`. Na criação do personagem
são gravados os prédios centrais de nível 1: 90101 (conselho, 901), 10101 (mina de ouro), 30101
(depósito), 40201 (quartel), 50101 (academia) e 120101 (casa). O cliente não consegue construí-los
e busca vários deles por `sonType` sem checar null. Os prédios 1501–1511 são do próprio cliente e
não ficam no banco.

### quests
`character_id`, `template_id` (único por personagem), `completed`, `progress` (`condition_1`),
`added_at`, `completed_at`. As concluídas viram o bitmap `questSite`; não há tabela para ele.

### items
`character_id`, `template_id`, `bag_type` (0 bancada, 1 mochila, 2 runas, 3 medalha, 4 herói),
`object_id` (id do herói nos bags 2–4), `pos`, `count`, `random_skill` e `random_skill_2..5`
(atributos sorteados), `is_new`, `strengthen_grade`, `join_1..4` (furos: −1 fechado, 0 vazio, >0
pedra), `is_locked` e `mould_grade`. Ver [itens.md](itens.md).

### shop_buys, mystery_shops, fashion_books
`shop_buys`: compras do dia por `good_id` (`ShopTempInfo.Id`), únicas por personagem; `day` muda e a
contagem zera. `mystery_shops`: uma por personagem, os itens sorteados da loja misteriosa, os índices
comprados e as compras do dia. `fashion_books`: modas do livro (`template_id` único por personagem,
`is_switch`, `appraisal_skill`).

### cash_ledger
Todo movimento de elmas (`point`) e elmas vinculado (`gift_token`): `delta_point`,
`delta_gift_token`, os saldos depois (`balance_*`), `reason` (`shop`, `bag`, `rental_bag`, `item`,
`gm`, `recharge`), `ref` (o que foi comprado), `gm` (quem, quando for GM) e `created_at`. Só cresce;
é gravado na mesma transação da compra (`services/cash.py`).

## Transações

Os serviços usam `async with uow_factory() as uow: …; await uow.commit()`. Sem `commit()`, o
bloco descarta as alterações. Os objetos carregados continuam utilizáveis depois do bloco
(`expire_on_commit=False`). Em jogo, a sessão altera o snapshot em memória e grava com
`CharacterService.save(*entidades)`: nova entra com `add`, já gravada com `merge`.

## Migrações

Alembic, em `src/wartune_server/persistence/migrations/` (sem `alembic.ini`: a configuração é montada
em `Database.migrate`). Ao subir e no `db init`, o servidor aplica as migrações pendentes. Um banco
criado antes delas (pelo antigo `create_all`) é marcado como `0001`, o baseline, e segue dali.

Para mudar o schema: edite `schema.py`, rode `uv run wartune-server db revision "o que mudou"`
(gera `versions/NNNN_*.py` comparando o banco com o schema), revise o arquivo e rode os testes.
`test_migrations_match_schema` falha se o schema mudou sem migração. O portal PHP usa o mesmo
banco: coluna nova precisa de valor padrão para os `INSERT` dele continuarem funcionando.
