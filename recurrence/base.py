"""Jalali recurrence primitives and the version 2 wire format."""

from __future__ import annotations

import datetime
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dataclasses import dataclass, field
from typing import Iterator, Optional

from django.utils.translation import gettext as _
import jdatetime

from recurrence import exceptions

YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY, SECONDLY = range(7)
FREQUENCIES = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY")
FARVARDIN, ORDIBEHESHT, KHORDAD, TIR, MORDAD, SHAHRIVAR = range(1, 7)
MEHR, ABAN, AZAR, DEY, BAHMAN, ESFAND = range(7, 13)
MONTHS = ("FARVARDIN", "ORDIBEHESHT", "KHORDAD", "TIR", "MORDAD", "SHAHRIVAR", "MEHR", "ABAN", "AZAR", "DEY", "BAHMAN", "ESFAND")
SATURDAY, SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY = range(7)
WEEKDAYS = ("SA", "SU", "MO", "TU", "WE", "TH", "FR")
SKIP_VALUES = ("OMIT", "BACKWARD", "FORWARD")


def _days_in_month(year, month):
    first = jdatetime.date(year, month, 1)
    next_month = jdatetime.date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    return (next_month - first).days


def _days_in_year(year):
    return (jdatetime.date(year + 1, 1, 1) - jdatetime.date(year, 1, 1)).days


def _normalize_digits(value):
    return value.translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    ))


class UnboundedRecurrenceError(exceptions.RecurrenceError):
    """Raised when a finite endpoint is required but not supplied."""


@dataclass(frozen=True, slots=True)
class Weekday:
    number: int
    index: Optional[int] = None

    def __post_init__(self):
        if not 0 <= self.number <= 6:
            raise ValueError("weekday must be between 0 and 6")

    def __call__(self, index: int):
        return type(self)(self.number, index)

    weekday = property(lambda self: self.number)
    n = property(lambda self: self.index)

    def __repr__(self):
        return f"{self.index or ''}{WEEKDAYS[self.number]}"


SA, SU, MO, TU, WE, TH, FR = [Weekday(i) for i in range(7)]


def to_weekday(token) -> Weekday:
    if isinstance(token, Weekday):
        return token
    if isinstance(token, int):
        return Weekday(token)
    if hasattr(token, "weekday") and hasattr(token, "n"):
        return Weekday(int(token.weekday), token.n)
    if not isinstance(token, str):
        raise ValueError("invalid weekday")
    token = _normalize_digits(token).upper()
    if token.isdigit():
        return Weekday(int(token))
    if token[-2:] not in WEEKDAYS:
        raise ValueError("invalid weekday")
    index = int(token[:-2]) if token[:-2] else None
    return Weekday(WEEKDAYS.index(token[-2:]), index)


def _require_jalali(value, name):
    if value is not None and not isinstance(value, jdatetime.datetime):
        raise TypeError(f"{name} must be jdatetime.datetime; Gregorian datetime is unsupported")


def _shift_month(value: jdatetime.datetime, amount: int) -> jdatetime.datetime:
    index = value.year * 12 + value.month - 1 + amount
    year, month0 = divmod(index, 12)
    month = month0 + 1
    return value.replace(year=year, month=month, day=min(value.day, _days_in_month(year, month)))


def _shift_year(value: jdatetime.datetime, amount: int) -> jdatetime.datetime:
    year = value.year + amount
    return value.replace(year=year, day=min(value.day, _days_in_month(year, value.month)))


def _day_delta(a: jdatetime.datetime, b: jdatetime.datetime) -> int:
    return (a.togregorian().date() - b.togregorian().date()).days


def _valid_local_time(value: jdatetime.datetime) -> Optional[jdatetime.datetime]:
    """Apply the v2 timezone policy: drop gaps and choose fold zero."""
    if value.tzinfo is None:
        return value
    # ``datetime.timezone`` has no DST transitions.  The UTC round-trip below
    # is useful for ZoneInfo, but is needlessly expensive for fixed offsets.
    if isinstance(value.tzinfo, datetime.timezone):
        return value.replace(fold=0)
    candidate = value.replace(fold=0)
    gregorian = candidate.togregorian()
    # A direct astimezone() to the same zone is a no-op.  Passing through UTC
    # forces zoneinfo to normalize gaps and folds.
    roundtrip = jdatetime.datetime.fromgregorian(
        datetime=gregorian.astimezone(datetime.timezone.utc).astimezone(value.tzinfo)
    )
    if (roundtrip.year, roundtrip.month, roundtrip.day, roundtrip.hour,
            roundtrip.minute, roundtrip.second, roundtrip.microsecond) != (
            candidate.year, candidate.month, candidate.day, candidate.hour,
            candidate.minute, candidate.second, candidate.microsecond):
        return None
    return candidate


