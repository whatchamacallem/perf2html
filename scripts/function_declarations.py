# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE-MIT.md file.

from __future__ import annotations

import collections, posixpath, re, subprocess, sys
from collections.abc import Collection, Iterable, Iterator, Sequence
from typing import NamedTuple

import callgrind, settings

_DWARF_COMPILE_DIR_ATTRIBUTE: str = ""
_DWARF_DECLARATION_FILE_ATTRIBUTE: str = ""
_DWARF_DECLARATION_LINE_ATTRIBUTE: str = ""
_DWARF_LINE_TABLE_ATTRIBUTE: str = ""
_DWARF_LOW_ADDRESS_ATTRIBUTE: str = ""
_DWARF_ORIGIN_ATTRIBUTES: tuple[str, ...] = ()
_DWARF_RANGES_ATTRIBUTE: str = ""
_DWARF_SUBPROGRAM_TAG: str = ""
_READELF_ATTRIBUTE_PATTERN: str = ""
_READELF_DEBUG_INFO_OPTIONS: tuple[str, ...] = ()
_READELF_DIRECTORY_ENTRY_PATTERN: str = ""
_READELF_DIRECTORY_TABLE_PREFIX: str = ""
_READELF_FILE_ENTRY_PATTERN: str = ""
_READELF_FILE_TABLE_PREFIX: str = ""
_READELF_LINE_TABLE_OFFSET_PATTERN: str = ""
_READELF_LINE_TABLE_OPTIONS: tuple[str, ...] = ()
_READELF_LOADED_FILE_PATTERN: str = ""
_READELF_RANGE_ENTRY_PATTERN: str = ""
_READELF_RANGE_LIST_END_TEXT: str = ""
_READELF_RANGE_LIST_OPTIONS: tuple[str, ...] = ()
_READELF_RANGE_PATTERN: str = ""
_READELF_RECORD_PATTERN: str = ""
_READELF_REFERENCE_PATTERN: str = ""
_READELF_SECTION_HEADER_PATTERN: str = ""
_READELF_STRING_FORM_PATTERN: str = ""
_SYMBOL_TABLE_COMMAND: tuple[str, ...] = ()
_SYMBOL_TABLE_PATTERN: str = ""
_SYMBOL_VERSION_SEPARATOR: str = ""
settings.load_into(__name__)


# Holds a debug information record's tag, compile unit and attributes.
class DebugRecord(NamedTuple):
    tag: str
    unit_offset: int
    attributes: dict[str, str]


# Holds a line table's directories and files, each by its entry number.
class LineTable(NamedTuple):
    directories: dict[int, str]
    files: dict[int, LineTableFile]


# Holds a line table file's directory entry number and its name.
class LineTableFile(NamedTuple):
    directory_index: int
    name: str


# Yields each line a command prints, refusing a failed run or a second section.
def command_lines(command: Sequence[str]) -> Iterator[str]:
    section_pattern = re.compile(_READELF_SECTION_HEADER_PATTERN)
    sections = 0
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, text=True, errors="replace"
    ) as dump_process:
        assert dump_process.stdout is not None, "stdout is a pipe"
        for line in dump_process.stdout:
            if section_pattern.match(line):
                sections += 1
                if sections > 1:
                    dump_process.kill()
                    sys.exit(
                        f"error: {command[0]} prints a second debug section,"
                        " whose offsets the first's could share:"
                        f" {' '.join(command)}"
                    )
            yield line.rstrip("\n")
    if dump_process.returncode:
        print(
            f"error: exit {dump_process.returncode} from: {' '.join(command)}",
            file=sys.stderr,
        )
        sys.exit(dump_process.returncode)


# Returns each record readelf prints, by its offset, and the file it read.
def debug_records_read(
    lines: Iterable[str], image_path: str
) -> tuple[dict[int, DebugRecord], str]:
    record_pattern = re.compile(_READELF_RECORD_PATTERN)
    attribute_pattern = re.compile(_READELF_ATTRIBUTE_PATTERN)
    loaded_file_pattern = re.compile(_READELF_LOADED_FILE_PATTERN)
    records: dict[int, DebugRecord] = {}
    debug_file_path = image_path
    unit_offset = 0
    attributes: dict[str, str] = {}
    for line in lines:
        loaded_file_match = loaded_file_pattern.match(line)
        if loaded_file_match:
            debug_file_path = loaded_file_match.group(1)
            continue
        record_match = record_pattern.match(line)
        if record_match:
            offset = int(record_match.group(2), 16)
            if not int(record_match.group(1)):
                unit_offset = offset
            attributes = {}
            records[offset] = DebugRecord(
                record_match.group(3), unit_offset, attributes
            )
            continue
        attribute_match = attribute_pattern.match(line)
        if attribute_match:
            attributes[attribute_match.group(1)] = attribute_match.group(2)
    return records, debug_file_path


