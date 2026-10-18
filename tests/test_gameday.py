from datetime import UTC, date, datetime, timedelta

from wartune_server.domain import gameday


def test_fuso_do_jogo_da_configuracao() -> None:
    """WARTUNE_GAME_TIMEZONE: deslocamento fixo ou nome IANA (com horário de verão, via tzdata)."""
    assert gameday.parse_timezone("UTC") is UTC
    assert gameday.parse_timezone("+03:00").utcoffset(None) == timedelta(hours=3)
    assert gameday.parse_timezone("UTC-7").utcoffset(None) == timedelta(hours=-7)
    pacific = gameday.parse_timezone("America/Los_Angeles")
    assert datetime(2026, 7, 1, tzinfo=pacific).utcoffset() == timedelta(hours=-7)  # PDT
    assert datetime(2026, 12, 1, tzinfo=pacific).utcoffset() == timedelta(hours=-8)  # PST


def test_dia_do_jogo_vira_as_5h_no_fuso_do_jogo() -> None:
    gameday.set_timezone("+03:00")  # 5h em UTC+3 = 02:00 UTC
    assert gameday.game_day(datetime(2026, 5, 21, 1, 59, tzinfo=UTC)) == date(2026, 5, 20)
    assert gameday.game_day(datetime(2026, 5, 21, 2, 0, tzinfo=UTC)) == date(2026, 5, 21)
    assert gameday.day_start(datetime(2026, 5, 21, 12, 0, tzinfo=UTC)) == datetime(2026, 5, 21, 2, 0, tzinfo=UTC)
    assert gameday.today(datetime(2026, 5, 21, 2, 0, tzinfo=UTC)) == "2026-05-21"
    now = datetime(2026, 5, 23, 3, 0, tzinfo=UTC)
    assert (gameday.days_between("2026-05-21", now), gameday.days_between("", now)) == (2, 1)
    assert gameday.days_between("2026-05-23", now) == 0
    assert gameday.same_day(datetime(2026, 5, 23, 2, 30, tzinfo=UTC), now)
    assert not gameday.same_day(datetime(2026, 5, 23, 1, 30, tzinfo=UTC), now)
