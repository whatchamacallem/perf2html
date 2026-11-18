#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE-MIT.md file.

from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType
from typing import Any, NamedTuple

import argparse, base64, bisect, contextlib, fcntl, json, os, re, shutil
import signal, subprocess, sys, urllib.parse

import PIL.Image, PIL.ImageChops, PIL.ImageDraw, PIL.ImageEnhance
import PIL.ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_settings


class KeyWalk(NamedTuple):
    # The key pressed until the walk reaches its element.
    key_name: str
    # The frame the element lies in, the menu's top page or the view.
    frame_name: str
    # Selects the elements the focus or an open pulldown's light may reach.
    element_selector: str


class ClickStep(NamedTuple):
    # What the timing calls the click.
    label: str
    # The walks taking the focus where the timed key acts, in order.
    key_walks: tuple[KeyWalk, ...]
    # The frame holding the focus the timed key acts on.
    frame_name: str
    # The timed key, a name of the key presses the settings hold.
    key_name: str
    # The frame the state expression runs in.
    state_frame_name: str
    # Evaluates to a value the click must change.
    state_expression: str
    # The text the clipboard holds for the timed key, empty for none.
    pasted_text: str = ""


class ClickSet(NamedTuple):
    shot_flags: int
    # What the timings of the set's clicks call the set.
    set_name: str
    view_hash: str
    click_steps: tuple[ClickStep, ...]


class PageTiming(NamedTuple):
    # A report page's file, relative to the report.
    page_file: str
    # Load, or the phase a trace slice of the page counts to.
    phase_name: str
    # The phase name, then a script phase's own script file.
    phase_label: str
    duration_us: float
    shot: str


class ShotVariant(NamedTuple):
    size_name: str
    width_px: int
    height_px: int
    toggle_dark_value: str
    # The dark mode the shot shows, as its file name says it.
    mode_name: str


class ScreenshotSet(NamedTuple):
    shot_flags: int
    view_hash: str
    # Digit of the menu entry the shot focuses or opens, empty for none.
    menu_entry_number: str
    view_name: str
    subview_name: str
    absent_files: tuple[str, ...]
    # First line of the error report the page draws, empty for none.
    error_message: str
    # The walks taking the focus to the cell the shot types in, in order.
    key_walks: tuple[KeyWalk, ...] = ()
    # The text typed where the walks leave the focus, empty for none.
    typed_text: str = ""

    # Returns the view's shots in one dark mode, the views with one in turn.
    def shot_variants(self, view_index: int) -> tuple[ShotVariant, ...]:
        if self.shot_flags & test_settings.SHOOT_INDEX_PAGE:
            return _SHOT_INDEX_PAGE
        shown_index = 0
        if self.takes_turn():
            shown_index = sum(
                earlier_view.takes_turn()
                for earlier_view in _VIEWS[: view_index - 1]
            ) % len(test_settings.SCREENSHOT_TOGGLE_DARK_VALUES)
        toggle_dark_values = test_settings.SCREENSHOT_TOGGLE_DARK_VALUES
        if self.shot_flags & test_settings.SHOOT_LIGHT_DEFAULT:
            toggle_dark_values = toggle_dark_values[::-1]
        viewports = (
            test_settings.SCREENSHOT_VIEWPORTS[:1]
            if self.shot_flags & test_settings.SHOOT_ONE_VARIANT
            else test_settings.SCREENSHOT_VIEWPORTS
        )
        return tuple(
            ShotVariant(
                *viewport,
                toggle_dark_values[shown_index],
                test_settings.SHOT_MODE_NAME_PARTS[
                    test_settings.SCREENSHOT_TOGGLE_DARK_VALUES[shown_index]
                ],
            )
            for viewport in viewports
        )

    # Returns whether the view writes images, of error pages the first alone.
    def is_pictured(self, view_index: int) -> bool:
        return not self.error_message or not any(
            earlier_view.error_message
            for earlier_view in _VIEWS[: view_index - 1]
        )

    # Returns whether the view takes a turn, not being an error or index page.
    def takes_turn(self) -> bool:
        return not (
            self.error_message
            or self.shot_flags & test_settings.SHOOT_INDEX_PAGE
        )


# The texts of a kept timing, as the index table and the verbose line show.
class TimingRow(NamedTuple):
    duration_ms: str
    page_file: str
    phase_label: str
    shot: str

    # Returns the limit of the timing, none for a frame after a page's first.
    def limit_ms(self) -> int | None:
        if self.phase_label in test_settings.TIMING_FRAME_PHASE_NAMES[1:]:
            return None
        if (
            self.phase_label.split()[0]
            == test_settings.TIMING_CLICK_PHASE_NAME
        ):
            return test_settings.TIMING_CLICK_LIMIT_MS
        return test_settings.TIMING_PAGE_LOAD_LIMIT_MS

    # Returns the line the verbose output prints for the timing.
    def verbose_line(self) -> str:
        return (
            f"{self.page_file}: {self.phase_label}"
            f" {self.duration_ms} ms, {self.shot}"
        )


_SHOOT_BOTH_REPORTS = (
    test_settings.SHOOT_DIFF_REPORT | test_settings.SHOOT_REGULAR_REPORT
)
# Shoots a page once, in the regular report at 720p.
_SHOOT_REGULAR_ONCE = (
    test_settings.SHOOT_REGULAR_REPORT | test_settings.SHOOT_ONE_VARIANT
)

_SHOT_INDEX_PAGE: tuple[ShotVariant, ...] = (
    ShotVariant(
        *test_settings.SCREENSHOT_VIEWPORTS[-1],
        test_settings.SCREENSHOT_TOGGLE_DARK_VALUES[0],
        test_settings.SHOT_MODE_NAME_PARTS[
            test_settings.SCREENSHOT_TOGGLE_DARK_VALUES[0]
        ],
    ),
)

_VIEWS: tuple[ScreenshotSet, ...] = (
    ScreenshotSet(
        test_settings.SHOOT_REGULAR_REPORT | test_settings.SHOOT_UNTIMED,
        "#test=urlparser&view=flame-graph&localProfilePath=profile",
        "",
        "flame_graph",
        "profile",
        (),
        "",
    ),
    ScreenshotSet(
        test_settings.SHOOT_DIFF_REPORT,
        "",
        "2",
        "overview",
        "home",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "",
        "",
        "overview",
        "home",
        (),
        "",
    ),
    ScreenshotSet(
        test_settings.SHOOT_REGULAR_REPORT,
        "#test=urlparser&view=database",
        "",
        "database",
        "urlparser",
        (),
        "",
        (
            KeyWalk(
                "Tab",
                test_settings.CLICK_VIEW_FRAME_NAME,
                '[data-entry-name-="filter"]',
            ),
        ),
        "urlapi|^curlx",
    ),
    ScreenshotSet(
        _SHOOT_BOTH_REPORTS | test_settings.SHOOT_UNTIMED,
        "#test=wsrecv&view=heat-map&file=libcrypto.so.3/(unknown)&functions=0",
        "",
        "heat_map",
        "file",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_BOTH_REPORTS,
        "#test=urlparser&view=heat-map"
        "&file=string/bits/string_fortified.h&line=59&functions=0",
        "",
        "heat_map",
        "line",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_BOTH_REPORTS | test_settings.SHOOT_UNTIMED,
        "#test=wsrecv&view=heat-map"
        "&file=lib/curlx/timeval.c&line=52&functions=1",
        "",
        "heat_map",
        "line_functions",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_BOTH_REPORTS | test_settings.SHOOT_TWO_FRAMES,
        "#test=urlparser&view=heat-map&function=formatf&functions=1",
        "",
        "heat_map",
        "function",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_BOTH_REPORTS | test_settings.SHOOT_UNTIMED,
        "#test=wsrecv&view=heat-map&function=cf_socket_ctx_init.isra.0"
        "&functions=1",
        "",
        "heat_map",
        "function_all_parts",
        (),
        "",
    ),
    ScreenshotSet(
        test_settings.SHOOT_REGULAR_REPORT,
        "#test=urlparser&view=database"
        "&setting-values=eyJEQVRBQkFTRV9DT1VOVEVSX0xJU1RfREVGQVVMVF9TSE9X"
        "Tl9OQU1FUyI6WyJjYWxscyIsIklyIiwiRDFtciIsIkRMbXIiLCJCY20iXX0%3D",
        "",
        "database",
        "urlparser_counters_four",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_BOTH_REPORTS,
        "#test=urlparser&view=heat-map"
        "&file=string/bits/string_fortified.h&line=59&functions=0"
        "&setting-values=eyJIRUFUX01BUF9DT1VOVEVSX0xJU1RfREVGQVVMVF9TSE9X"
        "Tl9OQU1FUyI6WyJjYWxscyIsIklyIiwiTDFtIiwiTExtIiwiQm0iXX0%3D",
        "",
        "heat_map",
        "line_counters_four",
        (),
        "",
    ),
    ScreenshotSet(
        test_settings.SHOOT_REGULAR_REPORT,
        "#test=urlparser&view=call-graph",
        "7",
        "call_graph",
        "urlparser",
        (),
        "",
    ),
    ScreenshotSet(
        test_settings.SHOOT_DIFF_REPORT,
        "#test=urlparser&view=database",
        "",
        "database",
        "urlparser",
        (),
        "",
    ),
    ScreenshotSet(
        test_settings.SHOOT_REGULAR_REPORT
        | test_settings.SHOOT_ONE_VARIANT
        | test_settings.SHOOT_UNTIMED
        | test_settings.SHOOT_LIGHT_DEFAULT,
        "#view=settings&setting=DARK_MODE_ENABLED_DEFAULT"
        "&setting-values=eyJEQVJLX01PREVfRU5BQkxFRF9ERUZBVUxUIjpmYWxzZX0%3D",
        "",
        "settings",
        "applied",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=urlparser&view=heat-map&functions=0",
        "",
        "error",
        "no_file_or_function_heat_map",
        (),
        "Error: heat map requires test and file or function",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=urlparser&view=heat-map&function=no_such_function&functions=1",
        "",
        "error",
        "bad_function",
        (),
        "Error: url encodes a function address this report never recorded:"
        " no_such_function",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "",
        "",
        "error",
        "debug_script_missing",
        test_settings.DEBUG_SCRIPT_ASSET,
        "Error: resource failed: scripts/debug.js",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "",
        "",
        "error",
        "stylesheet_missing",
        test_settings.REPORT_THEME_STYLESHEET_ASSET,
        "Error: resource failed: scripts/theme.css",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#view=database",
        "",
        "error",
        "no_test_database",
        (),
        "Error: No test selected.",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=no_such_test&view=database",
        "",
        "error",
        "bad_test",
        (),
        "Error: url encodes a test this report does not have: no_such_test",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=urlparser&view=no-such-view",
        "",
        "error",
        "bad_view",
        (),
        "Error: url encodes a view this report does not have: no-such-view",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=urlparser&view=database&no-such-part=1",
        "",
        "error",
        "bad_part",
        (),
        "Error: url part unrecognized: no-such-part=1",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=urlparser&view=heat-map&file=lib/no_such_file.c&functions=0",
        "",
        "error",
        "bad_file",
        (),
        "Error: url encodes a file this report never profiled:"
        " lib/no_such_file.c",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=urlparser&view=heat-map"
        "&file=sysdeps/x86_64/multiarch/memchr-avx2.S&line=100000"
        "&functions=0",
        "",
        "error",
        "bad_line",
        (),
        "Error: url encodes a line sysdeps/x86_64/multiarch/memchr-avx2.S"
        " does not have: 100000",
    ),
    ScreenshotSet(
        test_settings.SHOOT_DIFF_REPORT | test_settings.SHOOT_ONE_VARIANT,
        "#test=urlparser&view=call-graph",
        "",
        "error",
        "call_graph",
        (),
        "Error: url encodes a view this diff report has no page for:"
        " call-graph",
    ),
    ScreenshotSet(
        test_settings.SHOOT_DIFF_REPORT | test_settings.SHOOT_INDEX_PAGE,
        "",
        "",
        "index",
        "page",
        (),
        "",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=urlparser&view=heat-map"
        "&file=string/bits/string_fortified.h&line=59",
        "",
        "error",
        "no_functions_heat_map",
        (),
        "Error: heat map requires functions=0 or functions=1",
    ),
    ScreenshotSet(
        _SHOOT_REGULAR_ONCE,
        "#test=wssend&view=heat-map&function=ws_opensocket&functions=0",
        "",
        "error",
        "function_lines_mode",
        (),
        "Error: url names function ws_opensocket together with functions=0",
    ),
)

_MENU = test_settings.CLICK_MENU_FRAME_NAME
_VIEW = test_settings.CLICK_VIEW_FRAME_NAME
_HASH_STATE = test_settings.CLICK_HASH_STATE
_CALL_GRAPH_SYMBOL_SELECTOR = (
    "#call-graph-table- > tbody > tr:not(.table-sizer-row-) .menu-button-"
)
_CALL_GRAPH_ITEM_SELECTOR = (
    "#call-graph-table- > tbody > tr:not(.table-sizer-row-) [role='treeitem']"
)
_CALL_GRAPH_FOCUS_STATE = (
    f'[...document.querySelectorAll("{_CALL_GRAPH_ITEM_SELECTOR}")]'
    ".indexOf(document.activeElement)"
)
_CALL_GRAPH_ROWS_STATE = (
    "document.querySelectorAll("
    '"#call-graph-table- > tbody > tr:not(.table-sizer-row-)").length'
)
_DATABASE_FIRST_ROW_STATE = (
    'document.querySelector("tbody > tr:not(.table-sizer-row-)").textContent'
)
_DATABASE_ROWS_STATE = (
    'document.querySelectorAll("tbody > tr:not(.table-sizer-row-)").length'
)
_DATABASE_TITLES_STATE = 'document.querySelectorAll("thead th").length'
_FOCUS_TEXT_STATE = "document.activeElement.textContent"
_HEAT_MAP_BOX_ROWS_STATE = (
    'document.querySelectorAll("tr.heat-map-source-line-detail-row-").length'
)
_HEAT_MAP_SCROLL_STATE = 'document.getElementById("heat-map-main-").scrollTop'
_HEAT_MAP_TITLES_STATE = (
    'document.querySelectorAll("table.heat-map-source-table- > thead th")'
    ".length"
)
_HEAT_MAP_BOX_CLOSE_SELECTOR = (
    'tr.heat-map-source-line-detail-row- [data-entry-name-="close"]'
)
_HEAT_MAP_BOX_COPY_SELECTOR = (
    'tr.heat-map-source-line-detail-row- [data-entry-name-="copy"]'
)
_HEAT_MAP_BOX_LINK_SELECTOR = (
    "tr.heat-map-source-line-detail-row- .strip-line- > .menu-button-:has(> a)"
)
_MENU_ROW_LAST_STOP = (
    '#menu- > .strip-line- > :nth-last-child(1 of [tabindex="0"])'
)
_STATUS_ROW_FIRST_STOP = (
    '#menu-preference- > .strip-line- > :nth-child(1 of [tabindex="0"])'
)
_STATUS_ROW_LAST_STOP = (
    '#menu-preference- > .strip-line- > :nth-last-child(1 of [tabindex="0"])'
)
_TAPE_ENTRY_SELECTOR = ".heat-map-source-ticker-tape-entry-"


