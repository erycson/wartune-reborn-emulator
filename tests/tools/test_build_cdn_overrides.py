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


def test_fills_missing_level_up_figures(tmp_path: Path) -> None:
    from build_cdn_overrides import fill_level_up_figures

    folder = tmp_path / "swf/register1"
    folder.mkdir(parents=True)
    body = b"\x0a\x00asset.choicefigure.Human_6\x00"
    (folder / "6.swf").write_bytes(b"CWS\x0a" + struct.pack("<I", len(body) + 8) + zlib.compress(body))
    assert fill_level_up_figures(tmp_path) == 5
    one = (folder / "1.swf").read_bytes()
    assert zlib.decompress(one[8:]) == body.replace(b"Human_6", b"Human_1") and one[:8] == b"CWS\x0a" + one[4:8]


def _bswf(package: bytes) -> bytes:
    """``.bswf`` mínimo: um registro de cabeçalho e um SWF com DoABC + SymbolClass citando ``package``."""
    from build_cdn_overrides import _put_u30

    pool = b"".join(_put_u30(len(s)) + s for s in (package, package + b".S_0_0"))
    abc = b"\x10\x00\x2e\x00" + b"\x01\x01\x01" + _put_u30(3) + pool + b"REST"
    tags = struct.pack("<HI", 82 << 6 | 0x3F, 5 + len(abc)) + b"\x01\x00\x00\x00\x00" + abc
    symbols = struct.pack("<HH", 1, 1) + package + b".S_0_0\x00"
    tags += struct.pack("<H", 76 << 6 | len(symbols)) + symbols + b"\x00\x00"
    body = b"\x00" + b"\x00\x18\x01\x00" + tags  # RECT de 1 byte (Nbits 0), frame rate, frame count
    swf = b"CWS\x0a" + struct.pack("<I", len(body) + 8) + zlib.compress(body)
    return b"\x01\x05\x02" + struct.pack(">H", 2) + b"ab" + b"\x10" + struct.pack(">i", len(swf)) + swf


def _classes(bswf: bytes) -> bytes:
    return zlib.decompress(bswf[12 + 8 :])


def test_fills_missing_default_bodies(tmp_path: Path) -> None:
    from build_cdn_overrides import fill_default_bodies

    out, cdn = tmp_path / "out", tmp_path / "cdn"
    for rel in (
        "warrior_body020/1.bswf",
        "warrior_body010/1.bswf",
        "hunter_default_body/0.bswf",
        "wizard_default_body/1.bswf",
    ):
        file = cdn / "swf/avatar" / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(_bswf(f"asset.{file.parent.name}_{file.stem}".encode()))
    fill_default_bodies(out, cdn)
    body = out / "swf/avatar"
    # primeira roupa da classe, com o pacote que o cliente procura pelo caminho
    warrior = _classes((body / "warrior_default_body/1.bswf").read_bytes())
    assert b"asset.warrior_default_body_1.S_0_0" in warrior and b"body010" not in warrior
    # sem roupa no sexo: o corpo padrão de outra classe
    assert b"asset.warrior_default_body_0" in _classes((body / "warrior_default_body/0.bswf").read_bytes())
    assert not (body / "wizard_default_body/1.bswf").exists()  # já existe no CDN


def test_rename_bswf_keeps_header_and_fixes_sizes() -> None:
    from build_cdn_overrides import rename_bswf

    old, new = b"asset.warrior_body010_1", b"asset.warrior_default_body_1"
    bswf = _bswf(old)
    out = rename_bswf(bswf, old.decode(), new.decode())
    assert out[:8] == bswf[:8]  # registros de cabeçalho intactos
    inner = out[12:]
    renamed = zlib.decompress(inner[8:])
    assert struct.unpack(">i", out[8:12])[0] == len(inner)
    assert struct.unpack("<I", inner[4:8])[0] == len(renamed) + 8
    assert old not in renamed and renamed.count(new) == 3 and b"REST" in renamed