@dataclass(frozen=True, slots=True)
class Rule:
    freq: int
    interval: int = 1
    wkst: int = SATURDAY
    count: Optional[int] = None
    until: Optional[jdatetime.datetime] = None
    bysetpos: tuple = field(default_factory=tuple)
    bymonth: tuple = field(default_factory=tuple)
    bymonthday: tuple = field(default_factory=tuple)
    byyearday: tuple = field(default_factory=tuple)
    byweekno: tuple = field(default_factory=tuple)
    byday: tuple = field(default_factory=tuple)
    byhour: tuple = field(default_factory=tuple)
    byminute: tuple = field(default_factory=tuple)
    bysecond: tuple = field(default_factory=tuple)
    skip: str = "OMIT"

    byparams = ("bysetpos", "bymonth", "bymonthday", "byyearday", "byweekno", "byday", "byhour", "byminute", "bysecond")
    frequencies = FREQUENCIES
    weekdays = WEEKDAYS

    def __init__(self, freq, interval=1, wkst=SATURDAY, count=None, until=None, skip="OMIT", **kwargs):
        object.__setattr__(self, "freq", int(freq))
        object.__setattr__(self, "interval", int(interval))
        object.__setattr__(self, "wkst", SATURDAY if wkst is None else to_weekday(wkst).number)
        object.__setattr__(self, "count", None if count is None else int(count))
        _require_jalali(until, "until")
        object.__setattr__(self, "until", until)
        skip = str(skip).upper()
        if skip not in SKIP_VALUES:
            raise ValueError("skip must be OMIT, BACKWARD or FORWARD")
        object.__setattr__(self, "skip", skip)
        for param in self.byparams:
            value = kwargs.get(param, ())
            if value is None:
                value = ()
            elif not isinstance(value, (tuple, list)):
                value = (value,)
            if param == "byday":
                value = tuple(to_weekday(v) for v in value)
            else:
                value = tuple(int(v) for v in value)
            object.__setattr__(self, param, value)
        validate(self)

    def to_text(self, short=False):
        return rule_to_text(self, short)

    def _matches_day(self, value: jdatetime.datetime) -> bool:
        if self.bymonth and value.month not in self.bymonth:
            return False
        if self.bymonthday:
            length = _days_in_month(value.year, value.month)
            valid = {day if day > 0 else length + day + 1 for day in self.bymonthday}
            if self.skip == "BACKWARD":
                valid.update(length for day in self.bymonthday if day > length)
            if self.skip == "FORWARD" and value.day == 1:
                previous = _shift_month(value, -1)
                previous_length = _days_in_month(previous.year, previous.month)
                if any(day > previous_length for day in self.bymonthday):
                    return True
            if value.day not in valid:
                return False
        if self.byyearday:
            day = value.day + sum(_days_in_month(value.year, month) for month in range(1, value.month))
            valid = {n if n > 0 else _days_in_year(value.year) + n + 1 for n in self.byyearday}
            if day not in valid:
                return False
        if self.byweekno:
            year_start = jdatetime.datetime(value.year, 1, 1)
            first = year_start - datetime.timedelta(days=year_start.weekday())
            week = _day_delta(value, first) // 7 + 1
            total = (_days_in_year(value.year) + first.weekday() + 6) // 7
            valid = {n if n > 0 else total + n + 1 for n in self.byweekno}
            if week not in valid:
                return False
        if self.byday:
            if self.bysetpos and all(day.index is None for day in self.byday):
                matching = [day for day in range(1, _days_in_month(value.year, value.month) + 1)
                            if jdatetime.datetime(value.year, value.month, day).weekday() in {item.number for item in self.byday}]
                selected = {matching[pos - 1] if pos > 0 else matching[pos] for pos in self.bysetpos if -len(matching) <= pos <= len(matching)}
                if value.day not in selected:
                    return False
            found = False
            for day in self.byday:
                if value.weekday() != day.number:
                    continue
                if day.index is None:
                    found = True
                elif day.index > 0:
                    first = value.replace(day=1)
                    found = value.day == 1 + (day.number - first.weekday()) % 7 + (day.index - 1) * 7
                else:
                    last = value.replace(day=_days_in_month(value.year, value.month))
                    found = value.day == last.day - (last.weekday() - day.number) % 7 + (day.index + 1) * 7
                if found:
                    break
            if not found:
                return False
        return True

    def _times(self, value):
        for hour in self.byhour or (value.hour,):
            for minute in self.byminute or (value.minute,):
                for second in self.bysecond or (value.second,):
                    yield value.replace(hour=hour, minute=minute, second=second)

    def _period_matches(self, value, seed):
        if self.freq == YEARLY:
            if (value.year - seed.year) % self.interval:
                return False
            if self.bymonth or self.bymonthday or self.byyearday or self.byweekno or self.byday or self.bysetpos:
                return True
            return value.month == seed.month and value.day == seed.day
        if self.freq == MONTHLY:
            if (value.year * 12 + value.month - seed.year * 12 - seed.month) % self.interval:
                return False
            if self.bymonth or self.bymonthday or self.byday or self.bysetpos:
                return True
            return value.day == seed.day
        if self.freq in (WEEKLY, DAILY):
            days = _day_delta(value, seed)
            if days < 0:
                return False
            if self.freq == WEEKLY:
                if self.byday:
                    value_week = value - datetime.timedelta(days=value.weekday())
                    seed_week = seed - datetime.timedelta(days=seed.weekday())
                    return _day_delta(value_week, seed_week) // 7 % self.interval == 0
                return days % (7 * self.interval) == 0
            return days % self.interval == 0
        seconds = (value.togregorian() - seed.togregorian()).total_seconds()
        divisor = {HOURLY: 3600, MINUTELY: 60, SECONDLY: 1}[self.freq] * self.interval
        return seconds >= 0 and seconds % divisor == 0

    def _next(self, value):
        if self.freq == YEARLY and not (self.bymonth or self.bymonthday or self.byyearday or self.byweekno or self.byday or self.bysetpos):
            return _shift_year(value, 1)
        if self.freq == MONTHLY and not (self.bymonth or self.bymonthday or self.byday or self.bysetpos):
            return _shift_month(value, 1)
        if self.freq in (YEARLY, MONTHLY):
            return value + datetime.timedelta(days=1)
        if self.freq in (WEEKLY, DAILY):
            return value + datetime.timedelta(days=1)
        return value + datetime.timedelta(seconds={HOURLY: 3600, MINUTELY: 60, SECONDLY: 1}[self.freq])

    def _seek(self, seed, lower):
        """Return a cursor at (or immediately before) ``lower``.

        The recurrence anchor remains ``seed``; only the enumeration cursor is
        moved.  This is what lets range queries preserve INTERVAL semantics
        without replaying years of history.
        """
        if lower is None or lower <= seed or self.count is not None:
            return seed

        selectors = self.bymonth or self.bymonthday or self.byyearday or self.byweekno or self.byday or self.bysetpos
        # Repeated month/year stepping intentionally carries clamped days
        # forward (31st -> 29th/30th, for example).  Direct jumps are
        # equivalent only for dates that cannot be clamped.
        if self.freq == YEARLY and not selectors and seed.day <= 28:
            periods = max(0, lower.year - seed.year) // self.interval
            cursor = _shift_year(seed, periods * self.interval)
            if cursor > lower and periods:
                cursor = _shift_year(cursor, -self.interval)
            return cursor
        if self.freq == MONTHLY and not selectors and seed.day <= 28:
            months = max(0, (lower.year - seed.year) * 12 + lower.month - seed.month)
            periods = months // self.interval
            cursor = _shift_month(seed, periods * self.interval)
            if cursor > lower and periods:
                cursor = _shift_month(cursor, -self.interval)
            return cursor

        if self.freq in (YEARLY, MONTHLY, WEEKLY, DAILY):
            days = max(0, _day_delta(lower, seed))
            return seed + datetime.timedelta(days=days)

        seconds = max(0, int((lower.togregorian() - seed.togregorian()).total_seconds()))
        unit = {HOURLY: 3600, MINUTELY: 60, SECONDLY: 1}[self.freq]
        return seed + datetime.timedelta(seconds=(seconds // unit) * unit)

    def _occurrences(self, dtstart, dtend=None, lower=None) -> Iterator[jdatetime.datetime]:
        _require_jalali(dtstart, "dtstart")
        dtstart = _valid_local_time(dtstart) or dtstart
        if dtend is None:
            dtend = self.until or jdatetime.datetime(
                jdatetime.datetime.max.year, jdatetime.datetime.max.month,
                jdatetime.datetime.max.day, 23, 59, 59, 999999,
                tzinfo=dtstart.tzinfo,
            )
        end = min(dtend, self.until) if self.until else dtend
        cursor, emitted = self._seek(dtstart, lower), 0
        while cursor <= end:
            if self._period_matches(cursor, dtstart):
                candidates = sorted({candidate for candidate in self._times(cursor) if self._matches_day(candidate)})
                if self.bysetpos and candidates:
                    selected = []
                    for pos in self.bysetpos:
                        index = pos - 1 if pos > 0 else pos
                        if -len(candidates) <= index < len(candidates):
                            selected.append(candidates[index])
                    candidates = selected
                for candidate in candidates:
                    candidate = _valid_local_time(candidate)
                    if candidate is None:
                        continue
                    if candidate < dtstart or candidate > end:
                        continue
                    emitted += 1
                    yield candidate
                    if self.count is not None and emitted >= self.count:
                        return
            cursor = self._next(cursor)

    def occurrences(self, dtstart, dtend=None) -> Iterator[jdatetime.datetime]:
        return self._occurrences(dtstart, dtend)


class Recurrence:
    def __init__(self, dtstart=None, dtend=None, rrules=(), exrules=(), rdates=(), exdates=(), include_dtstart=True):
        for name, value in (("dtstart", dtstart), ("dtend", dtend)):
            _require_jalali(value, name)
        for name, values in (("rdates", rdates), ("exdates", exdates)):
            for value in values:
                _require_jalali(value, name)
        self.dtstart, self.dtend = dtstart, dtend
        self.rrules, self.exrules = tuple(rrules), tuple(exrules)
        self.rdates, self.exdates = tuple(rdates), tuple(exdates)
        self.include_dtstart = bool(include_dtstart)
        timezone_kinds = {
            value.tzinfo is not None
            for value in (
                self.dtstart,
                self.dtend,
                *self.rdates,
                *self.exdates,
                *(rule.until for rule in self.rrules),
                *(rule.until for rule in self.exrules),
            )
            if value is not None
        }
        if len(timezone_kinds) > 1:
            raise TypeError("aware and naive JalaliDateTime values cannot be mixed")
        validate(self)

    def __iter__(self):
        return self.occurrences()

    def __str__(self):
        return serialize(self)

    def __bool__(self):
        return bool(self.dtstart or self.dtend or self.rrules or self.exrules or self.rdates or self.exdates)

    def __eq__(self, other):
        return isinstance(other, Recurrence) and self.__dict__ == other.__dict__

    def _start(self, value):
        return value or self.dtstart or jdatetime.datetime.now()

    @staticmethod
    def _query_datetime(value, reference):
        """Normalize a public query bound to the recurrence calendar."""
        if value is None or isinstance(value, jdatetime.datetime):
            return value
        if not isinstance(value, datetime.datetime):
            raise TypeError("query bounds must be datetime or jdatetime.datetime")
        if reference.tzinfo is not None:
            if value.tzinfo is None:
                raise TypeError("aware and naive datetime values cannot be mixed")
            value = value.astimezone(reference.tzinfo)
        elif value.tzinfo is not None:
            raise TypeError("aware and naive datetime values cannot be mixed")
        return jdatetime.datetime.fromgregorian(datetime=value)

    def _window_occurrences(self, dtstart=None, dtend=None, lower=None, filter_lower=True):
        start = self._start(dtstart)
        start = self._query_datetime(start, start) if not isinstance(start, jdatetime.datetime) else start
        end = dtend or self.dtend
        end = self._query_datetime(end, start)
        lower = self._query_datetime(lower, start)
        if end is None and not any(rule.count is not None or rule.until is not None for rule in self.rrules):
            raise UnboundedRecurrenceError("occurrences() requires dtend for an unbounded recurrence")

        values = set(self.rdates)
        if self.include_dtstart and (dtstart or self.dtstart):
            values.add(start)
        for rule in self.rrules:
            values.update(rule._occurrences(start, end, lower))

        excluded = set(self.exdates)
        for rule in self.exrules:
            excluded.update(rule._occurrences(start, end, lower))

        for value in sorted(values):
            if (end is None or value <= end) and (not filter_lower or lower is None or value >= lower) and value not in excluded:
                yield value
        if self.dtend and end and start <= self.dtend <= end and self.dtend not in excluded:
            if self.dtend not in values and (not filter_lower or lower is None or self.dtend >= lower):
                yield self.dtend

    def occurrences(self, dtstart=None, dtend=None, cache=False):
        yield from self._window_occurrences(dtstart, dtend)

    def count(self, dtstart=None, dtend=None, cache=False):
        if dtend is None and self.dtend is None and not any(rule.count is not None or rule.until is not None for rule in self.rrules):
            raise UnboundedRecurrenceError("count() requires a finite recurrence")
        return sum(1 for _ in self.occurrences(dtstart, dtend, cache))

    def before(self, dt, inc=False, dtstart=None, dtend=None, cache=False):
        start = self._start(dtstart)
        bound = self._query_datetime(dt, start)
        # A bounded look-back covers the largest possible gap of each rule.
        # RDATE values are retained independently, so old explicit dates are
        # not lost by this optimization.
        spans = []
        for rule in self.rrules:
            if rule.freq == YEARLY:
                spans.append(366 * rule.interval + 2)
            elif rule.freq == MONTHLY:
                spans.append(31 * rule.interval + 2)
            elif rule.freq == WEEKLY:
                spans.append(7 * rule.interval + 2)
            else:
                spans.append(2)
        lower = bound - datetime.timedelta(days=max(spans or [2]))
        end = self._query_datetime(dtend, start) if dtend else bound
        if end is not None:
            end = min(end, bound)
        values = [value for value in self._window_occurrences(dtstart, end, lower, filter_lower=False)
                  if value < bound or inc and value == bound]
        return values[-1] if values else None

    def after(self, dt, inc=False, dtstart=None, dtend=None, cache=False):
        start = self._start(dtstart)
        bound = self._query_datetime(dt, start)
        for value in self._window_occurrences(dtstart, dtend, bound):
            if value > bound or inc and value == bound:
                return value
        return None

    def between(self, after, before, inc=False, dtstart=None, dtend=None, cache=False):
        start = self._start(dtstart)
        lower = self._query_datetime(after, start)
        upper = self._query_datetime(before, start)
        if dtend is not None:
            requested_end = self._query_datetime(dtend, start)
            upper = min(upper, requested_end)
        values = self._window_occurrences(dtstart, upper, lower)
        return [value for value in values
                if (value > lower or inc and value == lower)
                and (value < upper or inc and value == upper)]


class InvalidRecurrence:
    """Placeholder for stored recurrence text this library cannot parse.

    Model fields return this instead of raising when a database row
    contains unreadable text (legacy formats, corrupted data, ...), so
    the row stays accessible, editable and deletable.

    Attributes:
        `raw`: the original stored text. Saving the instance writes it
            back to the database unchanged, so no data is lost.
        `error`: the exception raised while parsing `raw`, or `None`.

    Evaluates as false, so ``if value:`` guards skip it instead of
    attempting to use it as a `Recurrence`.
    """

    def __init__(self, raw, error=None):
        self.raw = raw
        self.error = error

    def __str__(self):
        return str(self.raw)

    def __repr__(self):
        return f"InvalidRecurrence({self.raw!r}, error={self.error!r})"

    def __bool__(self):
        return False

    def __eq__(self, other):
        if not isinstance(other, InvalidRecurrence):
            return NotImplemented
        return (self.raw, self.error) == (other.raw, other.error)

    def __hash__(self):
        return hash((self.raw, self.error))


def validate(obj):
    if not isinstance(obj, (Rule, Recurrence)):
        raise exceptions.ValidationError("incompatible object")
    rules = [obj] if isinstance(obj, Rule) else list(obj.rrules) + list(obj.exrules)
    for rule in rules:
        if not 0 <= rule.freq < len(FREQUENCIES):
            raise exceptions.ValidationError(f"invalid freq parameter: {rule.freq}")
        if rule.interval < 1 or rule.count is not None and rule.count < 1:
            raise exceptions.ValidationError("invalid interval/count parameter")
        if any(month < 1 or month > 12 for month in rule.bymonth):
            raise exceptions.ValidationError("invalid bymonth parameter")
    return None


def _format_dt(value):
    text = value.strftime("%Y%m%dT%H%M%S")
    if value.microsecond:
        text += f".{value.microsecond:06d}"
    if value.tzinfo is datetime.timezone.utc:
        text += "Z"
    return text


def _format_until(value):
    """Format an UNTIL value as an aware UTC Jalali timestamp when needed."""
    if value.tzinfo is not None:
        value = jdatetime.datetime.fromgregorian(
            datetime=value.togregorian().astimezone(datetime.timezone.utc)
        )
        return _format_dt(value)
    return _format_dt(value)


def _dt_property(label, value):
    parameter = ""
    if value.tzinfo is not None and value.tzinfo is not datetime.timezone.utc:
        key = getattr(value.tzinfo, "key", None)
        if key:
            parameter = f";TZID={key}"
        else:
            offset = value.togregorian().utcoffset()
            if offset is not None:
                seconds = int(offset.total_seconds())
                sign = "+" if seconds >= 0 else "-"
                seconds = abs(seconds)
                parameter = f";TZOFFSET={sign}{seconds // 3600:02d}{(seconds % 3600) // 60:02d}"
    return f"{label}{parameter}:{_format_dt(value)}"


def _serialize_rule(rule):
    parts = [("FREQ", FREQUENCIES[rule.freq])]
    if rule.interval != 1: parts.append(("INTERVAL", str(rule.interval)))
    # Keep the week origin explicit in the canonical v2 representation.
    parts.append(("WKST", WEEKDAYS[rule.wkst]))
    if rule.count is not None: parts.append(("COUNT", str(rule.count)))
    elif rule.until is not None: parts.append(("UNTIL", _format_until(rule.until)))
    if rule.skip != "OMIT": parts.append(("SKIP", rule.skip))
    for name in rule.byparams:
        values = getattr(rule, name)
        if values:
            parts.append((name.upper(), ",".join(repr(v) if name == "byday" else str(v) for v in values)))
    return ";".join(f"{name}={value}" for name, value in parts)


def serialize(value):
    if value is None:
        return None
    if isinstance(value, Rule):
        value = Recurrence(rrules=(value,))
    if not isinstance(value, Recurrence):
        raise exceptions.SerializationError("expected Jalali Rule or Recurrence")
    validate(value)
    lines = ["X-RECURRENCE-VERSION:2", "CALSCALE:JALALI"]
    if value.dtstart: lines.append(_dt_property("DTSTART", value.dtstart))
    if value.dtend: lines.append(_dt_property("DTEND", value.dtend))
    lines.extend(f"RRULE:{_serialize_rule(rule)}" for rule in value.rrules)
    lines.extend(f"EXRULE:{_serialize_rule(rule)}" for rule in value.exrules)
    lines.extend(_dt_property("RDATE", date) for date in value.rdates)
    lines.extend(_dt_property("EXDATE", date) for date in value.exdates)
    return "\n".join(lines)


_LINE_RE = re.compile(r"^(X-RECURRENCE-VERSION|CALSCALE|DTSTART|DTEND|RRULE|EXRULE|RDATE|EXDATE)(?:;([^:]+))?:(.*)$")


def _parse_dt(text, params=None):
    text = _normalize_digits(text.strip())
    utc = text.endswith("Z")
    if utc: text = text[:-1]
    match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})(?:\.(\d{1,6}))?", text)
    if not match:
        raise exceptions.DeserializationError(f"malformed Jalali date-time: {text!r}")
    year, month, day, hour, minute, second, micro = match.groups()
    tzinfo = datetime.timezone.utc if utc else None
    params = params or ""
    for parameter in params.split(";"):
        if not parameter or "=" not in parameter:
            continue
        key, value = parameter.split("=", 1)
        if key.upper() == "TZID":
            try:
                tzinfo = ZoneInfo(value)
            except ZoneInfoNotFoundError as error:
                raise exceptions.DeserializationError(f"unknown timezone: {value}") from error
        elif key.upper() == "TZOFFSET":
            sign = -1 if value.startswith("-") else 1
            digits = value.lstrip("+-")
            tzinfo = datetime.timezone(sign * datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))
    return jdatetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), int((micro or "0").ljust(6, "0")), tzinfo)


