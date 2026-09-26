from types import SimpleNamespace

import jdatetime
import pytest

import recurrence
from recurrence import forms
from recurrence.fields import JalaliDateTimeField
from recurrence.models import Recurrence as RecurrenceModel
from tests.models import EventWithNoNulls, EventWithNulls


@pytest.mark.django_db
def test_recurrence_field_serialization_descriptor_and_database_round_trip():
    value = recurrence.Recurrence(
        dtstart=jdatetime.datetime(1404, 1, 1),
        rrules=[recurrence.Rule(recurrence.DAILY, count=2)],
    )
    field = EventWithNoNulls._meta.get_field("recurs")
    encoded = recurrence.serialize(value)

    assert field.get_internal_type() == "TextField"
    assert field.to_python(None) is None
    assert field.to_python(value) is value
    assert field.to_python(encoded) == value
    assert field.from_db_value(encoded) == value
    assert field.get_prep_value(encoded) == encoded
    assert field.get_prep_value(value) == encoded

    instance = EventWithNoNulls(recurs=encoded)
    assert instance.recurs == value
    assert field.value_to_string(instance) == encoded
    assert EventWithNoNulls.recurs.field is field

    form_field = field.formfield(required=False)
    assert isinstance(form_field, forms.RecurrenceField)
    assert isinstance(form_field.widget, forms.RecurrenceWidget)

    saved = EventWithNoNulls.objects.create(recurs=value)
    saved.refresh_from_db()
    assert saved.recurs == value
    nullable = EventWithNulls.objects.create(recurs=None)
    nullable.refresh_from_db()
    assert nullable.recurs is None


def test_jalali_datetime_field_conversion_and_validation():
    field = JalaliDateTimeField()
    value = jdatetime.datetime(1404, 1, 1, 9, 30)
    encoded = recurrence.serialize_datetime(value)

    assert field.get_internal_type() == "TextField"
    assert field.to_python(None) is None
    assert field.to_python(value) is value
    assert field.to_python(encoded) == value
    assert field.from_db_value(encoded) == value
    assert field.get_prep_value(None) is None
    assert field.get_prep_value(value) == encoded
    with pytest.raises(TypeError, match="jdatetime.datetime"):
        field.get_prep_value("1404-01-01")


@pytest.mark.django_db
def test_manager_round_trip_preserves_rules_dates_and_parameters():
    start = jdatetime.datetime(1404, 1, 1, 9, 30, 15)
    end = jdatetime.datetime(1404, 2, 1, 9, 30, 15)
    included_rule = recurrence.Rule(
        recurrence.YEARLY,
        interval=2,
        wkst=recurrence.SUNDAY,
        count=3,
        skip="BACKWARD",
        bysetpos=[-1],
        bymonth=[1],
        bymonthday=[1],
        byyearday=[1],
        byweekno=[1],
        byday=[recurrence.MO(2)],
        byhour=[9],
        byminute=[30],
        bysecond=[15],
    )
    excluded_rule = recurrence.Rule(recurrence.WEEKLY, byday=[recurrence.FR])
    value = recurrence.Recurrence(
        start,
        end,
        rrules=[included_rule],
        exrules=[excluded_rule],
        rdates=[jdatetime.datetime(1404, 1, 3, 9, 30, 15)],
        exdates=[jdatetime.datetime(1404, 1, 4, 9, 30, 15)],
    )

    model = RecurrenceModel.objects.create_from_recurrence_object(value)

    assert model.to_recurrence_object() == value
    assert model.rules.get(mode=True).to_rule_object() == included_rule
    assert model.rules.filter(mode=True).get().params.count() == 9
    assert model.rules.filter(mode=False).exists()
    assert model.dates.filter(mode=True).exists()
    assert model.dates.filter(mode=False).exists()


@pytest.mark.django_db
def test_rule_manager_accepts_a_scalar_parameter_value():
    recurrence_model = RecurrenceModel.objects.create()
    rule = SimpleNamespace(
        freq=recurrence.MONTHLY,
        interval=1,
        wkst=recurrence.SATURDAY,
        count=1,
        until=None,
        skip="OMIT",
        bymonth=1,
        **{name: () for name in recurrence.Rule.byparams if name != "bymonth"},
    )

    saved = recurrence_model.rules.model.objects.create_from_rule_object(
        True, rule, recurrence_model
    )

    assert list(saved.params.values_list("param", "value")) == [("bymonth", 1)]

