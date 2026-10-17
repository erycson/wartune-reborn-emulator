# Administração: painel GM, banimento e históricos

O painel fica no portal PHP (`D:/xampp/htdocs/wartune-reborn/portal/admin.php`, repositório separado).
O servidor só oferece duas rotas HTTP e grava os históricos.

## Rotas HTTP do servidor

Só existem com `WARTUNE_GM_SECRET` definido; o portal manda o mesmo valor (`gm_secret`) no cabeçalho
`X-GM-Secret`. Segredo errado: 403.

| Rota | Campos | O que faz | Resposta |
|---|---|---|---|
| `POST /gm/kick` | `character_id` | derruba a sessão e espera ela gravar e sair | 200 `{"ok":true}`; 503 se não terminou a tempo |
| `POST /gm/ban` | `account_id`, `banned` 0/1 | marca `accounts.banned`; banindo, invalida as sessões HTTP de login da conta (`InMemoryLoginSessionStore.drop_account`) e derruba o personagem dela neste servidor | 200; 400 campo inválido; 404 conta inexistente; 503 kick sem fim |

Conta banida é recusada no `POST /login` (`value="false"`, já existia) e no 20001 (`claim_socket`
relê a conta: cobre o ban feito pelo portal com o servidor fora do ar, quando a chave HTTP ainda vale).

O portal chama `/gm/kick` antes de qualquer escrita num personagem: conexão recusada = servidor fora,
grava; qualquer outro erro = não grava. No ban ele marca `accounts.banned` e chama `/gm/ban` em
todos os servidores de `game_servers`.

## Históricos

| Tabela | Quem grava | Quando |
|---|---|---|
| `login_history` | servidor (`source='game'`, IP de `request.remote` / peer do socket) | `POST /login` e 20001 aceito |
| | portal (`source='portal'`, IP e user agent) | login no portal |
| `cash_ledger` | servidor, `services/ledger.py` (`record_cash` / `cash_entry`) na mesma transação | 5006 que dá `point`/`gift_token` (`reason='item'`, `ref='5006:<template do pacote>'`) |
| | portal, na mesma transação PDO do UPDATE | edição GM (`reason='gm'`, `gm` = usuário do portal) e recarga manual (`reason='recharge'`) |
| `item_log` | servidor | 5006: pacote consumido (`action='use'`, `count=-1`) e cada item ganho (`'drop'`) |

`balance_*` é o saldo depois do movimento. Todas as colunas têm `server_default` (o PHP pode omitir
`created_at`). Migração `0003_historicos_de_login_cash_e_itens`.

Sistemas que gastam ou dão cash gravam o ledger na mesma `characters.save(...)`:
`cash_entry(c, delta_point, delta_gift_token, reason, ref)` devolve a entidade para passar junto
(`record_cash(uow, ...)` faz o mesmo dentro de um `UnitOfWork` aberto).

## Limites

- O jogador pode relogar entre o `/gm/kick` e o UPDATE do portal (milissegundos).
- No Windows, conexão recusada em localhost demora ~2 s (o portal usa `CONNECTTIMEOUT` de 5 s).
- Resetar personagem apaga também o `cash_ledger` e o `item_log` dele (CASCADE); o `login_history` fica com `character_id` nulo.
