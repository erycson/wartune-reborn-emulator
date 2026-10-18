# Templates do jogo no banco

O `tempinfos.xml` é o template do jogo: itens, lojas, missões, campanhas, mapas, heróis, tropas e skills (70 categorias). É o mesmo arquivo que o cliente baixa de `TEMPLATE_PATH`. Por isso servidor e cliente precisam usar o mesmo arquivo.

Desde 2026-10-18 vale a versão inglesa do cliente novo, guardada em `data/templates/tempinfos.xml`. É uma cópia sem edição de `mirror/s134-bmclas-sq.7road.net/xml/tempinfos.xml`. O turco (`data/overlay`) ficou como legado.

## Onde fica

- **`template_nodes`**: cada elemento abaixo de `<root>` vira uma linha.
  - `parent_id` e `position` guardam a árvore e a ordem.
  - `tag` é o nome do elemento: categoria (`ItemTempInfos`) ou linha (`ItemTempInfo`).
  - `attrs` guarda os atributos em JSON, na ordem do arquivo.
  - Na categoria, `key_name` é o atributo id das linhas: o primeiro atributo, quando está em todas as linhas e não repete (`TemplateId`, `Id`, `CampaignId`).
  - Na linha, `row_key` é o valor desse atributo. Ele é indexado e serve para cruzar com `items.template_id`, `shop_buys.good_id`, etc.
  - Categorias de chave composta (os drops) ficam com `row_key` nulo.
  - O nível a mais do `TollgateReward` (`ScoreRewards`, `BossRewards`...) é guardado. O `GameTemplates.parse` ignora esse nível, mas o XML gerado o devolve.
- **`template_imports`**: o histórico de importações, com origem, sha256 do XML e número de nós.

Importar troca o conjunto inteiro numa transação. Se o arquivo não abrir, o banco fica como estava.

## Comandos

| Comando | O que faz |
|---|---|
| `wartune-server db init` | Migra o banco. Se o banco não tem templates, importa o `WARTUNE_TEMPLATES_FILE` |
| `wartune-server templates import [arquivo]` | Importa um `tempinfos.xml` (zlib ou XML puro) e troca o que estava no banco |
| `wartune-server templates export <saida>` | Gera o `tempinfos.xml` do banco, em zlib como o oficial |
| `wartune-server templates update [url]` | Baixa da CDN para o arquivo local e importa |

Depois de importar, reinicie o servidor: os templates são carregados uma vez, na subida.

## Na subida

`app._templates`: se o banco tem templates, o `GameTemplates` sai do banco. Senão sai do arquivo, com um aviso no log. Banco novo de teste cai nesse segundo caso, então a suíte não importa 68 mil nós a cada teste. O caminho do banco é coberto por `tests/test_template_store.py`.

## Garantia

`tests/test_template_store.py` importa o arquivo real e exporta de volta. As duas árvores (tags, atributos, ordem, aninhamento) são iguais. O `GameTemplates` do banco é igual ao do `GameTemplates.parse` do arquivo. Os bytes não são iguais: a indentação e as entidades podem mudar, mas o conteúdo não.

## Consultas úteis

Item de cada linha da mochila:

```sql
select i.character_id, i.template_id, i.count, json_extract(n.attrs, '$.TemplateName') as nome
from items i
join template_nodes n on n.row_key = cast(i.template_id as text)
join template_nodes c on c.id = n.parent_id and c.tag = 'ItemTempInfos';
```

`json_extract` é do SQLite. No MySQL e no Postgres a função de JSON muda de nome.
