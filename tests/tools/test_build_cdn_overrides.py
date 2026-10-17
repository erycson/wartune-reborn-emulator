import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from build_cdn_overrides import decrypt_module, encrypt_module, normalize_modules, strip_module_padding  # noqa: E402


def _module(body: bytes, padding: int) -> bytes:
    swf = b"CWS\x14" + struct.pack("<I", len(body) + 8) + zlib.compress(body + bytes(padding))
    return encrypt_module(b"road7" + b"a" * 32 + bytes(range(21)), swf)


def test_roundtrip_and_strip(tmp_path: Path) -> None:
    body = bytes(range(256)) * 10
    raw = _module(body, 100_000)
    assert decrypt_module(encrypt_module(raw, decrypt_module(raw))) == decrypt_module(raw)
    fixed = strip_module_padding(raw)
    assert fixed is not None and fixed[:58] == raw[:58]
    swf = decrypt_module(fixed)
    assert zlib.decompress(swf[8:]) == body
    assert strip_module_padding(fixed) is None

    (tmp_path / "8.png").write_bytes(raw)
    (tmp_path / "ui/zh_cn").mkdir(parents=True)
    (tmp_path / "ui/zh_cn/size.xml").write_text('<a><Item size="1" name="8.png" /><Item size="2" name="18.png" /></a>')
    assert normalize_modules(tmp_path) == 1
    xml = (tmp_path / "ui/zh_cn/size.xml").read_text(encoding="utf-8-sig")
    assert f'size="{len(fixed)}" name="8.png"' in xml and 'size="2" name="18.png"' in xml


def test_sync_md5_list(tmp_path: Path) -> None:
    from build_cdn_overrides import sync_md5_list

    out, cdn = tmp_path / "out", tmp_path / "cdn"
    (out / "client").mkdir(parents=True)
    cdn.mkdir()
    (cdn / "9.png").write_bytes(b"road7" + b"b" * 32 + b"resto")
    (out / "8.png").write_bytes(b"road7" + b"c" * 32 + b"resto")
    xml = (
        '\ufeff<md5><check><Item name="9.png" md5="'
        + "a" * 32
        + '" /><Item name="8.png" md5="'
        + "c" * 32
        + '" /></check></md5>'
    )
    (out / "client/resouececheck.sq").write_bytes(zlib.compress(xml.encode()))
    assert sync_md5_list(out, cdn) == 1
    text = zlib.decompress((out / "client/resouececheck.sq").read_bytes()).decode("utf-8-sig")
    assert 'name="9.png" md5="' + "b" * 32 in text and 'name="8.png" md5="' + "c" * 32 in text
