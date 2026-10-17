"""Ambiente do Alembic: roda na conexão que ``Database.migrate`` passa em ``config.attributes``."""

from alembic import context

from wartune_server.persistence.schema import metadata

connection = context.config.attributes["connection"]
# render_as_batch: o SQLite não tem ALTER COLUMN; o Alembic recria a tabela
context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
