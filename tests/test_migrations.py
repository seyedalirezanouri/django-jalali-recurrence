import datetime

import jdatetime
import pytest
from django.apps import apps
from django.db import connection
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState

import recurrence
from recurrence.models import Date, Recurrence, Rule


LATEST_MIGRATION = ("recurrence", "0003_jalali_storage")
PRE_JALALI_MIGRATION = (
    "recurrence",
    "0002_alter_date_id_alter_param_id_alter_recurrence_id_and_more",
)


def test_migration_state_matches_current_models():
    loader = MigrationLoader(None)
    migration_state = loader.project_state()
    model_state = ProjectState.from_apps(apps)

    changes = MigrationAutodetector(migration_state, model_state).changes(
        graph=loader.graph,
        trim_to_apps={"recurrence"},
    )

    assert changes.get("recurrence", []) == []


@pytest.mark.django_db
def test_jalali_model_fields_round_trip_through_database():
    start = jdatetime.datetime(1404, 1, 1, 9, 30)
    end = jdatetime.datetime(1404, 1, 3, 9, 30)
    recurrence_model = Recurrence.objects.create(dtstart=start, dtend=end)
    rule = Rule.objects.create(
        recurrence=recurrence_model,
        freq=recurrence.DAILY,
        until=end,
    )
    date = Date.objects.create(recurrence=recurrence_model, dt=start)

    recurrence_model.refresh_from_db()
    rule.refresh_from_db()
    date.refresh_from_db()

    assert recurrence_model.dtstart == start
    assert recurrence_model.dtend == end
    assert rule.until == end
    assert date.dt == start
    assert isinstance(recurrence_model.dtstart, jdatetime.datetime)
    assert isinstance(rule.until, jdatetime.datetime)
    assert isinstance(date.dt, jdatetime.datetime)


@pytest.mark.django_db(transaction=True)
def test_jalali_migration_rejects_legacy_gregorian_rows():
    executor = MigrationExecutor(connection)
    executor.migrate([PRE_JALALI_MIGRATION])
    old_apps = executor.loader.project_state([PRE_JALALI_MIGRATION]).apps
    legacy_recurrence = old_apps.get_model("recurrence", "Recurrence")
    legacy_recurrence.objects.create(
        dtstart=datetime.datetime(2025, 3, 21, tzinfo=datetime.timezone.utc)
    )

    try:
        with pytest.raises(RuntimeError, match="existing recurrence rows"):
            MigrationExecutor(connection).migrate([LATEST_MIGRATION])
    finally:
        legacy_recurrence.objects.all().delete()
        MigrationExecutor(connection).migrate([LATEST_MIGRATION])
