django-jalali-recurrence
*************************

django-jalali-recurrence is a utility for working with recurring Jalali dates in
Django.

It provides:

- Recurrence/Rule objects using Jalali calendar semantics;
- ``RecurrenceField`` for storing recurring datetimes in the
  database;
- a JavaScript widget.

Backend date conversion is delegated to ``jdatetime``.  The existing
JavaScript widget remains unchanged; for dates from Jalali year 1503 onward,
its historical ICU-based conversion is not guaranteed to match ``jdatetime``'s
calendar algorithm.

Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   usage/index
   contributing
   changelog
