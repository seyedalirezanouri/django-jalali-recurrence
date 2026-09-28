import logging

from django.db.models import fields
import jdatetime
import recurrence
from recurrence import exceptions, forms
from recurrence.compat import Creator


logger = logging.getLogger(__name__)

# Unreadable stored text must never make a database row inaccessible:
# reading falls back to a placeholder instead of raising.
_READ_ERRORS = (exceptions.RecurrenceError, TypeError, ValueError)


# Do not use SubfieldBase meta class because is removed in Django 1.10

class RecurrenceField(fields.Field):
    """Field that stores a `recurrence.base.Recurrence` to the database."""

    def __init__(self, include_dtstart=True, **kwargs):
        self.include_dtstart = include_dtstart
        super(RecurrenceField, self).__init__(**kwargs)

    def get_internal_type(self):
        return 'TextField'

    def to_python(self, value):
        if value is None or isinstance(value, (recurrence.Recurrence, recurrence.InvalidRecurrence)):
            return value
        value = super(RecurrenceField, self).to_python(value) or u''
        return recurrence.deserialize(value, self.include_dtstart)

    def from_db_value(self, value, *args, **kwargs):
        try:
            return self.to_python(value)
        except _READ_ERRORS as error:
            logger.warning("stored recurrence value could not be deserialized: %s", error)
            return recurrence.InvalidRecurrence(value, error)

    def get_prep_value(self, value):
        if isinstance(value, recurrence.InvalidRecurrence):
            return value.raw
        if not isinstance(value, str):
            value = recurrence.serialize(value)
        return value

    def contribute_to_class(self, cls, *args, **kwargs):
        super(RecurrenceField, self).contribute_to_class(cls, *args, **kwargs)
        setattr(cls, self.name, Creator(self))

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.RecurrenceField,
            'widget': forms.RecurrenceWidget,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class JalaliDateTimeField(fields.TextField):
    """Persist a :class:`jdatetime.datetime` as canonical Jalali text."""

    def get_internal_type(self):
        return 'TextField'

    def to_python(self, value):
        if value is None or isinstance(value, (jdatetime.datetime, recurrence.InvalidRecurrence)):
            return value
        return recurrence.deserialize_datetime(value)

    def from_db_value(self, value, *args, **kwargs):
        try:
            return self.to_python(value)
        except _READ_ERRORS as error:
            logger.warning("stored Jalali datetime value could not be deserialized: %s", error)
            return recurrence.InvalidRecurrence(value, error)

    def get_prep_value(self, value):
        if isinstance(value, recurrence.InvalidRecurrence):
            return value.raw
        if value is None:
            return None
        if not isinstance(value, jdatetime.datetime):
            raise TypeError('JalaliDateTimeField accepts jdatetime.datetime values only')
        return recurrence.serialize_datetime(value)
