"""Standalone, database-free acceptance tests for the Jalali v2 API.

Run from the repository root with either of these commands::

    python tests/test_jalali_no_database.py
    pytest -q tests/test_jalali_no_database.py

The module deliberately uses only ``unittest`` and public ``recurrence`` APIs.
It never configures Django, imports the ORM models, or opens a database.
"""

from __future__ import annotations

import datetime
import pathlib
import sys
import unittest
from zoneinfo import ZoneInfo

import jdatetime
# Make direct execution work without installing the package first.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import recurrence


JDT = jdatetime.datetime


def month_length(year, month):
    next_month = jdatetime.date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    return (next_month - jdatetime.date(year, month, 1)).days


class CalendarArithmeticTests(unittest.TestCase):
    def test_known_nowruz_and_leap_correction_vectors(self):
        vectors = (
            (datetime.date(2021, 3, 21), jdatetime.date(1400, 1, 1)),
            (datetime.date(2024, 3, 20), jdatetime.date(1403, 1, 1)),
            (datetime.date(2025, 3, 20), jdatetime.date(1403, 12, 30)),
            (datetime.date(2025, 3, 21), jdatetime.date(1404, 1, 1)),
        )
        for gregorian, jalali in vectors:
            with self.subTest(gregorian=gregorian):
                self.assertEqual(jdatetime.date.fromgregorian(date=gregorian), jalali)
                self.assertEqual(jalali.togregorian(), gregorian)

    def test_every_day_round_trips_across_four_centuries(self):
        current = datetime.date(1800, 1, 1)
        end = datetime.date(2200, 12, 31)
        one_day = datetime.timedelta(days=1)
        while current <= end:
            converted = jdatetime.date.fromgregorian(date=current)
            self.assertEqual(converted.togregorian(), current)
            current += one_day

    def test_month_and_year_lengths(self):
        self.assertEqual([31] * 6 + [30] * 5 + [29], [
            (jdatetime.date(1404, month + 1, 1) - jdatetime.date(1404, month, 1)).days
            for month in range(1, 12)
        ] + [(jdatetime.date(1405, 1, 1) - jdatetime.date(1404, 12, 1)).days])
        self.assertEqual((jdatetime.date(1404, 1, 1) - jdatetime.date(1403, 1, 1)).days, 366)
        self.assertEqual((jdatetime.date(1405, 1, 1) - jdatetime.date(1404, 1, 1)).days, 365)

    def test_invalid_dates_are_rejected(self):
        invalid = ((0, 1, 1), (1404, 0, 1), (1404, 13, 1),
                   (1404, 1, 32), (1404, 7, 31), (1404, 12, 30))
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                jdatetime.date(*fields)

    def test_value_objects_are_immutable_hashable_and_replaceable(self):
        value = JDT(1404, 1, 1, 12, 30, 15, 123456)
        self.assertEqual({value, value}, {value})
        self.assertEqual(value.replace(day=2).day, 2)
        self.assertEqual(value.day, 1)
        with self.assertRaises((AttributeError, TypeError)):
            value.day = 2

    def test_week_starts_on_saturday(self):
        self.assertEqual(jdatetime.date(1403, 1, 4).weekday(), recurrence.SATURDAY)
        self.assertEqual(jdatetime.date(1403, 1, 10).weekday(), recurrence.FRIDAY)
        self.assertEqual([recurrence.to_weekday(name).number for name in
                          ("SA", "SU", "MO", "TU", "WE", "TH", "FR")], list(range(7)))

    def test_datetime_arithmetic_formatting_and_explicit_conversion(self):
        value = JDT(1403, 12, 30, 23, 59, 58, 123456)
        self.assertEqual(value + datetime.timedelta(seconds=2), JDT(1404, 1, 1, 0, 0, 0, 123456))
        self.assertEqual(value.strftime("%Y/%m/%d %H:%M:%S"), "1403/12/30 23:59:58")
        self.assertEqual(JDT.fromgregorian(datetime=value.togregorian()), value)


