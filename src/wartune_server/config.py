"""Configuração (variáveis de ambiente ``WARTUNE_*`` ou arquivo ``.env``)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
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

    # URL base dos assets estáticos (CDN). Vazio = o próprio servidor HTTP serve asset_dirs.
    resource_url: str = ""
    asset_dirs: list[Path] = Field(
        default_factory=lambda: [Path("data/overlay"), Path("D:/wartune/server-relay/public")]
    )
    config_template: Path = Path("data/overlay/client/config.xml")
    templates_file: Path = Path("data/overlay/xml/tempinfos.xml")
    rsa_key_file: Path = Path("data/rsa_private.pem")

    # Pula o tutorial: o noviceProcess salvo nunca fica abaixo de 19000 (cena do castelo)
    skip_tutorial: bool = True

    login_ticket_ttl_seconds: int = 300
    socket_session_ttl_seconds: int = 120
    idle_timeout_seconds: int = 300

    log_dir: Path = Path("logs")
    log_level: str = "INFO"
    log_packets: bool = True  # logs/packets.log com cada pacote decodificado

    @property
    def public_http_url(self) -> str:
        return f"http://{self.public_host}:{self.http_port}/"

    @property
    def public_resource_url(self) -> str:
        return self.resource_url or self.public_http_url
