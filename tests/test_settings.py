from django.conf import settings
from django.test import override_settings

from recurrence.settings import deserialize_tz


def test_deserialize_tz_prefers_recurrence_setting():
    with override_settings(RECURRENCE_USE_TZ=True, USE_TZ=False):
        assert deserialize_tz() is True


def test_deserialize_tz_falls_back_to_django_setting():
    with override_settings(RECURRENCE_USE_TZ=True, USE_TZ=True):
        del settings.RECURRENCE_USE_TZ
        assert deserialize_tz() is True
