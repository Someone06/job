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
class Operation(Enum):
    BEGIN = auto()
    END = auto()
    PAUSE = auto()
    RESUME = auto()

    @classmethod
    def names(cls) -> list[str]:
        return [e.name for e in Operation]


class RecordParseError(Exception):
    pass


class Record:
    _datetime_format = "%Y-%m-%d, %H:%M"

    def __init__(self, date: datetime, operation: Operation) -> None:
        self._date = date
        self._operation = operation

    def __str__(self) -> str:
        return (
            self._date.strftime(self._datetime_format)
            + "\t"
            + self._operation.name.lower()
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
            operation = Operation[components[1].upper()]
        except KeyError:
            raise RecordParseError()

        return Record(date, operation)


class Records:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._old_records: list[Record] = list()
        self._new_records: list[Record] = list()

        with open(self._path) as file:
            for number, line in enumerate(file, start=1):
                try:
                    self._old_records.append(Record.parse(line))
                except RecordParseError:
                    eprint(f"[line {number}] Cannot parse '{line}'")

    def add_record(self, record: Record) -> None:
        self._new_records.append(record)

    def add_operation(self, operation: Operation) -> None:
        record = Record(datetime.now(), operation)
        self.add_record(record)

    def write(self) -> None:
        with open(self._path, "a") as file:
            file.writelines(str(record) + "\n" for record in self._new_records)
            self._old_records.extend(self._new_records)
            self._new_records.clear()

    def __str__(self) -> str:
        records = chain(iter(self._old_records), iter(self._new_records))
        return "\n".join(str(r) for r in records)


@dataclass
class Args:
    records_file: Path
    operation: Operation


def _parse_args() -> Args:
    parser = ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("operation", choices=[o.lower() for o in Operation.names()])
    args = parser.parse_args()
    return Args(args.file, Operation[args.operation.upper()])


def main() -> None:
    args = _parse_args()
    try:
        records = Records(args.records_file)
    except FileNotFoundError:
        eprint(f"File '{args.records_file}' not found")
        return

    records.add_operation(args.operation)

    try:
        records.write()
    except FileNotFoundError:
        eprint(f"Cannot write to file '{args.records_file}'")
        return


if __name__ == "__main__":
    main()
