#!/usr/bin/env python3
"""Developer CLI for validating and canonicalizing recurrence text.

The input is passed to :func:`recurrence.deserialize` and the resulting
object is written back with :func:`recurrence.serialize`.  No Django setup or
database connection is used.

Examples::

    python3 recurrence_text_helper.py --file recurrence.txt
    python3 recurrence_text_helper.py 'X-RECURRENCE-VERSION:2
    CALSCALE:JALALI
    DTSTART:14040101T090000
    RRULE:FREQ=DAILY;COUNT=2'
    printf '%s\n' 'X-RECURRENCE-VERSION:2' 'CALSCALE:JALALI' \
        'DTSTART:14040101T090000' 'RRULE:FREQ=DAILY;COUNT=2' \
        | python3 recurrence_text_helper.py
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import recurrence


def canonicalize(text: str, *, include_dtstart: bool = True) -> str:
    """Deserialize recurrence text and return its canonical serialization."""
    value = recurrence.deserialize(text, include_dtstart=include_dtstart)
    return recurrence.serialize(value)


def _read_input(text: str | None, filename: Path | None) -> str:
    if text is not None and filename is not None:
        raise ValueError("pass recurrence text or --file, not both")
    if filename is not None:
        return filename.read_text(encoding="utf-8")
    if text is not None:
        return text
    return sys.stdin.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Jalali recurrence text and print the canonical output "
            "produced by serialize(deserialize(text))."
        )
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="recurrence text; when omitted, input is read from stdin",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="read recurrence text from this UTF-8 file",
    )
    parser.add_argument(
        "--exclude-dtstart",
        action="store_true",
        help="deserialize with include_dtstart=False",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        source = _read_input(args.text, args.file)
        result = canonicalize(source, include_dtstart=not args.exclude_dtstart)
    except (OSError, UnicodeError, ValueError, recurrence.RecurrenceError) as error:
        parser.exit(2, f"error: {error}\n")

    sys.stdout.write(result)
    if result and not result.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
