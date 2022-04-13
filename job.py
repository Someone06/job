#!/usr/bin/env python3

from __future__ import (
    annotations,
)

from abc import (
    abstractmethod,
)
from argparse import (
    ArgumentParser,
)
from dataclasses import (
    dataclass,
)
from datetime import (
    date,
    datetime,
)
from enum import (
    Enum,
    auto,
    unique,
)
from pathlib import (
    Path,
)
from sys import (
    stderr,
)
from typing import (
    Any,
    Callable,
    Optional,
    Protocol,
    TypeVar,
)


class Comparable(Protocol):
    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        pass

    @abstractmethod
    def __lt__(self: C, other: C) -> bool:
        pass

    def __gt__(self: C, other: C) -> bool:
        return (not self < other) and self != other

    def __le__(self: C, other: C) -> bool:
        return self < other or self == other

    def __ge__(self: C, other: C) -> bool:
        return not self < other


T = TypeVar("T")

C = TypeVar("C", bound="Comparable")


def bin_search(
    elements: list[T], goal: C, *, key: Callable[[T], C], asc: bool = True
) -> Optional[tuple[int, int]]:
    low = 0
    high = len(elements)
    found: Optional[int] = None

    while low < high:
        mid = (low + high) // 2
        value = key(elements[mid])
        if value == goal:
            found = mid
            break
        elif (value < goal and asc) or (value > goal and not asc):
            low = mid + 1
        else:
            high = mid

    if found is not None:
        low = found
        high = found + 1

        while low > 0 and key(elements[low - 1]) == goal:
            low -= 1

        while high < len(elements) and key(elements[high]) == goal:
            high += 1

        return (low, high)
    else:
        return None


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
        self._records: list[Record] = list()
        self._new = 0

    def _check_kind(self, kind: Kind) -> None:
        newest = self._records[-1] if self._records else None
        if (newest and newest.get_kind() == kind) or (
            newest is None and kind != Kind.START
        ):
            eprint(f"Expected kind '{Kind.START}' but got kind '{kind}'")
            raise InvalidKindError()

    def add_record(self, kind: Kind) -> None:
        self._check_kind(kind)
        record = Record(datetime.now(), kind)
        self._records.append(record)

    def with_date(self, d: date) -> list[Record]:
        r = bin_search(self._records, d, key=lambda r: r.get_time().date())
        if r is not None:
            (low, high) = r
            if self._records[low].get_kind() == Kind.STOP:
                # We know records start with kind START, so this is fine.
                low -= 1
            return self._records[low:high]
        else:
            return list()

    def _parse_records(self) -> None:
        with open(self._path) as file:
            had_record_parse_error = False
            for number, line in enumerate(file, start=1):
                try:
                    self._records.append(Record.parse(line))
                except RecordParseError:
                    had_record_parse_error = True
                    eprint(f"[line {number}] Cannot parse '{line}'")

            self._new = len(self._records)
            if had_record_parse_error:
                raise FileFormatError()

    def _check_records_sorted(self) -> None:
        for (index, current) in enumerate(self._records[1:], start=1):
            prev = self._records[index - 1]
            if prev.get_time() > current.get_time():
                eprint(
                    f"Records are not ordered oldest to newest. See records {index} and {index + 1}"
                )
                raise FileFormatError()

    def _check_records_in_past(self) -> None:
        if self._records:
            newest = self._records[-1]
            if newest.get_time() > datetime.now():
                eprint("Records reference the future")
                raise FileFormatError()

    def _check_start_stop_pairs(self) -> None:
        if self._records:
            if self._records[0].get_kind() != Kind.START:
                eprint("The first records must be a start")

            for (index, current) in enumerate(self._records[1:], start=1):
                prev = self._records[index - 1]
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
        if ex_type is None and len(self._records) > self._new:
            with open(self._path, "a") as file:
                file.writelines(
                    str(record) + "\n" for record in self._records[self._new :]
                )

    def __str__(
        self,
    ) -> str:
        return "\n".join(str(r) for r in self._records)


def print_times(records: list[Record]) -> None:
    f = "%H:%M"
    if records:
        if records[0].get_kind() != Kind.START:
            print(f"Ignoring record '{records[0]}'")

        if records[-1].get_kind() != Kind.STOP:
            print("Assuming work time ends now")
            records.append(Record(datetime.now(), Kind.STOP))

        print("Start - End")
        for (start, end) in zip(records[::2], records[1::2]):
            print(f"{start.get_time().strftime(f)} - {end.get_time().strftime(f)}")


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
            print_times(records.with_date(date.today()))
    except FileNotFoundError:
        eprint(f"File '{args.records_file}' not found")
    except (FileFormatError, InvalidKindError):
        pass


if __name__ == "__main__":
    main()
