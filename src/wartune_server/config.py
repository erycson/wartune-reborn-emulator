"""Configuração (variáveis de ambiente ``WARTUNE_*`` ou arquivo ``.env``)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WARTUNE_", env_file=".env", extra="ignore")

    # Banco: sqlite+aiosqlite:///data/wartune.db | mysql+asyncmy://u:p@host/db | postgresql+asyncpg://u:p@host/db
    database_url: str = "sqlite+aiosqlite:///data/wartune.db"
    database_echo: bool = False

    # Este processo atende UM servidor de jogo (linha em game_servers). Vários processos
    # podem compartilhar o mesmo banco, um por servidor (S1, S2...).
    server_id: int = 1
    server_name: str = "S1 - Local"
    site: str = "local_0001"

    bind_host: str = "0.0.0.0"
    public_host: str = "127.0.0.1"  # host que o cliente usa (vai para o config.xml)
    http_port: int = 8080
    socket_port: int = 5000
    websocket_port: int = 5001  # ponte para o Ruffle (socketProxy)
    policy_port: int | None = 843  # None desliga o servidor de policy dedicado

    templates_file: Path = Path("data/overlay/xml/tempinfos.xml")
    # URL do tempinfos.xml na CDN (TEMPLATE_PATH + tempinfos.xml), para ``templates update``
    templates_url: str | None = None
    rsa_key_file: Path = Path("data/rsa_private.pem")

    # true pula o tutorial: o noviceProcess salvo nunca fica abaixo de 19000 (cena do castelo)
    skip_tutorial: bool = False

    socket_session_ttl_seconds: int = 1800  # sem uso por esse tempo, o login HTTP precisa ser refeito
    idle_timeout_seconds: int = 300

    log_dir: Path = Path("logs")
    log_level: str = "INFO"
    log_packets: bool = True  # logs/packets.log com cada pacote decodificado