class PublicContractTests(unittest.TestCase):
    def test_gregorian_datetime_is_rejected_at_public_boundaries(self):
        gregorian = datetime.datetime(2025, 3, 21)
        constructors = (
            lambda: recurrence.Recurrence(dtstart=gregorian),
            lambda: recurrence.Recurrence(dtend=gregorian),
            lambda: recurrence.Recurrence(rdates=[gregorian]),
            lambda: recurrence.Recurrence(exdates=[gregorian]),
            lambda: recurrence.Rule(recurrence.DAILY, until=gregorian),
        )
        for constructor in constructors:
            with self.subTest(constructor=constructor), self.assertRaisesRegex(TypeError, "jdatetime.datetime"):
                constructor()

    def test_aware_and_naive_values_cannot_be_mixed(self):
        aware = JDT(1404, 1, 1, tzinfo=datetime.timezone.utc)
        naive = JDT(1404, 1, 2)
        with self.assertRaises(TypeError):
            recurrence.Recurrence(dtstart=aware, rdates=[naive])

    def test_rule_and_recurrence_equality_is_field_based(self):
        left_rule = recurrence.Rule(recurrence.MONTHLY, interval=2, bymonthday=[-1])
        right_rule = recurrence.Rule(recurrence.MONTHLY, interval=2, bymonthday=[-1])
        self.assertEqual(left_rule, right_rule)
        left = recurrence.Recurrence(JDT(1404, 1, 1), rrules=[left_rule])
        right = recurrence.Recurrence(JDT(1404, 1, 1), rrules=[right_rule])
        self.assertEqual(left, right)

    def test_invalid_rule_options_are_rejected(self):
        for kwargs in ({"interval": 0}, {"count": 0}, {"bymonth": [13]}, {"skip": "INVALID"}):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, recurrence.ValidationError)):
                recurrence.Rule(recurrence.DAILY, **kwargs)


