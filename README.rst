django-jalali-recurrence
========================

.. image:: https://img.shields.io/github/stars/seyedalirezanouri/django-jalali-recurrence.svg?label=Stars&style=social
   :target: https://github.com/seyedalirezanouri/django-jalali-recurrence
   :alt: GitHub

.. image:: https://img.shields.io/pypi/v/django-jalali-recurrence.svg
   :target: https://pypi.org/project/django-jalali-recurrence/
   :alt: PyPI release

.. image:: https://img.shields.io/pypi/pyversions/django-jalali-recurrence.svg
   :target: https://pypi.org/project/django-jalali-recurrence/
   :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/djversions/django-jalali-recurrence.svg
   :target: https://pypi.org/project/django-jalali-recurrence/
   :alt: Supported Django versions

.. image:: https://github.com/seyedalirezanouri/django-jalali-recurrence/workflows/Test/badge.svg
   :target: https://github.com/seyedalirezanouri/django-jalali-recurrence/actions
   :alt: GitHub actions


django-jalali-recurrence is a Jalali (Persian calendar) utility for working
with recurring dates in Django. Version 2 uses Jalali dates throughout its
public API and stores versioned Jalali recurrence text. Gregorian recurrence
strings from older releases are intentionally rejected.

Date values are provided by the ``jdatetime`` package (for example,
``jdatetime.datetime(1403, 1, 1)``); import that package directly when
constructing dates.


Installation
------------

::

    pip install django-jalali-recurrence


Functionality
-------------

* Recurrence/Rule objects using Jalali calendar semantics,
* ``RecurrenceField`` for storing recurring datetimes in the database, and
* JavaScript widget.

``RecurrenceField`` provides a Django model field which serializes
recurrence information for storage in the database.

For example - say you were storing information about a university course
in your app. You could use a model like this:

.. code:: python

   import recurrence.fields

   class Course(models.Model):
       title = models.CharField(max_length=200)
       start = models.TimeField()
       end = models.TimeField()
       recurrences = recurrence.fields.RecurrenceField()

You’ll notice that I’m storing my own start and end time.
The recurrence field only deals with *recurrences*
not with specific time information.
I have an event that starts at 2pm.
Its recurrences would be “every Friday”.


Documentation
-------------

For more information on installation and configuration see the documentation at:

https://github.com/seyedalirezanouri/django-jalali-recurrence/tree/master/docs


Issues
------

If you have questions or have trouble using the app please file a bug report at:

https://github.com/seyedalirezanouri/django-jalali-recurrence/issues


Credits
-------

django-jalali-recurrence is a fork of django-recurrence_ created to add
Jalali (Persian calendar) support. django-recurrence_ was originally
created by Tamas Kemenczy, Lino Helms and individual contributors.
The upstream project remains available at
https://github.com/jazzband/django-recurrence and keeps its own
copyright (see the LICENSE file).

.. _django-recurrence: https://github.com/jazzband/django-recurrence


Contributions
-------------

All contributions are welcome!

It is best to separate proposed changes and PRs into small, distinct patches
by type so that they can be merged faster and released quicker.

One way to organize contributions would be to separate PRs for e.g.

* bugfixes,
* new features,
* code and design improvements,
* documentation improvements, or
* tooling and CI improvements.

Merging contributions requires passing the checks configured
with the CI. This includes running tests and linters successfully
on the currently officially supported Python and Django versions.

The test automation is run automatically with GitHub Actions, but you can
run it locally with the ``tox`` command before pushing commits.

Consideration
-------------
--I used AI as well :)
