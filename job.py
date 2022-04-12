#!/usr/bin/env python3

from __future__ import (
    annotations,
)

from argparse import (
    ArgumentParser,
)
from dataclasses import (
    dataclass,
)
from datetime import (
    datetime,
)
from enum import (
    Enum,
    auto,
    unique,
)
from itertools import (
    chain,
)
from pathlib import (
    Path,
)
from sys import (
    stderr,
)


def eprint(*args, **kwargs):
    print(*args, file=stderr, **kwargs)


@unique
class Kind(Enum):
    START = auto()
    STOP = auto()

    @classmethod
    def names(cls) -> list[str]:
        return [e.name.lower() for e in Kind]

    def other(self) -> Kind:
        return Kind.START if self == Kind.STOP else Kind.STOP

    def __str__(self) -> str:
        return self.name.lower()

    @staticmethod
    def parse(name: str) -> Kind:
        return Kind[name.upper()]


class RecordParseError(Exception):
    pass


class Record:
    _datetime_format = "%Y-%m-%d, %H:%M"

    def __init__(self, date: datetime, kind: Kind) -> None:
        self._date = date
        self._kind = kind

    def get_time(self) -> datetime:
        return self._date

    def get_kind(self) -> Kind:
        return self._kind

    def __str__(self) -> str:
        return (
            self._date.strftime(self._datetime_format) + "\t" + self._kind.name.lower()
        )

    @staticmethod
    def parse(line: str) -> Record:
        components = line.strip().split("\t")
        if len(components) != 2:
            raise RecordParseError()

        try:
            date = datetime.strptime(components[0], Record._datetime_format)
        except ValueError:
            raise RecordParseError()

        try:
            operation = Kind.parse(components[1])
        except KeyError:
            raise RecordParseError()

        return Record(date, operation)


class FileFormatError(Exception):
    pass


class InvalidKindError(Exception):
    pass


class Records:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._old_records: list[Record] = list()
        self._new_records: list[Record] = list()

    def _check_kind(self, kind: Kind) -> None:
        newest = (
            self._new_records[-1]
            if self._new_records
            else self._old_records[-1]
            if self._old_records
            else None
        )
        if newest and newest.get_kind() == kind:
            eprint(f"Expected kind '{newest.get_kind().other()}' but got kind '{kind}'")
            raise InvalidKindError()

    def add_record(self, kind: Kind) -> None:
        self._check_kind(kind)
        record = Record(datetime.now(), kind)
        self._new_records.append(record)

    def _parse_records(self) -> None:
        with open(self._path) as file:
            had_record_parse_error = False
            for number, line in enumerate(file, start=1):
                try:
                    self._old_records.append(Record.parse(line))
                except RecordParseError:
                    had_record_parse_error = True
                    eprint(f"[line {number}] Cannot parse '{line}'")

            if had_record_parse_error:
                raise FileFormatError()

    def _check_records_sorted(self) -> None:
        for (index, current) in enumerate(self._old_records[1:], start=1):
            prev = self._old_records[index - 1]
            if prev.get_time() > current.get_time():
                eprint(
                    f"Records are not ordered oldest to newest. See records {index} and {index + 1}"
                )
                raise FileFormatError()

    def _check_records_in_past(self) -> None:
        if self._old_records:
            newest = self._old_records[-1]
            if newest.get_time() > datetime.now():
                eprint("Records reference the future")
                raise FileFormatError()

    def _check_start_stop_pairs(self) -> None:
        if self._old_records:
            if self._old_records[0].get_kind() != Kind.START:
                eprint("The first records must be a start")

            for (index, current) in enumerate(self._old_records[1:], start=1):
                prev = self._old_records[index - 1]
                if prev.get_kind() != current.get_kind().other():
                    eprint(
                        f"Lines {index} and {index + 1} have the same kind of record"
                    )
                    raise FileFormatError()

    def __enter__(self) -> Records:
        self._parse_records()
        self._check_records_sorted()
        self._check_records_in_past()
        self._check_start_stop_pairs()
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback) -> None:
        if ex_type is None:
            with open(self._path, "a") as file:
                file.writelines(str(record) + "\n" for record in self._new_records)
                self._old_records.extend(self._new_records)
                self._new_records.clear()

    def __str__(
        self,
    ) -> str:
        records = chain(iter(self._old_records), iter(self._new_records))
        return "\n".join(str(r) for r in records)


@dataclass
class Args:
    records_file: Path
    operation: Kind


def _parse_args() -> Args:
    parser = ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("operation", choices=Kind.names())
    args = parser.parse_args()
    return Args(args.file, Kind.parse(args.operation))


def main() -> None:
    args = _parse_args()
    try:
        with Records(args.records_file) as records:
            records.add_record(args.operation)

    except FileNotFoundError:
        eprint(f"File '{args.records_file}' not found")
    except Exception:
        pass


if __name__ == "__main__":
    main()