# Returns the declaration each named function's address alone gives it.
def declarations_read(
    records: dict[int, DebugRecord],
    line_table_lines: Iterable[str],
    range_lines: Iterable[str],
    symbol_lines: Iterable[str],
    function_names: Collection[str],
) -> dict[str, callgrind.SourceLine]:
    line_tables = line_tables_read(line_table_lines)
    range_starts = range_list_starts(range_lines)
    symbols = symbol_addresses_read(symbol_lines)
    unversioned: dict[str, set[int]] = collections.defaultdict(set)
    for symbol_name, symbol_set in symbols.items():
        base_name, separator, _ = symbol_name.partition(
            _SYMBOL_VERSION_SEPARATOR
        )
        if separator:
            unversioned[base_name] |= symbol_set
    starts: dict[int, list[int]] = collections.defaultdict(list)
    for offset, record in records.items():
        if record.tag != _DWARF_SUBPROGRAM_TAG:
            continue
        start = record_start(record, range_starts)
        if start is not None:
            starts[start].append(offset)
    declarations: dict[str, callgrind.SourceLine] = {}
    for function_name in function_names:
        address = function_address(symbols, unversioned, function_name)
        if address is None or len(starts[address]) != 1:
            continue
        declaration = record_declaration(
            records, line_tables, starts[address][0]
        )
        if declaration is not None:
            declarations[function_name] = declaration
    return declarations


# Returns the one address a function's name has, or None for none or several.
def function_address(
    symbols: dict[str, set[int]],
    unversioned: dict[str, set[int]],
    function_name: str,
) -> int | None:
    addresses = set(symbols.get(function_name, ()))
    if _SYMBOL_VERSION_SEPARATOR not in function_name:
        addresses |= unversioned.get(function_name, set())
    if len(addresses) != 1:
        return None
    return next(iter(addresses))


# Returns the declarations of an image's named functions, read by readelf.
def image_declarations(
    image_path: str, function_names: Collection[str]
) -> dict[str, callgrind.SourceLine]:
    records, debug_file_path = debug_records_read(
        readelf_lines(_READELF_DEBUG_INFO_OPTIONS, image_path), image_path
    )
    # The symbols are those of the file readelf read the debug records from.
    return declarations_read(
        records,
        readelf_lines(_READELF_LINE_TABLE_OPTIONS, image_path),
        readelf_lines(_READELF_RANGE_LIST_OPTIONS, image_path),
        command_lines([*_SYMBOL_TABLE_COMMAND, debug_file_path]),
        function_names,
    )


# Returns each line table's directories and files, by the table's offset.
def line_tables_read(lines: Iterable[str]) -> dict[int, LineTable]:
    offset_pattern = re.compile(_READELF_LINE_TABLE_OFFSET_PATTERN)
    directory_pattern = re.compile(_READELF_DIRECTORY_ENTRY_PATTERN)
    file_pattern = re.compile(_READELF_FILE_ENTRY_PATTERN)
    tables: dict[int, LineTable] = {}
    table = LineTable({}, {})
    filling_table = ""
    for line in lines:
        offset_match = offset_pattern.match(line)
        if offset_match:
            table = tables[int(offset_match.group(1), 0)] = LineTable({}, {})
            filling_table = ""
        elif line.startswith(
            (_READELF_DIRECTORY_TABLE_PREFIX, _READELF_FILE_TABLE_PREFIX)
        ):
            filling_table = line
        elif not line.strip():
            filling_table = ""
        elif filling_table.startswith(_READELF_DIRECTORY_TABLE_PREFIX):
            directory_match = directory_pattern.match(line)
            if directory_match:
                table.directories[int(directory_match.group(1))] = (
                    string_value(directory_match.group(2))
                )
        elif filling_table.startswith(_READELF_FILE_TABLE_PREFIX):
            file_match = file_pattern.match(line)
            if file_match:
                table.files[int(file_match.group(1))] = LineTableFile(
                    int(file_match.group(2)), string_value(file_match.group(3))
                )
    return tables


