import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from fetch_missing import missing_from_log, safe  # noqa: E402


def test_missing_from_log(tmp_path: Path) -> None:
    log = tmp_path / "access.log"
    log.write_text(
        '::1 - - [x] "GET /wartune-reborn/cdn/equip/a/1.swf?v=2 HTTP/1.1" 404 196\n'
        '::1 - - [x] "GET /wartune-reborn/cdn/equip/a/1.swf HTTP/1.1" 404 196\n'
        '::1 - - [x] "GET /wartune-reborn/cdn/equip/b/1.swf HTTP/1.1" 200 196\n'
        '::1 - - [x] "GET /wartune-reborn/cdn/xml/version.xml HTTP/1.1" 404 196\n'
        '::1 - - [x] "GET /favicon.ico HTTP/1.1" 404 196\n'
    )
    assert missing_from_log(log) == ["equip/a/1.swf"]
    assert not safe("../x.swf") and not safe("/x.swf") and safe("equip/a/1.swf")
