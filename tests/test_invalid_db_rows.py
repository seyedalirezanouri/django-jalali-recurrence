import jdatetime
import pytest
from django.db import connection

import recurrence
from recurrence.fields import JalaliDateTimeField
from tests.models import EventWithNoNulls

VALID_TEXT = recurrence.serialize(
    recurrence.Recurrence(
        jdatetime.datetime(1404, 1, 1),
        rrules=[recurrence.Rule(recurrence.DAILY)],
    )
)


def _create_corrupt_row(text):
    obj = EventWithNoNulls.objects.create(recurs=VALID_TEXT)
    table = EventWithNoNulls._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} SET recurs = %s WHERE id = %s",
            [text, obj.id],
        )
    return obj


@pytest.mark.django_db
def test_invalid_row_loads_as_placeholder_and_keeps_raw_text_on_save():
    obj = _create_corrupt_row("this is not a recurrence")

    loaded = EventWithNoNulls.objects.get(id=obj.id)

    assert isinstance(loaded.recurs, recurrence.InvalidRecurrence)
    assert loaded.recurs.raw == "this is not a recurrence"
    assert isinstance(loaded.recurs.error, recurrence.DeserializationError)
    assert str(loaded.recurs) == "this is not a recurrence"

    loaded.save()
    reloaded = EventWithNoNulls.objects.get(id=obj.id)
    assert isinstance(reloaded.recurs, recurrence.InvalidRecurrence)
    assert reloaded.recurs.raw == "this is not a recurrence"


@pytest.mark.django_db
def test_invalid_row_can_be_deleted_from_queryset():
    obj = _create_corrupt_row("garbage")
    EventWithNoNulls.objects.create(recurs=VALID_TEXT)

    loaded = EventWithNoNulls.objects.get(id=obj.id)
    assert not loaded.recurs

    EventWithNoNulls.objects.all().delete()
    assert not EventWithNoNulls.objects.filter(id=obj.id).exists()


@pytest.mark.django_db
def test_legacy_rfc2445_rows_stay_accessible():
    legacy = "DTSTART:20210321T000000Z\nRRULE:FREQ=DAILY"
    obj = _create_corrupt_row(legacy)

    loaded = EventWithNoNulls.objects.get(id=obj.id)

    assert isinstance(loaded.recurs, recurrence.InvalidRecurrence)
    assert loaded.recurs.raw == legacy
    loaded.delete()
    assert not EventWithNoNulls.objects.filter(id=obj.id).exists()


def test_assigning_invalid_text_in_code_still_raises():
    field = EventWithNoNulls._meta.get_field("recurs")

    with pytest.raises(recurrence.DeserializationError):
        field.to_python("this is not a recurrence")
    with pytest.raises(recurrence.DeserializationError):
        EventWithNoNulls(recurs="this is not a recurrence")

    placeholder = recurrence.InvalidRecurrence("x")
    assert field.to_python(placeholder) is placeholder


def test_invalid_recurrence_placeholder_protocol():
    first = recurrence.InvalidRecurrence("x", recurrence.DeserializationError("bad"))
    second = recurrence.InvalidRecurrence("x", first.error)

    assert first == second
    assert hash(first) == hash(second)
    assert first != recurrence.InvalidRecurrence("y")
    assert first != "x"
    assert not first
    assert str(first) == "x"
    assert "InvalidRecurrence" in repr(first)
    assert "x" in repr(first)


def test_jalali_datetime_field_tolerates_invalid_stored_text():
    field = JalaliDateTimeField()
    valid = recurrence.serialize_datetime(jdatetime.datetime(1404, 1, 1, 9, 30))

    assert field.from_db_value(valid) == jdatetime.datetime(1404, 1, 1, 9, 30)

    value = field.from_db_value("not-a-datetime")
    assert isinstance(value, recurrence.InvalidRecurrence)
    assert value.raw == "not-a-datetime"
    assert isinstance(value.error, recurrence.DeserializationError)
    assert field.to_python(value) is value
    assert field.get_prep_value(value) == "not-a-datetime"

    with pytest.raises(recurrence.DeserializationError):
        field.to_python("not-a-datetime")
