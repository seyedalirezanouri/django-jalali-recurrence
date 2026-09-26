import datetime

import jdatetime
import pytest

import recurrence


JDT = jdatetime.datetime


def test_rule_none_parameters_week_numbers_and_period_mismatches():
    assert recurrence.Rule(recurrence.DAILY, bymonth=None).bymonth == ()

    start = JDT(1404, 1, 1)
    assert recurrence.Rule(
        recurrence.YEARLY, byweekno=[1]
    )._matches_day(start)
    assert not recurrence.Rule(
        recurrence.YEARLY, byweekno=[999]
    )._matches_day(start)

    assert not recurrence.Rule(
        recurrence.YEARLY, interval=2
    )._period_matches(JDT(1405, 1, 1), start)
    assert not recurrence.Rule(
        recurrence.MONTHLY, interval=2
    )._period_matches(JDT(1404, 2, 1), start)
    assert not recurrence.Rule(recurrence.DAILY)._period_matches(
        JDT(1403, 12, 29), start
    )


def test_seek_optimizations_for_calendar_and_clock_frequencies():
    seed = JDT(1400, 6, 15, 9)

    yearly = recurrence.Rule(recurrence.YEARLY)
    assert yearly._seek(seed, JDT(1405, 1, 1, 9)) == JDT(1404, 6, 15, 9)
    assert yearly._seek(seed, JDT(1405, 8, 1, 9)) == JDT(1405, 6, 15, 9)

    monthly = recurrence.Rule(recurrence.MONTHLY)
    assert monthly._seek(seed, JDT(1401, 1, 1, 9)) == JDT(1400, 12, 15, 9)
    assert monthly._seek(seed, JDT(1401, 1, 20, 9)) == JDT(1401, 1, 15, 9)

    hourly = recurrence.Rule(recurrence.HOURLY)
    assert hourly._seek(seed, JDT(1400, 6, 15, 12, 45)) == JDT(
        1400, 6, 15, 12
    )


def test_occurrence_bounds_skip_out_of_range_candidates():
    start = JDT(1404, 1, 1, 9)
    rule = recurrence.Rule(recurrence.DAILY, byhour=[8])

    assert list(rule.occurrences(start, start)) == []


def test_recurrence_bounds_count_and_empty_queries():
    start = JDT(1404, 1, 1)
    finite = recurrence.Recurrence(
        start,
        rrules=[recurrence.Rule(recurrence.DAILY, count=2)],
    )
    assert finite.count() == 2
    assert finite.after(JDT(1404, 1, 10)) is None
    assert finite.between(
        start,
        JDT(1404, 1, 10),
        dtend=JDT(1404, 1, 2),
        inc=True,
    ) == [start, JDT(1404, 1, 2)]

    with pytest.raises(recurrence.UnboundedRecurrenceError):
        list(recurrence.Recurrence(start).occurrences())


def test_before_calculates_frequency_specific_lookback_windows():
    start = JDT(1404, 1, 1)
    value = recurrence.Recurrence(
        start,
        rrules=[
            recurrence.Rule(recurrence.YEARLY, count=1),
            recurrence.Rule(recurrence.MONTHLY, count=1),
            recurrence.Rule(recurrence.WEEKLY, count=1),
        ],
    )

    assert value.before(JDT(1404, 1, 2)) == start


def test_query_bounds_reject_naive_gregorian_for_aware_recurrence():
    start = JDT(1404, 1, 1, tzinfo=datetime.timezone.utc)
    value = recurrence.Recurrence(
        start,
        rrules=[recurrence.Rule(recurrence.DAILY, count=1)],
    )

    with pytest.raises(TypeError, match="aware and naive"):
        value.after(datetime.datetime(2025, 3, 21))


def test_datetime_serialization_parser_edges():
    naive = JDT(1404, 1, 1, 9)
    encoded_rule = recurrence.serialize(
        recurrence.Rule(recurrence.DAILY, until=naive)
    )
    assert "UNTIL=14040101T090000" in encoded_rule
    assert recurrence.to_utc(naive).tzinfo is datetime.timezone.utc

    assert recurrence.deserialize_datetime("14040101T090000") == naive
    offset = recurrence.deserialize_datetime(
        "IGNORED=value;TZOFFSET=-0330|14040101T090000"
    )
    assert offset.utcoffset() == datetime.timedelta(hours=-3, minutes=-30)

    with pytest.raises(recurrence.DeserializationError, match="malformed"):
        recurrence.deserialize(
            "X-RECURRENCE-VERSION:2\nCALSCALE:JALALI\nDTSTART:not-a-date"
        )


def test_rule_parser_ignores_unknown_parameters_and_rule_text_can_be_plain():
    value = recurrence.deserialize(
        "X-RECURRENCE-VERSION:2\n"
        "CALSCALE:JALALI\n"
        "RRULE:FREQ=DAILY;IGNORED=value;COUNT=1"
    )

    assert value.rrules[0].count == 1
    assert recurrence.Rule(recurrence.DAILY).to_text() == "daily"