# Returns the selector of a strip entry's cell.
def _entry_cell(entry_name: str) -> str:
    return f'[data-entry-name-="{entry_name}"]'


# Returns the expression of whether a strip cell's pulldown is open.
def _expanded_state(entry_selector: str) -> str:
    return (
        f"document.querySelector('{entry_selector}')"
        '.getAttribute("aria-expanded")'
    )


# Returns the expression of a strip cell's text.
def _entry_text_state(entry_selector: str) -> str:
    return f"document.querySelector('{entry_selector}').textContent"


# Returns the expression of whether the focus is on a matching element.
def _focus_state(element_selector: str) -> str:
    return f"document.activeElement.matches('{element_selector}')"


# Returns the expression of the index of a pulldown's lit option.
def _lit_option_state(entry_selector: str) -> str:
    return (
        f"[...document.querySelectorAll('{entry_selector} [role=option]')]"
        '.findIndex((option) => option.getAttribute("aria-selected")'
        ' === "true")'
    )


# Returns the expression of the stop a slider cell shows.
def _slider_state(entry_selector: str) -> str:
    return (
        f"document.querySelector('{entry_selector}')"
        '.getAttribute("aria-valuenow")'
    )


# Returns the walk tabbing to an element.
def _tab_to(frame_name: str, element_selector: str) -> KeyWalk:
    return KeyWalk("Tab", frame_name, element_selector)


# Returns the steps opening a pulldown by its key, then lighting its option.
def _pulldown_steps(
    frame_name: str,
    label: str,
    entry_selector: str,
    option_selector: str,
    state_frame_name: str,
    state_expression: str,
) -> tuple[ClickStep, ...]:
    return (
        ClickStep(
            f"{label} pulldown",
            (_tab_to(frame_name, entry_selector),),
            frame_name,
            "Enter",
            frame_name,
            _expanded_state(entry_selector),
        ),
        _option_step(
            frame_name,
            label,
            entry_selector,
            option_selector,
            state_frame_name,
            state_expression,
        ),
    )


# Returns the step lighting an open pulldown's option, then choosing it.
def _option_step(
    frame_name: str,
    label: str,
    entry_selector: str,
    option_selector: str,
    state_frame_name: str,
    state_expression: str,
) -> ClickStep:
    return ClickStep(
        label,
        (
            KeyWalk(
                "ArrowDown", frame_name, f"{entry_selector} {option_selector}"
            ),
        ),
        frame_name,
        "Enter",
        state_frame_name,
        state_expression,
    )


# Returns the step pasting into a closed pulldown, which opens searching.
def _pulldown_paste_step(
    frame_name: str, label: str, entry_selector: str, pasted_text: str
) -> ClickStep:
    return ClickStep(
        f"{label} paste",
        (_tab_to(frame_name, entry_selector),),
        frame_name,
        "ctrl+v",
        frame_name,
        _expanded_state(entry_selector),
        pasted_text,
    )


