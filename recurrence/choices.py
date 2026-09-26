from django.utils.translation import gettext_lazy as _

import recurrence


FREQUENCY_CHOICES = (
    (recurrence.SECONDLY, _('Secondly')),
    (recurrence.MINUTELY, _('Minutely')),
    (recurrence.HOURLY, _('Hourly')),
    (recurrence.DAILY, _('Daily')),
    (recurrence.WEEKLY, _('Weekly')),
    (recurrence.MONTHLY, _('Monthly')),
    (recurrence.YEARLY, _('Yearly')),
)

WEEKDAY_CHOICES = (
    (recurrence.SATURDAY, _('Saturday')),
    (recurrence.SUNDAY, _('Sunday')),
    (recurrence.MONDAY, _('Monday')),
    (recurrence.TUESDAY, _('Tuesday')),
    (recurrence.WEDNESDAY, _('Wednesday')),
    (recurrence.THURSDAY, _('Thursday')),
    (recurrence.FRIDAY, _('Friday')),
)

MONTH_CHOICES = (
    (recurrence.FARVARDIN, _('Farvardin')),
    (recurrence.ORDIBEHESHT, _('Ordibehesht')),
    (recurrence.KHORDAD, _('Khordad')),
    (recurrence.TIR, _('Tir')),
    (recurrence.MORDAD, _('Mordad')),
    (recurrence.SHAHRIVAR, _('Shahrivar')),
    (recurrence.MEHR, _('Mehr')),
    (recurrence.ABAN, _('Aban')),
    (recurrence.AZAR, _('Azar')),
    (recurrence.DEY, _('Dey')),
    (recurrence.BAHMAN, _('Bahman')),
    (recurrence.ESFAND, _('Esfand')),
)

EXCLUSION = False
INCLUSION = True
MODE_CHOICES = (
    (INCLUSION, _('Inclusion')),
    (EXCLUSION, _('Exclusion')),
)