# Returns the number an attribute's value starts with, decimal or hex.
def number_value(text: str) -> int:
    return int(text.split()[0], 0)


# Returns the first address of each range list, by the list's offset.
def range_list_starts(lines: Iterable[str]) -> dict[int, int]:
    entry_pattern = re.compile(_READELF_RANGE_ENTRY_PATTERN)
    range_pattern = re.compile(_READELF_RANGE_PATTERN)
    starts: dict[int, int] = {}
    list_offset: int | None = None
    for line in lines:
        entry_match = entry_pattern.match(line)
        if not entry_match:
            continue
        if list_offset is None:
            list_offset = int(entry_match.group(1), 16)
        entry_text = entry_match.group(2)
        if entry_text.startswith(_READELF_RANGE_LIST_END_TEXT):
            list_offset = None
            continue
        range_match = range_pattern.match(entry_text)
        if range_match and list_offset not in starts:
            starts[list_offset] = int(range_match.group(1), 16)
    return starts


# Yields each line readelf prints of an image, refusing a failed run.
def readelf_lines(options: Iterable[str], image_path: str) -> Iterator[str]:
    return command_lines(["readelf", *options, image_path])


# Returns where a subprogram is declared, following its origin chain.
def record_declaration(
    records: dict[int, DebugRecord],
    line_tables: dict[int, LineTable],
    offset: int,
) -> callgrind.SourceLine | None:
    reference_pattern = re.compile(_READELF_REFERENCE_PATTERN)
    file_record: DebugRecord | None = None
    line_record: DebugRecord | None = None
    seen: set[int] = set()
    while offset in records:
        if offset in seen:
            sys.exit(f"error: the origin chain of <0x{offset:x}> loops")
        seen.add(offset)
        record = records[offset]
        if file_record is None and (
            _DWARF_DECLARATION_FILE_ATTRIBUTE in record.attributes
        ):
            file_record = record
        if line_record is None and (
            _DWARF_DECLARATION_LINE_ATTRIBUTE in record.attributes
        ):
            line_record = record
        references = [
            reference_pattern.match(record.attributes[name])
            for name in _DWARF_ORIGIN_ATTRIBUTES
            if name in record.attributes
        ]
        if not references or references[0] is None:
            break
        offset = int(references[0].group(1), 16)
    if file_record is None or line_record is None:
        return None
    unit = records[file_record.unit_offset]
    table = line_tables[
        number_value(unit.attributes[_DWARF_LINE_TABLE_ATTRIBUTE])
    ]
    table_file = table.files[
        number_value(file_record.attributes[_DWARF_DECLARATION_FILE_ATTRIBUTE])
    ]
    # The path is joined as valgrind joins it, so it reads as recorded.
    directory = table.directories[table_file.directory_index]
    if not posixpath.isabs(directory):
        directory = (
            f"{string_value(unit.attributes[_DWARF_COMPILE_DIR_ATTRIBUTE])}"
            f"/{directory}"
        )
    path = (
        table_file.name
        if posixpath.isabs(table_file.name)
        else f"{directory}/{table_file.name}"
    )
    return callgrind.SourceLine(
        path,
        number_value(
            line_record.attributes[_DWARF_DECLARATION_LINE_ATTRIBUTE]
        ),
    )


# Returns the address a subprogram starts at, or None for one with no code.
def record_start(
    record: DebugRecord, range_starts: dict[int, int]
) -> int | None:
    if _DWARF_LOW_ADDRESS_ATTRIBUTE in record.attributes:
        return number_value(record.attributes[_DWARF_LOW_ADDRESS_ATTRIBUTE])
    if _DWARF_RANGES_ATTRIBUTE in record.attributes:
        return range_starts.get(
            number_value(record.attributes[_DWARF_RANGES_ATTRIBUTE])
        )
    return None


# Returns the text of a string attribute or table entry, its form cut.
def string_value(text: str) -> str:
    form_match = re.match(_READELF_STRING_FORM_PATTERN, text)
    return form_match.group(1) if form_match else text


# Returns each defined function symbol's addresses, by its printed name.
def symbol_addresses_read(lines: Iterable[str]) -> dict[str, set[int]]:
    symbol_pattern = re.compile(_SYMBOL_TABLE_PATTERN)
    addresses: dict[str, set[int]] = collections.defaultdict(set)
    for line in lines:
        symbol_match = symbol_pattern.match(line)
        if symbol_match:
            addresses[symbol_match.group(2)].add(
                int(symbol_match.group(1), 16)
            )
    return addresses
