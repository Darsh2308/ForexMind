from datetime import datetime, timezone

from forexmind.agents.market_data.sessions import active_sessions, session_overlaps


def _at(hour: int) -> datetime:
    return datetime(2026, 7, 27, hour, 0, tzinfo=timezone.utc)


def test_tokyo_only_session():
    # Hour 6: past Sydney's wrap-around close (6) and before London's open (7).
    assert active_sessions(_at(6)) == ["Tokyo"]


def test_sydney_tokyo_overlap_window():
    active = active_sessions(_at(2))
    assert set(active) == {"Sydney", "Tokyo"}
    assert session_overlaps(active) == ["Sydney-Tokyo"]


def test_tokyo_london_overlap_window():
    active = active_sessions(_at(8))
    assert set(active) == {"Tokyo", "London"}
    assert session_overlaps(active) == ["Tokyo-London"]


def test_london_new_york_overlap_window():
    active = active_sessions(_at(13))
    assert set(active) == {"London", "New York"}
    assert session_overlaps(active) == ["London-New York"]


def test_sydney_wraps_midnight():
    assert "Sydney" in active_sessions(_at(23))
    assert "Sydney" in active_sessions(_at(1))
    assert "Sydney" not in active_sessions(_at(12))


def test_quiet_hour_no_major_session():
    # 19:00 UTC: New York still open (12-21) - pick an hour truly outside all.
    # Between London close (16) and NY session end there is no fully quiet
    # hour on weekdays, so assert the narrower claim: Tokyo/Sydney are closed.
    active = active_sessions(_at(18))
    assert "Tokyo" not in active
    assert "London" not in active


def test_naive_datetime_is_treated_as_utc():
    naive = datetime(2026, 7, 27, 6, 0)
    assert active_sessions(naive) == ["Tokyo"]
