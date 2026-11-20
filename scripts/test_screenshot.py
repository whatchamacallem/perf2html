#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE-MIT.md file.

from __future__ import annotations

from collections.abc import Callable, Iterator
from types import TracebackType
from typing import IO, Any, NamedTuple

import abc, argparse, base64, bisect, contextlib, fcntl, functools, hashlib
import json, os, re, shutil, signal, socket, subprocess, sys, threading
import urllib.parse

import PIL.Image, PIL.ImageChops

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
        toggle_dark_value = test_settings.SCREENSHOT_TOGGLE_DARK_VALUES[
            shown_index
        ]
        viewports = (
            test_settings.SCREENSHOT_VIEWPORTS[:1]
            if self.shot_flags & test_settings.SHOOT_ONE_VARIANT
            else test_settings.SCREENSHOT_VIEWPORTS
        )
        return tuple(
            ShotVariant(
                *viewport,
                toggle_dark_value,
                test_settings.SHOT_MODE_NAME_PARTS[toggle_dark_value],
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
# Selects a box heading's function links, its menu buttons holding no role.
_HEAT_MAP_BOX_LINK_SELECTOR = (
    "tr.heat-map-source-line-detail-row- .strip-line-"
    " > .menu-button-:not([role])"
)
_MENU_ROW_LAST_STOP = '#menu- > .strip-line- > [tabindex="0"]:last-child'
_STATUS_ROW_FIRST_STOP = (
    '#menu-preference- > .strip-line- > [tabindex="0"]:first-child'
)
_STATUS_ROW_LAST_STOP = (
    '#menu-preference- > .strip-line- > [tabindex="0"]:last-child'
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
                        " [role=option]:nth-child(2)",
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


# A frame's script context, a number in Chrome, a realm name in Firefox.
ScriptContext = int | str


# A frame of a tab and the frames it holds, as its browser names them.
class FrameNode(NamedTuple):
    frame_id: str
    # The frame holding this one, empty for the tab's top frame.
    parent_id: str
    child_nodes: tuple[FrameNode, ...]


# Drives one browser, each tab in a fresh profile.
class BrowserSession(abc.ABC):
    # What an error message calls the browser.
    browser_name = ""
    # The square side and channel change a shot matches its own gold twin by.
    own_gold_compare_rule = (
        test_settings.COMPARE_EXACT_SQUARE_PX,
        test_settings.COMPARE_EXACT_CHANNEL_CHANGE,
    )
    # The browser's dir in the screenshots dir, the gold dir beside that.
    shot_dir_name = ""
    # Whether the browser writes the trace every timing reads.
    traces_pages = False
    # The views the browser lacks, which its runs neither shoot nor open.
    unsupported_views: tuple[str, ...] = ()

    # Starts the browser, whatever files it keeps under the build root.
    @abc.abstractmethod
    def __init__(self, build_root: str) -> None: ...

    def __enter__(self) -> BrowserSession:
        return self

    @abc.abstractmethod
    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        error_traceback: TracebackType | None,
    ) -> None: ...

    # Reads the next message, handing an open tab's event to that tab.
    @abc.abstractmethod
    def message_read(self) -> dict[str, Any]: ...

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
    @abc.abstractmethod
    def tab_open(self, width_px: int, height_px: int) -> PageTab: ...


# Runs one browser speaking JSON messages over a pipe, each ended by a NUL.
class BrowserPipe:
    # Starts the browser, handing each message read to the session's reader.
    def __init__(
        self,
        command_line: list[str],
        message_take: Callable[[dict[str, Any]], None],
    ) -> None:
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
            command_line,
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
        self.message_take = message_take
        self.unread_bytes = b""

    # Sends a command with its address fields, returning its result.
    def command(
        self,
        method: str,
        parameters: dict[str, Any] | None,
        address_fields: dict[str, str],
    ) -> dict[str, Any]:
        self.command_count += 1
        command_number = self.command_count
        self.command_file.write(
            json.dumps(
                {
                    "id": command_number,
                    "method": method,
                    "params": parameters or {},
                    **address_fields,
                }
            ).encode()
            + test_settings.BROWSER_PIPE_MESSAGE_END
        )
        self.command_file.flush()
        while True:
            reply_message = self.message_read()
            if reply_message.get("id") != command_number:
                continue
            if "error" in reply_message:
                raise RuntimeError(f"{method}: {reply_message['error']}")
            return reply_message["result"]

    # Waits for a browser told to close, else kills it with its process group.
    def end(self, is_closed: bool) -> None:
        if not is_closed and self.browser_process.poll() is None:
            os.killpg(self.browser_process.pid, signal.SIGKILL)
        self.browser_process.wait()
        self.command_file.close()
        os.close(self.reply_read_fd)

    # Reads the next message, handing it to the session's reader.
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
        self.message_take(message)
        return message


# Drives one Chrome over its DevTools pipe, each tab in a fresh profile.
class ChromeSession(BrowserSession):
    browser_name = "Chrome"
    shot_dir_name = test_settings.SCREENSHOT_CHROME_DIR_NAME
    traces_pages = True

    # Chrome keeps each tab's profile in memory, none under the build root.
    def __init__(self, build_root: str) -> None:
        # The open tabs, by the session their commands and events go through.
        self.page_tabs: dict[str, ChromeTab] = {}
        self.browser_pipe = BrowserPipe(
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
            self.message_take,
        )

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        error_traceback: TracebackType | None,
    ) -> None:
        if error_type is None:
            self.command("Browser.close")
        self.browser_pipe.end(error_type is None)

    # Sends a command, to a tab's session if named, returning its result.
    def command(
        self,
        method: str,
        parameters: dict[str, Any] | None = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        return self.browser_pipe.command(
            method, parameters, {"sessionId": session_id} if session_id else {}
        )

    def message_read(self) -> dict[str, Any]:
        return self.browser_pipe.message_read()

    # Hands a tab's event to that tab.
    def message_take(self, message: dict[str, Any]) -> None:
        page_tab = self.page_tabs.get(message.get("sessionId", ""))
        # A closed tab's late event and a browser event belong to no page.
        if "method" in message and page_tab:
            page_tab.event_take(message)

    def tab_open(self, width_px: int, height_px: int) -> ChromeTab:
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
        page_tab = ChromeTab(
            self, session_id, browser_context_id, (width_px, height_px)
        )
        self.page_tabs[session_id] = page_tab
        page_tab.command("Page.enable")
        page_tab.command("Runtime.enable")
        page_tab.command(
            "Runtime.addBinding",
            {"name": test_settings.PAGE_DRAWN_BINDING_NAME},
        )
        # Sizes the page as the tab, as hidden toolbars take window rows.
        page_tab.command(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width_px,
                "height": height_px,
                "deviceScaleFactor": 0,
                "mobile": False,
            },
        )
        return page_tab


# Runs one X server, the display a browser draws through, until it ends.
class DisplayServer:
    def __init__(self) -> None:
        display_read_fd, display_write_fd = os.pipe()
        self.server_process = subprocess.Popen(
            [
                test_settings.SCREENSHOT_DISPLAY_SERVER_NAME,
                "-displayfd",
                str(display_write_fd),
                *test_settings.SCREENSHOT_DISPLAY_SERVER_ARGUMENTS,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(display_write_fd,),
            start_new_session=True,
        )
        os.close(display_write_fd)
        # The server writes its display number once it takes clients.
        with os.fdopen(display_read_fd) as display_file:
            display_number = display_file.readline().strip()
        if not display_number:
            raise RuntimeError(
                f"{test_settings.SCREENSHOT_DISPLAY_SERVER_NAME} wrote no"
                f" display, exit {self.server_process.wait()}"
            )
        self.display_name = f":{display_number}"

    # Ends the server, its display with it.
    def end(self) -> None:
        self.server_process.terminate()
        self.server_process.wait()


# Drives one Gecko browser, drawing through a display server of its own.
class GeckoSession(BrowserSession):
    browser_process: subprocess.Popen[bytes]
    # The pipe the browser writes its output to, the line saying it listens.
    output_pipe: IO[bytes]
    # The browser's profile dir, under the build root.
    profile_dir_path = ""

    # Makes the browser's empty profile dir and starts its display server.
    def __init__(self, build_root: str) -> None:
        self.profile_dir = os.path.abspath(
            os.path.join(build_root, self.profile_dir_path)
        )
        if os.path.exists(self.profile_dir):
            shutil.rmtree(self.profile_dir)
        # Only the user reaches its socket, whose scripts run as the browser.
        os.makedirs(self.profile_dir, mode=0o700)
        self.display_server = DisplayServer()

    # Kills a browser still running, ends its display, deletes its profile.
    def browser_end(self) -> None:
        if self.browser_process.poll() is None:
            os.killpg(self.browser_process.pid, signal.SIGKILL)
        self.browser_process.wait()
        self.output_pipe.close()
        self.display_server.end()
        shutil.rmtree(self.profile_dir)

    # Reads the rest of the browser's output, so a full pipe never stops it.
    def output_drain_begin(self) -> None:
        def output_drain() -> None:
            for _ in self.output_pipe:
                pass

        threading.Thread(target=output_drain, daemon=True).start()


# Drives one Firefox over WebDriver BiDi, each tab in a fresh user context.
class FirefoxSession(GeckoSession):
    browser_name = "Firefox"
    profile_dir_path = test_settings.SCREENSHOT_FIREFOX_PROFILE_DIR_PATH
    shot_dir_name = test_settings.SCREENSHOT_FIREFOX_DIR_NAME

    def __init__(self, build_root: str) -> None:
        super().__init__(build_root)
        self.browser_process = subprocess.Popen(
            [
                test_settings.SCREENSHOT_FIREFOX_PATH,
                "--headless",
                "--no-remote",
                "--profile",
                self.profile_dir,
                "--remote-debugging-port=0",
                test_settings.BLANK_PAGE_URL,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env={
                **os.environ,
                # Gives the flame graph WebGL, which needs an X display.
                "DISPLAY": self.display_server.display_name,
                # Lets a key walk hand the focus back from the controls.
                "MOZ_REMOTE_ALLOW_SYSTEM_ACCESS": "1",
            },
        )
        assert self.browser_process.stderr, "Firefox writes stderr to a pipe"
        self.output_pipe = self.browser_process.stderr
        self.command_count = 0
        # The open tabs, by each frame's browsing context.
        self.context_tabs: dict[str, FirefoxTab] = {}
        # The open tabs, by each script realm of their frames.
        self.realm_tabs: dict[str, FirefoxTab] = {}
        # A start failing before the with statement ends the browser itself.
        try:
            self.web_socket = WebSocketChannel(
                self.listening_url_read()
                + test_settings.SCREENSHOT_FIREFOX_SESSION_PATH
            )
            self.command("session.new", {"capabilities": {}})
            self.command(
                "session.subscribe",
                {
                    "events": [
                        "browsingContext.contextCreated",
                        "browsingContext.contextDestroyed",
                        "browsingContext.fragmentNavigated",
                        "browsingContext.load",
                        "browsingContext.navigationFailed",
                        "browsingContext.navigationStarted",
                        "log.entryAdded",
                        "script.message",
                        "script.realmCreated",
                        "script.realmDestroyed",
                    ]
                },
            )
        except BaseException:
            self.browser_end()
            raise

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        error_traceback: TracebackType | None,
    ) -> None:
        if error_type is None:
            self.command("browser.close")
            self.browser_process.wait()
        self.web_socket.close()
        self.browser_end()

    # Sends a command, returning its result once its reply comes.
    def command(
        self, method: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.command_count += 1
        self.web_socket.message_send(
            json.dumps(
                {
                    "id": self.command_count,
                    "method": method,
                    "params": parameters or {},
                }
            )
        )
        while True:
            reply_message = self.message_read()
            if reply_message.get("id") != self.command_count:
                continue
            if reply_message["type"] == "error":
                raise RuntimeError(
                    f"{method}: {reply_message['error']}:"
                    f" {reply_message['message']}"
                )
            return reply_message["result"]

    # Returns the tab an event belongs to, keeping the frames and realms made.
    def event_tab(self, message: dict[str, Any]) -> FirefoxTab | None:
        method = message["method"]
        event_parameters = message["params"]
        if method == "browsingContext.contextCreated":
            page_tab = self.context_tabs.get(event_parameters["parent"])
            if page_tab:
                self.context_tabs[event_parameters["context"]] = page_tab
            return page_tab
        if method == "browsingContext.contextDestroyed":
            return self.context_tabs.get(event_parameters["context"])
        if method == "script.realmCreated":
            page_tab = self.context_tabs.get(event_parameters["context"])
            if page_tab:
                self.realm_tabs[event_parameters["realm"]] = page_tab
            return page_tab
        if method == "script.realmDestroyed":
            return self.realm_tabs.pop(event_parameters["realm"], None)
        if method in ("log.entryAdded", "script.message"):
            return self.realm_tabs.get(event_parameters["source"]["realm"])
        return self.context_tabs.get(event_parameters["context"])

    # Moves the focus through the browser's controls back into its page.
    def focus_return(self, is_backward: bool) -> None:
        chrome_contexts = self.command(
            "browsingContext.getTree", {"moz:scope": "chrome"}
        )["contexts"]
        focus_call = self.command(
            "script.callFunction",
            {
                "functionDeclaration": (
                    test_settings.FIREFOX_FOCUS_RETURN_FUNCTION
                ),
                "arguments": [
                    {"type": "boolean", "value": is_backward},
                    {
                        "type": "number",
                        "value": test_settings.CLICK_WALK_PRESS_LIMIT,
                    },
                ],
                "target": {"context": chrome_contexts[0]["context"]},
                "awaitPromise": False,
            },
        )
        if focus_call["type"] == "exception":
            raise RuntimeError(
                f"focus return: {focus_call['exceptionDetails']['text']}"
            )

    # Reads the browser's stderr up to the address it listens at.
    def listening_url_read(self) -> str:
        for stderr_line in self.output_pipe:
            listening_match = (
                test_settings.SCREENSHOT_FIREFOX_LISTENING_PATTERN.search(
                    stderr_line.decode()
                )
            )
            if listening_match:
                self.output_drain_begin()
                return listening_match.group(1)
        raise RuntimeError(
            "Firefox closed its stderr before it listened, exit"
            f" {self.browser_process.wait()}"
        )

    def message_read(self) -> dict[str, Any]:
        try:
            message = json.loads(self.web_socket.message_read())
        except ConnectionError as error:
            raise RuntimeError(
                f"the browser closed its socket, exit"
                f" {self.browser_process.wait()}"
            ) from error
        if message["type"] == "event":
            page_tab = self.event_tab(message)
            # A closed tab's late event and a browser event belong to no page.
            if page_tab:
                page_tab.event_take(message)
        return message

    def tab_open(self, width_px: int, height_px: int) -> FirefoxTab:
        user_context = self.command("browser.createUserContext")["userContext"]
        top_context = self.command(
            "browsingContext.create",
            # Its own window keeps the tab shown, a hidden tab never drawing.
            {"type": "window", "userContext": user_context},
        )["context"]
        page_tab = FirefoxTab(
            self, top_context, user_context, (width_px, height_px)
        )
        self.context_tabs[top_context] = page_tab
        self.command(
            "browsingContext.setViewport",
            {
                "context": top_context,
                "viewport": {"width": width_px, "height": height_px},
            },
        )
        page_tab.preload_script = self.command(
            "script.addPreloadScript",
            {
                "functionDeclaration": (
                    test_settings.PAGE_DRAWN_CHANNEL_FUNCTION
                ),
                "arguments": [
                    {
                        "type": "channel",
                        "value": {
                            "channel": test_settings.PAGE_DRAWN_BINDING_NAME
                        },
                    }
                ],
                "userContexts": [user_context],
            },
        )["script"]
        return page_tab


# Drives one SeaMonkey over its DevTools server, each tab in a fresh context.
class SeaMonkeySession(GeckoSession):
    browser_name = "SeaMonkey"
    profile_dir_path = test_settings.SCREENSHOT_SEAMONKEY_PROFILE_DIR_PATH
    shot_dir_name = test_settings.SCREENSHOT_SEAMONKEY_DIR_NAME
    unsupported_views = test_settings.SCREENSHOT_SEAMONKEY_UNSUPPORTED_VIEWS

    def __init__(self, build_root: str) -> None:
        super().__init__(build_root)
        with open(
            os.path.join(
                self.profile_dir,
                test_settings.SCREENSHOT_SEAMONKEY_PREFERENCES_FILE_NAME,
            ),
            "w",
            encoding="utf-8",
        ) as preferences_file:
            preferences_file.writelines(
                f"user_pref({json.dumps(name)}, {json.dumps(value)});\n"
                for name, value in (
                    test_settings.SCREENSHOT_SEAMONKEY_PREFERENCES.items()
                )
            )
        socket_path = os.path.join(
            self.profile_dir, test_settings.SCREENSHOT_SEAMONKEY_SOCKET_NAME
        )
        self.browser_process = subprocess.Popen(
            [
                test_settings.SCREENSHOT_SEAMONKEY_PATH,
                "-headless",
                "-no-remote",
                "-profile",
                self.profile_dir,
                "-start-debugger-server",
                socket_path,
                test_settings.BLANK_PAGE_URL,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "DISPLAY": self.display_server.display_name},
        )
        assert self.browser_process.stdout, "SeaMonkey writes stdout to a pipe"
        self.output_pipe = self.browser_process.stdout
        # Numbers each tab open and each awaited script.
        self.call_count = 0
        # The event of each tab open, by its number, until the open reads it.
        self.opened_tabs: dict[int, dict[str, Any]] = {}
        # The open tabs, by the top frame each one's page fills.
        self.page_tabs: dict[str, SeaMonkeyTab] = {}
        self.unread_bytes = bytearray()
        # A start failing before the with statement ends the browser itself.
        try:
            self.listening_wait()
            self.socket_connection = socket.socket(socket.AF_UNIX)
            self.socket_connection.connect(socket_path)
            self.packet_read()
            process_form = self.command(
                "root",
                "getProcess",
                {"id": test_settings.SCREENSHOT_SEAMONKEY_PROCESS_ID},
            )["form"]
            self.command(
                process_form["actor"], "attach", reply_type="tabAttached"
            )
            self.console_actor = process_form["consoleActor"]
            self.command(
                self.console_actor,
                "startListeners",
                {
                    "listeners": list(
                        test_settings.SCREENSHOT_SEAMONKEY_LISTENERS
                    )
                },
            )
            self.evaluate(
                "driver install",
                f"({test_settings.SCREENSHOT_SEAMONKEY_DRIVER_FUNCTION})("
                + json.dumps(test_settings.SCREENSHOT_SEAMONKEY_EVENT_MARKER)
                + ", "
                + json.dumps(test_settings.PAGE_DRAWN_BINDING_NAME)
                + ", "
                + json.dumps(
                    test_settings.SCREENSHOT_SEAMONKEY_EVENT_CHUNK_LENGTH
                )
                + ")",
            )
        except BaseException:
            self.browser_end()
            raise

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        error_traceback: TracebackType | None,
    ) -> None:
        if error_type is None:
            # SeaMonkey quits before it replies, so no reply is read.
            self.packet_send(
                {
                    "to": self.console_actor,
                    "type": "evaluateJS",
                    "text": self.driver_text("quit"),
                }
            )
            self.browser_process.wait()
        self.socket_connection.close()
        self.browser_end()

    # Receives the bytes the socket holds, waiting for some.
    def bytes_receive(self) -> None:
        received_bytes = self.socket_connection.recv(
            test_settings.SCREENSHOT_SEAMONKEY_READ_BYTES
        )
        if not received_bytes:
            raise RuntimeError(
                "the browser closed its socket, exit"
                f" {self.browser_process.wait()}"
            )
        self.unread_bytes += received_bytes

    # Sends a request to an actor, returning its reply once it comes.
    def command(
        self,
        actor: str,
        packet_type: str,
        fields: dict[str, Any] | None = None,
        reply_type: str = "",
    ) -> dict[str, Any]:
        self.packet_send({"to": actor, "type": packet_type, **(fields or {})})
        while True:
            packet = self.message_read()
            # An actor's event names its type, a reply none but an attach's.
            if (
                packet.get("from") != actor
                or packet.get("type", "") != reply_type
            ):
                continue
            if "error" in packet:
                raise RuntimeError(f"{packet_type}: {packet}")
            return packet

    # Hands a driver event the browser console reports to its tab.
    def console_message_take(self, console_message: dict[str, Any]) -> None:
        marker_argument, *event_chunks = console_message["arguments"]
        # A browser window's own line is no driver event.
        if marker_argument != test_settings.SCREENSHOT_SEAMONKEY_EVENT_MARKER:
            return
        driver_event = json.loads("".join(event_chunks))
        if driver_event["event"] == "tab_opened":
            self.opened_tabs[driver_event["open_number"]] = driver_event
            return
        page_tab = self.page_tabs.get(driver_event["tab"])
        # A closed tab's late event belongs to no page.
        if page_tab:
            page_tab.event_take(driver_event)

    # Calls a driver function, returning the JSON its text holds, if any.
    def driver_call(self, function_name: str, *call_arguments: Any) -> Any:
        result = self.evaluate(
            function_name, self.driver_text(function_name, *call_arguments)
        )
        if isinstance(result, dict) and result["type"] == "undefined":
            return None
        return json.loads(self.text_read(result))

    # Returns the script text calling a driver function with its arguments.
    def driver_text(self, function_name: str, *call_arguments: Any) -> str:
        return (
            f"screenshot_driver.{function_name}("
            + ", ".join(
                json.dumps(call_argument) for call_argument in call_arguments
            )
            + ")"
        )

    # Returns the value a browser window script evaluates to, as its grip.
    def evaluate(self, script_label: str, script_text: str) -> Any:
        reply = self.command(
            self.console_actor, "evaluateJS", {"text": script_text}
        )
        if reply["exception"] is not None:
            raise RuntimeError(f"{script_label}: {reply['exceptionMessage']}")
        return reply["result"]

    # Reads the browser's stdout up to the line saying its server opened.
    def listening_wait(self) -> None:
        for stdout_line in self.output_pipe:
            line_text = stdout_line.decode()
            if test_settings.SCREENSHOT_SEAMONKEY_LISTEN_FAILED_PATTERN.search(
                line_text
            ):
                raise RuntimeError(f"SeaMonkey: {line_text.strip()}")
            if test_settings.SCREENSHOT_SEAMONKEY_LISTENING_PATTERN.search(
                line_text
            ):
                self.output_drain_begin()
                return
        raise RuntimeError(
            "SeaMonkey closed its stdout before it listened, exit"
            f" {self.browser_process.wait()}"
        )

    def message_read(self) -> dict[str, Any]:
        packet = self.packet_read()
        if packet.get("type") == "consoleAPICall":
            self.console_message_take(packet["message"])
        return packet

    # Reads one packet, its length in digits, a colon, then its JSON.
    def packet_read(self) -> dict[str, Any]:
        length_end = test_settings.SCREENSHOT_SEAMONKEY_PACKET_LENGTH_END
        while length_end not in self.unread_bytes:
            self.bytes_receive()
        length_text, _, self.unread_bytes = self.unread_bytes.partition(
            length_end
        )
        packet_length = int(length_text)
        while len(self.unread_bytes) < packet_length:
            self.bytes_receive()
        packet_bytes = bytes(self.unread_bytes[:packet_length])
        del self.unread_bytes[:packet_length]
        return json.loads(packet_bytes)

    def packet_send(self, packet: dict[str, Any]) -> None:
        packet_bytes = json.dumps(packet).encode()
        self.socket_connection.sendall(
            str(len(packet_bytes)).encode()
            + test_settings.SCREENSHOT_SEAMONKEY_PACKET_LENGTH_END
            + packet_bytes
        )

    # Forgets a closing tab, so its late events belong to no page.
    def tab_forget(self, page_tab: SeaMonkeyTab) -> None:
        del self.page_tabs[page_tab.tab_key]

    def tab_open(self, width_px: int, height_px: int) -> SeaMonkeyTab:
        self.call_count += 1
        open_number = self.call_count
        self.driver_call("tab_open", open_number, width_px, height_px)
        while open_number not in self.opened_tabs:
            self.message_read()
        opened_event = self.opened_tabs.pop(open_number)
        if "error" in opened_event:
            raise RuntimeError(f"tab open: {opened_event['error']}")
        page_tab = SeaMonkeyTab(
            self, opened_event["tab"], (width_px, height_px)
        )
        self.page_tabs[page_tab.tab_key] = page_tab
        return page_tab

    # Returns a reply's text, reading a long one from its actor.
    def text_read(self, text_value: Any) -> str:
        if isinstance(text_value, str):
            return text_value
        if text_value["type"] != "longString":
            raise RuntimeError(f"a value of no text: {text_value}")
        text = self.command(
            text_value["actor"],
            "substring",
            {"start": 0, "end": text_value["length"]},
        )["substring"]
        self.command(text_value["actor"], "release")
        return text


# Drives one WebKit over its inspector pipe, each tab in a fresh context.
class WebKitSession(BrowserSession):
    browser_name = "WebKit"
    # WebKit's index page shot varies per load at the frame edges, so vaguely.
    own_gold_compare_rule = (
        test_settings.COMPARE_VAGUE_SQUARE_PX,
        test_settings.COMPARE_VAGUE_CHANNEL_CHANGE,
    )
    shot_dir_name = test_settings.SCREENSHOT_WEBKIT_DIR_NAME

    # WebKit keeps each tab's context in memory, none under the build root.
    def __init__(self, build_root: str) -> None:
        # The first target of each page made, until its tab takes it.
        self.created_targets: dict[str, dict[str, Any]] = {}
        # The open tabs, by the page their commands and events name.
        self.page_tabs: dict[str, WebKitTab] = {}
        self.browser_pipe = BrowserPipe(
            [
                test_settings.SCREENSHOT_WEBKIT_PATH,
                *test_settings.SCREENSHOT_WEBKIT_ARGUMENTS,
            ],
            self.message_take,
        )
        # A start failing before the with statement ends the browser itself.
        try:
            self.command("Playwright.enable")
        except BaseException:
            self.browser_pipe.end(False)
            raise

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        error_traceback: TracebackType | None,
    ) -> None:
        if error_type is None:
            self.command("Playwright.close")
        self.browser_pipe.end(error_type is None)

    # Sends a command, to a page's session if named, returning its result.
    def command(
        self,
        method: str,
        parameters: dict[str, Any] | None = None,
        page_proxy_id: str = "",
    ) -> dict[str, Any]:
        return self.browser_pipe.command(
            method,
            parameters,
            {"pageProxyId": page_proxy_id} if page_proxy_id else {},
        )

    def message_read(self) -> dict[str, Any]:
        return self.browser_pipe.message_read()

    # Keeps a page's first target and hands a tab's messages to that tab.
    def message_take(self, message: dict[str, Any]) -> None:
        method = message.get("method", "")
        event_parameters = message.get("params", {})
        page_proxy_id = message.get(
            "pageProxyId", event_parameters.get("pageProxyId", "")
        )
        page_tab = self.page_tabs.get(page_proxy_id)
        if method == "Target.targetCreated":
            target_info = event_parameters["targetInfo"]
            # A navigation swapping processes makes a page's second target.
            if page_tab or page_proxy_id in self.created_targets:
                raise RuntimeError(f"{page_proxy_id}: a second target")
            self.created_targets[page_proxy_id] = target_info
        # A closed tab's late message and a browser event belong to no page.
        if not page_tab:
            return
        if method == "Playwright.provisionalLoadFailed":
            raise RuntimeError(f"a load failed: {event_parameters['error']}")
        if method == "Target.dispatchMessageFromTarget":
            page_tab.target_message_take(
                json.loads(event_parameters["message"])
            )

    def tab_open(self, width_px: int, height_px: int) -> WebKitTab:
        browser_context_id = self.command("Playwright.createContext")[
            "browserContextId"
        ]
        page_proxy_id = self.command(
            "Playwright.createPage", {"browserContextId": browser_context_id}
        )["pageProxyId"]
        while page_proxy_id not in self.created_targets:
            self.message_read()
        target_info = self.created_targets.pop(page_proxy_id)
        page_tab = WebKitTab(
            self,
            page_proxy_id,
            browser_context_id,
            target_info["targetId"],
            (width_px, height_px),
        )
        self.page_tabs[page_proxy_id] = page_tab
        page_tab.command(
            "Emulation.setDeviceMetricsOverride",
            {"width": width_px, "height": height_px, "fixedLayout": False},
        )
        # Gives the page the focus a shown window's page holds.
        page_tab.command("Emulation.setActiveAndFocused", {"active": True})
        for method in ("Page.enable", "Runtime.enable", "Console.enable"):
            page_tab.target_command(method)
        for binding_name in (
            test_settings.PAGE_DRAWN_BINDING_NAME,
            test_settings.WEBKIT_CONSOLE_BINDING_NAME,
        ):
            page_tab.target_command(
                "Runtime.addBinding", {"name": binding_name}
            )
        page_tab.target_command(
            "Page.setBootstrapScript",
            {
                "source": f"({test_settings.WEBKIT_CONSOLE_FORWARD_FUNCTION})"
                f"({json.dumps(test_settings.WEBKIT_CONSOLE_BINDING_NAME)})"
            },
        )
        if target_info.get("isPaused"):
            page_tab.command(
                "Target.resume", {"targetId": target_info["targetId"]}
            )
        return page_tab


# Holds one tab's page: its frames, their script contexts and error reports.
class PageTab(abc.ABC):
    def __init__(
        self, browser_session: BrowserSession, tab_size: tuple[int, int]
    ) -> None:
        self.browser_session = browser_session
        self.tab_size = tab_size
        # The contexts whose drawn check this settle started.
        self.checked_contexts: set[ScriptContext] = set()
        # The contexts the page left, read before any failed reply.
        self.destroyed_contexts: set[ScriptContext] = set()
        # The frames the page removed, read before any failed reply.
        self.detached_frames: set[str] = set()
        # The contexts whose drawn check of this settle passed.
        self.drawn_contexts: set[ScriptContext] = set()
        # The contexts from before this settle, whose load renders are logged.
        self.earlier_contexts: set[ScriptContext] = set()
        # The first line of each error report, by the context drawing it.
        self.error_reports: dict[ScriptContext, str] = {}
        self.frame_contexts: dict[str, ScriptContext] = {}
        # Whether an event came since the last settle step.
        self.has_news = False
        # The frames out of view, which no shot shows.
        self.hidden_frames: set[str] = set()
        # Whether the frame a navigation opens started loading, after an input.
        self.is_started = False
        self.loading_frames: set[str] = set()
        self.navigation_frame_id = ""
        # The settle steps the tab's events call for, in their order.
        self.pending_events: list[Callable[[], None]] = []
        # Numbers the settles, so a drawn check reports to its own alone.
        self.settle_count = 0
        self.thrown_texts: list[str] = []

    # Types each character, a key's press and release each.
    @abc.abstractmethod
    def characters_send(self, typed_text: str) -> None: ...

    # Writes text to the clipboard from a frame, as a copy there would.
    def clipboard_write(self, frame_name: str, pasted_text: str) -> None:
        write_function = test_settings.CLICK_CLIPBOARD_WRITE_FUNCTION
        _, exception_text = self.script_run(
            self.frame_context(frame_name),
            f"({write_function})({json.dumps(pasted_text)})",
            is_awaited=True,
            is_activated=True,
        )
        if exception_text:
            raise RuntimeError(
                f"{frame_name}: clipboard write: {exception_text}"
            )

    # Closes the tab with its profile, any late event of it unread.
    @abc.abstractmethod
    def close(self) -> None: ...

    # Forgets a script context the page left.
    def context_end(self, context_id: ScriptContext) -> None:
        self.destroyed_contexts.add(context_id)
        self.frame_contexts = {
            frame_id: frame_context
            for frame_id, frame_context in self.frame_contexts.items()
            if frame_context != context_id
        }

    # Returns the first line of the page's first error report, if any.
    def error_message(self) -> str:
        return next(iter(self.error_reports.values()), "")

    # Keeps the first line of an error report a context writes to its console.
    def error_report_keep(
        self, context_id: ScriptContext, console_text: str
    ) -> None:
        error_match = test_settings.CONSOLE_ERROR_REPORT_PATTERN.search(
            console_text
        )
        if error_match:
            self.error_reports.setdefault(context_id, error_match.group(1))

    # Refuses an error report or an uncaught exception of the page.
    def errors_refuse(self, fault_label: str) -> None:
        if self.error_reports:
            raise RuntimeError(f"{fault_label}: {self.error_message()}")
        if self.thrown_texts:
            raise RuntimeError(f"{fault_label}: {self.thrown_texts[0]}")

    # Returns the value an expression evaluates to in a frame.
    def frame_evaluate(self, frame_name: str, expression: str) -> Any:
        value, exception_text = self.script_run(
            self.frame_context(frame_name), expression
        )
        if exception_text:
            raise RuntimeError(f"{frame_name}: {expression}: {exception_text}")
        return value

    def frame_context(self, frame_name: str) -> ScriptContext:
        frame_id = self.frame_id(frame_name)
        if frame_id not in self.frame_contexts:
            raise RuntimeError(f"{frame_name}: no script context")
        return self.frame_contexts[frame_id]

    # Returns the frame of the menu's top page or of its one view.
    def frame_id(self, frame_name: str) -> str:
        frame_tree = self.frame_tree()
        if frame_name == test_settings.CLICK_MENU_FRAME_NAME:
            return frame_tree.frame_id
        if len(frame_tree.child_nodes) != 1:
            raise RuntimeError(
                f"the page holds {len(frame_tree.child_nodes)} views"
            )
        return frame_tree.child_nodes[0].frame_id

    # Returns whether a child frame's element shows in the tab's view.
    @abc.abstractmethod
    def frame_shown(self, frame_node: FrameNode) -> bool: ...

    # Returns the tab's frames, its top frame the root.
    @abc.abstractmethod
    def frame_tree(self) -> FrameNode: ...

    # Returns whether each shown frame drew or erred, a child after its parent.
    def frames_drawn(self, frame_node: FrameNode) -> bool:
        if frame_node.frame_id in self.hidden_frames:
            return True
        context_id = self.frame_contexts.get(frame_node.frame_id)
        if context_id is None:
            return False
        # The error handler's page replaces the frame's own and its frames.
        if context_id in self.error_reports:
            return True
        is_new = context_id not in self.earlier_contexts
        if context_id not in self.checked_contexts:
            self.checked_contexts.add(context_id)
            # A frame out of view never paints, so no shot shows it drawn.
            for child_node in frame_node.child_nodes:
                if not self.frame_shown(child_node):
                    self.hidden_frames.add(child_node.frame_id)
            try:
                self.script_run(
                    context_id,
                    self.wait_expression(
                        test_settings.PAGE_DRAWN_FUNCTION,
                        json.dumps(test_settings.PAGE_DRAWN_BINDING_NAME),
                        json.dumps(str(self.settle_count)),
                    ),
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
            self.frames_drawn(child_node)
            for child_node in frame_node.child_nodes
        ]
        return context_id in self.drawn_contexts and all(child_states)

    # Writes the page as drawn to an image file.
    @abc.abstractmethod
    def image_write(self, image_path: str) -> None: ...

    # Sends a key's press and release to whatever holds the focus.
    @abc.abstractmethod
    def key_send(self, key_name: str) -> None: ...

    # Presses a key, returning once each frame drew after it.
    def key_settle(self, key_name: str) -> None:
        self.settle_begin()
        self.key_send(key_name)
        self.browser_session.settled_tab_wait([self])

    # Counts a frame's load begun, the navigation's frame starting it.
    def load_begin(self, frame_id: str) -> None:
        self.loading_frames.add(frame_id)
        self.is_started |= frame_id == self.navigation_frame_id

    # Counts a frame's load ended, a frame removed while loading too.
    def load_end(self, frame_id: str) -> None:
        self.loading_frames.discard(frame_id)

    # Starts opening a page, returning the frame whose load starts it.
    @abc.abstractmethod
    def navigation_begin(self, page_url: str) -> str: ...

    # Counts a context drawn when its check of this settle reports.
    def page_drawn_mark(
        self, context_id: ScriptContext, settle_text: str
    ) -> None:
        # A check begun before this settle reports nothing about it.
        if settle_text == str(self.settle_count):
            self.drawn_contexts.add(context_id)

    # Starts opening a page, which a settle then waits on.
    def page_navigate(self, page_url: str) -> None:
        self.settle_begin()
        self.navigation_frame_id = self.navigation_begin(page_url)
        self.is_started = False

    # Opens a page, returning once its frames stopped loading and each drew.
    def page_open(self, page_url: str) -> None:
        self.page_navigate(page_url)
        self.browser_session.settled_tab_wait([self])

    # Returns once a frame painted again, after a task following the paint.
    def paint_wait(self, frame_name: str) -> None:
        _, exception_text = self.script_run(
            self.frame_context(frame_name),
            self.wait_expression("(after_paint) => after_paint()"),
            is_awaited=True,
        )
        if exception_text:
            raise RuntimeError(f"{frame_name}: paint wait: {exception_text}")

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
            _, exception_text = self.script_run(
                state_context,
                self.wait_expression(
                    test_settings.STATE_CHANGE_FUNCTION,
                    f"() => ({state_expression})",
                    json.dumps(state_before),
                ),
                is_awaited=True,
            )
        except RuntimeError:
            # A state frame the press reloads is read again once it drew.
            if state_context not in self.destroyed_contexts:
                raise
        else:
            if exception_text:
                raise RuntimeError(
                    f"{state_frame_name}: {state_expression}: {exception_text}"
                )
        self.browser_session.settled_tab_wait([self])

    # Returns whether any of an element's quads, in the tab's px, shows in it.
    def quads_shown(self, element_quads: list[list[float]]) -> bool:
        width_px, height_px = self.tab_size
        return any(
            max(quad[0::2]) > 0
            and max(quad[1::2]) > 0
            and min(quad[0::2]) < width_px
            and min(quad[1::2]) < height_px
            for quad in element_quads
        )

    # Returns an expression's value in a context and its exception's text.
    @abc.abstractmethod
    def script_run(
        self,
        context_id: ScriptContext,
        expression: str,
        is_awaited: bool = False,
        is_activated: bool = False,
    ) -> tuple[Any, str]: ...

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
            self.pending_events.pop(0)()
        return (
            self.is_started
            and not self.loading_frames
            and self.frames_drawn(self.frame_tree())
        )

    # Types text a key per character, returning once each frame drew after it.
    def text_type(self, typed_text: str) -> None:
        self.settle_begin()
        self.characters_send(typed_text)
        self.browser_session.settled_tab_wait([self])

    # Starts the trace a timing reads, which only Chrome writes.
    def trace_begin(self) -> None:
        raise RuntimeError(f"{type(self).__name__} writes no trace")

    # Ends the trace, returning its events.
    def trace_end(self) -> list[Any]:
        raise RuntimeError(f"{type(self).__name__} writes no trace")

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


# Drives one Chrome tab through its DevTools session.
class ChromeTab(PageTab):
    def __init__(
        self,
        chrome_session: ChromeSession,
        session_id: str,
        browser_context_id: str,
        tab_size: tuple[int, int],
    ) -> None:
        super().__init__(chrome_session, tab_size)
        self.chrome_session = chrome_session
        self.session_id = session_id
        self.browser_context_id = browser_context_id
        # The events no settle step reads, which a wait may take.
        self.waited_events: list[dict[str, Any]] = []

    def characters_send(self, typed_text: str) -> None:
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

    def close(self) -> None:
        del self.chrome_session.page_tabs[self.session_id]
        self.chrome_session.command(
            "Target.disposeBrowserContext",
            {"browserContextId": self.browser_context_id},
        )

    # Sends a command to the tab, returning its result once its reply comes.
    def command(
        self, method: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.chrome_session.command(method, parameters, self.session_id)

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
            self.error_report_keep(
                event_parameters["executionContextId"],
                " ".join(
                    str(console_argument.get("value", ""))
                    for console_argument in event_parameters["args"]
                ),
            )
        elif method == "Runtime.executionContextCreated":
            context = event_parameters["context"]
            if context["auxData"]["isDefault"]:
                self.frame_contexts[context["auxData"]["frameId"]] = context[
                    "id"
                ]
        elif method == "Runtime.executionContextDestroyed":
            self.context_end(event_parameters["executionContextId"])
        elif method == "Runtime.executionContextsCleared":
            self.destroyed_contexts.update(self.frame_contexts.values())
            self.frame_contexts = {}
        elif method == "Page.frameStartedLoading":
            self.pending_events.append(
                functools.partial(self.load_begin, event_parameters["frameId"])
            )
        # A frame removed while loading never stops loading.
        elif method in ("Page.frameDetached", "Page.frameStoppedLoading"):
            if method == "Page.frameDetached":
                self.detached_frames.add(event_parameters["frameId"])
            self.pending_events.append(
                functools.partial(self.load_end, event_parameters["frameId"])
            )
        elif method == "Runtime.bindingCalled":
            self.pending_events.append(
                functools.partial(
                    self.page_drawn_mark,
                    event_parameters["executionContextId"],
                    event_parameters["payload"],
                )
            )
        else:
            self.waited_events.append(message)

    # Returns the next event of a method, reading messages until one comes.
    def event_wait(self, method: str) -> dict[str, Any]:
        while True:
            for event_index, waited_event in enumerate(self.waited_events):
                if waited_event["method"] == method:
                    return self.waited_events.pop(event_index)["params"]
            self.chrome_session.message_read()

    def frame_shown(self, frame_node: FrameNode) -> bool:
        try:
            owner_node_id = self.command(
                "DOM.getFrameOwner", {"frameId": frame_node.frame_id}
            )["backendNodeId"]
            owner_object = self.command(
                "DOM.resolveNode",
                {
                    "backendNodeId": owner_node_id,
                    "executionContextId": self.frame_contexts[
                        frame_node.parent_id
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
            if frame_node.frame_id in self.detached_frames:
                return False
            raise
        return self.quads_shown(frame_quads)

    def frame_tree(self) -> FrameNode:
        return self.frame_node_of(
            self.command("Page.getFrameTree")["frameTree"]
        )

    # Returns the node of a frame tree DevTools reports.
    def frame_node_of(self, frame_tree: dict[str, Any]) -> FrameNode:
        return FrameNode(
            frame_tree["frame"]["id"],
            frame_tree["frame"].get("parentId", ""),
            tuple(
                self.frame_node_of(child_tree)
                for child_tree in frame_tree.get("childFrames", [])
            ),
        )

    def image_write(self, image_path: str) -> None:
        # The fast encoding writes the same pixels to a larger file.
        image_data = self.command(
            "Page.captureScreenshot", {"optimizeForSpeed": True}
        )["data"]
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(image_data))

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

    def navigation_begin(self, page_url: str) -> str:
        navigation = self.command("Page.navigate", {"url": page_url})
        if "errorText" in navigation:
            raise RuntimeError(f"{page_url}: {navigation['errorText']}")
        return navigation["frameId"]

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

    def script_run(
        self,
        context_id: ScriptContext,
        expression: str,
        is_awaited: bool = False,
        is_activated: bool = False,
    ) -> tuple[Any, str]:
        evaluation = self.command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "contextId": context_id,
                "returnByValue": True,
                "awaitPromise": is_awaited,
                "userGesture": is_activated,
            },
        )
        if "exceptionDetails" in evaluation:
            return None, evaluation["exceptionDetails"]["text"]
        return evaluation["result"].get("value"), ""

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


# Drives one Firefox tab through its top browsing context.
class FirefoxTab(PageTab):
    def __init__(
        self,
        firefox_session: FirefoxSession,
        top_context: str,
        user_context: str,
        tab_size: tuple[int, int],
    ) -> None:
        super().__init__(firefox_session, tab_size)
        self.firefox_session = firefox_session
        # The navigation each frame started last, whose end alone counts.
        self.frame_navigations: dict[str, str] = {}
        # The script handing the drawn channel to each page of the tab.
        self.preload_script = ""
        self.top_context = top_context
        self.user_context = user_context

    def characters_send(self, typed_text: str) -> None:
        self.key_actions_send(
            [
                {"type": key_action, "value": typed_character}
                for typed_character in typed_text
                for key_action in ("keyDown", "keyUp")
            ]
        )

    def close(self) -> None:
        for frame_tabs in (
            self.firefox_session.context_tabs,
            self.firefox_session.realm_tabs,
        ):
            for frame_key in [
                frame_key
                for frame_key, page_tab in frame_tabs.items()
                if page_tab is self
            ]:
                del frame_tabs[frame_key]
        self.firefox_session.command(
            "script.removePreloadScript", {"script": self.preload_script}
        )
        self.firefox_session.command(
            "browser.removeUserContext", {"userContext": self.user_context}
        )

    # Ends the loads of a removed frame and of every frame it held.
    def context_remove(self, context_info: dict[str, Any]) -> None:
        self.detached_frames.add(context_info["context"])
        self.frame_navigations.pop(context_info["context"], None)
        self.pending_events.append(
            functools.partial(self.load_end, context_info["context"])
        )
        for child_info in context_info["children"] or ():
            self.context_remove(child_info)

    # Keeps an event of the tab, its error reports and script realms.
    def event_take(self, message: dict[str, Any]) -> None:
        self.has_news = True
        method = message["method"]
        event_parameters = message["params"]
        if method == "log.entryAdded":
            if event_parameters["type"] == "console":
                self.error_report_keep(
                    event_parameters["source"]["realm"],
                    event_parameters["text"],
                )
            elif event_parameters["level"] == "error":
                self.thrown_texts.append(event_parameters["text"])
        elif method == "script.realmCreated":
            if (
                event_parameters["type"] == "window"
                and "sandbox" not in event_parameters
            ):
                self.frame_contexts[event_parameters["context"]] = (
                    event_parameters["realm"]
                )
        elif method == "script.realmDestroyed":
            self.context_end(event_parameters["realm"])
        elif method == "script.message":
            self.pending_events.append(
                functools.partial(
                    self.page_drawn_mark,
                    event_parameters["source"]["realm"],
                    event_parameters["data"]["value"],
                )
            )
        elif method == "browsingContext.navigationStarted":
            self.frame_navigations[event_parameters["context"]] = (
                event_parameters["navigation"]
            )
            self.pending_events.append(
                functools.partial(self.load_begin, event_parameters["context"])
            )
        elif method == "browsingContext.contextDestroyed":
            self.context_remove(event_parameters)
        # A late end of a navigation a later one replaced ends nothing.
        elif (
            method != "browsingContext.contextCreated"
            and self.frame_navigations.get(event_parameters["context"])
            == event_parameters["navigation"]
        ):
            self.pending_events.append(
                functools.partial(self.load_end, event_parameters["context"])
            )

    def frame_shown(self, frame_node: FrameNode) -> bool:
        try:
            shown_call = self.firefox_session.command(
                "script.callFunction",
                {
                    "functionDeclaration": (
                        test_settings.FRAME_WINDOWS_SHOWN_FUNCTION
                    ),
                    "target": {"context": frame_node.parent_id},
                    "awaitPromise": True,
                },
            )
        except RuntimeError:
            # A frame its page removed meanwhile is out of view.
            if frame_node.frame_id in self.detached_frames:
                return False
            raise
        if shown_call["type"] == "exception":
            raise RuntimeError(
                f"{frame_node.frame_id}: frame shown check:"
                f" {shown_call['exceptionDetails']['text']}"
            )
        for frame_entry in shown_call["result"]["value"]:
            frame_window, frame_shown = frame_entry["value"]
            # An element holding no page yet has a null window.
            if (
                frame_window["type"] == "window"
                and frame_window["value"]["context"] == frame_node.frame_id
            ):
                return frame_shown["value"]
        # A frame its page removed meanwhile is out of view.
        if frame_node.frame_id in self.detached_frames:
            return False
        raise RuntimeError(f"{frame_node.frame_id}: no frame element shows it")

    def frame_tree(self) -> FrameNode:
        (top_info,) = self.firefox_session.command(
            "browsingContext.getTree", {"root": self.top_context}
        )["contexts"]
        return self.frame_node_of(top_info, "")

    # Returns the node of a browsing context tree Firefox reports.
    def frame_node_of(
        self, context_info: dict[str, Any], parent_id: str
    ) -> FrameNode:
        return FrameNode(
            context_info["context"],
            parent_id,
            tuple(
                self.frame_node_of(child_info, context_info["context"])
                for child_info in context_info["children"]
            ),
        )

    def image_write(self, image_path: str) -> None:
        image_data = self.firefox_session.command(
            "browsingContext.captureScreenshot", {"context": self.top_context}
        )["data"]
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(image_data))

    # Performs key actions on the keyboard input source, in order.
    def key_actions_send(self, key_actions: list[dict[str, str]]) -> None:
        self.firefox_session.command(
            "input.performActions",
            {
                "context": self.top_context,
                "actions": [
                    {"type": "key", "id": "keyboard", "actions": key_actions}
                ],
            },
        )

    def key_send(self, key_name: str) -> None:
        key_values = test_settings.CLICK_FIREFOX_KEY_VALUES[key_name]
        self.key_actions_send(
            [
                {"type": "keyDown", "value": key_value}
                for key_value in key_values
            ]
            + [
                {"type": "keyUp", "value": key_value}
                for key_value in reversed(key_values)
            ]
        )
        if key_name not in test_settings.CLICK_FOCUS_MOVES_BACKWARD:
            return
        top_focus = self.firefox_session.command(
            "script.evaluate",
            {
                "expression": "document.hasFocus()",
                "target": {"context": self.top_context},
                "awaitPromise": False,
            },
        )
        # A move past the page's end puts the focus on the browser's controls.
        if not top_focus["result"]["value"]:
            self.firefox_session.focus_return(
                test_settings.CLICK_FOCUS_MOVES_BACKWARD[key_name]
            )
            self.firefox_session.command(
                "script.evaluate",
                {
                    "expression": self.wait_expression(
                        test_settings.FIREFOX_PAGE_FOCUS_WAIT_FUNCTION
                    ),
                    "target": {"context": self.top_context},
                    "awaitPromise": True,
                },
            )

    def navigation_begin(self, page_url: str) -> str:
        self.firefox_session.command(
            "browsingContext.navigate",
            {"context": self.top_context, "url": page_url, "wait": "none"},
        )
        return self.top_context

    # Returns the value a serialized script value holds.
    def remote_value_read(self, remote_value: dict[str, Any]) -> Any:
        value_type = remote_value["type"]
        # A promise not awaited holds no value yet.
        if value_type in ("null", "promise", "undefined"):
            return None
        if value_type in ("boolean", "string"):
            return remote_value["value"]
        if value_type == "array":
            return [
                self.remote_value_read(item_value)
                for item_value in remote_value["value"]
            ]
        if value_type == "object":
            return {
                item_key: self.remote_value_read(item_value)
                for item_key, item_value in remote_value["value"]
            }
        # NaN, an infinity and minus zero come as text, which no check reads.
        if value_type == "number" and not isinstance(
            remote_value["value"], str
        ):
            return remote_value["value"]
        raise RuntimeError(f"a script value of no plain value: {remote_value}")

    def script_run(
        self,
        context_id: ScriptContext,
        expression: str,
        is_awaited: bool = False,
        is_activated: bool = False,
    ) -> tuple[Any, str]:
        # Firefox loses the realm of a page that rewrote itself, not its frame.
        realm_frames = [
            frame_id
            for frame_id, frame_realm in self.frame_contexts.items()
            if frame_realm == context_id
        ]
        if not realm_frames:
            raise RuntimeError(f"{context_id}: a realm its page left")
        (frame_id,) = realm_frames
        evaluation = self.firefox_session.command(
            "script.evaluate",
            {
                "expression": expression,
                "target": {"context": frame_id},
                "awaitPromise": is_awaited,
                "userActivation": is_activated,
            },
        )
        if evaluation["type"] == "exception":
            return None, evaluation["exceptionDetails"]["text"]
        return self.remote_value_read(evaluation["result"]), ""


# Drives one SeaMonkey window through the driver, its page the tab's.
class SeaMonkeyTab(PageTab):
    def __init__(
        self,
        seamonkey_session: SeaMonkeySession,
        tab_key: str,
        tab_size: tuple[int, int],
    ) -> None:
        super().__init__(seamonkey_session, tab_size)
        self.seamonkey_session = seamonkey_session
        # The value or exception of each awaited script, by its call number.
        self.call_results: dict[int, dict[str, Any]] = {}
        # The tab's top frame, which the driver names the tab by.
        self.tab_key = tab_key

    def characters_send(self, typed_text: str) -> None:
        self.keys_send(
            [
                [action_name, {"key": typed_character}]
                for typed_character in typed_text
                for action_name in ("keydown", "keyup")
            ]
        )

    # SeaMonkey's pages hold no clipboard, so its browser window writes it.
    def clipboard_write(self, frame_name: str, pasted_text: str) -> None:
        self.seamonkey_session.driver_call("clipboard_write", pasted_text)

    def close(self) -> None:
        self.seamonkey_session.tab_forget(self)
        self.seamonkey_session.driver_call("tab_close", self.tab_key)

    # Keeps a driver event of the tab, its error reports and script contexts.
    def event_take(self, driver_event: dict[str, Any]) -> None:
        self.has_news = True
        event_name = driver_event["event"]
        if event_name == "console":
            self.error_report_keep(
                driver_event["context"], driver_event["text"]
            )
        elif event_name == "thrown":
            self.thrown_texts.append(driver_event["text"])
        elif event_name == "context_created":
            self.frame_contexts[driver_event["frame"]] = driver_event[
                "context"
            ]
        elif event_name == "context_destroyed":
            self.context_end(driver_event["context"])
        elif event_name == "drawn":
            self.pending_events.append(
                functools.partial(
                    self.page_drawn_mark,
                    driver_event["context"],
                    driver_event["payload"],
                )
            )
        elif event_name == "frame_removed":
            self.detached_frames.add(driver_event["frame"])
            self.pending_events.append(
                functools.partial(self.load_end, driver_event["frame"])
            )
        elif event_name == "load_begin":
            self.pending_events.append(
                functools.partial(self.load_begin, driver_event["frame"])
            )
        elif event_name == "load_end":
            self.pending_events.append(
                functools.partial(self.load_end, driver_event["frame"])
            )
        elif event_name == "result":
            self.call_results[driver_event["call_number"]] = driver_event
        else:
            raise RuntimeError(f"a driver event of no kind: {driver_event}")

    def frame_shown(self, frame_node: FrameNode) -> bool:
        frame_shown = self.seamonkey_session.driver_call(
            "frame_shown", frame_node.parent_id, frame_node.frame_id
        )
        if isinstance(frame_shown, bool):
            return frame_shown
        # A frame its page removed meanwhile is out of view.
        if frame_node.frame_id in self.detached_frames:
            return False
        raise RuntimeError(f"{frame_node.frame_id}: no frame element shows it")

    def frame_tree(self) -> FrameNode:
        return self.frame_node_of(
            self.seamonkey_session.driver_call("frame_tree", self.tab_key), ""
        )

    # Returns the node of a frame tree the driver reports.
    def frame_node_of(
        self, tree_entry: list[Any], parent_id: str
    ) -> FrameNode:
        frame_id, child_entries = tree_entry
        return FrameNode(
            frame_id,
            parent_id,
            tuple(
                self.frame_node_of(child_entry, frame_id)
                for child_entry in child_entries
            ),
        )

    def image_write(self, image_path: str) -> None:
        image_url = self.seamonkey_session.driver_call(
            "image_data", self.tab_key, *self.tab_size
        )
        _, image_data = image_url.split(",", 1)
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(image_data))

    def key_send(self, key_name: str) -> None:
        key_events = test_settings.CLICK_SEAMONKEY_KEY_EVENTS[key_name]
        self.keys_send(
            [["keydown", key_event] for key_event in key_events]
            + [["keyup", key_event] for key_event in reversed(key_events)]
        )
        # A move past the page's end puts the focus on the browser's controls.
        if key_name in test_settings.CLICK_FOCUS_MOVES_BACKWARD:
            self.seamonkey_session.driver_call(
                "focus_return",
                self.tab_key,
                test_settings.CLICK_FOCUS_MOVES_BACKWARD[key_name],
                test_settings.CLICK_WALK_PRESS_LIMIT,
            )

    # Sends key actions to the window's focus, each a press or a release.
    def keys_send(self, key_actions: list[list[Any]]) -> None:
        self.seamonkey_session.driver_call(
            "keys_send", self.tab_key, key_actions
        )

    def navigation_begin(self, page_url: str) -> str:
        self.seamonkey_session.driver_call("navigate", self.tab_key, page_url)
        return self.tab_key

    def script_run(
        self,
        context_id: ScriptContext,
        expression: str,
        is_awaited: bool = False,
        is_activated: bool = False,
    ) -> tuple[Any, str]:
        if is_activated:
            raise RuntimeError(f"{context_id}: SeaMonkey activates no script")
        call_number = None
        if is_awaited:
            self.seamonkey_session.call_count += 1
            call_number = self.seamonkey_session.call_count
        run_reply = self.seamonkey_session.driver_call(
            "script_run", self.tab_key, context_id, expression, call_number
        )
        if "gone" in run_reply:
            self.context_end(context_id)
            raise RuntimeError(f"{context_id}: a context its page left")
        if "exception" in run_reply:
            return None, run_reply["exception"]
        if call_number is None:
            return run_reply.get("value"), ""
        while call_number not in self.call_results:
            self.seamonkey_session.message_read()
        call_result = self.call_results.pop(call_number)
        if "exception" in call_result:
            return None, call_result["exception"]
        return call_result.get("value"), ""