def serialize_datetime(value):
    _require_jalali(value, "datetime")
    property_value = _dt_property("DT", value)
    prefix, date = property_value.split(":", 1)
    return prefix[2:] + "|" + date


def deserialize_datetime(value):
    value = str(value)
    params = ""
    if "|" in value:
        params, value = value.split("|", 1)
    return _parse_dt(value, params)


def deserialize(text, include_dtstart=True):
    if not text:
        return Recurrence(include_dtstart=include_dtstart)
    text = _normalize_digits(str(text))
    version = scale = None
    dtstart = dtend = None
    rrules, exrules, rdates, exdates = [], [], [], []
    for raw in text.splitlines():
        match = _LINE_RE.match(raw.strip())
        if not match:
            raise exceptions.DeserializationError("malformed Jalali recurrence")
        label, params, value = match.groups()
        if label == "X-RECURRENCE-VERSION": version = value
        elif label == "CALSCALE": scale = value.upper()
        elif label == "DTSTART": dtstart = _parse_dt(value, params)
        elif label == "DTEND": dtend = _parse_dt(value, params)
        elif label in ("RDATE", "EXDATE"):
            (rdates if label == "RDATE" else exdates).extend(_parse_dt(item, params) for item in value.split(","))
        else:
            params_dict = {}
            for item in value.split(";"):
                if "=" not in item: raise exceptions.DeserializationError("missing rule parameter value")
                key, val = item.split("=", 1)
                params_dict[key.upper()] = val.split(",")
            try: freq = FREQUENCIES.index(params_dict.pop("FREQ")[0])
            except (KeyError, ValueError): raise exceptions.DeserializationError("frequency parameter missing or invalid")
            kwargs = {}
            for key, values in params_dict.items():
                key = key.lower()
                if key == "wkst": kwargs[key] = to_weekday(values[0]).number
                elif key == "until": kwargs[key] = _parse_dt(values[0])
                elif key == "byday": kwargs[key] = [to_weekday(v) for v in values]
                elif key in Rule.byparams or key in ("interval", "count", "skip"):
                    kwargs[key] = int(values[0]) if key in ("interval", "count") else values[0]
            (rrules if label == "RRULE" else exrules).append(Rule(freq, **kwargs))
    if version != "2" or scale != "JALALI":
        raise exceptions.DeserializationError("legacy or non-Jalali recurrence data is unsupported")
    return Recurrence(dtstart, dtend, rrules, exrules, rdates, exdates, include_dtstart)


def rule_to_text(rule, short=False):
    names = (_("annually"), _("monthly"), _("weekly"), _("daily"), _("hourly"), _("minutely"), _("secondly"))
    units = (_("years"), _("months"), _("weeks"), _("days"), _("hours"), _("minutes"), _("seconds"))
    text = _("every %(number)s %(unit)s") % {"number": rule.interval, "unit": units[rule.freq]} if rule.interval > 1 else names[rule.freq]
    if rule.bymonth:
        text += _(", each %(months)s") % {"months": _(", ").join(MONTHS[m - 1].title() for m in rule.bymonth)}
    if rule.byday:
        text += _(", on %(days)s") % {"days": _(", ").join(WEEKDAYS[d.number] for d in rule.byday)}
    if rule.count:
        text += _(", occurring %(number)s times") % {"number": rule.count}
    elif rule.until:
        text += _(", until %(date)s") % {"date": rule.until.isoformat()}
    return text


def to_utc(value):
    if value is None:
        return None
    _require_jalali(value, "datetime")
    value = value.togregorian()
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return jdatetime.datetime.fromgregorian(datetime=value.astimezone(datetime.timezone.utc))
