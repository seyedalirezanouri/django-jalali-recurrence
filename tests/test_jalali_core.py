import datetime

import jdatetime
import pytest
from zoneinfo import ZoneInfo

import recurrence


def test_icu_conversion_vectors():
    assert jdatetime.date.fromgregorian(date=datetime.date(2021, 3, 21)) == jdatetime.date(1400, 1, 1)
    assert jdatetime.date.fromgregorian(date=datetime.date(2025, 3, 20)) == jdatetime.date(1403, 12, 30)
    assert jdatetime.date(1404, 1, 1).togregorian() == datetime.date(2025, 3, 21)


def test_jalali_month_lengths():
    assert (jdatetime.date(1404, 1, 1) - jdatetime.date(1403, 1, 1)).days == 366
    assert jdatetime.date(1404, 12, 29).isleap() is False


def test_jalali_recurrence_and_wire_format():
    start = jdatetime.datetime(1404, 1, 1)
    pattern = recurrence.Recurrence(
        dtstart=start,
        dtend=jdatetime.datetime(1404, 1, 3),
        rrules=[recurrence.Rule(recurrence.DAILY)],
    )
    assert list(pattern.occurrences()) == [
        start,
        jdatetime.datetime(1404, 1, 2),
        jdatetime.datetime(1404, 1, 3),
    ]
    text = recurrence.serialize(pattern)
    assert "X-RECURRENCE-VERSION:2" in text
    assert "CALSCALE:JALALI" in text
    assert recurrence.deserialize(text) == pattern


def test_legacy_wire_format_is_rejected():
    with pytest.raises(recurrence.DeserializationError):
        recurrence.deserialize("DTSTART:20210321T000000Z\nRRULE:FREQ=DAILY")


def test_monthly_ordinal_and_timezone_round_trip():
    start = jdatetime.datetime(1403, 1, 1, 9, tzinfo=ZoneInfo("Asia/Tehran"))
    rule = recurrence.Rule(recurrence.MONTHLY, byday=[recurrence.SA], bysetpos=[-1])
    values = list(recurrence.Recurrence(start, jdatetime.datetime(1403, 4, 1, tzinfo=start.tzinfo), rrules=[rule]).occurrences())
    assert [value.day for value in values] == [1, 25, 29, 26, 1]
    restored = recurrence.deserialize(recurrence.serialize(recurrence.Recurrence(start, rrules=[rule])))
    assert restored.dtstart.tzinfo == ZoneInfo("Asia/Tehran")


def test_invalid_date_policy():
    start = jdatetime.datetime(1403, 7, 1)
    end = jdatetime.datetime(1404, 1, 1)
    omit = recurrence.Rule(recurrence.MONTHLY, bymonthday=[31], skip="OMIT")
    backward = recurrence.Rule(recurrence.MONTHLY, bymonthday=[31], skip="BACKWARD")
    omitted = list(recurrence.Recurrence(start, end, rrules=[omit]).occurrences())
    moved = list(recurrence.Recurrence(start, end, rrules=[backward]).occurrences())
    assert all(value.day != 30 or value.month == 12 for value in omitted)
    assert any(value.month == 7 and value.day == 30 for value in moved)
