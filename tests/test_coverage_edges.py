import datetime
from types import SimpleNamespace

import jdatetime
import pytest

import recurrence
from recurrence import forms


def test_weekday_conversion_validation_and_legacy_shape():
    assert recurrence.to_weekday("۲MO") == recurrence.MO(2)
    assert recurrence.to_weekday("1") == recurrence.Weekday(recurrence.SUNDAY)
    assert recurrence.to_weekday(SimpleNamespace(weekday=3, n=-1)) == recurrence.TU(-1)

    with pytest.raises(ValueError, match="between 0 and 6"):
        recurrence.Weekday(7)
    with pytest.raises(ValueError, match="invalid weekday"):
        recurrence.to_weekday(object())
    with pytest.raises(ValueError, match="invalid weekday"):
        recurrence.to_weekday("XX")


def test_rule_text_serialization_and_validation_edges():
    counted = recurrence.Rule(
        recurrence.YEARLY,
        interval=2,
        count=3,
        bymonth=[recurrence.FARVARDIN],
        byday=[recurrence.SA],
    )
    text = counted.to_text()
    assert "2" in text
    assert "Farvardin" in text
    assert "SA" in text
    assert "3" in text
    assert "RRULE:" in recurrence.serialize(counted)

    until = jdatetime.datetime(1404, 1, 2)
    assert until.isoformat() in recurrence.Rule(
        recurrence.DAILY, until=until
    ).to_text()

    with pytest.raises(recurrence.SerializationError):
        recurrence.serialize(object())
    with pytest.raises(recurrence.ValidationError, match="incompatible"):
        recurrence.validate(object())

    invalid = recurrence.Rule(recurrence.DAILY)
    object.__setattr__(invalid, "freq", 99)
    with pytest.raises(recurrence.ValidationError, match="invalid freq"):
        recurrence.validate(invalid)


def test_recurrence_protocol_and_query_errors():
    start = jdatetime.datetime(1404, 1, 1)
    value = recurrence.Recurrence(
        start,
        rrules=[recurrence.Rule(recurrence.DAILY, count=2)],
    )

    assert bool(value)
    assert str(value) == recurrence.serialize(value)
    assert list(value) == [start, jdatetime.datetime(1404, 1, 2)]
    assert recurrence.to_utc(None) is None

    with pytest.raises(TypeError, match="query bounds"):
        value.after("tomorrow")
    with pytest.raises(TypeError, match="aware and naive"):
        value.after(datetime.datetime(2025, 3, 21, tzinfo=datetime.timezone.utc))


@pytest.mark.parametrize(
    "text",
    [
        "X-RECURRENCE-VERSION:2\nCALSCALE:JALALI\nRRULE:DAILY",
        "X-RECURRENCE-VERSION:2\nCALSCALE:JALALI\nRRULE:FREQ=INVALID",
    ],
)
def test_rule_parser_reports_malformed_parameters(text):
    with pytest.raises(recurrence.DeserializationError):
        recurrence.deserialize(text)


def test_form_field_handles_deserializer_type_error(monkeypatch):
    def fail(value):
        raise TypeError

    monkeypatch.setattr(forms.recurrence, "deserialize", fail)
    assert forms.RecurrenceField().clean("value") is None


def test_form_field_allows_values_at_configured_limits():
    value = recurrence.serialize(
        recurrence.Recurrence(
            rrules=[recurrence.Rule(recurrence.DAILY)],
            exrules=[recurrence.Rule(recurrence.WEEKLY)],
            rdates=[jdatetime.datetime(1404, 1, 1)],
            exdates=[jdatetime.datetime(1404, 1, 2)],
        )
    )
    field = forms.RecurrenceField(
        max_rrules=1,
        max_exrules=1,
        max_rdates=1,
        max_exdates=1,
    )

    assert field.clean(value) == recurrence.deserialize(value)