_CLICKS: tuple[ClickSet, ...] = (
    ClickSet(
        test_settings.SHOOT_REGULAR_REPORT,
        "clicks_overview",
        "",
        (
            ClickStep(
                "overview test",
                (
                    _tab_to(_MENU, "tr.row-link-"),
                    KeyWalk(
                        "ArrowDown",
                        _MENU,
                        'tr.row-link-[data-href-="#test=cookierecv'
                        '&view=database"]',
                    ),
                ),
                _MENU,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "menu call graph",
                (_tab_to(_MENU, _entry_cell("str_view_call_graph")),),
                _MENU,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "menu digit database", (), _MENU, "5", _MENU, _HASH_STATE
            ),
            ClickStep(
                "menu call graph space",
                (_tab_to(_MENU, _entry_cell("str_view_call_graph")),),
                _MENU,
                "Space",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "menu overview",
                (_tab_to(_MENU, _entry_cell("str_view_overview")),),
                _MENU,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "overview row space",
                (_tab_to(_MENU, "tr.row-link-"),),
                _MENU,
                "Space",
                _MENU,
                _HASH_STATE,
            ),
        ),
    ),
    ClickSet(
        _SHOOT_BOTH_REPORTS,
        "clicks_database",
        "#test=cookierecv&view=database",
        (
            ClickStep(
                "tab first menu row to status menu row",
                (_tab_to(_MENU, _MENU_ROW_LAST_STOP),),
                _MENU,
                "Tab",
                _MENU,
                _focus_state(_STATUS_ROW_FIRST_STOP),
            ),
            ClickStep(
                "tab status menu row to view",
                (_tab_to(_MENU, _STATUS_ROW_LAST_STOP),),
                _MENU,
                "Tab",
                _VIEW,
                "document.hasFocus()",
            ),
            ClickStep(
                "shift tab view to status menu row",
                (),
                _VIEW,
                "shift+Tab",
                _MENU,
                _focus_state(_STATUS_ROW_LAST_STOP),
            ),
            ClickStep(
                "shift tab status menu row to first menu row",
                (KeyWalk("shift+Tab", _MENU, _STATUS_ROW_FIRST_STOP),),
                _MENU,
                "shift+Tab",
                _MENU,
                _focus_state(_MENU_ROW_LAST_STOP),
            ),
            *_pulldown_steps(
                _VIEW,
                "database sort order",
                _entry_cell("sort_order"),
                '[data-entry-value-="function"]',
                _VIEW,
                _DATABASE_FIRST_ROW_STATE,
            ),
            ClickStep(
                "database sort direction",
                (_tab_to(_VIEW, _entry_cell("sort_direction")),),
                _VIEW,
                "Enter",
                _VIEW,
                _DATABASE_FIRST_ROW_STATE,
            ),
            *_pulldown_steps(
                _VIEW,
                "database count",
                _entry_cell("count"),
                '[data-entry-value-="1000"]',
                _VIEW,
                _DATABASE_ROWS_STATE,
            ),
            *_pulldown_steps(
                _MENU,
                "counters",
                _entry_cell("counters"),
                '[data-entry-value-="Ir"]',
                _VIEW,
                _DATABASE_TITLES_STATE,
            ),
            ClickStep(
                "counters close",
                (),
                _MENU,
                "Escape",
                _MENU,
                _expanded_state(_entry_cell("counters")),
            ),
            ClickStep(
                "database filter paste",
                (_tab_to(_VIEW, _entry_cell("filter")),),
                _VIEW,
                "ctrl+v",
                _VIEW,
                _DATABASE_ROWS_STATE,
                "lib/vtls",
            ),
            ClickStep(
                "database filter erase",
                (),
                _VIEW,
                "Backspace",
                _VIEW,
                _entry_text_state(_entry_cell("filter")),
            ),
            ClickStep(
                "database filter type",
                (),
                _VIEW,
                "s",
                _VIEW,
                _entry_text_state(_entry_cell("filter")),
            ),
            ClickStep(
                "database filter clear",
                (),
                _VIEW,
                "Escape",
                _VIEW,
                _DATABASE_ROWS_STATE,
            ),
            ClickStep(
                "database filter function paste",
                (_tab_to(_VIEW, _entry_cell("filter")),),
                _VIEW,
                "ctrl+v",
                _VIEW,
                _DATABASE_ROWS_STATE,
                "^Curl_headers_push$",
            ),
            *_pulldown_steps(
                _VIEW,
                "database copy",
                _entry_cell("copy"),
                '[data-entry-value-="text"]',
                _VIEW,
                _expanded_state(_entry_cell("copy")),
            ),
            ClickStep(
                "database caller",
                (
                    _tab_to(_VIEW, "tr.row-link-"),
                    KeyWalk(
                        "ArrowRight",
                        _VIEW,
                        'tr.row-link- a[href="#test=cookierecv&view=heat-map'
                        '&function=hds_cw_collect_write&functions=1"]',
                    ),
                ),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "menu digit database", (), _VIEW, "5", _MENU, _HASH_STATE
            ),
            ClickStep(
                "database row last",
                (_tab_to(_VIEW, "tr.row-link-"),),
                _VIEW,
                "End",
                _VIEW,
                _FOCUS_TEXT_STATE,
            ),
            ClickStep(
                "database row first",
                (),
                _VIEW,
                "Home",
                _VIEW,
                _FOCUS_TEXT_STATE,
            ),
            ClickStep(
                "database row down",
                (),
                _VIEW,
                "ArrowDown",
                _VIEW,
                _FOCUS_TEXT_STATE,
            ),
            ClickStep(
                "database row up",
                (),
                _VIEW,
                "ArrowUp",
                _VIEW,
                _FOCUS_TEXT_STATE,
            ),
            ClickStep(
                "database row link",
                (),
                _VIEW,
                "ArrowRight",
                _VIEW,
                _FOCUS_TEXT_STATE,
            ),
            ClickStep(
                "database row link left",
                (),
                _VIEW,
                "ArrowLeft",
                _VIEW,
                _FOCUS_TEXT_STATE,
            ),
            ClickStep(
                "database function",
                (_tab_to(_VIEW, "tr.row-link-"),),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
        ),
    ),
    ClickSet(
        _SHOOT_BOTH_REPORTS,
        "clicks_heat_map",
        "#test=cookierecv&view=heat-map&file=lib/progress.c&functions=0",
        (
            ClickStep(
                "heat map page down",
                (_tab_to(_VIEW, "tr[data-line-number-]"),),
                _VIEW,
                "PageDown",
                _VIEW,
                _HEAT_MAP_SCROLL_STATE,
            ),
            ClickStep(
                "heat map hottest line",
                (_tab_to(_VIEW, _TAPE_ENTRY_SELECTOR),),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "heat map tape next",
                (_tab_to(_VIEW, _TAPE_ENTRY_SELECTOR),),
                _VIEW,
                "ArrowRight",
                _VIEW,
                _FOCUS_TEXT_STATE,
            ),
            ClickStep(
                "heat map arrow scroll",
                (_tab_to(_VIEW, _HEAT_MAP_BOX_CLOSE_SELECTOR),),
                _VIEW,
                "ArrowDown",
                _VIEW,
                _HEAT_MAP_SCROLL_STATE,
            ),
            ClickStep(
                "heat map line box close",
                (_tab_to(_VIEW, _HEAT_MAP_BOX_CLOSE_SELECTOR),),
                _VIEW,
                "Enter",
                _VIEW,
                _HEAT_MAP_BOX_ROWS_STATE,
            ),
            _pulldown_paste_step(
                _MENU,
                "file line",
                _entry_cell("str_menu_file"),
                "lib/progress.c:660",
            ),
            ClickStep("file line", (), _MENU, "Enter", _MENU, _HASH_STATE),
            ClickStep(
                "heat map line box escape",
                (_tab_to(_VIEW, 'tr[data-line-number-="660"]'),),
                _VIEW,
                "Escape",
                _VIEW,
                _HEAT_MAP_BOX_ROWS_STATE,
            ),
            ClickStep(
                "heat map line",
                (),
                _VIEW,
                "Enter",
                _VIEW,
                _HEAT_MAP_BOX_ROWS_STATE,
            ),
            ClickStep(
                "heat map line close",
                (),
                _VIEW,
                "Enter",
                _VIEW,
                _HEAT_MAP_BOX_ROWS_STATE,
            ),
            ClickStep(
                "heat map function line",
                (
                    KeyWalk(
                        "ArrowDown",
                        _VIEW,
                        'tr.function-entry-[data-line-number-="706"]',
                    ),
                ),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "heat map function body line",
                (KeyWalk("ArrowDown", _VIEW, 'tr[data-line-number-="708"]'),),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            *_pulldown_steps(
                _VIEW,
                "heat map box copy",
                _HEAT_MAP_BOX_COPY_SELECTOR,
                '[data-entry-value-="path"]',
                _VIEW,
                _expanded_state(_HEAT_MAP_BOX_COPY_SELECTOR),
            ),
            ClickStep(
                "heat map box function",
                (KeyWalk("shift+Tab", _VIEW, _HEAT_MAP_BOX_LINK_SELECTOR),),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "heat map tree folder",
                (
                    _tab_to(_VIEW, ".heat-map-tree-node-"),
                    KeyWalk("Home", _VIEW, '[data-dir-="lib"]'),
                    KeyWalk("ArrowDown", _VIEW, '[data-dir-="lib/vtls"]'),
                ),
                _VIEW,
                "Enter",
                _VIEW,
                "document.querySelector('[data-dir-=\"lib/vtls\"]')"
                '.getAttribute("aria-expanded")',
            ),
            ClickStep(
                "heat map tree folder close",
                (),
                _VIEW,
                "ArrowLeft",
                _VIEW,
                "document.querySelector('[data-dir-=\"lib/vtls\"]')"
                '.getAttribute("aria-expanded")',
            ),
            ClickStep(
                "heat map tree folder open",
                (),
                _VIEW,
                "ArrowRight",
                _VIEW,
                "document.querySelector('[data-dir-=\"lib/vtls\"]')"
                '.getAttribute("aria-expanded")',
            ),
            ClickStep(
                "heat map tree file",
                (
                    KeyWalk(
                        "ArrowDown",
                        _VIEW,
                        '[data-file-="lib/vtls/vtls_config.c"]',
                    ),
                ),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "heat scale",
                (_tab_to(_MENU, _entry_cell("heat_scale")),),
                _MENU,
                "Enter",
                _MENU,
                _entry_text_state(_entry_cell("heat_scale")),
            ),
            ClickStep(
                "heat sort",
                (_tab_to(_MENU, _entry_cell("heat_sort")),),
                _MENU,
                "Enter",
                _MENU,
                _entry_text_state(_entry_cell("heat_sort")),
            ),
            ClickStep(
                "heat sort space",
                (),
                _MENU,
                "Space",
                _MENU,
                _entry_text_state(_entry_cell("heat_sort")),
            ),
            ClickStep(
                "heat counter source",
                (_tab_to(_MENU, _entry_cell("heat_counter_source")),),
                _MENU,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
            _pulldown_paste_step(
                _MENU, "counters", _entry_cell("counters"), "Ir"
            ),
            _option_step(
                _MENU,
                "counters",
                _entry_cell("counters"),
                '[data-entry-value-="Ir"]',
                _VIEW,
                _HEAT_MAP_TITLES_STATE,
            ),
            ClickStep(
                "counters close",
                (),
                _MENU,
                "Escape",
                _MENU,
                _expanded_state(_entry_cell("counters")),
            ),
            _pulldown_paste_step(
                _MENU, "file", _entry_cell("str_menu_file"), "lib/transfer"
            ),
            _option_step(
                _MENU,
                "file",
                _entry_cell("str_menu_file"),
                '[href^="#test=cookierecv&view=heat-map&file=lib/transfer.c"]',
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "function pulldown type",
                (_tab_to(_MENU, _entry_cell("str_menu_function")),),
                _MENU,
                "c",
                _MENU,
                _expanded_state(_entry_cell("str_menu_function")),
            ),
            ClickStep(
                "function pulldown paste",
                (),
                _MENU,
                "ctrl+v",
                _MENU,
                _entry_text_state(_entry_cell("str_menu_function")),
                "url_headers_push$",
            ),
            _option_step(
                _MENU,
                "function",
                _entry_cell("str_menu_function"),
                '[href="#test=cookierecv&view=heat-map'
                '&function=Curl_headers_push&functions=1"]',
                _MENU,
                _HASH_STATE,
            ),
            ClickStep(
                "dark mode",
                (_tab_to(_MENU, _entry_cell("dark_mode")),),
                _MENU,
                "Enter",
                _MENU,
                _entry_text_state(_entry_cell("dark_mode")),
            ),
            ClickStep(
                "scale",
                (_tab_to(_MENU, _entry_cell("str_menu_scale")),),
                _MENU,
                "ArrowLeft",
                _MENU,
                _slider_state(_entry_cell("str_menu_scale")),
            ),
            ClickStep(
                "scale key",
                (),
                _MENU,
                "-",
                _MENU,
                _slider_state(_entry_cell("str_menu_scale")),
            ),
            ClickStep(
                "scale key plus",
                (),
                _MENU,
                "+",
                _MENU,
                _slider_state(_entry_cell("str_menu_scale")),
            ),
            ClickStep(
                "scale key equals",
                (),
                _MENU,
                "=",
                _MENU,
                _slider_state(_entry_cell("str_menu_scale")),
            ),
            ClickStep(
                "scale home",
                (),
                _MENU,
                "Home",
                _MENU,
                _slider_state(_entry_cell("str_menu_scale")),
            ),
            ClickStep(
                "reset",
                (_tab_to(_MENU, _entry_cell("str_menu_reset")),),
                _MENU,
                "Enter",
                _MENU,
                _slider_state(_entry_cell("str_menu_scale")),
            ),
            ClickStep(
                "test pulldown space",
                (_tab_to(_MENU, _entry_cell("str_menu_test")),),
                _MENU,
                "Space",
                _MENU,
                _expanded_state(_entry_cell("str_menu_test")),
            ),
            ClickStep(
                "test pulldown previous",
                (
                    KeyWalk(
                        "ArrowDown",
                        _MENU,
                        f"{_entry_cell('str_menu_test')}"
                        " :nth-child(2 of [role=option])",
                    ),
                ),
                _MENU,
                "ArrowUp",
                _MENU,
                _lit_option_state(_entry_cell("str_menu_test")),
            ),
            ClickStep(
                "test pulldown type",
                (),
                _MENU,
                "r",
                _MENU,
                _entry_text_state(_entry_cell("str_menu_test")),
            ),
            ClickStep(
                "test pulldown erase",
                (),
                _MENU,
                "Backspace",
                _MENU,
                _entry_text_state(_entry_cell("str_menu_test")),
            ),
            ClickStep(
                "test pulldown close",
                (),
                _MENU,
                "Escape",
                _MENU,
                _expanded_state(_entry_cell("str_menu_test")),
            ),
            ClickStep(
                "test pulldown view digit",
                (_tab_to(_VIEW, _TAPE_ENTRY_SELECTOR),),
                _VIEW,
                "2",
                _MENU,
                _expanded_state(_entry_cell("str_menu_test")),
            ),
            ClickStep(
                "test pulldown paste",
                (),
                _MENU,
                "ctrl+v",
                _MENU,
                _entry_text_state(_entry_cell("str_menu_test")),
                "resp",
            ),
            _option_step(
                _MENU,
                "test",
                _entry_cell("str_menu_test"),
                '[href^="#test=respheaders&view=heat-map"]',
                _MENU,
                _HASH_STATE,
            ),
        ),
    ),
    ClickSet(
        test_settings.SHOOT_REGULAR_REPORT,
        "clicks_call_graph",
        "#test=cookierecv&view=call-graph",
        (
            *_pulldown_steps(
                _MENU,
                "call graph sort",
                _entry_cell("call_graph_sort"),
                '[data-entry-value-="name"]',
                _VIEW,
                "[...document.querySelectorAll("
                f'"{_CALL_GRAPH_SYMBOL_SELECTOR}")]'
                ".map((symbol) => symbol.textContent).join()",
            ),
            *_pulldown_steps(
                _VIEW,
                "call graph copy",
                _entry_cell("copy"),
                '[data-entry-value-="text"]',
                _VIEW,
                _expanded_state(_entry_cell("copy")),
            ),
            ClickStep(
                "call graph cutoff lowest",
                (_tab_to(_VIEW, _entry_cell("cutoff")),),
                _VIEW,
                "Home",
                _VIEW,
                _CALL_GRAPH_ROWS_STATE,
            ),
            ClickStep(
                "call graph cutoff step",
                (),
                _VIEW,
                "ArrowRight",
                _VIEW,
                _CALL_GRAPH_ROWS_STATE,
            ),
            ClickStep(
                "call graph cutoff highest",
                (_tab_to(_VIEW, _entry_cell("cutoff")),),
                _VIEW,
                "End",
                _VIEW,
                _slider_state(_entry_cell("cutoff")),
            ),
            ClickStep(
                "call graph node close",
                (_tab_to(_VIEW, _CALL_GRAPH_ITEM_SELECTOR),),
                _VIEW,
                "Enter",
                _VIEW,
                _CALL_GRAPH_ROWS_STATE,
            ),
            ClickStep(
                "call graph node open",
                (),
                _VIEW,
                "Enter",
                _VIEW,
                _CALL_GRAPH_ROWS_STATE,
            ),
            ClickStep(
                "call graph node child",
                (),
                _VIEW,
                "ArrowRight",
                _VIEW,
                _CALL_GRAPH_FOCUS_STATE,
            ),
            ClickStep(
                "call graph node down",
                (),
                _VIEW,
                "ArrowDown",
                _VIEW,
                _CALL_GRAPH_FOCUS_STATE,
            ),
            ClickStep(
                "call graph node parent",
                (),
                _VIEW,
                "ArrowLeft",
                _VIEW,
                _CALL_GRAPH_FOCUS_STATE,
            ),
            ClickStep(
                "call graph node up",
                (),
                _VIEW,
                "ArrowUp",
                _VIEW,
                _CALL_GRAPH_FOCUS_STATE,
            ),
            ClickStep(
                "call graph node shut",
                (),
                _VIEW,
                "ArrowLeft",
                _VIEW,
                _CALL_GRAPH_ROWS_STATE,
            ),
            ClickStep(
                "call graph node unshut",
                (),
                _VIEW,
                "ArrowRight",
                _VIEW,
                _CALL_GRAPH_ROWS_STATE,
            ),
            ClickStep(
                "call graph node last",
                (),
                _VIEW,
                "End",
                _VIEW,
                _CALL_GRAPH_FOCUS_STATE,
            ),
            ClickStep(
                "call graph node first",
                (),
                _VIEW,
                "Home",
                _VIEW,
                _CALL_GRAPH_FOCUS_STATE,
            ),
            ClickStep(
                "call graph selected function",
                (
                    KeyWalk(
                        "shift+Tab", _VIEW, _entry_cell("selected_function")
                    ),
                ),
                _VIEW,
                "Enter",
                _MENU,
                _HASH_STATE,
            ),
        ),
    ),
)


# Drives one browser over its DevTools pipe, each tab in a fresh profile.
class BrowserSession:
    def __init__(self) -> None:
        command_read_fd, command_write_fd = os.pipe()
        self.reply_read_fd, reply_write_fd = os.pipe()

        # Moves the browser's pipe ends to the descriptors it reads and writes.
        def pipe_ends_place() -> None:
            command_spare_fd = fcntl.fcntl(
                command_read_fd,
                fcntl.F_DUPFD,
                test_settings.BROWSER_PIPE_SPARE_FD,
            )
            reply_spare_fd = fcntl.fcntl(
                reply_write_fd,
                fcntl.F_DUPFD,
                test_settings.BROWSER_PIPE_SPARE_FD,
            )
            os.dup2(command_spare_fd, test_settings.BROWSER_PIPE_COMMAND_FD)
            os.dup2(reply_spare_fd, test_settings.BROWSER_PIPE_REPLY_FD)

        self.browser_process = subprocess.Popen(
            [
                test_settings.SCREENSHOT_BROWSER_PATH,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--incognito",
                "--hide-scrollbars",
                # Draws a frame only after the page's own work for it.
                "--run-all-compositor-stages-before-draw",
                "--remote-debugging-pipe",
                test_settings.BLANK_PAGE_URL,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(
                test_settings.BROWSER_PIPE_COMMAND_FD,
                test_settings.BROWSER_PIPE_REPLY_FD,
            ),
            preexec_fn=pipe_ends_place,
            start_new_session=True,
        )
        os.close(command_read_fd)
        os.close(reply_write_fd)
        self.command_file = os.fdopen(command_write_fd, "wb")
        self.command_count = 0
        # The open tabs, by the session their commands and events go through.
        self.page_tabs: dict[str, PageTab] = {}
        self.unread_bytes = b""

    def __enter__(self) -> BrowserSession:
        return self

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        error_traceback: TracebackType | None,
    ) -> None:
        if error_type is None:
            self.command("Browser.close")
            self.browser_process.wait()
        else:
            # Kills a browser still running with every process of its group.
            if self.browser_process.poll() is None:
                os.killpg(self.browser_process.pid, signal.SIGKILL)
            self.browser_process.wait()
        self.command_file.close()
        os.close(self.reply_read_fd)

    # Sends a command, to a tab's session if named, returning its result.
    def command(
        self,
        method: str,
        parameters: dict[str, Any] | None = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        self.command_count += 1
        command_message: dict[str, Any] = {
            "id": self.command_count,
            "method": method,
            "params": parameters or {},
        }
        if session_id:
            command_message["sessionId"] = session_id
        self.command_file.write(
            json.dumps(command_message).encode()
            + test_settings.BROWSER_PIPE_MESSAGE_END
        )
        self.command_file.flush()
        while True:
            reply_message = self.message_read()
            if reply_message.get("id") != self.command_count:
                continue
            if "error" in reply_message:
                raise RuntimeError(f"{method}: {reply_message['error']}")
            return reply_message["result"]

    # Reads the next message, handing an open tab's event to that tab.
    def message_read(self) -> dict[str, Any]:
        while test_settings.BROWSER_PIPE_MESSAGE_END not in self.unread_bytes:
            read_bytes = os.read(
                self.reply_read_fd, test_settings.BROWSER_PIPE_READ_BYTES
            )
            if not read_bytes:
                raise RuntimeError(
                    "the browser closed its pipe, exit"
                    f" {self.browser_process.wait()}"
                )
            self.unread_bytes += read_bytes
        message_bytes, self.unread_bytes = self.unread_bytes.split(
            test_settings.BROWSER_PIPE_MESSAGE_END, 1
        )
        message = json.loads(message_bytes)
        page_tab = self.page_tabs.get(message.get("sessionId", ""))
        # A closed tab's late event and a browser event belong to no page.
        if "method" in message and page_tab:
            page_tab.event_take(message)
        return message

    # Returns the first line of each page's error report, tabs loading at once.
    def pages_error_messages(self, page_urls: list[str]) -> list[str]:
        _, width_px, height_px = test_settings.SCREENSHOT_VIEWPORTS[0]
        error_messages = [""] * len(page_urls)
        loading_tabs: dict[PageTab, int] = {}

        # Keeps the error message of the first tab to settle, closing it.
        def settled_tab_close() -> None:
            settled_tab = self.settled_tab_wait(list(loading_tabs))
            error_messages[loading_tabs.pop(settled_tab)] = (
                settled_tab.error_message()
            )
            settled_tab.close()

        for url_index, page_url in enumerate(page_urls):
            if len(loading_tabs) == test_settings.PAGE_CHECK_TABS_AT_ONCE:
                settled_tab_close()
            page_tab = self.tab_open(width_px, height_px)
            page_tab.page_navigate(page_url)
            loading_tabs[page_tab] = url_index
        while loading_tabs:
            settled_tab_close()
        return error_messages

    # Returns the first tab whose page settled, reading while none has news.
    def settled_tab_wait(self, page_tabs: list[PageTab]) -> PageTab:
        while True:
            for page_tab in page_tabs:
                if page_tab.has_news and page_tab.settle_step():
                    return page_tab
            # A check's own commands may have kept events, read only after.
            if not any(page_tab.has_news for page_tab in page_tabs):
                self.message_read()

    # Opens a blank tab of a size in a fresh profile, closing it after.
    @contextlib.contextmanager
    def tab(self, width_px: int, height_px: int) -> Iterator[PageTab]:
        page_tab = self.tab_open(width_px, height_px)
        yield page_tab
        page_tab.close()

    # Opens a blank tab of a size in a fresh profile.
    def tab_open(self, width_px: int, height_px: int) -> PageTab:
        browser_context_id = self.command("Target.createBrowserContext")[
            "browserContextId"
        ]
        target_id = self.command(
            "Target.createTarget",
            {
                "url": test_settings.BLANK_PAGE_URL,
                "browserContextId": browser_context_id,
                "width": width_px,
                "height": height_px,
            },
        )["targetId"]
        session_id = self.command(
            "Target.attachToTarget", {"targetId": target_id, "flatten": True}
        )["sessionId"]
        page_tab = PageTab(
            self, session_id, browser_context_id, (width_px, height_px)
        )
        self.page_tabs[session_id] = page_tab
        page_tab.command("Page.enable")
        page_tab.command("Runtime.enable")
        page_tab.command(
            "Runtime.addBinding",
            {"name": test_settings.PAGE_DRAWN_BINDING_NAME},
        )
        return page_tab


# Holds one tab's page: its frames, their script contexts and error reports.
class PageTab:
    def __init__(
        self,
        browser_session: BrowserSession,
        session_id: str,
        browser_context_id: str,
        tab_size: tuple[int, int],
    ) -> None:
        self.browser_session = browser_session
        self.session_id = session_id
        self.browser_context_id = browser_context_id
        self.tab_size = tab_size
        # The contexts whose drawn check this settle started.
        self.checked_contexts: set[int] = set()
        # The contexts the page left, read before any failed reply.
        self.destroyed_contexts: set[int] = set()
        # The frames the page removed, read before any failed reply.
        self.detached_frames: set[str] = set()
        # The contexts whose drawn check of this settle passed.
        self.drawn_contexts: set[int] = set()
        # The contexts from before this settle, whose load renders are logged.
        self.earlier_contexts: set[int] = set()
        # The first line of each error report, by the context drawing it.
        self.error_reports: dict[int, str] = {}
        self.frame_contexts: dict[str, int] = {}
        # Whether an event came since the last settle step.
        self.has_news = False
        # The frames out of view, which no shot shows.
        self.hidden_frames: set[str] = set()
        # Whether the frame a navigation opens started loading, after an input.
        self.is_started = False
        self.loading_frames: set[str] = set()
        self.navigation_frame_id = ""
        self.pending_events: list[dict[str, Any]] = []
        # Numbers the settles, so a drawn check reports to its own alone.
        self.settle_count = 0
        self.thrown_texts: list[str] = []

    # Closes the tab with its profile, any late event of it unread.
    def close(self) -> None:
        del self.browser_session.page_tabs[self.session_id]
        self.browser_session.command(
            "Target.disposeBrowserContext",
            {"browserContextId": self.browser_context_id},
        )

    # Sends a command to the tab, returning its result once its reply comes.
    def command(
        self, method: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.browser_session.command(
            method, parameters, self.session_id
        )

    # Returns the first line of the page's first error report, if any.
    def error_message(self) -> str:
        return next(iter(self.error_reports.values()), "")

    # Refuses an error report or an uncaught exception of the page.
    def errors_refuse(self, fault_label: str) -> None:
        if self.error_reports:
            raise RuntimeError(f"{fault_label}: {self.error_message()}")
        if self.thrown_texts:
            raise RuntimeError(f"{fault_label}: {self.thrown_texts[0]}")

    # Keeps an event of the tab, its error reports and script contexts.
    def event_take(self, message: dict[str, Any]) -> None:
        self.has_news = True
        method = message["method"]
        event_parameters = message["params"]
        if method == "Runtime.exceptionThrown":
            exception_details = event_parameters["exceptionDetails"]
            self.thrown_texts.append(
                exception_details.get("exception", {}).get(
                    "description", exception_details["text"]
                )
            )
        elif method == "Runtime.consoleAPICalled":
            console_text = " ".join(
                str(console_argument.get("value", ""))
                for console_argument in event_parameters["args"]
            )
            error_match = test_settings.CONSOLE_ERROR_REPORT_PATTERN.search(
                console_text
            )
            if error_match:
                self.error_reports.setdefault(
                    event_parameters["executionContextId"],
                    error_match.group(1),
                )
        elif method == "Runtime.executionContextCreated":
            context = event_parameters["context"]
            if context["auxData"]["isDefault"]:
                self.frame_contexts[context["auxData"]["frameId"]] = context[
                    "id"
                ]
        elif method == "Runtime.executionContextDestroyed":
            self.destroyed_contexts.add(event_parameters["executionContextId"])
            self.frame_contexts = {
                frame_id: context_id
                for frame_id, context_id in self.frame_contexts.items()
                if context_id != event_parameters["executionContextId"]
            }
        elif method == "Runtime.executionContextsCleared":
            self.destroyed_contexts.update(self.frame_contexts.values())
            self.frame_contexts = {}
        else:
            if method == "Page.frameDetached":
                self.detached_frames.add(event_parameters["frameId"])
            self.pending_events.append(message)

    # Returns the next event of a method, reading messages until one comes.
    def event_wait(self, method: str) -> dict[str, Any]:
        while True:
            for event_index, pending_event in enumerate(self.pending_events):
                if pending_event["method"] == method:
                    return self.pending_events.pop(event_index)["params"]
            self.browser_session.message_read()

    # Returns the value an expression evaluates to in a frame.
    def frame_evaluate(self, frame_name: str, expression: str) -> Any:
        evaluation = self.command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "contextId": self.frame_context(frame_name),
                "returnByValue": True,
            },
        )
        if "exceptionDetails" in evaluation:
            raise RuntimeError(
                f"{frame_name}: {expression}:"
                f" {evaluation['exceptionDetails']['text']}"
            )
        return evaluation["result"].get("value")

    def frame_context(self, frame_name: str) -> int:
        frame_id = self.frame_id(frame_name)
        if frame_id not in self.frame_contexts:
            raise RuntimeError(f"{frame_name}: no script context")
        return self.frame_contexts[frame_id]

    # Returns the frame of the menu's top page or of its one view.
    def frame_id(self, frame_name: str) -> str:
        frame_tree = self.command("Page.getFrameTree")["frameTree"]
        if frame_name == test_settings.CLICK_MENU_FRAME_NAME:
            return frame_tree["frame"]["id"]
        child_frames = frame_tree.get("childFrames", [])
        if len(child_frames) != 1:
            raise RuntimeError(f"the page holds {len(child_frames)} views")
        return child_frames[0]["frame"]["id"]

    # Returns whether a child frame's element shows in the tab's view.
    def frame_shown(self, frame: dict[str, Any]) -> bool:
        try:
            owner_node_id = self.command(
                "DOM.getFrameOwner", {"frameId": frame["id"]}
            )["backendNodeId"]
            owner_object = self.command(
                "DOM.resolveNode",
                {
                    "backendNodeId": owner_node_id,
                    "executionContextId": self.frame_contexts[
                        frame["parentId"]
                    ],
                },
            )["object"]
            if not self.object_call(
                owner_object["objectId"],
                test_settings.FRAME_LAID_OUT_FUNCTION,
            ):
                return False
            frame_quads = self.command(
                "DOM.getContentQuads", {"backendNodeId": owner_node_id}
            )["quads"]
        except RuntimeError:
            # A frame its page removed meanwhile is out of view.
            if frame["id"] in self.detached_frames:
                return False
            raise
        width_px, height_px = self.tab_size
        return any(
            max(quad[0::2]) > 0
            and max(quad[1::2]) > 0
            and min(quad[0::2]) < width_px
            and min(quad[1::2]) < height_px
            for quad in frame_quads
        )

    # Returns whether each shown frame drew or erred, a child after its parent.
    def frames_drawn(self, frame_tree: dict[str, Any]) -> bool:
        if frame_tree["frame"]["id"] in self.hidden_frames:
            return True
        context_id = self.frame_contexts.get(frame_tree["frame"]["id"])
        if context_id is None:
            return False
        # The error handler's page replaces the frame's own and its frames.
        if context_id in self.error_reports:
            return True
        child_trees = frame_tree.get("childFrames", [])
        is_new = context_id not in self.earlier_contexts
        if context_id not in self.checked_contexts:
            self.checked_contexts.add(context_id)
            # A frame out of view never paints, so no shot shows it drawn.
            for child_tree in child_trees:
                if not self.frame_shown(child_tree["frame"]):
                    self.hidden_frames.add(child_tree["frame"]["id"])
            try:
                self.command(
                    "Runtime.evaluate",
                    {
                        "expression": self.wait_expression(
                            test_settings.PAGE_DRAWN_FUNCTION,
                            json.dumps(test_settings.PAGE_DRAWN_BINDING_NAME),
                            json.dumps(str(self.settle_count)),
                        ),
                        "contextId": context_id,
                    },
                )
            except RuntimeError:
                # A page left meanwhile is checked in its next context.
                if context_id not in self.destroyed_contexts:
                    raise
        # A new page lays its frames out as it draws, an earlier page did.
        if is_new and context_id not in self.drawn_contexts:
            return False
        # Every child is checked, so their drawn checks all start at once.
        child_states = [
            self.frames_drawn(child_tree) for child_tree in child_trees
        ]
        return context_id in self.drawn_contexts and all(child_states)

    # Writes text to the clipboard from a frame, as a copy there would.
    def clipboard_write(self, frame_name: str, pasted_text: str) -> None:
        write_function = test_settings.CLICK_CLIPBOARD_WRITE_FUNCTION
        clipboard_write = self.command(
            "Runtime.evaluate",
            {
                "expression": f"({write_function})({json.dumps(pasted_text)})",
                "contextId": self.frame_context(frame_name),
                "awaitPromise": True,
                "userGesture": True,
            },
        )
        if "exceptionDetails" in clipboard_write:
            raise RuntimeError(
                f"{frame_name}: clipboard write:"
                f" {clipboard_write['exceptionDetails']['text']}"
            )

    # Writes the page as drawn to an image file.
    def image_write(self, image_path: str) -> None:
        # The fast encoding writes the same pixels to a larger file.
        image_data = self.command(
            "Page.captureScreenshot", {"optimizeForSpeed": True}
        )["data"]
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(image_data))

    # Sends a key's press and release to whatever holds the focus.
    def key_send(self, key_name: str) -> None:
        key_press = test_settings.CLICK_KEY_PRESSES[key_name]
        self.command(
            "Input.dispatchKeyEvent",
            {
                "type": "keyDown" if "text" in key_press else "rawKeyDown",
                **key_press,
            },
        )
        self.command(
            "Input.dispatchKeyEvent",
            {
                "type": "keyUp",
                **{
                    part_name: part_value
                    for part_name, part_value in key_press.items()
                    if part_name not in ("commands", "text")
                },
            },
        )

    # Presses a key, returning once each frame drew after it.
    def key_settle(self, key_name: str) -> None:
        self.settle_begin()
        self.key_send(key_name)
        self.browser_session.settled_tab_wait([self])

    # Returns what a function returns called on an object with arguments.
    def object_call(
        self, object_id: str, function_text: str, *call_arguments: Any
    ) -> Any:
        return self.command(
            "Runtime.callFunctionOn",
            {
                "objectId": object_id,
                "functionDeclaration": function_text,
                "arguments": [
                    {"value": call_argument}
                    for call_argument in call_arguments
                ],
                "returnByValue": True,
            },
        )["result"].get("value")

    # Starts opening a page, which a settle then waits on.
    def page_navigate(self, page_url: str) -> None:
        self.settle_begin()
        navigation = self.command("Page.navigate", {"url": page_url})
        if "errorText" in navigation:
            raise RuntimeError(f"{page_url}: {navigation['errorText']}")
        self.navigation_frame_id = navigation["frameId"]
        self.is_started = False

    # Opens a page, returning once its frames stopped loading and each drew.
    def page_open(self, page_url: str) -> None:
        self.page_navigate(page_url)
        self.browser_session.settled_tab_wait([self])

    # Presses a key, returning once the state changed and each frame drew.
    def press(
        self,
        key_name: str,
        state_frame_name: str,
        state_expression: str,
        state_before: str,
    ) -> None:
        state_context = self.frame_context(state_frame_name)
        self.settle_begin()
        self.key_send(key_name)
        try:
            state_change = self.command(
                "Runtime.evaluate",
                {
                    "expression": self.wait_expression(
                        test_settings.STATE_CHANGE_FUNCTION,
                        f"() => ({state_expression})",
                        json.dumps(state_before),
                    ),
                    "contextId": state_context,
                    "awaitPromise": True,
                },
            )
        except RuntimeError:
            # A state frame the press reloads is read again once it drew.
            if state_context not in self.destroyed_contexts:
                raise
        else:
            if "exceptionDetails" in state_change:
                raise RuntimeError(
                    f"{state_frame_name}: {state_expression}:"
                    f" {state_change['exceptionDetails']['text']}"
                )
        self.browser_session.settled_tab_wait([self])

    # Forgets the drawn checks, so each frame draws again after what follows.
    def settle_begin(self) -> None:
        self.checked_contexts = set()
        self.destroyed_contexts = set()
        self.detached_frames = set()
        self.drawn_contexts = set()
        self.earlier_contexts = set(self.frame_contexts.values())
        self.has_news = True
        self.hidden_frames = set()
        self.is_started = True
        self.loading_frames = set()
        self.pending_events = []
        self.settle_count += 1

    # Returns whether, after its events, the frames stopped loading and drew.
    def settle_step(self) -> bool:
        self.has_news = False
        while self.pending_events:
            event = self.pending_events.pop(0)
            event_parameters = event["params"]
            if event["method"] == "Page.frameStartedLoading":
                self.loading_frames.add(event_parameters["frameId"])
                self.is_started |= (
                    event_parameters["frameId"] == self.navigation_frame_id
                )
            # A frame removed while loading never stops loading.
            elif event["method"] in (
                "Page.frameDetached",
                "Page.frameStoppedLoading",
            ):
                self.loading_frames.discard(event_parameters["frameId"])
            elif event["method"] == "Runtime.bindingCalled":
                # A check begun before this settle reports nothing about it.
                if event_parameters["payload"] == str(self.settle_count):
                    self.drawn_contexts.add(
                        event_parameters["executionContextId"]
                    )
        return (
            self.is_started
            and not self.loading_frames
            and self.frames_drawn(
                self.command("Page.getFrameTree")["frameTree"]
            )
        )

    # Types text a key per character, returning once each frame drew after it.
    def text_type(self, typed_text: str) -> None:
        self.settle_begin()
        for typed_character in typed_text:
            self.command(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyDown",
                    "key": typed_character,
                    "text": typed_character,
                },
            )
            self.command(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "key": typed_character},
            )
        self.browser_session.settled_tab_wait([self])

    def trace_begin(self) -> None:
        self.command(
            "Tracing.start",
            {
                "traceConfig": {
                    "includedCategories": list(test_settings.TRACE_CATEGORIES)
                },
                "transferMode": "ReturnAsStream",
            },
        )

    # Ends the trace, returning its events.
    def trace_end(self) -> list[Any]:
        self.command("Tracing.end")
        trace_stream = self.event_wait("Tracing.tracingComplete")["stream"]
        trace_chunks: list[bytes] = []
        while True:
            stream_read = self.command(
                "IO.read",
                {
                    "handle": trace_stream,
                    "size": test_settings.TRACE_READ_BYTES,
                },
            )
            trace_chunks.append(
                base64.b64decode(stream_read["data"])
                if stream_read.get("base64Encoded")
                else stream_read["data"].encode()
            )
            if stream_read["eof"]:
                break
        self.command("IO.close", {"handle": trace_stream})
        return json.loads(b"".join(trace_chunks))["traceEvents"]

    # Presses each walk's key until the walk reaches its element.
    def walks_take(
        self, fault_label: str, key_walks: tuple[KeyWalk, ...]
    ) -> None:
        for key_walk in key_walks:
            reached_expression = (
                f"({test_settings.CLICK_WALK_REACHED_FUNCTION})"
                f"({json.dumps(key_walk.element_selector)})"
            )
            press_count = 0
            while not self.frame_evaluate(
                key_walk.frame_name, reached_expression
            ):
                if press_count == test_settings.CLICK_WALK_PRESS_LIMIT:
                    raise RuntimeError(
                        f"{fault_label}: {press_count} {key_walk.key_name}"
                        f" presses reach no {key_walk.element_selector}"
                    )
                self.key_settle(key_walk.key_name)
                self.errors_refuse(fault_label)
                press_count += 1

    # Returns an expression calling a waiting function, named in a trace.
    def wait_expression(self, function_text: str, *argument_texts: str) -> str:
        return (
            f"({function_text})({test_settings.PAINT_WAIT_FUNCTION},"
            f" {', '.join(argument_texts)})\n"
            f"//# sourceURL={test_settings.WAIT_SCRIPT_URL}"
        )