# Drives one WebKit page through its page session and its one target.
class WebKitTab(PageTab):
    def __init__(
        self,
        webkit_session: WebKitSession,
        page_proxy_id: str,
        browser_context_id: str,
        target_id: str,
        tab_size: tuple[int, int],
    ) -> None:
        super().__init__(webkit_session, tab_size)
        self.webkit_session = webkit_session
        self.browser_context_id = browser_context_id
        self.page_proxy_id = page_proxy_id
        self.target_command_count = 0
        self.target_id = target_id
        # The reply of each target command, by its number, until it is read.
        self.target_replies: dict[int, dict[str, Any]] = {}

    def characters_send(self, typed_text: str) -> None:
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

    def close(self) -> None:
        del self.webkit_session.page_tabs[self.page_proxy_id]
        self.webkit_session.command(
            "Playwright.deleteContext",
            {"browserContextId": self.browser_context_id},
        )

    # Sends a command to the page's session, returning its result.
    def command(
        self, method: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.webkit_session.command(
            method, parameters, self.page_proxy_id
        )

    # Ends the script context a frame's document held, if any.
    def document_end(self, frame_id: str) -> None:
        ended_context = self.frame_contexts.get(frame_id)
        if ended_context is not None:
            self.context_end(ended_context)

    # Keeps an event of the target, its error reports and script contexts.
    def event_take(self, message: dict[str, Any]) -> None:
        self.has_news = True
        method = message["method"]
        event_parameters = message["params"]
        if method == "Console.messageAdded":
            console_message = event_parameters["message"]
            # A console error report comes through its binding instead.
            if (
                console_message["source"] == "javascript"
                and console_message["level"] == "error"
            ):
                self.thrown_texts.append(console_message["text"])
        elif method == "Runtime.executionContextCreated":
            context = event_parameters["context"]
            if context["type"] == "normal":
                self.document_end(context["frameId"])
                self.frame_contexts[context["frameId"]] = context["id"]
        elif method == "Runtime.bindingCalled":
            binding_name = event_parameters["name"]
            if binding_name == test_settings.WEBKIT_CONSOLE_BINDING_NAME:
                self.error_report_keep(
                    event_parameters["contextId"], event_parameters["argument"]
                )
            elif binding_name == test_settings.PAGE_DRAWN_BINDING_NAME:
                self.pending_events.append(
                    functools.partial(
                        self.page_drawn_mark,
                        event_parameters["contextId"],
                        event_parameters["argument"],
                    )
                )
            else:
                raise RuntimeError(f"a call of no binding: {binding_name}")
        # A frame's new document ends the context of the one it replaces.
        elif method == "Page.frameNavigated":
            self.document_end(event_parameters["frame"]["id"])
        elif method == "Page.frameDetached":
            self.detached_frames.add(event_parameters["frameId"])
            self.document_end(event_parameters["frameId"])
            self.pending_events.append(
                functools.partial(self.load_end, event_parameters["frameId"])
            )
        # A frame's load starts at its navigation's check, a hash change none.
        elif method == "Page.willCheckNavigationPolicy":
            self.pending_events.append(
                functools.partial(self.load_begin, event_parameters["frameId"])
            )
        elif method == "Page.loadEventFired" or (
            method == "Page.didCheckNavigationPolicy"
            and event_parameters["cancel"]
        ):
            self.pending_events.append(
                functools.partial(self.load_end, event_parameters["frameId"])
            )

    def frame_shown(self, frame_node: FrameNode) -> bool:
        parent_context = self.frame_contexts[frame_node.parent_id]
        try:
            # One static list, so a frame its page removes meanwhile stays in.
            frame_list = self.target_command(
                "Runtime.evaluate",
                {
                    "expression": (
                        test_settings.WEBKIT_FRAME_ELEMENTS_EXPRESSION
                    ),
                    "contextId": parent_context,
                    "objectGroup": test_settings.WEBKIT_OBJECT_GROUP_NAME,
                },
            )
            if frame_list["wasThrown"]:
                raise RuntimeError(
                    f"{frame_node.parent_id}: frame list:"
                    f" {frame_list['result'].get('description', '')}"
                )
            frame_count = self.list_property_read(
                frame_list["result"]["objectId"], "length", True
            )["value"]
            for frame_index in range(frame_count):
                frame_element = self.list_property_read(
                    frame_list["result"]["objectId"], frame_index, False
                )
                element_frames = self.target_command(
                    "DOM.describeNode", {"objectId": frame_element["objectId"]}
                )
                if element_frames.get("contentFrameId") != frame_node.frame_id:
                    continue
                laid_out_call = self.target_command(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": frame_element["objectId"],
                        "functionDeclaration": (
                            test_settings.FRAME_LAID_OUT_FUNCTION
                        ),
                        "returnByValue": True,
                    },
                )
                if not laid_out_call["result"]["value"]:
                    return False
                return self.quads_shown(
                    self.target_command(
                        "DOM.getContentQuads",
                        {"objectId": frame_element["objectId"]},
                    )["quads"]
                )
        except RuntimeError:
            # A frame its page removed meanwhile is out of view.
            if frame_node.frame_id in self.detached_frames:
                return False
            raise
        finally:
            self.target_command(
                "Runtime.releaseObjectGroup",
                {"objectGroup": test_settings.WEBKIT_OBJECT_GROUP_NAME},
            )
        # A frame its page removed meanwhile is out of view.
        if frame_node.frame_id in self.detached_frames:
            return False
        raise RuntimeError(f"{frame_node.frame_id}: no frame element shows it")

    def frame_tree(self) -> FrameNode:
        return self.frame_node_of(
            self.target_command("Page.getResourceTree")["frameTree"]
        )

    # Returns the node of a frame tree the target reports.
    def frame_node_of(self, frame_tree: dict[str, Any]) -> FrameNode:
        return FrameNode(
            frame_tree["frame"]["id"],
            frame_tree["frame"].get("parentId", ""),
            tuple(
                self.frame_node_of(child_tree)
                for child_tree in frame_tree.get("childFrames", [])
            ),
        )

    def image_write(self, image_path: str) -> None:
        # WebKit shoots the last frame painted, so the page paints once more.
        self.paint_wait(test_settings.CLICK_MENU_FRAME_NAME)
        width_px, height_px = self.tab_size
        image_url = self.webkit_session.command(
            "Playwright.takePageScreenshot",
            {
                "pageProxyId": self.page_proxy_id,
                "x": 0,
                "y": 0,
                "width": width_px,
                "height": height_px,
                "omitDeviceScaleFactor": True,
            },
        )["dataURL"]
        _, image_data = image_url.split(",", 1)
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(image_data))

    def key_send(self, key_name: str) -> None:
        key_press = test_settings.CLICK_KEY_PRESSES[key_name]
        # WebKit numbers the modifier keys otherwise than DevTools does.
        key_fields = {
            part_name: part_value
            for part_name, part_value in key_press.items()
            if part_name not in ("commands", "modifiers")
        }
        key_fields["modifiers"] = sum(
            webkit_bit
            for devtools_bit, webkit_bit in (
                test_settings.CLICK_WEBKIT_MODIFIER_BITS.items()
            )
            if key_press.get("modifiers", 0) & devtools_bit
        )
        self.command(
            "Input.dispatchKeyEvent", {"type": "keyDown", **key_fields}
        )
        self.command(
            "Input.dispatchKeyEvent",
            {
                "type": "keyUp",
                **{
                    part_name: part_value
                    for part_name, part_value in key_fields.items()
                    if part_name != "text"
                },
            },
        )

    # Returns a property of a list object, its value or a remote object of it.
    def list_property_read(
        self, list_object_id: str, property_key: str | int, is_value: bool
    ) -> dict[str, Any]:
        property_call = self.target_command(
            "Runtime.callFunctionOn",
            {
                "objectId": list_object_id,
                "functionDeclaration": (
                    test_settings.WEBKIT_PROPERTY_READ_FUNCTION
                ),
                "arguments": [{"value": property_key}],
                "returnByValue": is_value,
            },
        )
        if property_call["wasThrown"]:
            raise RuntimeError(
                f"{list_object_id}: property {property_key}:"
                f" {property_call['result'].get('description', '')}"
            )
        return property_call["result"]

    def navigation_begin(self, page_url: str) -> str:
        self.webkit_session.command(
            "Playwright.navigate",
            {"url": page_url, "pageProxyId": self.page_proxy_id},
        )
        return self.frame_tree().frame_id

    def script_run(
        self,
        context_id: ScriptContext,
        expression: str,
        is_awaited: bool = False,
        is_activated: bool = False,
    ) -> tuple[Any, str]:
        # An awaited promise is kept in a group, read once it settles.
        group_fields = (
            {"objectGroup": test_settings.WEBKIT_OBJECT_GROUP_NAME}
            if is_awaited
            else {"returnByValue": True}
        )
        try:
            evaluation = self.target_command(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "contextId": context_id,
                    "emulateUserGesture": is_activated,
                    **group_fields,
                },
            )
            if is_awaited and not evaluation["wasThrown"]:
                evaluation = self.target_command(
                    "Runtime.awaitPromise",
                    {
                        "promiseObjectId": evaluation["result"]["objectId"],
                        "returnByValue": True,
                    },
                )
        finally:
            if is_awaited:
                self.target_command(
                    "Runtime.releaseObjectGroup",
                    {"objectGroup": test_settings.WEBKIT_OBJECT_GROUP_NAME},
                )
        if evaluation["wasThrown"]:
            return None, evaluation["result"].get("description", "")
        return evaluation["result"].get("value"), ""

    # Sends a command to the page's target, returning its result.
    def target_command(
        self, method: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.target_command_count += 1
        command_number = self.target_command_count
        self.command(
            "Target.sendMessageToTarget",
            {
                "targetId": self.target_id,
                "message": json.dumps(
                    {
                        "id": command_number,
                        "method": method,
                        "params": parameters or {},
                    }
                ),
            },
        )
        while command_number not in self.target_replies:
            self.webkit_session.message_read()
        reply_message = self.target_replies.pop(command_number)
        if "error" in reply_message:
            raise RuntimeError(f"{method}: {reply_message['error']}")
        return reply_message["result"]

    # Keeps a target command's reply, or takes the target's event.
    def target_message_take(self, message: dict[str, Any]) -> None:
        if "id" in message:
            self.target_replies[message["id"]] = message
        else:
            self.event_take(message)


# Sends and reads the text messages of one WebSocket, as its client.
class WebSocketChannel:
    def __init__(self, socket_url: str) -> None:
        split_url = urllib.parse.urlsplit(socket_url)
        if not split_url.hostname or not split_url.port:
            raise RuntimeError(f"{socket_url}: names no host and port")
        self.socket_connection = socket.create_connection(
            (split_url.hostname, split_url.port)
        )
        self.unread_bytes = bytearray()
        handshake_key = base64.b64encode(
            os.urandom(test_settings.WEB_SOCKET_KEY_BYTES)
        ).decode()
        self.socket_connection.sendall(
            (
                f"GET {split_url.path} HTTP/1.1\r\n"
                f"Host: {split_url.netloc}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {handshake_key}\r\n"
                f"Sec-WebSocket-Version: {test_settings.WEB_SOCKET_VERSION}"
                "\r\n\r\n"
            ).encode()
        )
        while test_settings.WEB_SOCKET_HEADER_END not in self.unread_bytes:
            self.bytes_receive()
        header_bytes, _, self.unread_bytes = self.unread_bytes.partition(
            test_settings.WEB_SOCKET_HEADER_END
        )
        status_line, *header_lines = header_bytes.decode().split("\r\n")
        _, status_code, _ = status_line.split(" ", 2)
        accept_key = base64.b64encode(
            hashlib.sha1(
                (handshake_key + test_settings.WEB_SOCKET_ACCEPT_GUID).encode()
            ).digest()
        ).decode()
        accept_values = [
            header_value.strip()
            for header_name, _, header_value in (
                header_line.partition(":") for header_line in header_lines
            )
            if header_name.strip().lower() == "sec-websocket-accept"
        ]
        if (
            status_code != test_settings.WEB_SOCKET_SWITCH_STATUS
            or accept_values != [accept_key]
        ):
            raise RuntimeError(f"{socket_url}: answered {status_line!r}")

    # Receives the bytes the socket holds, waiting for some.
    def bytes_receive(self) -> None:
        received_bytes = self.socket_connection.recv(
            test_settings.WEB_SOCKET_READ_BYTES
        )
        if not received_bytes:
            raise ConnectionError("the socket closed")
        self.unread_bytes += received_bytes

    # Reads exactly a count of bytes, receiving until they came.
    def bytes_take(self, byte_count: int) -> bytes:
        while len(self.unread_bytes) < byte_count:
            self.bytes_receive()
        taken_bytes = bytes(self.unread_bytes[:byte_count])
        del self.unread_bytes[:byte_count]
        return taken_bytes

    def close(self) -> None:
        self.socket_connection.close()

    # Sends one frame, its payload masked as a client's must be.
    def frame_send(self, opcode: int, payload: bytes) -> None:
        payload_length = len(payload)
        if payload_length < test_settings.WEB_SOCKET_SHORT_LENGTH_MARK:
            length_bytes = bytes(
                [test_settings.WEB_SOCKET_MASK_BIT | payload_length]
            )
        elif payload_length < test_settings.WEB_SOCKET_SHORT_LENGTH_LIMIT:
            length_bytes = bytes(
                [
                    test_settings.WEB_SOCKET_MASK_BIT
                    | test_settings.WEB_SOCKET_SHORT_LENGTH_MARK
                ]
            ) + payload_length.to_bytes(
                test_settings.WEB_SOCKET_SHORT_LENGTH_BYTES, "big"
            )
        else:
            length_bytes = bytes(
                [
                    test_settings.WEB_SOCKET_MASK_BIT
                    | test_settings.WEB_SOCKET_LONG_LENGTH_MARK
                ]
            ) + payload_length.to_bytes(
                test_settings.WEB_SOCKET_LONG_LENGTH_BYTES, "big"
            )
        mask_key = os.urandom(test_settings.WEB_SOCKET_MASK_BYTES)
        mask_repeats = payload_length // len(mask_key) + 1
        repeated_mask = (mask_key * mask_repeats)[:payload_length]
        masked_payload = (
            int.from_bytes(payload, "big")
            ^ int.from_bytes(repeated_mask, "big")
        ).to_bytes(payload_length, "big")
        self.socket_connection.sendall(
            bytes([test_settings.WEB_SOCKET_FINAL_BIT | opcode])
            + length_bytes
            + mask_key
            + masked_payload
        )

    # Reads the next text message, its fragments joined, answering pings.
    def message_read(self) -> str:
        message_bytes = bytearray()
        while True:
            first_byte, second_byte = self.bytes_take(
                test_settings.WEB_SOCKET_FRAME_HEAD_BYTES
            )
            opcode = first_byte & test_settings.WEB_SOCKET_OPCODE_MASK
            payload_length = second_byte & test_settings.WEB_SOCKET_LENGTH_MASK
            if payload_length == test_settings.WEB_SOCKET_SHORT_LENGTH_MARK:
                payload_length = int.from_bytes(
                    self.bytes_take(
                        test_settings.WEB_SOCKET_SHORT_LENGTH_BYTES
                    ),
                    "big",
                )
            elif payload_length == test_settings.WEB_SOCKET_LONG_LENGTH_MARK:
                payload_length = int.from_bytes(
                    self.bytes_take(
                        test_settings.WEB_SOCKET_LONG_LENGTH_BYTES
                    ),
                    "big",
                )
            if second_byte & test_settings.WEB_SOCKET_MASK_BIT:
                raise RuntimeError("the server masked a frame")
            payload = self.bytes_take(payload_length)
            if opcode == test_settings.WEB_SOCKET_CLOSE_OPCODE:
                raise ConnectionError("the server closed the socket")
            if opcode == test_settings.WEB_SOCKET_PING_OPCODE:
                self.frame_send(test_settings.WEB_SOCKET_PONG_OPCODE, payload)
            elif opcode != test_settings.WEB_SOCKET_PONG_OPCODE:
                message_bytes += payload
                if first_byte & test_settings.WEB_SOCKET_FINAL_BIT:
                    return message_bytes.decode()

    def message_send(self, message_text: str) -> None:
        self.frame_send(
            test_settings.WEB_SOCKET_TEXT_OPCODE, message_text.encode()
        )


class Screenshots:
    def __init__(
        self,
        report: str,
        report_flag: int,
        out_dir: str,
        scratch_dir: str,
        chosen_shot: str,
        session_type: type[BrowserSession],
    ) -> None:
        # The browser session the run opens, set once the browser starts.
        self.browser_session: BrowserSession | None = None
        # The one shot a single shot run takes, empty for every shot.
        self.chosen_shot = chosen_shot
        self.report = report
        self.report_flag = report_flag
        self.out_dir = out_dir
        self.scratch_dir = scratch_dir
        # The browser's kind, which names the views it shoots.
        self.session_type = session_type
        self.report_views = self.report_views_select()
        self.click_timings: list[PageTiming] = []
        # The timings of each page drawn in two frames, every one kept.
        self.frame_timings: list[PageTiming] = []
        self.page_timings: list[PageTiming] = []

    # Walks to a step's element and presses its key, timing it when traced.
    def click_time(
        self,
        page_tab: PageTab,
        set_name: str,
        click_step: ClickStep,
    ) -> None:
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
        is_traced = self.session().traces_pages
        if is_traced:
            page_tab.trace_begin()
        page_tab.press(
            click_step.key_name,
            click_step.state_frame_name,
            click_step.state_expression,
            state_before,
        )
        trace_events = page_tab.trace_end() if is_traced else None
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
        if trace_events is None:
            return
        phase_name = (
            f"{test_settings.TIMING_CLICK_PHASE_NAME} {click_step.label}"
        )
        self.click_timings.append(
            PageTiming(
                page_file,
                phase_name,
                phase_name,
                self.trace_press_span(
                    trace_events, f"{set_name}: {click_step.label}"
                ),
                set_name,
            )
        )

    # Presses every click of each click set this report runs, timing each.
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
                    self.click_time(page_tab, click_set.set_name, click_step)

    def copy_shoot(
        self,
        view_index: int,
        report_name: str,
        view: ScreenshotSet,
    ) -> int:
        if os.path.exists(self.scratch_dir):
            shutil.rmtree(self.scratch_dir)
        shutil.copytree(self.report, self.scratch_dir)
        try:
            for relative_path in view.absent_files:
                os.remove(os.path.join(self.scratch_dir, relative_path))
            return self.view_shoot(
                self.scratch_dir, view_index, report_name, view
            )
        finally:
            shutil.rmtree(self.scratch_dir)

    # Returns each pixel's largest color channel change between two images.
    def channel_change(
        self, new_image: PIL.Image.Image, gold_image: PIL.Image.Image
    ) -> PIL.Image.Image:
        return functools.reduce(
            PIL.ImageChops.lighter,
            PIL.ImageChops.difference(new_image, gold_image).split(),
        )

    # Returns the commit of a frame a time falls after, minus one for none.
    def commit_index_at(
        self, commit_times: dict[str, list[float]], frame: str, at_time: float
    ) -> int:
        return bisect.bisect_right(commit_times.get(frame, []), at_time) - 1

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

    # Returns the error line of the first shot unlike its gold twin, else none.
    def gold_difference(
        self,
        report_name: str,
        gold_dir: str,
        compare_rule: tuple[int, int],
        same_lines: list[str],
    ) -> str | None:
        square_px, matching_change = compare_rule
        for shot_name in self.shot_names(report_name):
            if not self.shot_is_taken(shot_name):
                continue
            file_name = shot_name + test_settings.IMAGE_SUFFIX
            new_path = os.path.join(self.out_dir, file_name)
            if not os.path.isfile(new_path):
                raise RuntimeError(f"{file_name}: absent from {self.out_dir}")
            gold_path = os.path.join(gold_dir, file_name)
            if not os.path.isfile(gold_path):
                return f"error: {new_path} has no gold twin {gold_path}"
            new_shot = PIL.Image.open(new_path).convert("RGB")
            gold_shot = PIL.Image.open(gold_path).convert("RGB")
            if new_shot.size != gold_shot.size:
                return (
                    f"error: {new_path} is {new_shot.width}x{new_shot.height},"
                    f" its gold twin {gold_path}"
                    f" {gold_shot.width}x{gold_shot.height}"
                )
            square_change = self.channel_change(
                new_shot.reduce(square_px), gold_shot.reduce(square_px)
            )
            if (
                square_change.point(
                    [
                        255 if channel_value > matching_change else 0
                        for channel_value in range(256)
                    ]
                ).getbbox()
                is not None
            ):
                return (
                    f"error: {new_path} differs from its gold twin {gold_path}"
                )
            same_lines.append(f"{file_name}: same as {gold_path}")
        return None

    # Merges this report's pages and timings into the index, returning all.
    def index_write(
        self,
        report_name: str,
        index_path: str,
        template: str,
        timing_rows: list[TimingRow],
    ) -> list[dict[str, str]]:
        assert template.count(test_settings.INDEX_MARKER) == 1, (
            test_settings.INDEX_MARKER
        )
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
                self.shot_name(
                    view_index, "", report_name, view, variant.mode_name
                )
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

    # Refuses a logo link other than the golden one.
    def logo_link_check(self) -> None:
        _, width_px, height_px = test_settings.SCREENSHOT_VIEWPORTS[0]
        entry_url = self.file_url(
            os.path.join(self.report, test_settings.ENTRY_PAGE)
        )
        with self.session().tab(width_px, height_px) as page_tab:
            page_tab.page_open(entry_url)
            page_markup = page_tab.frame_evaluate(
                test_settings.CLICK_MENU_FRAME_NAME,
                "document.documentElement.outerHTML",
            )
            error_message = page_tab.error_message()
        link_match = test_settings.MENU_LOGO_LINK_PATTERN.search(page_markup)
        found_text = link_match.group(1) if link_match else None
        if found_text == test_settings.MENU_LOGO_REPOSITORY_LINK:
            return
        raise RuntimeError(
            f"{entry_url}: the logo link holds {found_text!r}, expected"
            f" {test_settings.MENU_LOGO_REPOSITORY_LINK!r}, the error handler"
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
            and self.view_is_supported(view.view_hash)
        ]

    # Returns the browser session the run opened.
    def session(self) -> BrowserSession:
        assert self.browser_session, "the browser has not started"
        return self.browser_session

    def shoot_all(self, report_name: str) -> int:
        written = 0
        for view_index, view in self.report_views:
            if view.shot_flags & test_settings.SHOOT_INDEX_PAGE:
                continue
            if not self.view_is_taken(view_index, report_name, view):
                continue
            if view.absent_files:
                written += self.copy_shoot(view_index, report_name, view)
            else:
                written += self.view_shoot(
                    self.report, view_index, report_name, view
                )
        return written

    # Shoots the index page at the given hash, else at its view's own.
    def index_shoot(
        self, report_name: str, index_path: str, index_hash: str
    ) -> int:
        written = 0
        for view_index, view in self.report_views:
            if view.shot_flags & test_settings.SHOOT_INDEX_PAGE and (
                self.view_is_taken(view_index, report_name, view)
            ):
                written += self.view_shoot(
                    index_path,
                    view_index,
                    report_name,
                    view._replace(view_hash=index_hash or view.view_hash),
                )
        return written

    # Names a shot, leaving out the resolution when the size is empty.
    def shot_name(
        self,
        view_index: int,
        size_name: str,
        report_name: str,
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
                report_name,
                mode_name,
            )
            if name_part
        )

    # Names every shot of this report, the index page's too.
    def shot_names(self, report_name: str) -> list[str]:
        return [
            shot
            for view_index, view in self.report_views
            if view.is_pictured(view_index)
            for shot in self.view_shot_names(view_index, report_name, view)
        ]

    # Returns whether the run takes a shot, a single shot run its own alone.
    def shot_is_taken(self, shot: str) -> bool:
        return not self.chosen_shot or shot == self.chosen_shot

    # Returns whether the browser supports the view an address part opens.
    def view_is_supported(self, address_part: str) -> bool:
        address_values = urllib.parse.parse_qs(address_part.removeprefix("#"))
        # An address naming no view opens the overview.
        return not set(address_values.get("view", ())) & set(
            self.session_type.unsupported_views
        )

    # Returns whether the run takes a shot of the view.
    def view_is_taken(
        self, view_index: int, report_name: str, view: ScreenshotSet
    ) -> bool:
        return any(
            self.shot_is_taken(shot)
            for shot in self.view_shot_names(view_index, report_name, view)
        )

    # Names the shots of one view, one for each of its variants.
    def view_shot_names(
        self, view_index: int, report_name: str, view: ScreenshotSet
    ) -> list[str]:
        return [
            self.shot_name(
                view_index,
                variant.size_name,
                report_name,
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
            if self.view_is_supported(view_part)
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
            frame_activations = [
                activation
                for activation in activations
                if activation["pid"] == process_id
                and activation["args"]["layerTreeId"] == layer_tree_id
                and activation["args"]["frameId"] == frame_number
            ]
            # A frame replaced before the compositor took it never shows.
            if not frame_activations:
                continue
            frame_draws = [
                screen_draw
                for screen_draw in screen_draws
                if screen_draw["pid"] == process_id
                and screen_draw["args"]["layerTreeId"] == layer_tree_id
                and screen_draw["ts"] >= frame_activations[0]["ts"]
            ]
            # A frame the trace ends before the compositor drew never shows.
            if not frame_draws:
                continue
            draw_times.append(frame_draws[0]["ts"])
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
        report_name: str,
        view: ScreenshotSet,
    ) -> int:
        browser_session = self.session()
        is_pictured = view.is_pictured(view_index)
        shot_variants = view.shot_variants(view_index)
        # The index page frames report pages, so only the report shots trace.
        is_traced = browser_session.traces_pages and not view.shot_flags & (
            test_settings.SHOOT_INDEX_PAGE | test_settings.SHOOT_UNTIMED
        )
        # Every shot of a page drawn in two frames is taken after its second.
        is_drawn_twice = browser_session.traces_pages and bool(
            view.shot_flags & test_settings.SHOOT_TWO_FRAMES
        )
        taken_count = 0
        for variant in shot_variants:
            shot = self.shot_name(
                view_index,
                variant.size_name,
                report_name,
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
                    # The screen shows a frame after its paint, so one more.
                    page_tab.paint_wait(test_settings.CLICK_MENU_FRAME_NAME)
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
    perf2html_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    session_types: tuple[type[BrowserSession], ...] = (
        ChromeSession,
        FirefoxSession,
        SeaMonkeySession,
        WebKitSession,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-root",
        default=perf2html_dir,
        metavar="DIR",
        help="the directory build/ lies in",
    )
    parser.add_argument(
        "--compare-browser",
        choices=[session_type.shot_dir_name for session_type in session_types],
        default="",
    )
    browser_group = parser.add_mutually_exclusive_group()
    browser_group.add_argument(
        "--firefox",
        action="store_const",
        const=FirefoxSession,
        default=ChromeSession,
        dest="session_type",
    )
    parser.add_argument("--index-hash", default="", metavar="HASH")
    browser_group.add_argument(
        "--seamonkey",
        action="store_const",
        const=SeaMonkeySession,
        default=ChromeSession,
        dest="session_type",
    )
    parser.add_argument("--shot", default="", metavar="NAME")
    parser.add_argument(
        "--verbose",
        action="count",
        default=0,
        help="print where the shots go and how many; a quiet run prints"
        " nothing on success",
    )
    browser_group.add_argument(
        "--webkit",
        action="store_const",
        const=WebKitSession,
        default=ChromeSession,
        dest="session_type",
    )
    namespace = parser.parse_args()
    session_type: type[BrowserSession] = namespace.session_type

    if namespace.compare_browser == session_type.shot_dir_name:
        print(
            f"error: --compare-browser {namespace.compare_browser} names the"
            " browser shooting",
            file=sys.stderr,
        )
        return 2

    if namespace.index_hash and not namespace.index_hash.startswith("#"):
        print(
            f"error: --index-hash {namespace.index_hash} starts with no #",
            file=sys.stderr,
        )
        return 2

    screenshots_dir = os.path.join(
        perf2html_dir, test_settings.SCREENSHOT_DIR_NAME
    )
    out_dir = os.path.join(screenshots_dir, session_type.shot_dir_name)
    own_gold_dir = os.path.join(
        screenshots_dir,
        test_settings.SCREENSHOT_GOLD_DIR_FORMAT.format(
            session_type.shot_dir_name
        ),
    )
    # Another browser's gold is compared on request, font smoothing passing.
    if namespace.compare_browser:
        gold_dir = os.path.join(
            screenshots_dir,
            test_settings.SCREENSHOT_GOLD_DIR_FORMAT.format(
                namespace.compare_browser
            ),
        )
        if not os.path.isdir(gold_dir):
            print(
                f"error: --compare-browser {namespace.compare_browser}:"
                f" {gold_dir} is no directory",
                file=sys.stderr,
            )
            return 2
        compare_rule = (
            test_settings.COMPARE_VAGUE_SQUARE_PX,
            test_settings.COMPARE_VAGUE_CHANNEL_CHANGE,
        )
    else:
        gold_dir = own_gold_dir if os.path.isdir(own_gold_dir) else ""
        compare_rule = session_type.own_gold_compare_rule
    # A whole run with no gold of its own browser to compare makes that gold.
    is_gold_made = not (
        namespace.shot or namespace.compare_browser or gold_dir
    )
    scratch_dir = os.path.abspath(
        os.path.join(
            namespace.build_root, test_settings.SCREENSHOT_SCRATCH_DIR_PATH
        )
    )

    shooters: list[tuple[str, Screenshots]] = []
    for (
        report_dir_name,
        report_name,
        report_flag,
    ) in test_settings.SHOOT_REPORTS:
        report = os.path.join(perf2html_dir, report_dir_name)
        if not os.path.isfile(os.path.join(report, test_settings.ENTRY_PAGE)):
            print(
                f"error: {report} holds no {test_settings.ENTRY_PAGE}",
                file=sys.stderr,
            )
            return 2
        shooters.append(
            (
                report_name,
                Screenshots(
                    report,
                    report_flag,
                    out_dir,
                    scratch_dir,
                    namespace.shot,
                    session_type,
                ),
            )
        )
    if namespace.shot and not any(
        namespace.shot in shooter.shot_names(report_name)
        for report_name, shooter in shooters
    ):
        print(
            f"error: --shot {namespace.shot} names no shot",
            file=sys.stderr,
        )
        return 2

    index_path = os.path.join(perf2html_dir, test_settings.INDEX_PAGE_NAME)
    # A browser writing no timing shoots the index page Chrome's run wrote.
    if (
        not session_type.traces_pages
        and not namespace.shot
        and not os.path.isfile(index_path)
    ):
        print(
            f"error: {session_type.browser_name} shoots {index_path},"
            " which is no file",
            file=sys.stderr,
        )
        return 2
    with open(
        os.path.join(
            perf2html_dir, "scripts", test_settings.INDEX_TEMPLATE_NAME
        )
    ) as template_file:
        index_template = template_file.read()
    # Every run writes its browser's shots afresh, the gold untouched.
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    browser_session = session_type(namespace.build_root)
    timing_rows: list[TimingRow] = []
    report_timings: list[dict[str, str]] = []
    written = 0
    with browser_session:
        for report_name, shooter in shooters:
            shooter.browser_session = browser_session
            if namespace.verbose:
                verbose_print(
                    namespace.verbose,
                    [f"{os.path.basename(shooter.report)} -> {out_dir}"],
                )
            # A single shot run takes its shot alone, checking and timing none.
            if namespace.shot:
                written += shooter.shoot_all(report_name)
                written += shooter.index_shoot(
                    report_name, index_path, namespace.index_hash
                )
                continue
            shooter.test_views_check()
            written += shooter.shoot_all(report_name)
            shooter.clicks_time()
            shooter.logo_link_check()
            if browser_session.traces_pages:
                report_timing_rows = shooter.timing_rows()
                timing_rows += report_timing_rows
                report_timings = shooter.index_write(
                    report_name, index_path, index_template, report_timing_rows
                )
            written += shooter.index_shoot(
                report_name, index_path, namespace.index_hash
            )
    if namespace.verbose:
        verbose_print(namespace.verbose, [f"{written} screenshot(s)"])
    if gold_dir:
        same_lines: list[str] = []
        for report_name, shooter in shooters:
            difference_line = shooter.gold_difference(
                report_name, gold_dir, compare_rule, same_lines
            )
            if difference_line:
                print(difference_line, file=sys.stderr)
                return 1
        if namespace.verbose:
            verbose_print(namespace.verbose, same_lines)
    if browser_session.traces_pages and not namespace.shot:
        if namespace.verbose:
            verbose_print(
                namespace.verbose,
                [timing_row.verbose_line() for timing_row in timing_rows],
            )
        timing_exit_code = shooters[-1][1].timing_file_write(
            os.path.join(out_dir, test_settings.TIMING_FILE_NAME),
            report_timings,
            timing_rows,
        )
        if timing_exit_code:
            return timing_exit_code
    if is_gold_made:
        os.rename(out_dir, own_gold_dir)
        if namespace.verbose:
            verbose_print(namespace.verbose, [f"{out_dir} -> {own_gold_dir}"])
    return 0


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
