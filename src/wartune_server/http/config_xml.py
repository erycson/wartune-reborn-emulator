"""Gera o ``client/config.xml`` a partir do arquivo oficial capturado.

Troca só o necessário (hosts, porta do socket, site e chave RSA do login) com
substituições de texto: o arquivo tem BOM, comentários e aspas mistas que um
parser XML reescreveria.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..security.rsa_keys import LoginKeyPair


def _attr(text: str, tag: str, attr: str = "value") -> str:
    match = re.search(rf"<{tag}\b[^>]*?\b{attr}\s*=\s*([\"'])(.*?)\1", text, re.S)
    if match is None:
        raise ValueError(f"config.xml modelo sem <{tag} {attr}=...>")
    return match.group(2)


def _set_attr(text: str, tag: str, attr: str, value: str) -> str:
    pattern = rf"(<{tag}\b[^>]*?\b{attr}\s*=\s*)([\"'])(.*?)\2"
    return re.sub(pattern, lambda m: f"{m.group(1)}{m.group(2)}{value}{m.group(2)}", text, flags=re.S)


def render_client_config(
    template: str,
    *,
    request_url: str,
    resource_url: str,
    socket_host: str,
    socket_port: int,
    site: str,
    keys: LoginKeyPair,
) -> str:
    old_request = _attr(template, "REQUEST_PATH")
    old_resource = _attr(template, "ResourcePath")
    old_site = _attr(template, "NODE", "site")

    text = template.replace(old_resource, resource_url).replace(old_request, request_url)
    text = _set_attr(text, "SocktPath", "value", socket_host)
    text = _set_attr(text, "SocktPath", "SocketPort", str(socket_port))
    text = _set_attr(text, "RSAKey", "PublicKeyModulus", keys.modulus_b64)
    text = _set_attr(text, "RSAKey", "publicExponent", keys.exponent_b64)
    return text.replace(f"'{old_site}'", f"'{site}'").replace(f'"{old_site}"', f'"{site}"')


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")
