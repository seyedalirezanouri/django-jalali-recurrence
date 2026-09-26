import sys
from types import ModuleType, SimpleNamespace

import jdatetime
import pytest
from django import forms as django_forms
from django.test import override_settings
from django.urls import NoReverseMatch, clear_url_caches

import recurrence
from recurrence import forms


def serialize(**kwargs):
    return recurrence.serialize(recurrence.Recurrence(**kwargs))


def test_widget_options_attributes_and_media(monkeypatch):
    monkeypatch.setattr(forms, "find_recurrence_i18n_js_catalog", lambda: "/jsi18n/")
    widget = forms.RecurrenceWidget(
        attrs={"class": "custom", "rows": 4}, first_day=recurrence.SATURDAY
    )

    assert widget.attrs == {"class": "custom", "cols": "40", "rows": 4}
    assert widget.js_widget_options == {"first_day": recurrence.SATURDAY}

    with override_settings(DEBUG=False):
        media = widget.media
    assert media._js[0] == "/jsi18n/"
    assert "admin/js/vendor/jquery/jquery.min.js" in media._js
    assert any(path.endswith("recurrence-widget.init.js") for path in media._js)
    assert media._css["all"][0].endswith("recurrence.css")

    monkeypatch.setattr(forms, "find_recurrence_i18n_js_catalog", lambda: None)
    with override_settings(DEBUG=True):
        assert "admin/js/vendor/jquery/jquery.js" in widget.media._js


def test_form_field_accepts_valid_recurrence_and_can_strip_bounds():
    start = jdatetime.datetime(1404, 1, 1)
    end = jdatetime.datetime(1404, 1, 2)
    value = serialize(
        dtstart=start,
        dtend=end,
        rrules=[recurrence.Rule(recurrence.DAILY)],
    )

    cleaned = forms.RecurrenceField(
        accept_dtstart=False,
        accept_dtend=False,
        frequencies=[recurrence.DAILY],
    ).clean(value)

    assert cleaned.dtstart is None
    assert cleaned.dtend is None
    assert cleaned.rrules == (recurrence.Rule(recurrence.DAILY),)


@pytest.mark.parametrize(
    ("limit", "value"),
    [
        ("max_rrules", serialize(rrules=[recurrence.Rule(recurrence.DAILY)])),
        ("max_exrules", serialize(exrules=[recurrence.Rule(recurrence.DAILY)])),
        ("max_rdates", serialize(rdates=[jdatetime.datetime(1404, 1, 1)])),
        ("max_exdates", serialize(exdates=[jdatetime.datetime(1404, 1, 1)])),
    ],
)
def test_form_field_enforces_collection_limits(limit, value):
    with pytest.raises(django_forms.ValidationError, match="limit is 0"):
        forms.RecurrenceField(**{limit: 0}).clean(value)


@pytest.mark.parametrize("rule_type", ["rrules", "exrules"])
def test_form_field_rejects_disallowed_frequencies(rule_type):
    value = serialize(**{rule_type: [recurrence.Rule(recurrence.YEARLY)]})

    with pytest.raises(django_forms.ValidationError, match="Invalid frequency"):
        forms.RecurrenceField(frequencies=[recurrence.DAILY]).clean(value)


def test_form_field_reports_invalid_and_required_values():
    with pytest.raises(django_forms.ValidationError, match="malformed"):
        forms.RecurrenceField().clean("not-a-recurrence")

    with pytest.raises(django_forms.ValidationError, match="required"):
        forms.RecurrenceField(required=True).clean(serialize())

    assert forms.RecurrenceField(required=False).clean(None) == recurrence.Recurrence()


def test_i18n_catalog_uses_cached_and_dynamic_urls(monkeypatch):
    monkeypatch.setattr(forms, "_recurrence_javascript_catalog_url", "/cached/")
    assert forms.find_recurrence_i18n_js_catalog() == "/cached/"

    catalog = object()
    monkeypatch.setattr(forms.i18n, "javascript_catalog", catalog, raising=False)
    monkeypatch.setattr(forms, "_recurrence_javascript_catalog_url", None)
    monkeypatch.setattr(forms.urls, "reverse", lambda *args, **kwargs: "/dynamic/")
    assert forms.find_recurrence_i18n_js_catalog() == "/dynamic/"


def test_i18n_catalog_finds_nested_named_pattern(monkeypatch):
    def catalog(request):
        return None

    pattern = SimpleNamespace(
        callback=catalog,
        default_args={"packages": ["recurrence"]},
        name="recurrence-catalog",
    )
    urlconf = ModuleType("tests.recurrence_urlconf")
    urlconf.urlpatterns = [SimpleNamespace(url_patterns=[pattern])]
    monkeypatch.setitem(sys.modules, urlconf.__name__, urlconf)
    monkeypatch.setattr(forms.i18n, "javascript_catalog", catalog, raising=False)
    monkeypatch.setattr(forms, "_recurrence_javascript_catalog_url", None)

    def reverse(view, kwargs=None):
        if kwargs:
            raise NoReverseMatch
        assert view == "recurrence-catalog"
        return "/nested/catalog/"

    monkeypatch.setattr(forms.urls, "reverse", reverse)
    clear_url_caches()
    with override_settings(ROOT_URLCONF=urlconf.__name__):
        assert forms.find_recurrence_i18n_js_catalog() == "/nested/catalog/"


def test_i18n_catalog_fallback_handles_missing_and_unnamed_patterns(monkeypatch):
    empty_urlconf = ModuleType("tests.empty_recurrence_urlconf")
    empty_urlconf.urlpatterns = []
    monkeypatch.setitem(sys.modules, empty_urlconf.__name__, empty_urlconf)
    monkeypatch.delattr(forms.i18n, "javascript_catalog", raising=False)
    monkeypatch.setattr(forms, "_recurrence_javascript_catalog_url", None)
    clear_url_caches()
    with override_settings(ROOT_URLCONF=empty_urlconf.__name__):
        assert forms.find_recurrence_i18n_js_catalog() is None

    def catalog(request):
        return None

    pattern = SimpleNamespace(
        callback=catalog,
        default_args={"packages": ["recurrence"]},
        name=None,
    )
    urlconf = ModuleType("tests.unnamed_recurrence_urlconf")
    urlconf.urlpatterns = [pattern]
    monkeypatch.setitem(sys.modules, urlconf.__name__, urlconf)
    monkeypatch.setattr(forms.i18n, "javascript_catalog", catalog, raising=False)
    monkeypatch.setattr(forms, "_recurrence_javascript_catalog_url", None)

    def reverse(view, kwargs=None):
        if kwargs:
            raise NoReverseMatch
        assert view is catalog
        return "/unnamed/catalog/"

    monkeypatch.setattr(forms.urls, "reverse", reverse)
    clear_url_caches()
    with override_settings(ROOT_URLCONF=urlconf.__name__):
        assert forms.find_recurrence_i18n_js_catalog() == "/unnamed/catalog/"