class Screenshots:
    def __init__(
        self,
        report: str,
        report_flag: int,
        out_dir: str,
        compare_dir: str,
        scratch_dir: str,
        chosen_shot: str,
    ) -> None:
        # The browser session a shooting run opens, none in a compare only run.
        self.browser_session: BrowserSession | None = None
        # The one shot a single shot run takes, empty for every shot.
        self.chosen_shot = chosen_shot
        self.report = report
        self.report_flag = report_flag
        self.out_dir = out_dir
        self.compare_dir = compare_dir
        self.scratch_dir = scratch_dir
        self.report_views = self.report_views_select()
        self.click_timings: list[PageTiming] = []
        # The timings of each page drawn in two frames, every one kept.
        self.frame_timings: list[PageTiming] = []
        self.page_timings: list[PageTiming] = []

    # Walks to a step's element, returning the time its key took to settle.
    def click_time(
        self,
        page_tab: PageTab,
        set_name: str,
        click_step: ClickStep,
    ) -> PageTiming:
        fault_label = f"{set_name}: {click_step.label}"
        page_tab.walks_take(fault_label, click_step.key_walks)
        if not page_tab.frame_evaluate(
            click_step.frame_name, "document.hasFocus()"
        ):
            raise RuntimeError(
                f"{fault_label}: {click_step.frame_name} holds no focus"
            )
        page_file = self.relative_file_of(
            page_tab.frame_evaluate(click_step.frame_name, "location.href"),
            self.file_url(self.report),
        )
        if not page_file:
            raise RuntimeError(
                f"{set_name}: {click_step.label} presses outside {self.report}"
            )
        if click_step.pasted_text:
            page_tab.clipboard_write(
                click_step.frame_name, click_step.pasted_text
            )
        # The page writes the state as the press wait compares it.
        state_text_expression = (
            f"JSON.stringify({click_step.state_expression})"
        )
        state_before = page_tab.frame_evaluate(
            click_step.state_frame_name, state_text_expression
        )
        hash_before = page_tab.frame_evaluate(
            test_settings.CLICK_MENU_FRAME_NAME, test_settings.CLICK_HASH_STATE
        )
        page_tab.trace_begin()
        page_tab.press(
            click_step.key_name,
            click_step.state_frame_name,
            click_step.state_expression,
            state_before,
        )
        trace_events = page_tab.trace_end()
        page_tab.errors_refuse(f"{set_name}: {click_step.label}")
        state_after = page_tab.frame_evaluate(
            click_step.state_frame_name, state_text_expression
        )
        if state_after == state_before:
            raise RuntimeError(
                f"{set_name}: {click_step.label} left"
                f" {click_step.state_expression} at {state_before}"
            )
        # A click changing other state than the address stays at its address.
        hash_after = page_tab.frame_evaluate(
            test_settings.CLICK_MENU_FRAME_NAME, test_settings.CLICK_HASH_STATE
        )
        if (
            click_step.state_expression != test_settings.CLICK_HASH_STATE
            and hash_after != hash_before
        ):
            raise RuntimeError(
                f"{set_name}: {click_step.label} moved to {hash_after}"
            )
        phase_name = (
            f"{test_settings.TIMING_CLICK_PHASE_NAME} {click_step.label}"
        )
        return PageTiming(
            page_file,
            phase_name,
            phase_name,
            self.trace_press_span(
                trace_events, f"{set_name}: {click_step.label}"
            ),
            set_name,
        )

    # Times every click of each click set this report runs.
    def clicks_time(self) -> None:
        _, width_px, height_px = test_settings.SCREENSHOT_VIEWPORTS[0]
        entry_url = self.file_url(
            os.path.join(self.report, test_settings.ENTRY_PAGE)
        )
        browser_session = self.session()
        for click_set in _CLICKS:
            if not click_set.shot_flags & self.report_flag:
                continue
            with browser_session.tab(width_px, height_px) as page_tab:
                # The golden bookmarks time page loads, so this one is not.
                page_tab.page_open(entry_url + click_set.view_hash)
                page_tab.errors_refuse(click_set.set_name)
                for click_step in click_set.click_steps:
                    self.click_timings.append(
                        self.click_time(
                            page_tab, click_set.set_name, click_step
                        )
                    )

    def copy_shoot(
        self,
        view_index: int,
        prefix: str,
        view: ScreenshotSet,
    ) -> int:
        if os.path.exists(self.scratch_dir):
            shutil.rmtree(self.scratch_dir)
        shutil.copytree(self.report, self.scratch_dir)
        try:
            for relative_path in view.absent_files:
                os.remove(os.path.join(self.scratch_dir, relative_path))
            return self.view_shoot(self.scratch_dir, view_index, prefix, view)
        finally:
            shutil.rmtree(self.scratch_dir)

    # Groups changed pixels into boxes, a tile touching another joining it.
    def changed_regions(
        self, changed_mask: PIL.Image.Image
    ) -> list[tuple[int, int, int, int]]:
        tile_mask = changed_mask.reduce(test_settings.COMPARE_REGION_TILE_PX)
        marked_tiles = {
            (tile_index % tile_mask.width, tile_index // tile_mask.width)
            for tile_index, tile_value in enumerate(tile_mask.tobytes())
            if tile_value
        }
        changed_regions: list[tuple[int, int, int, int]] = []
        while marked_tiles:
            pending_tiles = [marked_tiles.pop()]
            region_columns: list[int] = []
            region_rows: list[int] = []
            while pending_tiles:
                tile_column, tile_row = pending_tiles.pop()
                region_columns.append(tile_column)
                region_rows.append(tile_row)
                for neighbour_tile in (
                    (tile_column + column_step, tile_row + row_step)
                    for column_step in (-1, 0, 1)
                    for row_step in (-1, 0, 1)
                ):
                    if neighbour_tile in marked_tiles:
                        marked_tiles.remove(neighbour_tile)
                        pending_tiles.append(neighbour_tile)
            tile_left = (
                min(region_columns) * test_settings.COMPARE_REGION_TILE_PX
            )
            tile_top = min(region_rows) * test_settings.COMPARE_REGION_TILE_PX
            inner_box = changed_mask.crop(
                (
                    tile_left,
                    tile_top,
                    (max(region_columns) + 1)
                    * test_settings.COMPARE_REGION_TILE_PX,
                    (max(region_rows) + 1)
                    * test_settings.COMPARE_REGION_TILE_PX,
                )
            ).getbbox()
            assert inner_box is not None, "a marked tile holds no change"
            inner_left, inner_top, inner_right, inner_bottom = inner_box
            changed_regions.append(
                (
                    tile_left + inner_left,
                    tile_top + inner_top,
                    tile_left + inner_right,
                    tile_top + inner_bottom,
                )
            )
        return sorted(
            changed_regions,
            key=lambda changed_region: (changed_region[1], changed_region[0]),
        )

    # Returns the commit of a frame a time falls after, minus one for none.
    def commit_index_at(
        self, commit_times: dict[str, list[float]], frame: str, at_time: float
    ) -> int:
        return bisect.bisect_right(commit_times.get(frame, []), at_time) - 1

    # Writes the dimmed shot with boxes, then each region gold and new.
    def compare_image_write(
        self,
        new_shot: PIL.Image.Image,
        gold_shot: PIL.Image.Image,
        changed_mask: PIL.Image.Image,
        changed_regions: list[tuple[int, int, int, int]],
        compare_path: str,
    ) -> None:
        overview_image = PIL.ImageEnhance.Brightness(new_shot).enhance(
            test_settings.COMPARE_KEPT_BRIGHTNESS_SHARE
        )
        overview_image.paste(
            test_settings.COMPARE_HIGHLIGHT_COLOR, mask=changed_mask
        )
        box_drawing = PIL.ImageDraw.Draw(overview_image)
        label_font = PIL.ImageFont.load_default(
            size=test_settings.COMPARE_LABEL_FONT_PX
        )
        for region_number, (
            region_left,
            region_top,
            region_right,
            region_bottom,
        ) in enumerate(changed_regions, 1):
            box_drawing.rectangle(
                (
                    region_left - test_settings.COMPARE_BOX_LINE_PX,
                    region_top - test_settings.COMPARE_BOX_LINE_PX,
                    region_right - 1 + test_settings.COMPARE_BOX_LINE_PX,
                    region_bottom - 1 + test_settings.COMPARE_BOX_LINE_PX,
                ),
                outline=test_settings.COMPARE_HIGHLIGHT_COLOR,
                width=test_settings.COMPARE_BOX_LINE_PX,
            )
            box_drawing.text(
                (
                    max(region_left - test_settings.COMPARE_BOX_LINE_PX, 0),
                    max(
                        region_top
                        - test_settings.COMPARE_BOX_LINE_PX
                        - test_settings.COMPARE_LABEL_FONT_PX,
                        0,
                    ),
                ),
                str(region_number),
                fill=test_settings.COMPARE_HIGHLIGHT_COLOR,
                font=label_font,
            )
        region_panels: list[PIL.Image.Image] = []
        panels_height = 0
        for region_number, changed_region in enumerate(changed_regions, 1):
            if any(
                self.region_holds(other_region, changed_region)
                for other_region in changed_regions
                if other_region != changed_region
            ):
                continue
            region_panel = self.region_panel(
                region_number, changed_region, gold_shot, new_shot, label_font
            )
            if (
                panels_height + region_panel.height
                > test_settings.COMPARE_PANELS_MAX_HEIGHT_SHARE
                * new_shot.height
            ):
                continue
            region_panels.append(region_panel)
            panels_height += region_panel.height + test_settings.COMPARE_GAP_PX
        compare_image = PIL.Image.new(
            "RGB",
            (
                max(
                    [overview_image.width]
                    + [region_panel.width for region_panel in region_panels]
                ),
                overview_image.height + panels_height,
            ),
            test_settings.COMPARE_BACKGROUND_COLOR,
        )
        compare_image.paste(overview_image, (0, 0))
        panel_top = overview_image.height
        for region_panel in region_panels:
            compare_image.paste(region_panel, (0, panel_top))
            panel_top += region_panel.height + test_settings.COMPARE_GAP_PX
        os.makedirs(self.compare_dir, exist_ok=True)
        compare_image.save(compare_path)

    # Refuses a call graph that draws past a limit of one with no error report.
    def draw_limit_check(self, test_name: str) -> None:
        if os.path.exists(self.scratch_dir):
            shutil.rmtree(self.scratch_dir)
        shutil.copytree(self.report, self.scratch_dir)
        try:
            settings_path = os.path.join(
                self.scratch_dir, test_settings.DRAW_LIMIT_SETTINGS_FILE_PATH
            )
            with open(settings_path, encoding="utf-8") as settings_file:
                settings_text = settings_file.read()
            lowered_text, change_count = (
                test_settings.DRAW_LIMIT_SETTING_PATTERN.subn(
                    test_settings.DRAW_LIMIT_SETTING_LOWERED, settings_text
                )
            )
            if change_count != 1:
                raise RuntimeError(f"{settings_path}: holds no draw limit")
            with open(settings_path, "w", encoding="utf-8") as settings_file:
                settings_file.write(lowered_text)
            page_address = (
                self.file_url(
                    os.path.join(self.scratch_dir, test_settings.ENTRY_PAGE)
                )
                + f"#test={test_name}&view=call-graph"
            )
            (error_report,) = self.session().pages_error_messages(
                [page_address]
            )
            if (
                not error_report
                or test_settings.DRAW_LIMIT_ERROR_TEXT not in error_report
            ):
                raise RuntimeError(
                    f"{page_address}: reports {error_report!r},"
                    f" expected {test_settings.DRAW_LIMIT_ERROR_TEXT!r}"
                )
        finally:
            shutil.rmtree(self.scratch_dir)

    # Returns the entry page's href relative to the index, symlinks resolved.
    def entry_href(self, report_dir: str, index_path: str) -> str:
        return urllib.parse.quote(
            os.path.relpath(
                os.path.realpath(
                    os.path.join(report_dir, test_settings.ENTRY_PAGE)
                ),
                os.path.realpath(os.path.dirname(index_path)),
            )
        )

    # Refuses a shot drawing an error message other than the one listed.
    def error_page_check(
        self, shot: str, view: ScreenshotSet, drawn_message: str
    ) -> None:
        if drawn_message != view.error_message:
            raise RuntimeError(
                f"{shot}: the error handler drew {drawn_message!r},"
                f" the list expects {view.error_message!r}"
            )

    # Returns the address the browser opens a file or directory at.
    def file_url(self, path: str) -> str:
        return "file://" + urllib.parse.quote(path)

    # Names each shot that differs from its gold twin, each one missing.
    def gold_compare(
        self, gold_dir: str, prefix: str, verbose_level: int
    ) -> None:
        shot_pattern = re.compile(
            f"[0-9]{{{test_settings.SHOT_NUMBER_DIGITS}}}-[^-]+-[^-]+-[^-]+"
            f"-{re.escape(prefix.rstrip('_'))}-.*"
            + re.escape(test_settings.IMAGE_SUFFIX)
        )
        if os.path.isdir(self.compare_dir):
            for file_name in os.listdir(self.compare_dir):
                shot_file_name = file_name.removeprefix(
                    test_settings.COMPARE_IMAGE_PREFIX
                )
                if (
                    file_name.startswith(test_settings.COMPARE_IMAGE_PREFIX)
                    and shot_pattern.fullmatch(shot_file_name)
                    and self.shot_is_taken(
                        shot_file_name.removesuffix(test_settings.IMAGE_SUFFIX)
                    )
                ):
                    os.remove(os.path.join(self.compare_dir, file_name))
        shot_names = [
            shot
            for shot in self.shot_names(prefix)
            if self.shot_is_taken(shot)
        ]
        is_same = True
        for shot_name in shot_names:
            if not self.gold_compare_one(
                shot_name + test_settings.IMAGE_SUFFIX, gold_dir, verbose_level
            ):
                is_same = False
        for file_name in sorted(os.listdir(gold_dir)):
            gold_shot = file_name.removesuffix(test_settings.IMAGE_SUFFIX)
            if (
                shot_pattern.fullmatch(file_name)
                and self.shot_is_taken(gold_shot)
                and gold_shot not in shot_names
            ):
                print(
                    f"{file_name}: in {gold_dir}, not among this run's shots"
                )
                is_same = False
        # A difference makes the compare directory, its one sign to the run.
        if not is_same:
            os.makedirs(self.compare_dir, exist_ok=True)

    def gold_compare_one(
        self, file_name: str, gold_dir: str, verbose_level: int
    ) -> bool:
        new_path = os.path.join(self.out_dir, file_name)
        if not os.path.isfile(new_path):
            raise RuntimeError(f"{file_name}: absent from {self.out_dir}")
        gold_path = os.path.join(gold_dir, file_name)
        if not os.path.isfile(gold_path):
            print(f"{file_name}: absent from {gold_dir}")
            return False
        new_shot = PIL.Image.open(new_path).convert("RGB")
        gold_shot = PIL.Image.open(gold_path).convert("RGB")
        if new_shot.size != gold_shot.size:
            print(
                f"{file_name}: {new_shot.width}x{new_shot.height}, gold"
                f" {gold_shot.width}x{gold_shot.height}"
            )
            return False
        red_change, green_change, blue_change = PIL.ImageChops.difference(
            new_shot, gold_shot
        ).split()
        channel_change = PIL.ImageChops.lighter(
            PIL.ImageChops.lighter(red_change, green_change), blue_change
        )
        if channel_change.getbbox() is None:
            if verbose_level:
                verbose_print(verbose_level, [f"{file_name}: same as gold"])
            return True
        changed_mask = channel_change.point(
            lambda channel_value: 255 if channel_value else 0
        )
        changed_count = changed_mask.histogram()[255]
        changed_regions = self.changed_regions(changed_mask)
        compare_path = os.path.join(
            self.compare_dir, test_settings.COMPARE_IMAGE_PREFIX + file_name
        )
        self.compare_image_write(
            new_shot, gold_shot, changed_mask, changed_regions, compare_path
        )
        listed_regions = "; ".join(
            f"{region_left},{region_top} to {region_right},{region_bottom}"
            for region_left, region_top, region_right, region_bottom in (
                changed_regions[: test_settings.COMPARE_LISTED_REGION_COUNT]
            )
        )
        unlisted_count = (
            len(changed_regions) - test_settings.COMPARE_LISTED_REGION_COUNT
        )
        if unlisted_count > 0:
            listed_regions += f"; {unlisted_count} more"
        changed_percent = (
            100 * changed_count / (new_shot.width * new_shot.height)
        )
        print(
            f"{file_name}: {changed_count} pixels differ"
            f" ({changed_percent:.2f}%),"
            f" largest channel change {channel_change.getextrema()[1]},"
            f" {len(changed_regions)} region(s) {listed_regions},"
            f" compare image {compare_path}"
        )
        return False

    # Merges this report's pages and timings into the index, returning all.
    def index_write(
        self,
        prefix: str,
        index_path: str,
        template: str,
        timing_rows: list[TimingRow],
    ) -> list[dict[str, str]]:
        assert template.count(test_settings.INDEX_MARKER) == 1, (
            test_settings.INDEX_MARKER
        )
        report_name = prefix.rstrip("_")
        report_href = self.entry_href(self.report, index_path)
        index_reports: list[dict[str, str]] = []
        for listed_report in test_settings.INDEX_REPORT_NAMES:
            listed_dir = os.path.join(
                os.path.dirname(index_path), listed_report
            )
            if not os.path.isfile(
                os.path.join(listed_dir, test_settings.ENTRY_PAGE)
            ):
                raise RuntimeError(
                    f"{listed_dir} holds no {test_settings.ENTRY_PAGE}"
                )
            index_reports.append(
                {
                    "name": listed_report,
                    "href": self.entry_href(listed_dir, index_path),
                }
            )
        width_px, height_px = test_settings.SCREENSHOT_VIEWPORTS[0][1:]
        pages: dict[str, str] = {}
        page_timings: list[dict[str, str]] = []
        if os.path.isfile(index_path):
            with open(index_path) as index_file:
                found = test_settings.INDEX_DATA_PATTERN.search(
                    index_file.read()
                )
            assert found, f"{index_path} holds no shot list"
            index_data = json.loads(found.group(1))
            if "page_timings" not in index_data:
                raise RuntimeError(f"{index_path} holds no page timings")
            for page in index_data["pages"]:
                if page["report"] != report_name:
                    pages[page["name"]] = page["href"]
            timing_keys = sorted(("report", *TimingRow._fields))
            for page_timing in index_data["page_timings"]:
                if sorted(page_timing) != timing_keys:
                    raise RuntimeError(
                        f"{index_path} holds a page timing keyed"
                        f" {sorted(page_timing)}, not {timing_keys}"
                    )
            page_timings = [
                page_timing
                for page_timing in index_data["page_timings"]
                if page_timing["report"] != report_name
            ]
        page_timings += [
            {"report": report_name, **timing_row._asdict()}
            for timing_row in timing_rows
        ]
        for view_index, view in self.report_views:
            if (
                view.absent_files
                or view.shot_flags & test_settings.SHOOT_INDEX_PAGE
            ):
                continue
            variant = view.shot_variants(view_index)[0]
            pages[
                self.shot_name(view_index, "", prefix, view, variant.mode_name)
            ] = report_href + self.page_address(
                view.view_hash,
                view.menu_entry_number,
                variant.toggle_dark_value,
            )
        report_timings = sorted(
            page_timings, key=lambda page_timing: page_timing["report"]
        )
        data = {
            "width": width_px,
            "height": height_px,
            "screenshot_keys": [
                test_settings.SCREENSHOT_LABEL_URL_PARAM,
                test_settings.SCREENSHOT_MENU_URL_PARAM,
            ],
            "pages": [
                {
                    "name": name,
                    "report": name.split(test_settings.SHOT_NAME_SEPARATOR)[
                        -2
                    ],
                    "href": pages[name],
                }
                for name in sorted(pages)
            ],
            "reports": index_reports,
            "page_timings": report_timings,
        }
        data_script = (
            '<script id="shot-list-" type="application/json">'
            + json.dumps(data, indent=1)
            + "</script>"
        )
        with open(index_path, "w") as index_file:
            index_file.write(
                template.replace(test_settings.INDEX_MARKER, data_script)
            )
        return report_timings

    # Refuses a logo link other than each debug query value's golden one.
    def logo_links_check(self) -> None:
        _, width_px, height_px = test_settings.SCREENSHOT_VIEWPORTS[0]
        entry_url = self.file_url(
            os.path.join(self.report, test_settings.ENTRY_PAGE)
        )
        browser_session = self.session()
        for query_text, link_text in test_settings.MENU_LOGO_LINKS.items():
            with browser_session.tab(width_px, height_px) as page_tab:
                page_tab.page_open(entry_url + query_text)
                page_markup = page_tab.frame_evaluate(
                    test_settings.CLICK_MENU_FRAME_NAME,
                    "document.documentElement.outerHTML",
                )
                error_message = page_tab.error_message()
            link_match = test_settings.MENU_LOGO_LINK_PATTERN.search(
                page_markup
            )
            found_text = link_match.group(1) if link_match else None
            if found_text == link_text:
                continue
            raise RuntimeError(
                f"{entry_url + query_text}: the logo link holds"
                f" {found_text!r}, expected {link_text!r}, the error handler"
                f" drawing {error_message!r}"
            )

    # Returns the query and hash a page is shot at.
    def page_address(
        self, view_hash: str, menu_entry_number: str, toggle_dark_value: str
    ) -> str:
        query_values = {
            test_settings.SCREENSHOT_TOGGLE_DARK_URL_PARAM: toggle_dark_value,
        }
        query_values[test_settings.SCREENSHOT_LABEL_URL_PARAM] = (
            test_settings.SCREENSHOT_LABEL_URL_VALUE
        )
        if menu_entry_number:
            query_values[test_settings.SCREENSHOT_MENU_URL_PARAM] = (
                menu_entry_number
            )
        return "?" + urllib.parse.urlencode(query_values) + view_hash

    # Keeps the longer of the timings of one page file and phase.
    def page_timing_keep(
        self,
        page_timings: dict[tuple[str, str], PageTiming],
        page_timing: PageTiming,
    ) -> None:
        timing_key = (page_timing.page_file, page_timing.phase_name)
        if (
            timing_key not in page_timings
            or page_timing.duration_us > page_timings[timing_key].duration_us
        ):
            page_timings[timing_key] = page_timing

    def page_url(
        self,
        page_dir: str,
        view_hash: str,
        menu_entry_number: str,
        toggle_dark_value: str,
    ) -> str:
        page = (
            page_dir
            if os.path.isfile(page_dir)
            else os.path.join(page_dir, test_settings.ENTRY_PAGE)
        )
        address = self.page_address(
            view_hash, menu_entry_number, toggle_dark_value
        )
        return self.file_url(page) + address

    # Returns whether the outer region holds the whole inner region.
    def region_holds(
        self,
        outer_region: tuple[int, int, int, int],
        inner_region: tuple[int, int, int, int],
    ) -> bool:
        return (
            outer_region[0] <= inner_region[0]
            and outer_region[1] <= inner_region[1]
            and inner_region[2] <= outer_region[2]
            and inner_region[3] <= outer_region[3]
        )

    # Sets the gold and the new cut of one region side by side under a label.
    def region_panel(
        self,
        region_number: int,
        changed_region: tuple[int, int, int, int],
        gold_shot: PIL.Image.Image,
        new_shot: PIL.Image.Image,
        label_font: PIL.ImageFont.FreeTypeFont | PIL.ImageFont.ImageFont,
    ) -> PIL.Image.Image:
        region_left, region_top, region_right, region_bottom = changed_region
        crop_box = (
            max(region_left - test_settings.COMPARE_CROP_MARGIN_PX, 0),
            max(region_top - test_settings.COMPARE_CROP_MARGIN_PX, 0),
            min(
                region_right + test_settings.COMPARE_CROP_MARGIN_PX,
                new_shot.width,
            ),
            min(
                region_bottom + test_settings.COMPARE_CROP_MARGIN_PX,
                new_shot.height,
            ),
        )
        crop_width = crop_box[2] - crop_box[0]
        crop_height = crop_box[3] - crop_box[1]
        gold_label = (
            f"{region_number} gold {region_left},{region_top}"
            f" to {region_right},{region_bottom}"
        )
        gold_label_width = int(label_font.getlength(gold_label)) + 1
        column_width = max(crop_width, gold_label_width)
        label_height = (
            test_settings.COMPARE_LABEL_FONT_PX + test_settings.COMPARE_GAP_PX
        )
        new_left = column_width + test_settings.COMPARE_GAP_PX
        region_panel = PIL.Image.new(
            "RGB",
            (new_left + column_width, label_height + crop_height),
            test_settings.COMPARE_BACKGROUND_COLOR,
        )
        region_panel.paste(gold_shot.crop(crop_box), (0, label_height))
        region_panel.paste(new_shot.crop(crop_box), (new_left, label_height))
        panel_drawing = PIL.ImageDraw.Draw(region_panel)
        panel_drawing.text(
            (0, 0),
            gold_label,
            fill=test_settings.COMPARE_LABEL_COLOR,
            font=label_font,
        )
        panel_drawing.text(
            (new_left, 0),
            f"{region_number} new",
            fill=test_settings.COMPARE_LABEL_COLOR,
            font=label_font,
        )
        return region_panel

    # Returns the file an address names under a root, empty outside that.
    def relative_file_of(self, url: str, root_url: str) -> str:
        split_url = urllib.parse.urlsplit(url)
        split_root = urllib.parse.urlsplit(root_url)
        url_place = (split_url.scheme, split_url.netloc.lower())
        root_place = (split_root.scheme, split_root.netloc.lower())
        url_path = urllib.parse.unquote(split_url.path)
        root_path = urllib.parse.unquote(split_root.path) + "/"
        if url_place != root_place or not url_path.startswith(root_path):
            return ""
        return url_path.removeprefix(root_path)

    def report_views_select(
        self,
    ) -> list[tuple[int, ScreenshotSet]]:
        return [
            (view_index, view)
            for view_index, view in enumerate(_VIEWS, 1)
            if view.shot_flags & self.report_flag
        ]

    # Returns the browser session, which a compare only run lacks.
    def session(self) -> BrowserSession:
        assert self.browser_session, "a compare only run opens no page"
        return self.browser_session

    def shoot_all(self, prefix: str) -> int:
        written = 0
        for view_index, view in self.report_views:
            if view.shot_flags & test_settings.SHOOT_INDEX_PAGE:
                continue
            if not self.view_is_taken(view_index, prefix, view):
                continue
            if view.absent_files:
                written += self.copy_shoot(view_index, prefix, view)
            else:
                written += self.view_shoot(
                    self.report, view_index, prefix, view
                )
        return written

    # Shoots the index page at the given hash, else at its view's own.
    def index_shoot(
        self, prefix: str, index_path: str, index_hash: str
    ) -> int:
        written = 0
        for view_index, view in self.report_views:
            if view.shot_flags & test_settings.SHOOT_INDEX_PAGE and (
                self.view_is_taken(view_index, prefix, view)
            ):
                written += self.view_shoot(
                    index_path,
                    view_index,
                    prefix,
                    view._replace(view_hash=index_hash or view.view_hash),
                )
        return written

    # Names a shot, leaving out the resolution when the size is empty.
    def shot_name(
        self,
        view_index: int,
        size_name: str,
        prefix: str,
        view: ScreenshotSet,
        mode_name: str,
    ) -> str:
        return test_settings.SHOT_NAME_SEPARATOR.join(
            name_part
            for name_part in (
                f"{view_index:0{test_settings.SHOT_NUMBER_DIGITS}d}",
                size_name,
                view.view_name,
                view.subview_name,
                prefix.rstrip("_"),
                mode_name,
            )
            if name_part
        )

    # Names every shot of this report, the index page's too.
    def shot_names(self, prefix: str) -> list[str]:
        return [
            shot
            for view_index, view in self.report_views
            if view.is_pictured(view_index)
            for shot in self.view_shot_names(view_index, prefix, view)
        ]

    # Returns whether the run takes a shot, a single shot run its own alone.
    def shot_is_taken(self, shot: str) -> bool:
        return not self.chosen_shot or shot == self.chosen_shot

    # Returns whether the run takes a shot of the view.
    def view_is_taken(
        self, view_index: int, prefix: str, view: ScreenshotSet
    ) -> bool:
        return any(
            self.shot_is_taken(shot)
            for shot in self.view_shot_names(view_index, prefix, view)
        )

    # Names the shots of one view, one for each of its variants.
    def view_shot_names(
        self, view_index: int, prefix: str, view: ScreenshotSet
    ) -> list[str]:
        return [
            self.shot_name(
                view_index,
                variant.size_name,
                prefix,
                view,
                variant.mode_name,
            )
            for variant in view.shot_variants(view_index)
        ]

    # Refuses an error report from any view of any test the report holds.
    def test_views_check(self) -> None:
        entry_path = os.path.join(self.report, test_settings.ENTRY_PAGE)
        database_path = os.path.join(
            self.report, test_settings.SOURCE_DATABASE_FILE_PATH
        )
        with open(database_path, encoding="utf-8") as database_file:
            database_match = test_settings.SOURCE_DATABASE_PATTERN.search(
                database_file.read()
            )
        if not database_match:
            raise RuntimeError(f"{database_path}: holds no source database")
        test_files = json.loads(database_match.group(1))["filesWithCounters"]
        page_addresses = [
            self.file_url(entry_path)
            + f"#test={test_name}&"
            + view_part.format(first_file=urllib.parse.quote(file_names[0]))
            for test_name, file_names in test_files.items()
            for view_part in test_settings.SHOOT_TEST_VIEW_PARTS[
                self.report_flag
            ]
        ]
        # A page holding an error proves that DevTools shows the reports.
        error_address = (
            self.file_url(entry_path) + test_settings.VIEW_CHECK_ERROR_HASH
        )
        error_reports = self.session().pages_error_messages(
            [*page_addresses, error_address]
        )
        for page_address, error_report in zip(
            page_addresses, error_reports[:-1], strict=True
        ):
            if error_report:
                raise RuntimeError(f"{page_address}: {error_report}")
        if not error_reports[-1]:
            raise RuntimeError(f"{error_address}: wrote no error report")
        if self.report_flag == test_settings.SHOOT_REGULAR_REPORT:
            self.draw_limit_check(next(iter(test_files)))

    # Writes every report's timings, slowest first, then refuses one too slow.
    def timing_file_write(
        self,
        timing_path: str,
        report_timings: list[dict[str, str]],
        timing_rows: list[TimingRow],
    ) -> int:
        file_columns = ("duration_ms", "report", "page_file", "phase_label")
        file_rows = [
            ("ms", "report", "page", "phase", "shot"),
            *(
                tuple(report_timing[column] for column in file_columns)
                + (report_timing["shot"],)
                for report_timing in sorted(
                    report_timings,
                    key=lambda report_timing: (
                        -float(report_timing["duration_ms"])
                    ),
                )
            ),
        ]
        column_widths = [
            max(len(file_row[column_index]) for file_row in file_rows)
            for column_index in range(len(file_columns))
        ]
        with open(timing_path, "w") as timing_file:
            for file_row in file_rows:
                timing_file.write(
                    "  ".join(
                        row_text.ljust(column_width)
                        for row_text, column_width in zip(
                            file_row[:-1], column_widths, strict=True
                        )
                    )
                    + f"  {file_row[-1]}\n"
                )
        slow_rows = [
            (timing_row, limit_ms)
            for timing_row in timing_rows
            if (limit_ms := timing_row.limit_ms()) is not None
            and float(timing_row.duration_ms) > limit_ms
        ]
        if not slow_rows:
            return 0
        slowest_row, slowest_limit_ms = max(
            slow_rows, key=lambda slow_row: float(slow_row[0].duration_ms)
        )
        print(
            f"error: {slowest_row.page_file}: {slowest_row.phase_label} took"
            f" {slowest_row.duration_ms} ms in {slowest_row.shot}, over"
            f" {slowest_limit_ms} ms, listed in {timing_path}",
            file=sys.stderr,
        )
        return 1

    # Returns each page file's slowest load and largest phases, then clicks.
    def timing_rows(self) -> list[TimingRow]:
        largest_timings: dict[tuple[str, str], PageTiming] = {}
        for page_timing in self.page_timings:
            self.page_timing_keep(largest_timings, page_timing)
        file_timings: dict[str, list[PageTiming]] = {}
        for page_timing in sorted(
            largest_timings.values(),
            key=lambda page_timing: (
                page_timing.phase_name != test_settings.TIMING_LOAD_PHASE_NAME,
                -page_timing.duration_us,
            ),
        ):
            file_timings.setdefault(page_timing.page_file, []).append(
                page_timing
            )
        kept_timings: list[PageTiming] = []
        for page_file_timings in sorted(
            file_timings.values(),
            key=lambda file_entry: -file_entry[0].duration_us,
        ):
            kept_timings += page_file_timings[
                : test_settings.TIMING_FILE_LINES_MAX
            ]
        kept_rows: list[TimingRow] = []
        for kept_timing in (
            kept_timings + self.frame_timings + self.click_timings
        ):
            duration_ms = (
                kept_timing.duration_us
                / test_settings.TIMING_MICROSECONDS_PER_MILLISECOND
            )
            kept_rows.append(
                TimingRow(
                    f"{duration_ms:.1f}",
                    kept_timing.page_file,
                    kept_timing.phase_label,
                    kept_timing.shot,
                )
            )
        return kept_rows

    # Returns each frame a view page drew, the first timed from its commit.
    def trace_frame_timings(
        self,
        trace_events: list[Any],
        trace_name: str,
        page_dir: str,
        shot: str,
    ) -> list[PageTiming]:
        root_url = self.file_url(page_dir)
        view_commits = [
            (trace_event, page_file)
            for trace_event in trace_events
            if trace_event["name"] == test_settings.TRACE_COMMIT_NAME
            and (
                page_file := self.relative_file_of(
                    trace_event["args"]["data"]["url"], root_url
                )
            )
            not in ("", test_settings.ENTRY_PAGE)
        ]
        if len(view_commits) != 1:
            raise RuntimeError(
                f"{trace_name}: {len(view_commits)} view page commits, not 1"
            )
        ((view_commit, page_file),) = view_commits
        view_frame = view_commit["args"]["data"]["frame"]

        # Lists the instant events of a name, in the order they happened.
        def instants_named(event_name: str) -> list[Any]:
            return sorted(
                (
                    trace_event
                    for trace_event in trace_events
                    if trace_event["name"] == event_name
                    and trace_event["ph"] == test_settings.TRACE_INSTANT_TYPE
                ),
                key=lambda trace_event: trace_event["ts"],
            )

        frame_begins = instants_named(test_settings.TRACE_FRAME_BEGIN_NAME)
        activations = instants_named(test_settings.TRACE_ACTIVATE_NAME)
        screen_draws = instants_named(test_settings.TRACE_DRAW_NAME)
        view_paints = sorted(
            (
                trace_event
                for trace_event in trace_events
                if trace_event["name"] == test_settings.TRACE_PAINT_NAME
                and trace_event["ph"] == test_settings.TRACE_COMPLETE_TYPE
                and trace_event["args"]["data"]["frame"] == view_frame
                and trace_event["ts"] > view_commit["ts"]
            ),
            key=lambda trace_event: trace_event["ts"],
        )
        # Each main thread frame painting the view, by its process and number.
        painted_frames: list[tuple[int, int, int]] = []
        for view_paint in view_paints:
            frame_begin = [
                frame_begin
                for frame_begin in frame_begins
                if (frame_begin["pid"], frame_begin["tid"])
                == (view_paint["pid"], view_paint["tid"])
                and frame_begin["ts"] <= view_paint["ts"]
            ][-1]
            painted_frame = (
                frame_begin["pid"],
                frame_begin["args"]["layerTreeId"],
                frame_begin["args"]["data"]["frameId"],
            )
            if painted_frame not in painted_frames:
                painted_frames.append(painted_frame)
        # A frame shows once the compositor draws after taking it.
        draw_times: list[float] = []
        for process_id, layer_tree_id, frame_number in painted_frames:
            activation = next(
                activation
                for activation in activations
                if activation["pid"] == process_id
                and activation["args"]["layerTreeId"] == layer_tree_id
                and activation["args"]["frameId"] == frame_number
            )
            screen_draw = next(
                screen_draw
                for screen_draw in screen_draws
                if screen_draw["pid"] == process_id
                and screen_draw["args"]["layerTreeId"] == layer_tree_id
                and screen_draw["ts"] >= activation["ts"]
            )
            draw_times.append(screen_draw["ts"])
        if len(draw_times) != len(test_settings.TIMING_FRAME_PHASE_NAMES):
            raise RuntimeError(
                f"{trace_name}: {page_file} drew {len(draw_times)} frames,"
                f" not {len(test_settings.TIMING_FRAME_PHASE_NAMES)}"
            )
        return [
            PageTiming(
                page_file, phase_name, phase_name, draw_time - start_time, shot
            )
            for phase_name, start_time, draw_time in zip(
                test_settings.TIMING_FRAME_PHASE_NAMES,
                [view_commit["ts"], *draw_times[:-1]],
                draw_times,
                strict=True,
            )
        ]

    # Returns the longest load and phase slice of each page file a trace shows.
    def trace_page_timings(
        self, trace_events: list[Any], root_url: str, shot: str
    ) -> list[PageTiming]:
        mark_events = [
            trace_event
            for trace_event in trace_events
            if trace_event["name"] in test_settings.TRACE_MARK_NAMES
            and trace_event["ph"] != test_settings.TRACE_END_TYPE
        ]
        mark_events.sort(key=lambda trace_event: trace_event["ts"])
        commit_times: dict[str, list[float]] = {}
        commit_files: dict[str, list[str]] = {}
        load_marks: list[tuple[str, float]] = []
        phase_slices = self.trace_page_slices(trace_events)
        for trace_event in mark_events:
            if trace_event["name"] == test_settings.TRACE_COMMIT_NAME:
                commit_data = trace_event["args"]["data"]
                commit_times.setdefault(commit_data["frame"], []).append(
                    trace_event["ts"]
                )
                commit_files.setdefault(commit_data["frame"], []).append(
                    self.relative_file_of(commit_data["url"], root_url)
                )
            elif trace_event["name"] == test_settings.TRACE_LOAD_NAME:
                load_marks.append(
                    (trace_event["args"]["data"]["frame"], trace_event["ts"])
                )
        commit_phase_ends: dict[tuple[str, int], float] = {}
        for begun_event, duration_us in phase_slices:
            frame = begun_event["args"][
                test_settings.TRACE_PHASES[begun_event["name"]][1]
            ]["frame"]
            commit_key = (
                frame,
                self.commit_index_at(commit_times, frame, begun_event["ts"]),
            )
            commit_phase_ends[commit_key] = max(
                commit_phase_ends.get(commit_key, 0),
                begun_event["ts"] + duration_us,
            )
        page_timings: dict[tuple[str, str], PageTiming] = {}
        loaded_commits: set[tuple[str, int]] = set()
        for frame, load_time in load_marks:
            commit_index = self.commit_index_at(commit_times, frame, load_time)
            if commit_index < 0 or (frame, commit_index) in loaded_commits:
                continue
            loaded_commits.add((frame, commit_index))
            if not commit_files[frame][commit_index]:
                continue
            self.page_timing_keep(
                page_timings,
                PageTiming(
                    commit_files[frame][commit_index],
                    test_settings.TIMING_LOAD_PHASE_NAME,
                    test_settings.TIMING_LOAD_PHASE_NAME,
                    max(
                        load_time,
                        commit_phase_ends.get((frame, commit_index), 0),
                    )
                    - commit_times[frame][commit_index],
                    shot,
                ),
            )
        for begun_event, duration_us in phase_slices:
            phase_name, data_key = test_settings.TRACE_PHASES[
                begun_event["name"]
            ]
            slice_data = begun_event["args"][data_key]
            frame = slice_data["frame"]
            commit_index = self.commit_index_at(
                commit_times, frame, begun_event["ts"]
            )
            if commit_index < 0 or not commit_files[frame][commit_index]:
                continue
            phase_label = phase_name
            if phase_name == test_settings.TIMING_SCRIPT_PHASE_NAME:
                script_file = self.relative_file_of(
                    slice_data["url"], root_url
                )
                if not script_file:
                    raise ValueError(
                        f"{begun_event['name']} runs {slice_data['url']!r}"
                        f" outside {root_url}"
                    )
                phase_label = f"{phase_name} {script_file}"
            self.page_timing_keep(
                page_timings,
                PageTiming(
                    commit_files[frame][commit_index],
                    phase_name,
                    phase_label,
                    duration_us,
                    shot,
                ),
            )
        return list(page_timings.values())

    # Returns the time from a trace's first press to the end of its last phase.
    def trace_press_span(
        self, trace_events: list[Any], trace_name: str
    ) -> float:
        press_starts = [
            begun_event["ts"]
            for begun_event, _ in self.trace_slices(trace_events)
            if begun_event["name"] == test_settings.TRACE_DISPATCH_NAME
            and begun_event["args"]["data"]["type"]
            in test_settings.TRACE_PRESS_EVENT_TYPES
        ]
        phase_ends = [
            begun_event["ts"] + duration_us
            for begun_event, duration_us in self.trace_page_slices(
                trace_events
            )
        ]
        if not press_starts:
            raise RuntimeError(
                f"{trace_name}: the trace holds no"
                f" {test_settings.TRACE_PRESS_EVENT_TYPES[0]}"
            )
        return max(phase_ends) - min(press_starts)

    # Returns each phase slice of page code, the tool's waits left out.
    def trace_page_slices(
        self, trace_events: list[Any]
    ) -> list[tuple[Any, float]]:
        page_slices: list[tuple[Any, float]] = []
        for begun_event, duration_us in self.trace_slices(trace_events):
            if begun_event["name"] not in test_settings.TRACE_PHASES:
                continue
            slice_data = begun_event["args"][
                test_settings.TRACE_PHASES[begun_event["name"]][1]
            ]
            # A wait's own call or a call into no script runs no page code.
            if slice_data.get("url") == test_settings.WAIT_SCRIPT_URL or (
                begun_event["name"] == test_settings.TRACE_FUNCTION_CALL_NAME
                and slice_data["scriptId"] == test_settings.TRACE_NO_SCRIPT_ID
            ):
                continue
            page_slices.append((begun_event, duration_us))
        return page_slices

    # Returns each slice a trace holds, its first event and its duration.
    def trace_slices(self, trace_events: list[Any]) -> list[tuple[Any, float]]:
        slice_events = [
            trace_event
            for trace_event in trace_events
            if trace_event["ph"] in test_settings.TRACE_SLICE_TYPES
        ]
        slice_events.sort(key=lambda trace_event: trace_event["ts"])
        trace_slices: list[tuple[Any, float]] = []
        begun_slices: dict[tuple[int, int], list[Any]] = {}
        for trace_event in slice_events:
            event_type = trace_event["ph"]
            thread = (trace_event["pid"], trace_event["tid"])
            if event_type == test_settings.TRACE_BEGIN_TYPE:
                begun_slices.setdefault(thread, []).append(trace_event)
            elif event_type == test_settings.TRACE_END_TYPE:
                begun_event = begun_slices[thread].pop()
                trace_slices.append(
                    (begun_event, trace_event["ts"] - begun_event["ts"])
                )
            else:
                trace_slices.append((trace_event, trace_event["dur"]))
        return trace_slices

    # Returns each report page's load and largest phase slices in a trace.
    def trace_timings(
        self,
        trace_events: list[Any],
        trace_name: str,
        page_dir: str,
        shot: str,
    ) -> list[PageTiming]:
        try:
            page_timings = self.trace_page_timings(
                trace_events, self.file_url(page_dir), shot
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"{trace_name}: {error!r}") from error
        if not any(
            page_timing.page_file == test_settings.ENTRY_PAGE
            and page_timing.phase_name == test_settings.TIMING_LOAD_PHASE_NAME
            for page_timing in page_timings
        ):
            raise RuntimeError(
                f"{trace_name}: no {test_settings.TRACE_LOAD_NAME} of"
                f" {test_settings.ENTRY_PAGE} after"
                f" its {test_settings.TRACE_COMMIT_NAME}"
            )
        return page_timings

    # Loads each shot of a view, checking its error, writing a pictured one.
    def view_shoot(
        self,
        page_dir: str,
        view_index: int,
        prefix: str,
        view: ScreenshotSet,
    ) -> int:
        browser_session = self.session()
        is_pictured = view.is_pictured(view_index)
        shot_variants = view.shot_variants(view_index)
        # The index page frames report pages, so only the report shots trace.
        is_traced = not view.shot_flags & (
            test_settings.SHOOT_INDEX_PAGE | test_settings.SHOOT_UNTIMED
        )
        # Every shot of a page drawn in two frames is taken after its second.
        is_drawn_twice = bool(view.shot_flags & test_settings.SHOOT_TWO_FRAMES)
        taken_count = 0
        for variant in shot_variants:
            shot = self.shot_name(
                view_index,
                variant.size_name,
                prefix,
                view,
                variant.mode_name,
            )
            if not self.shot_is_taken(shot):
                continue
            taken_count += 1
            with browser_session.tab(
                variant.width_px, variant.height_px
            ) as page_tab:
                if is_traced or is_drawn_twice:
                    page_tab.trace_begin()
                page_tab.page_open(
                    self.page_url(
                        page_dir,
                        view.view_hash,
                        view.menu_entry_number,
                        variant.toggle_dark_value,
                    )
                )
                if is_drawn_twice:
                    try:
                        frame_timings = self.trace_frame_timings(
                            page_tab.trace_end(), shot, page_dir, shot
                        )
                    except (IndexError, KeyError, StopIteration) as error:
                        raise RuntimeError(f"{shot}: {error!r}") from error
                    if is_traced:
                        self.frame_timings += frame_timings
                elif is_traced:
                    self.page_timings += self.trace_timings(
                        page_tab.trace_end(), shot, page_dir, shot
                    )
                page_tab.walks_take(shot, view.key_walks)
                if view.typed_text:
                    page_tab.text_type(view.typed_text)
                # The index page frames error pages, so it draws reports.
                if not view.shot_flags & test_settings.SHOOT_INDEX_PAGE:
                    self.error_page_check(shot, view, page_tab.error_message())
                if is_pictured:
                    page_tab.image_write(
                        os.path.join(
                            self.out_dir, shot + test_settings.IMAGE_SUFFIX
                        )
                    )
            # Only the first shot traces, so a page's timing is its 720p load.
            is_traced = False
        return taken_count if is_pictured else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", help="a report directory to shoot")
    parser.add_argument("prefix", help="what every file name starts with")
    parser.add_argument(
        "--build-root",
        default="",
        metavar="DIR",
        help="the directory build/ lies in",
    )
    parser.add_argument(
        "--compare-gold",
        default="",
        metavar="DIR",
        help="compare each new shot with the same named shot in DIR, naming"
        " every difference on stdout and writing a compare_ image of it; a"
        " difference exits 0, the --compare-out directory made only for"
        " one, and a shot this run did not write is an error",
    )
    parser.add_argument(
        "--compare-only",
        action="store_true",
        help="shoot nothing and compare the shots already in the --out"
        " directory; needs --compare-gold",
    )
    parser.add_argument(
        "--compare-out",
        default="",
        metavar="DIR",
        help="where the compare_ images go, made when a shot differs"
        " (default the --out directory)",
    )
    parser.add_argument(
        "--diff", action="store_true", help="the report is a diff report"
    )
    parser.add_argument("--index-hash", default="", metavar="HASH")
    parser.add_argument(
        "--out",
        default="",
        help="where the PNGs go (default"
        f" tests/perf2html/{test_settings.SCREENSHOT_DIR_NAME})",
    )
    parser.add_argument("--shot", default="", metavar="NAME")
    parser.add_argument(
        "--verbose",
        action="count",
        default=0,
        help="print where the shots go and how many; a quiet run prints"
        " nothing on success",
    )
    namespace = parser.parse_args()

    report = os.path.abspath(namespace.report)
    if not os.path.isfile(os.path.join(report, test_settings.ENTRY_PAGE)):
        print(
            f"error: {report} holds no {test_settings.ENTRY_PAGE}",
            file=sys.stderr,
        )
        return 2

    gold_dir = os.path.abspath(namespace.compare_gold)
    if namespace.compare_gold and not os.path.isdir(gold_dir):
        print(
            f"error: --compare-gold {gold_dir} is no directory",
            file=sys.stderr,
        )
        return 2

    if namespace.compare_out and not namespace.compare_gold:
        print("error: --compare-out needs --compare-gold", file=sys.stderr)
        return 2

    if namespace.compare_only and not namespace.compare_gold:
        print("error: --compare-only needs --compare-gold", file=sys.stderr)
        return 2

    if namespace.index_hash and not namespace.index_hash.startswith("#"):
        print(
            f"error: --index-hash {namespace.index_hash} starts with no #",
            file=sys.stderr,
        )
        return 2

    if not namespace.build_root and not namespace.compare_only:
        print("error: shooting needs --build-root", file=sys.stderr)
        return 2

    perf2html_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."
    )
    out_dir = namespace.out or os.path.join(
        perf2html_dir, test_settings.SCREENSHOT_DIR_NAME
    )
    out_dir = os.path.abspath(out_dir)
    scratch_dir = os.path.abspath(
        os.path.join(
            namespace.build_root, test_settings.SCREENSHOT_SCRATCH_DIR_PATH
        )
    )

    report_flag = (
        test_settings.SHOOT_DIFF_REPORT
        if namespace.diff
        else test_settings.SHOOT_REGULAR_REPORT
    )
    compare_dir = os.path.abspath(namespace.compare_out or out_dir)
    shooter = Screenshots(
        report, report_flag, out_dir, compare_dir, scratch_dir, namespace.shot
    )
    if namespace.shot and namespace.shot not in shooter.shot_names(
        namespace.prefix
    ):
        print(
            f"error: --shot {namespace.shot} names no shot of {report}",
            file=sys.stderr,
        )
        return 2

    if namespace.compare_only:
        shooter.gold_compare(gold_dir, namespace.prefix, namespace.verbose)
        return 0

    index_path = os.path.join(perf2html_dir, test_settings.INDEX_PAGE_NAME)
    os.makedirs(out_dir, exist_ok=True)
    if namespace.verbose:
        verbose_print(
            namespace.verbose, [f"{os.path.basename(report)} -> {out_dir}"]
        )
    # A single shot run takes its shot alone, checking and timing nothing.
    if namespace.shot:
        with BrowserSession() as browser_session:
            shooter.browser_session = browser_session
            written = shooter.shoot_all(namespace.prefix)
            written += shooter.index_shoot(
                namespace.prefix, index_path, namespace.index_hash
            )
        if namespace.verbose:
            verbose_print(namespace.verbose, [f"{written} screenshot(s)"])
        if namespace.compare_gold:
            shooter.gold_compare(gold_dir, namespace.prefix, namespace.verbose)
        return 0

    with BrowserSession() as browser_session:
        shooter.browser_session = browser_session
        shooter.test_views_check()
        written = shooter.shoot_all(namespace.prefix)
        shooter.clicks_time()
        shooter.logo_links_check()
        timing_rows = shooter.timing_rows()

        with open(
            os.path.join(
                perf2html_dir, "scripts", test_settings.INDEX_TEMPLATE_NAME
            )
        ) as template_file:
            index_template = template_file.read()
        report_timings = shooter.index_write(
            namespace.prefix, index_path, index_template, timing_rows
        )
        written += shooter.index_shoot(
            namespace.prefix, index_path, namespace.index_hash
        )
    if namespace.verbose:
        verbose_print(namespace.verbose, [f"{written} screenshot(s)"])
    if namespace.compare_gold:
        shooter.gold_compare(gold_dir, namespace.prefix, namespace.verbose)
    if namespace.verbose:
        verbose_print(
            namespace.verbose,
            [timing_row.verbose_line() for timing_row in timing_rows],
        )
    return shooter.timing_file_write(
        os.path.join(out_dir, test_settings.TIMING_FILE_NAME),
        report_timings,
        timing_rows,
    )


# Prints success lines, below the raw level as one Markdown text block.
def verbose_print(verbose_level: int, lines: list[str]) -> None:
    if verbose_level >= test_settings.VERBOSE_RAW_LEVEL:
        print("\n".join(lines), flush=True)
        return
    mark_run = max(
        (
            len(marks)
            for line in lines
            for marks in re.findall(
                f"{test_settings.MARKDOWN_FENCE_MARK}+", line
            )
        ),
        default=0,
    )
    fence = test_settings.MARKDOWN_FENCE_MARK * max(
        test_settings.MARKDOWN_FENCE_MIN_MARKS, mark_run + 1
    )
    fenced_lines = [fence + test_settings.MARKDOWN_FENCE_INFO, *lines, fence]
    print("\n" + "\n".join(fenced_lines), flush=True)


if __name__ == "__main__":
    sys.exit(main())
