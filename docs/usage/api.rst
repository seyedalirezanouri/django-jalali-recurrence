Generating Recurrences Programmatically
---------------------------------------

All dates in version 2 are ``jdatetime.datetime`` values.  Gregorian
``datetime`` values and legacy recurrence strings are intentionally rejected.

.. contents::
   :local:

``Rule`` and ``Recurrence``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To create recurrence objects, the two main classes you'll need are
``Rule`` and ``Recurrence``.

``Rule`` specifies a single rule (e.g. "every third Friday of the
month"), and a ``Recurrence`` is a collection of rules (some of which
may be inclusion rules, others of which may be exclusion rules),
together with date limits, and other configuration parameters.

For example:

.. code-block:: python

    import recurrence
    import jdatetime


    myrule = recurrence.Rule(
        recurrence.DAILY
    )

    pattern = recurrence.Recurrence(
        dtstart=jdatetime.datetime(1403, 1, 2),
        dtend=jdatetime.datetime(1403, 1, 3),
        rrules=[myrule, ]
    )

You can then generate a set of recurrences for that recurrence
pattern, like this::

    >>> list(mypattern.occurrences())
    [jdatetime.datetime(1403, 1, 2), jdatetime.datetime(1403, 1, 3)]

Exclusion Rules
^^^^^^^^^^^^^^^

You can specify exclusion rules too, which are exactly the same as
inclusion rules, but they represent rules which match dates which
should *not* be included in the list of occurrences. Inclusion rules
are provided to the ``Recurrence`` object using the kwarg ``rrules``,
and exclusion rules are provided to the ``Recurrence`` object using
the kwargs ``exrules``.

Adding or Excluding Individual Dates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similarly, you can specify individual dates to include or exclude
using ``rdates`` and ``exdates``, both of which should be a list of
``jdatetime.datetime`` objects.

.. code-block:: python

    import recurrence
    import jdatetime

    pattern = recurrence.Recurrence(
        rdates=[
            jdatetime.datetime(1403, 1, 1),
            jdatetime.datetime(1403, 1, 2),
        ]
    )