class RecurrenceEngineTests(unittest.TestCase):
    def test_between_seeks_to_a_distant_gregorian_window(self):
        pattern = recurrence.deserialize(
            "X-RECURRENCE-VERSION:2\n"
            "CALSCALE:JALALI\n"
            "DTSTART:13150307T000000Z\n"
            "DTEND:14281012T000000Z\n"
            "RRULE:FREQ=DAILY;WKST=SA"
        )
        values = pattern.between(
            datetime.datetime(2026, 9, 20, tzinfo=datetime.timezone.utc),
            datetime.datetime(2028, 9, 20, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(len(values), 730)
        self.assertEqual(values[0].togregorian().date(), datetime.date(2026, 9, 21))
        self.assertEqual(values[-1].togregorian().date(), datetime.date(2028, 9, 19))

    def test_all_frequencies_honor_count(self):
        cases = (
            (recurrence.YEARLY, JDT(1406, 1, 1)),
            (recurrence.MONTHLY, JDT(1404, 3, 1)),
            (recurrence.WEEKLY, JDT(1404, 1, 15)),
            (recurrence.DAILY, JDT(1404, 1, 3)),
            (recurrence.HOURLY, JDT(1404, 1, 1, 2)),
            (recurrence.MINUTELY, JDT(1404, 1, 1, 0, 2)),
            (recurrence.SECONDLY, JDT(1404, 1, 1, 0, 0, 2)),
        )
        start = JDT(1404, 1, 1)
        for frequency, expected_last in cases:
            with self.subTest(frequency=frequency):
                values = list(recurrence.Rule(frequency, count=3).occurrences(start))
                self.assertEqual(len(values), 3)
                self.assertEqual(values[-1], expected_last)

    def test_daily_interval_count_and_until(self):
        start = JDT(1404, 1, 1, 9)
        rule = recurrence.Rule(recurrence.DAILY, interval=2, until=JDT(1404, 1, 6, 9))
        self.assertEqual(list(rule.occurrences(start)),
                         [JDT(1404, 1, 1, 9), JDT(1404, 1, 3, 9), JDT(1404, 1, 5, 9)])

    def test_weekly_byday_uses_saturday_based_weeks(self):
        start = JDT(1403, 1, 4, 9)  # Saturday
        rule = recurrence.Rule(recurrence.WEEKLY, count=4, byday=[recurrence.SA, recurrence.FR])
        values = list(rule.occurrences(start))
        self.assertEqual([value.weekday() for value in values], [0, 6, 0, 6])

    def test_monthly_negative_monthday_and_ordinal_weekday(self):
        start = JDT(1404, 1, 1)
        last_days = list(recurrence.Rule(recurrence.MONTHLY, count=3, bymonthday=[-1]).occurrences(start))
        self.assertEqual([(item.month, item.day) for item in last_days], [(1, 31), (2, 31), (3, 31)])

    def test_first_saturday_of_each_month(self):
        rule = recurrence.Rule(recurrence.MONTHLY, count=6, byday=[recurrence.SA(1)])
        values = list(rule.occurrences(JDT(1404, 1, 1)))
        self.assertEqual([(value.month, value.day) for value in values],
                         [(1, 2), (2, 6), (3, 3), (4, 7), (5, 4), (6, 1)])
        self.assertTrue(all(value.weekday() == recurrence.SATURDAY and value.day <= 7
                            for value in values))

    def test_third_monday_of_each_month(self):
        rule = recurrence.Rule(recurrence.MONTHLY, count=6, byday=[recurrence.MO(3)])
        values = list(rule.occurrences(JDT(1404, 1, 1)))
        self.assertEqual([(value.month, value.day) for value in values],
                         [(1, 18), (2, 15), (3, 19), (4, 16), (5, 20), (6, 17)])
        self.assertTrue(all(value.weekday() == recurrence.MONDAY and 15 <= value.day <= 21
                            for value in values))

    def test_last_friday_of_each_month(self):
        rule = recurrence.Rule(recurrence.MONTHLY, count=6, byday=[recurrence.FR(-1)])
        values = list(rule.occurrences(JDT(1404, 1, 1)))
        self.assertEqual([(value.month, value.day) for value in values],
                         [(1, 29), (2, 26), (3, 30), (4, 27), (5, 31), (6, 28)])
        self.assertTrue(all(value.weekday() == recurrence.FRIDAY and
                            month_length(value.year, value.month) - value.day < 7
                            for value in values))

    def test_other_positive_and_negative_monthly_ordinals(self):
        cases = (
            (recurrence.SU(2), recurrence.SUNDAY, range(8, 15)),
            (recurrence.TH(-2), recurrence.THURSDAY, range(16, 26)),
        )
        for ordinal, weekday, valid_days in cases:
            with self.subTest(ordinal=ordinal):
                values = list(recurrence.Rule(recurrence.MONTHLY, count=12, byday=[ordinal])
                              .occurrences(JDT(1404, 1, 1)))
                self.assertEqual(len(values), 12)
                self.assertEqual(len({(value.year, value.month) for value in values}), 12)
                self.assertTrue(all(value.weekday() == weekday and value.day in valid_days
                                    for value in values))

    def test_yearly_by_month_and_year_day(self):
        start = JDT(1403, 1, 1)
        nowruz = recurrence.Rule(recurrence.YEARLY, count=3, bymonth=[1], bymonthday=[1])
        self.assertEqual(list(nowruz.occurrences(start)),
                         [JDT(1403, 1, 1), JDT(1404, 1, 1), JDT(1405, 1, 1)])
        year_end = recurrence.Rule(recurrence.YEARLY, count=2, byyearday=[-1])
        self.assertEqual(list(year_end.occurrences(start)), [JDT(1403, 12, 30), JDT(1404, 12, 29)])

    def test_time_by_parts_and_bysetpos(self):
        start = JDT(1404, 1, 1)
        rule = recurrence.Rule(recurrence.DAILY, count=2, byhour=[8, 16], byminute=[30], bysetpos=[-1])
        self.assertEqual(list(rule.occurrences(start)), [JDT(1404, 1, 1, 16, 30), JDT(1404, 1, 2, 16, 30)])

    def test_skip_omit_backward_and_forward(self):
        start, end = JDT(1404, 7, 1), JDT(1404, 9, 2)
        omit = list(recurrence.Rule(recurrence.MONTHLY, bymonthday=[31], skip="OMIT").occurrences(start, end))
        backward = list(recurrence.Rule(recurrence.MONTHLY, bymonthday=[31], skip="BACKWARD").occurrences(start, end))
        forward = list(recurrence.Rule(recurrence.MONTHLY, bymonthday=[31], skip="FORWARD").occurrences(start, end))
        self.assertEqual(omit, [])
        self.assertEqual([(item.month, item.day) for item in backward], [(7, 30), (8, 30)])
        self.assertEqual([(item.month, item.day) for item in forward], [(8, 1), (9, 1)])

    def test_inclusion_exclusion_sorting_and_deduplication(self):
        start = JDT(1404, 1, 1)
        pattern = recurrence.Recurrence(
            dtstart=start,
            dtend=JDT(1404, 1, 5),
            rrules=[recurrence.Rule(recurrence.DAILY)],
            exrules=[recurrence.Rule(recurrence.DAILY, interval=2)],
            rdates=[JDT(1404, 1, 2), JDT(1404, 1, 2)],
            exdates=[JDT(1404, 1, 4)],
            include_dtstart=False,
        )
        self.assertEqual(list(pattern.occurrences()), [JDT(1404, 1, 2)])

    def test_before_after_between_and_unbounded_error(self):
        start = JDT(1404, 1, 1)
        pattern = recurrence.Recurrence(start, rrules=[recurrence.Rule(recurrence.DAILY, count=5)])
        self.assertEqual(pattern.before(JDT(1404, 1, 3)), JDT(1404, 1, 2))
        self.assertEqual(pattern.after(JDT(1404, 1, 3)), JDT(1404, 1, 4))
        self.assertEqual(pattern.between(JDT(1404, 1, 2), JDT(1404, 1, 4), inc=True),
                         [JDT(1404, 1, 2), JDT(1404, 1, 3), JDT(1404, 1, 4)])
        unbounded = recurrence.Recurrence(start, rrules=[recurrence.Rule(recurrence.DAILY)])
        with self.assertRaises(recurrence.UnboundedRecurrenceError):
            unbounded.count()


class SerializationTests(unittest.TestCase):
    def round_trip(self, value):
        encoded = recurrence.serialize(value)
        self.assertEqual(recurrence.deserialize(encoded), value)
        return encoded

    def test_canonical_headers_and_ascii_output(self):
        pattern = recurrence.Recurrence(
            JDT(1405, 1, 1, 9),
            rrules=[recurrence.Rule(recurrence.YEARLY, bymonth=[1], bymonthday=[1])],
        )
        encoded = self.round_trip(pattern)
        self.assertEqual(encoded.splitlines()[:2], ["X-RECURRENCE-VERSION:2", "CALSCALE:JALALI"])
        self.assertIn("DTSTART:14050101T090000", encoded)
        self.assertIn("WKST=SA", encoded)
        self.assertFalse(any(character in encoded for character in "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"))

    def test_naive_utc_iana_and_fixed_offset_round_trip(self):
        zones = (None, datetime.timezone.utc, ZoneInfo("Asia/Tehran"),
                 datetime.timezone(datetime.timedelta(hours=3, minutes=30)))
        for zone in zones:
            with self.subTest(zone=zone):
                value = JDT(1404, 1, 1, 9, 8, 7, 654321, zone)
                encoded = recurrence.serialize_datetime(value)
                self.assertEqual(recurrence.deserialize_datetime(encoded), value)

    def test_aware_until_is_canonical_utc(self):
        tehran = ZoneInfo("Asia/Tehran")
        pattern = recurrence.Recurrence(
            JDT(1404, 1, 1, 9, tzinfo=tehran),
            rrules=[recurrence.Rule(recurrence.DAILY, until=JDT(1404, 1, 2, 9, tzinfo=tehran))],
        )
        encoded = recurrence.serialize(pattern)
        restored = recurrence.deserialize(encoded)
        self.assertIn("UNTIL=14040102T053000Z", encoded)
        self.assertEqual(restored.rrules[0].until,
                         recurrence.to_utc(pattern.rrules[0].until))

    def test_ordinal_weekdays_survive_serialization(self):
        rule = recurrence.Rule(
            recurrence.MONTHLY,
            count=4,
            byday=[recurrence.SA(1), recurrence.MO(3), recurrence.FR(-1)],
        )
        pattern = recurrence.Recurrence(JDT(1404, 1, 1), rrules=[rule])
        encoded = recurrence.serialize(pattern)
        self.assertIn("BYDAY=1SA,3MO,-1FR", encoded)
        self.assertEqual(recurrence.deserialize(encoded), pattern)

    def test_parser_accepts_persian_and_arabic_digits(self):
        persian = "X-RECURRENCE-VERSION:۲\nCALSCALE:JALALI\nDTSTART:۱۴۰۴۰۱۰۱T۰۹۰۰۰۰\nRRULE:FREQ=DAILY;COUNT=۲"
        arabic = "X-RECURRENCE-VERSION:٢\nCALSCALE:JALALI\nDTSTART:١٤٠٤٠١٠١T٠٩٠٠٠٠\nRRULE:FREQ=DAILY;COUNT=٢"
        for encoded in (persian, arabic):
            with self.subTest(encoded=encoded):
                pattern = recurrence.deserialize(encoded)
                self.assertEqual(pattern.dtstart, JDT(1404, 1, 1, 9))
                self.assertEqual(pattern.rrules[0].count, 2)

    def test_legacy_missing_headers_bad_dates_and_unknown_zones_are_rejected(self):
        invalid = (
            "DTSTART:14040101T090000\nRRULE:FREQ=DAILY",
            "X-RECURRENCE-VERSION:1\nCALSCALE:GREGORIAN\nDTSTART:20250321T090000",
            "X-RECURRENCE-VERSION:2\nCALSCALE:JALALI\nDTSTART:14041301T090000",
            "X-RECURRENCE-VERSION:2\nCALSCALE:JALALI\nDTSTART;TZID=Not/AZone:14040101T090000",
        )
        for encoded in invalid:
            with self.subTest(encoded=encoded), self.assertRaises((recurrence.DeserializationError,
                ValueError)):
                recurrence.deserialize(encoded)


class TimezonePolicyTests(unittest.TestCase):
    def test_nonexistent_local_time_is_omitted(self):
        new_york = ZoneInfo("America/New_York")
        # Gregorian 2024-03-10 02:30 is inside the DST spring-forward gap.
        start = JDT.fromgregorian(datetime=datetime.datetime(2024, 3, 9, 2, 30, tzinfo=new_york))
        end = JDT.fromgregorian(datetime=datetime.datetime(2024, 3, 11, 2, 30, tzinfo=new_york))
        values = list(recurrence.Rule(recurrence.DAILY).occurrences(start, end))
        self.assertEqual([item.togregorian().date() for item in values],
                         [datetime.date(2024, 3, 9), datetime.date(2024, 3, 11)])

    def test_repeated_local_time_uses_earlier_fold(self):
        new_york = ZoneInfo("America/New_York")
        start = JDT.fromgregorian(datetime=datetime.datetime(2024, 11, 3, 1, 30, tzinfo=new_york, fold=1))
        value = next(recurrence.Rule(recurrence.DAILY, count=1).occurrences(start))
        self.assertEqual(value.fold, 0)
        self.assertEqual(value.togregorian().utcoffset(), datetime.timedelta(hours=-4))


if __name__ == "__main__":
    unittest.main(verbosity=2)
