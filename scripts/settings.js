// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE-MIT.md file.

window.try_catch_handler_(function () {
  "use strict";

  const is_framed = window.is_framed_;
  const written_object = {
  "ARTIFACTS_NAME": "perf2html_temporary_artifacts",
  "ARTIFACT_ARCHIVE_KINDS": [
    "callgrind",
    "function-data"
  ],
  "ARTIFACT_ARCHIVE_RUN_KINDS": [
    "file-data",
    "timing-data"
  ],
  "ARTIFACT_DIFFED_KINDS": [
    "delta",
    "function-diff"
  ],
  "ARTIFACT_FILE_PURPOSES": {
    "baseline-header": "the baseline report's header block",
    "baseline-profiles": "the baseline report's raw data archive, extracted",
    "callgrind": "the callgrind recording",
    "delta": "the callgrind delta, modified minus baseline",
    "diff-log": "the diff run's log",
    "diff-regenerate-log": "the last diff --regenerate run's log",
    "file-data": "the paths document, each path's code",
    "function-data": "each function's place, self costs, callers and callees",
    "function-diff": "the function data diff with the baseline costs",
    "header-rows": "the manifest rows of the measuring run",
    "modified-header": "the modified report's header block",
    "modified-profiles": "the modified report's raw data archive, extracted",
    "profile-log": "the measuring run's log",
    "profile-regenerate-log": "the last --regenerate run's log",
    "test-list": "the test names, one per line, sorted",
    "timing-data": "the timing document, each test's overview values",
    "timing-json": "the perf stat counters, one JSON line per event",
    "timing-page": "the timing page, the command and the curl perf tool's runs",
    "timing-summary": "the timing summary rows, one label=value each",
    "trace-binary": "the function trace of the sampled run",
    "trace-log": "the trace page, both runs and the conversion",
    "trace-maps": "the traced process's mappings",
    "trace-speedscope": "the speedscope profile of the sampled run",
    "valgrind-log": "the valgrind log"
  },
  "ARTIFACT_RECORDED_KINDS": [
    "callgrind",
    "timing-json",
    "timing-page",
    "trace-log",
    "trace-speedscope",
    "valgrind-log"
  ],
  "ARTIFACT_RUN_FILE_FORMATS": {
    "baseline-header": "%s/baseline.txt",
    "baseline-profiles": "%s/baseline",
    "diff-log": "%s/perf2html_diff.log",
    "diff-regenerate-log": "%s/perf2html_diff.regenerate.log",
    "file-data": "%s/0_file_data.json",
    "header-rows": "%s/perf2html.txt",
    "modified-header": "%s/modified.txt",
    "modified-profiles": "%s/modified",
    "profile-log": "%s/perf2html.log",
    "profile-regenerate-log": "%s/perf2html.regenerate.log",
    "test-list": "%s/test_list.txt",
    "timing-data": "%s/0_timing_data.json"
  },
  "ARTIFACT_TEST_FILE_FORMATS": {
    "callgrind": "%s/%s.callgrind.out",
    "delta": "%s/%s.callgrind_diff.out",
    "function-data": "%s/%s_function_data.json",
    "function-diff": "%s/%s.callgrind_diff.json",
    "timing-json": "%s/%s.perf-stat.json",
    "timing-page": "%s/%s.perf-stat.txt",
    "timing-summary": "%s/%s.perf-stat.summary",
    "trace-binary": "%s/%s.cyg_callback.bin",
    "trace-log": "%s/%s.cyg_callback.log",
    "trace-maps": "%s/%s.cyg_callback.bin.maps",
    "trace-speedscope": "%s/%s.trace_to_speedscope.json",
    "valgrind-log": "%s/%s.valgrind.log"
  },
  "ASSET_CALL_GRAPH_SCRIPT_NAME": "call_graph.js",
  "ASSET_DARK_MODE_STYLESHEET_NAME": "dark_mode.css",
  "ASSET_DATABASE_SCRIPT_NAME": "database.js",
  "ASSET_DEBUG_SCRIPT_NAME": "debug.js",
  "ASSET_ERROR_OVERLAY_SCRIPT_NAME": "error_overlay.js",
  "ASSET_FLAME_GRAPH_SCRIPT_NAME": "flame_graph.js",
  "ASSET_FRAME_SCRIPT_NAME": "frame.js",
  "ASSET_HEAT_MAP_SCRIPT_NAME": "heat_map.js",
  "ASSET_HEAT_MAP_STYLESHEET_NAME": "heat_map.css",
  "ASSET_LIGHT_MODE_STYLESHEET_NAME": "light_mode.css",
  "ASSET_MENU_SCRIPT_NAME": "menu.js",
  "ASSET_OVERVIEW_SCRIPT_NAME": "overview.js",
  "ASSET_PREFERENCES_SCRIPT_NAME": "preferences.js",
  "ASSET_SETTINGS_PAGE_SCRIPT_NAME": "settings_page.js",
  "ASSET_SETTINGS_SCRIPT_NAME": "settings.js",
  "ASSET_SOURCE_DATABASE_SCRIPT_NAME": "source_database.js",
  "ASSET_TEMPLATE_CALL_GRAPH_PAGE_NAME": "call_graph.html",
  "ASSET_TEMPLATE_DATABASE_PAGE_NAME": "database.html",
  "ASSET_TEMPLATE_FLAME_GRAPH_PAGE_NAME": "flame_graph.html",
  "ASSET_TEMPLATE_HEAT_MAP_PAGE_NAME": "heat_map.html",
  "ASSET_TEMPLATE_OVERVIEW_PAGE_NAME": "overview.html",
  "ASSET_TEMPLATE_README_PAGE_NAME": "readme_page.html",
  "ASSET_TEMPLATE_SETTINGS_PAGE_NAME": "settings_page.html",
  "ASSET_THEME_SCRIPT_NAME": "theme.js",
  "ASSET_THEME_STYLESHEET_NAME": "theme.css",
  "ASSET_UI_STRINGS_SCRIPT_NAME": "ui_strings.js",
  "ASSET_UTILITY_SCRIPT_NAME": "utility.js",
  "BUILD_CCACHE_NAMESPACE": "perf2html",
  "BUILD_DIR": "build-relwithdebinfo",
  "CACHE_ARCHIVE_BASE_URL": "http://archive.ubuntu.com/ubuntu/pool/main",
  "CACHE_EXTERNAL_PACKAGE": "libc6",
  "CACHE_ROOT_DIR": "~/.cache/perf2html",
  "CALLGRIND_FILE_DATA_CODE_KEY": "t",
  "CALLGRIND_FILE_DATA_ERROR_CODE": "err",
  "CALLGRIND_FILE_DATA_GIT_CODE": "git",
  "CALLGRIND_FILE_DATA_PATH_KEY": "p",
  "CALLGRIND_FILE_DATA_REPO_CODE": "repo",
  "CALLGRIND_FILE_DATA_SYSTEM_CODE": "sys",
  "CALLGRIND_FORMAT_CALLEE_FILE_KEYS": [
    "cfl",
    "cfi"
  ],
  "CALLGRIND_FORMAT_CALLEE_FUNCTION_KEY": "cfn",
  "CALLGRIND_FORMAT_CALLEE_IMAGE_KEY": "cob",
  "CALLGRIND_FORMAT_CALLS_KEY": "calls",
  "CALLGRIND_FORMAT_COMMAND_KEY": "cmd",
  "CALLGRIND_FORMAT_COUNTERS_KEY": "events",
  "CALLGRIND_FORMAT_FILE_KEY": "fl",
  "CALLGRIND_FORMAT_FUNCTION_KEY": "fn",
  "CALLGRIND_FORMAT_IMAGE_KEY": "ob",
  "CALLGRIND_FORMAT_INLINE_FILE_KEYS": [
    "fi",
    "fe"
  ],
  "CALLGRIND_FORMAT_JUMP_FILE_KEY": "jfi",
  "CALLGRIND_FORMAT_JUMP_FUNCTION_KEY": "jfn",
  "CALLGRIND_FORMAT_LINE_POSITION_NAME": "line",
  "CALLGRIND_FORMAT_POSITIONS_KEY": "positions",
  "CALLGRIND_FORMAT_SUMMARY_KEYS": [
    "summary",
    "totals"
  ],
  "CALLGRIND_LAST_LEVEL_CACHE": "16777216,16,64",
  "CALLGRIND_NAME_COMPRESSION_PATTERN": "^\\((\\d+)\\)(?: (.*))?$",
  "CALLGRIND_UNKNOWN_DISPLAY_PATH": "(unknown)",
  "CALLGRIND_UNKNOWN_NAME": "???",
  "CALL_GRAPH_BRANCH_FIRST_TEXT": "┳━",
  "CALL_GRAPH_BRANCH_LAST_TEXT": "┗━",
  "CALL_GRAPH_BRANCH_MIDDLE_TEXT": "┣━",
  "CALL_GRAPH_BRANCH_ONLY_TEXT": "━━",
  "CALL_GRAPH_BRANCH_PASS_TEXT": "┃",
  "CALL_GRAPH_CLOSED_TEXT": "⊞",
  "CALL_GRAPH_DOWNLOAD_FILE_NAME_SUFFIX": "_call_graph.svg",
  "CALL_GRAPH_LINE_TEXT": "━",
  "CALL_GRAPH_PAD_TEXT": " ",
  "CALL_GRAPH_PAGE_DIR_NAME": "call-graph",
  "CALL_GRAPH_REVEAL_CLEARANCE_CHARS": 1,
  "CALL_GRAPH_REVEAL_CLEARANCE_LINES": 0.5,
  "CALL_GRAPH_SORT_DEFAULT_MODE": "cumulative",
  "CALL_GRAPH_VIEW_KEY": "call-graph",
  "CONTAINING_PACKAGES": {
    "addr2line": "binutils",
    "cc": "build-essential",
    "ccache": "ccache",
    "cksum": "coreutils",
    "cmake": "cmake",
    "cmark-gfm": "cmark-gfm",
    "curl": "curl",
    "dpkg-query": "dpkg",
    "ninja": "ninja-build",
    "perf": "linux-perf",
    "python3": "python3",
    "readelf": "binutils",
    "tar": "tar",
    "taskset": "util-linux",
    "valgrind": "valgrind",
    "xz": "xz-utils"
  },
  "COUNTER_LIST_CALLEES_LINE_NAME": "callees",
  "COUNTER_LIST_CALLERS_LINE_NAME": "callers",
  "COUNTER_LIST_CALLGRIND_LINE_NAMES": [
    "Ir",
    "Dr",
    "Dw",
    "I1mr",
    "D1mr",
    "D1mw",
    "ILmr",
    "DLmr",
    "DLmw",
    "Bc",
    "Bcm",
    "Bi",
    "Bim",
    "D1m",
    "DLm",
    "L1m",
    "LLm",
    "Bm",
    "CEst"
  ],
  "COUNTER_LIST_CALLS_LINE_NAME": "calls",
  "COUNTER_LIST_NON_CALLGRIND_LINE_NAMES": [
    "calls",
    "callers",
    "callees"
  ],
  "DARK_MODE_ATTRIBUTE_NAME": "data-dark-mode-",
  "DARK_MODE_DISABLED_VALUE": "disabled",
  "DARK_MODE_ENABLED_DEFAULT": true,
  "DARK_MODE_ENABLED_VALUE": "enabled",
  "DARK_MODE_FRAME_QUERY_KEY_NAME": "dark-mode",
  "DARK_MODE_TOGGLE_QUERY_KEY_NAME": "toggle-dark",
  "DATABASE_CELL_SEPARATOR_TEXT": ", ",
  "DATABASE_COUNTER_LIST_DEFAULT_SHOWN_NAMES": [
    "CEst",
    "calls",
    "callers"
  ],
  "DATABASE_DOWNLOAD_FILE_NAME_SUFFIX": "_database.svg",
  "DATABASE_PAGE_DIR_NAME": "database",
  "DATABASE_TIME_SUFFIX_SECONDS": {
    "ns": 1e-09,
    "usecs": 1e-06
  },
  "DATABASE_TOP_FUNCTION_ROWS": 50,
  "DATABASE_VIEW_KEY": "database",
  "DEFAULT_FLAGS": [
    "-D",
    "CMAKE_C_FLAGS=-Os"
  ],
  "DERIVED_COUNTER_TERMS": {
    "Bm": {
      "Bcm": 1,
      "Bim": 1
    },
    "CEst": {
      "D1mr": 10,
      "D1mw": 10,
      "DLmr": 100,
      "DLmw": 100,
      "I1mr": 10,
      "ILmr": 100,
      "Ir": 1
    },
    "D1m": {
      "D1mr": 1,
      "D1mw": 1
    },
    "DLm": {
      "DLmr": 1,
      "DLmw": 1
    },
    "L1m": {
      "D1mr": 1,
      "D1mw": 1,
      "I1mr": 1
    },
    "LLm": {
      "DLmr": 1,
      "DLmw": 1,
      "ILmr": 1
    }
  },
  "DIFF_EXTRACTED_ROOT_DISPLAY_NAME": "$tmp",
  "DRAG_DIRECTION_THRESHOLD_PX": 5,
  "FLAME_GRAPH_ADDRESS_FRAME_NAME_FORMAT": "%s+%#x",
  "FLAME_GRAPH_APP_DIR_NAME": "flame-graph-app",
  "FLAME_GRAPH_APP_NAME_PATTERNS": {
    "font": "url\\(\"\\./([^\"]+\\.woff2)\"\\)",
    "script": "<script src=\"([^\"]+)\"",
    "stylesheet": "<link rel=\"stylesheet\" href=\"([^\"]+)\""
  },
  "FLAME_GRAPH_COLOR_SCHEME_KEY_NAME": "speedscope-color-scheme",
  "FLAME_GRAPH_EXPORTER_NAME": "tests/perf2html/scripts/trace_to_speedscope.py",
  "FLAME_GRAPH_FILE_FORMAT_CLOSE_EVENT_TYPE": "C",
  "FLAME_GRAPH_FILE_FORMAT_OPEN_EVENT_TYPE": "O",
  "FLAME_GRAPH_FILE_FORMAT_PROFILE_TYPE": "evented",
  "FLAME_GRAPH_FILE_FORMAT_PROFILE_UNIT": "nanoseconds",
  "FLAME_GRAPH_FILE_FORMAT_SCHEMA_URL": "https://www.speedscope.app/file-format-schema.json",
  "FLAME_GRAPH_LOCAL_PROFILE_PATH": "profile",
  "FLAME_GRAPH_LOCAL_PROFILE_URL_PREFIX": "file:///",
  "FLAME_GRAPH_MAX_RECORDED_CALLS": 200,
  "FLAME_GRAPH_PROFILE_DIR_NAME": "profiles",
  "FLAME_GRAPH_PROFILE_GLOBAL_NAME": "report_flame_graph_profiles_",
  "FLAME_GRAPH_PROFILE_NAME_FORMAT": "%s (loops=%s)",
  "FLAME_GRAPH_STARTUP_POLL_DELAY_MS": 50,
  "FLAME_GRAPH_STARTUP_POLL_MAX_ATTEMPTS": 200,
  "FLAME_GRAPH_TRACE_PROFILE_NAME_FORMAT": "rdtsc trace (-finstrument-functions), %s calls, events %s..%s of %s",
  "FLAME_GRAPH_VIEW_ENTRY": [
    "flame-graph",
    "flame-graph/index.html"
  ],
  "HEAT_MAP_COUNTER_DESCRIPTION_STRING_ID_PREFIX": "str_counter_",
  "HEAT_MAP_COUNTER_LIST_DEFAULT_SHOWN_NAMES": [
    "Bm"
  ],
  "HEAT_MAP_MINIMAP_VIEWPORT_BOX_SMALLEST_PX": 8,
  "HEAT_MAP_MODEL_DIR_NAME": "data",
  "HEAT_MAP_MODEL_GLOBAL_NAME": "report_heat_map_models_",
  "HEAT_MAP_SCALE_DEFAULT_VALUE": "log",
  "HEAT_MAP_SORT_DEFAULT_MODE": "heat",
  "HEAT_MAP_SOURCE_TAB_SIZE_CHARS": 4,
  "HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_LEAST_SHARE": 0.01,
  "HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_MAX_COUNT": 10,
  "HEAT_MAP_SOURCE_VIEW_WIDTH_CHARS": 80,
  "HEAT_MAP_TREE_ALWAYS_LISTED_DIRS": [
    "lib",
    "include",
    "src",
    "tests/perf"
  ],
  "HEAT_MAP_TREE_BRANCH_LAST_TEXT": "┗━",
  "HEAT_MAP_TREE_BRANCH_MIDDLE_TEXT": "┣━",
  "HEAT_MAP_TREE_BRANCH_PASS_TEXT": "┃ ",
  "HEAT_MAP_TREE_CLOSED_TEXT": "⊞",
  "HEAT_MAP_TREE_FILE_TEXT": "━",
  "HEAT_MAP_TREE_OPEN_TEXT": "┳",
  "HEAT_MAP_VIEW_ENTRY": [
    "heat-map",
    "heat-map/index.html"
  ],
  "LOAD_LOG_INPUT_EVENT_NAMES": {
    "click": "click",
    "key": "keydown"
  },
  "LOAD_LOG_MESSAGE_NAME": "load_log_entry",
  "LOAD_LOG_NAVIGATION_CAUSE_NAME": "navigation",
  "LOG_FAILURE_TAIL_LINES": 40,
  "MENU_DIGIT_KEY_COUNT": 10,
  "MENU_ENTRY_NEEDS": {
    "counters": [
      "counter_list"
    ],
    "str_menu_file": [
      "test"
    ],
    "str_menu_function": [
      "test"
    ],
    "str_view_call_graph": [
      "test",
      "view_page"
    ],
    "str_view_database": [
      "test",
      "view_page"
    ],
    "str_view_flame_graph": [
      "test",
      "view_page"
    ]
  },
  "MENU_ENTRY_VIEW_KEYS": {
    "call_graph_sort": [
      "call-graph"
    ],
    "heat_scale": [
      "call-graph",
      "database",
      "heat-map"
    ],
    "heat_sort": [
      "heat-map"
    ]
  },
  "MENU_FLASH_DURATION_MS": 500,
  "MENU_LOGO_REPOSITORY_URL": "https://github.com/whatchamacallem/perf2html",
  "MENU_PULLDOWN_KEY_NAMES": {
    "close": "Escape",
    "erase": "Backspace",
    "next": "ArrowDown",
    "previous": "ArrowUp",
    "select": "Enter"
  },
  "MENU_PULLDOWN_LINE_NUMBER_PATTERN": "^(.*):([0-9]+)$",
  "MENU_PULLDOWN_OPENING_KEY_PATTERN": "^[a-zA-Z]$",
  "MENU_PULLDOWN_SKIPPED_KEY_NAMES": [
    " "
  ],
  "MENU_PULLDOWN_SMALL_ENTRY_MAX_COUNT": 3,
  "MENU_SCALE_KEY_STEPS": {
    "+": 1,
    "-": -1,
    "=": 1
  },
  "NUMBER_FRACTION_DIGITS": 2,
  "NUMBER_LARGEST_PRINTED_MULTIPLE_TIMES": 999.99,
  "NUMBER_MULTIPLE_SUFFIX_TEXT": "x",
  "OVERVIEW_PAGE_PATH": "index.html",
  "PACKAGE_INSTALL_COMMAND": "sudo apt-get install -y",
  "PERF_TOOL_TIME_LABEL": "Time",
  "PROFILE_PINNED_CPU": 3,
  "PROFILE_SKIPPED_FUNCTION_PATTERN": "0x*",
  "PROFILE_START_FUNCTION_NAME": "main",
  "PROFILE_START_FUNCTION_UNRECORDED_CALLS": 1,
  "PROFILE_STOP_FUNCTION_NAME": "exit",
  "PUBLISH_BRANCH_NAME": "gh-pages",
  "PUBLISH_COMMIT_MESSAGE_FORMAT": "report %s checksum=%s",
  "PUBLISH_JEKYLL_DISABLE_FILE_MODE": 100644,
  "PUBLISH_JEKYLL_DISABLE_FILE_NAME": ".nojekyll",
  "PUBLISH_REMOTE_NAME": "origin",
  "RANKING_COUNTER_NAME": "CEst",
  "README_HTML_BUILD_PATH": "build/README.html",
  "README_HTML_NAME": "README.html",
  "README_MARKDOWN_NAME": "README.md",
  "README_PAGE_BODY_MARKER": "__README_BODY__",
  "README_PAGE_CONVERTER_EXTENSION_ARGUMENTS": [
    "-e",
    "table"
  ],
  "README_PAGE_HEADING_ANCHOR_DROPPED_PATTERN": "[^\\w\\- ]",
  "README_PAGE_HEADING_PATTERN": "(?s)<h([1-6])>(.*?)</h\\1>",
  "README_PAGE_HEADING_TEXT_DROPPED_PATTERN": "<[^>]*>|&\\w+;",
  "README_PAGE_INPUTS_RECORD_SUFFIX": ".inputs",
  "README_PAGE_ROOT_VALUES_MARKER": "__ROOT_VALUES__",
  "README_PAGE_SCRIPT_NAME": "build_readme_page.py",
  "README_PAGE_STAGED_FILE_SUFFIX": ".part",
  "REGULAR_REPORT_VIEW_KEYS": [
    "call-graph",
    "flame-graph"
  ],
  "REPORT_ARTIFACTS_DIR_FORMAT": "%s/%s",
  "REPORT_BASELINE_DIR_NAME": "perf2html_baseline_report",
  "REPORT_DIFF_DIR_NAME": "perf2html_diff_report",
  "REPORT_MANIFEST_CHECKSUM_LABEL": "checksum",
  "REPORT_MANIFEST_EXECUTABLE_LABEL": "executable",
  "REPORT_MANIFEST_VERSION_DIFF": "curl/perf2html_diff.sh v0",
  "REPORT_MANIFEST_VERSION_FULL": "curl/perf2html.sh v0",
  "REPORT_MANIFEST_VERSION_LABEL": "manifest",
  "REPORT_MODIFIED_DIR_NAME": "perf2html_modified_report",
  "REPORT_RAW_ARCHIVE_SUFFIX": ".txz",
  "REPORT_SCRIPTS_DIR_NAME": "scripts",
  "REPORT_SOURCES_DIR_NAME": "sources",
  "RESOURCE_FAILURE_TEXT": "resource failed: ",
  "RESOURCE_TAG_NAMES": [
    "LINK",
    "SCRIPT",
    "IMG"
  ],
  "SCREENSHOT_GOLD_DIFFERENCE_EXIT_CODE": 3,
  "SCREENSHOT_LABEL_QUERY_KEY_NAME": "screenshot",
  "SCREENSHOT_LABEL_QUERY_VALUE": "1",
  "SCREENSHOT_MENU_KEY_NUMBER": "screenshot-menu",
  "SETTINGS_DEBUG_ENABLED": false,
  "SETTINGS_DEBUG_HASH_KEY_NAME": "setting-values",
  "SETTINGS_DEBUG_JSON_INDENT_CHARS": 2,
  "SETTINGS_DEBUG_JSON_MAX_LENGTH_CHARS": 79,
  "SETTINGS_DEBUG_JSON_SPACING_PATTERN": "(\"(?:[^\\\\\"]|\\\\.)*\")|[:,]",
  "SETTINGS_DEBUG_QUERY_KEY_NAME": "debug",
  "SETTINGS_DEBUG_QUERY_VALUES": {
    "disabled": "0",
    "enabled": "1"
  },
  "SETTINGS_HELD_SCRIPT_TEMPLATE_ID": "page-held-script-",
  "SETTINGS_LOAD_LOG_HISTORY_DEFAULT_LINES": 0,
  "SETTINGS_LOAD_LOG_HISTORY_ENTRY_NAME": "history",
  "SETTINGS_LOAD_LOG_HISTORY_LINE_CHOICES": [
    0,
    10,
    20,
    50,
    100
  ],
  "SETTINGS_LOAD_LOG_HISTORY_MAX_LINES": 100,
  "SETTINGS_RELAY_MESSAGE_NAME": "settings_relay",
  "SETTINGS_REQUEST_MESSAGE_NAME": "settings_request",
  "SETTINGS_VIEW_ENTRY": [
    "settings",
    "settings/index.html"
  ],
  "SIGNAL_EXIT_CODE_BASE": 128,
  "STORAGE_KEY_CALL_GRAPH_SORT": "call_graph.sort",
  "STORAGE_KEY_DATABASE_COUNTER_LIST": "database.counter_list",
  "STORAGE_KEY_DATABASE_FUNCTION_ROWS": "database.function_rows",
  "STORAGE_KEY_HEATMAP_COUNTER_LIST": "heatmap.counter_list",
  "STORAGE_KEY_HEATMAP_SCALE": "heatmap.scale",
  "STORAGE_KEY_HEATMAP_SORT": "heatmap.sort",
  "STORAGE_KEY_LOG_DISPLAY_LENGTH": "log.display_length",
  "STORAGE_KEY_VIEW_DARK_MODE": "view.dark_mode",
  "STORAGE_KEY_VIEW_SCALE": "view.scale",
  "STORAGE_OWNED_KEYS": [
    "speedscope-color-scheme",
    "call_graph.sort",
    "database.counter_list",
    "database.function_rows",
    "heatmap.counter_list",
    "heatmap.scale",
    "heatmap.sort",
    "log.display_length",
    "view.dark_mode",
    "view.scale"
  ],
  "STORAGE_VERSION": "perf2html v0",
  "STORAGE_VERSION_KEY": "perf2html.version",
  "STYLE_COLOR_DARK_MODE": {
    "#000000": [
      "dark-mode-screenshot-bg-"
    ],
    "#0e171e": [
      "dark-mode-page-bg-",
      "dark-mode-page-emphasis-fg-"
    ],
    "#20354a": [
      "dark-mode-panel-bg-",
      "dark-mode-status-bar-bg-"
    ],
    "#295987": [
      "dark-mode-menu-normal-bg-",
      "dark-mode-menu-focus-fg-"
    ],
    "#9fd9ff": [
      "dark-mode-page-fg-",
      "dark-mode-page-emphasis-bg-"
    ],
    "#D2691E": [
      "dark-mode-status-bar-fg-"
    ],
    "#FFFFFF": [
      "dark-mode-screenshot-fg-"
    ],
    "#effdff": [
      "dark-mode-menu-normal-fg-",
      "dark-mode-menu-normal-outline-",
      "dark-mode-menu-focus-bg-"
    ]
  },
  "STYLE_COLOR_DARK_MODE_ROLE_PREFIX": "dark-mode-",
  "STYLE_COLOR_LIGHT_MODE": {
    "#101010": [
      "light-mode-menu-focus-bg-",
      "light-mode-menu-normal-fg-",
      "light-mode-menu-normal-outline-",
      "light-mode-page-emphasis-bg-",
      "light-mode-page-fg-",
      "light-mode-screenshot-bg-"
    ],
    "#10AAA9": [
      "light-mode-status-bar-bg-",
      "light-mode-table-hover-outline-"
    ],
    "#AAAAA9": [
      "light-mode-menu-normal-bg-"
    ],
    "#FCFCFA": [
      "light-mode-menu-focus-fg-",
      "light-mode-page-emphasis-fg-",
      "light-mode-page-bg-",
      "light-mode-screenshot-fg-",
      "light-mode-status-bar-fg-"
    ]
  },
  "STYLE_COLOR_LIGHT_MODE_ROLE_PREFIX": "light-mode-",
  "STYLE_DESIGN_COORDINATES_WIDTH_PX": 1920,
  "STYLE_DESIGN_FONT_CHARACTER_WIDTH_SHARE": 0.6,
  "STYLE_DESIGN_FONT_FIT_PROPERTY": "--design-font-fit-",
  "STYLE_DESIGN_FONT_FIT_START_MULTIPLE": 1,
  "STYLE_DESIGN_FONT_SIZE_PROPERTY": "--design-font-size-px-",
  "STYLE_DESIGN_FONT_SIZE_PX": 20,
  "STYLE_DESIGN_MINIMUM_WINDOW_WIDTH_PX": 1280,
  "STYLE_DESIGN_SCALE_DEFAULT_MULTIPLE": 1,
  "STYLE_DESIGN_SCALE_DEFAULT_STOP": 6,
  "STYLE_DESIGN_SCALE_LARGEST_MULTIPLE": 2,
  "STYLE_DESIGN_SCALE_SMALLEST_MULTIPLE": 0.5,
  "STYLE_DESIGN_SCALE_STOP_COUNT": 11,
  "STYLE_DESIGN_SCALE_STOP_MULTIPLE_FRACTION_DIGITS": 2,
  "STYLE_DESIGN_VIEWPORT_HEIGHT_PROPERTY": "--design-viewport-height-",
  "STYLE_DESIGN_VIEWPORT_HEIGHT_START_PERCENT": 100,
  "STYLE_HEAT_CELL_ON_BRIGHT_ABOVE_LUMINANCE_SHARE": 0.5,
  "STYLE_HEAT_CELL_ON_BRIGHT_ROLE": "light-mode-page-fg-",
  "STYLE_HEAT_CELL_ON_DARK_ROLE": "light-mode-page-bg-",
  "STYLE_HEAT_COLOR_FULL_SCALE_PERCENT": 100,
  "STYLE_HEAT_COLOR_STOPS": [
    "#3E4A89",
    "#31688E",
    "#26828E",
    "#1F9E89",
    "#35B779",
    "#6DCD59",
    "#B4DE2C",
    "#FDE725",
    "#FFC83B",
    "#FFA22C",
    "#FF7F21",
    "#F06142"
  ],
  "STYLE_HEAT_MAP_SOURCE_LINE_NUMBER_MARKER_WIDTH_CHARS": 2,
  "STYLE_HEAT_MAP_SOURCE_LINE_NUMBER_MARKER_WIDTH_PROPERTY": "--heat-map-source-table-line-number-cell-callee-marker-width-",
  "STYLE_MENU_LOGO_START_SHARE": 0.5,
  "STYLE_PAGE_BACKGROUND_DARK_MODE_ROLE": "dark-mode-page-bg-",
  "STYLE_PAGE_BACKGROUND_EARLY_FILL_ENABLED": true,
  "STYLE_PAGE_BACKGROUND_LIGHT_MODE_ROLE": "light-mode-page-bg-",
  "STYLE_PAGE_FONT_FAMILY": "Monaco, Menlo, \"DejaVu Sans Mono\", \"Liberation Mono\", Consolas, monospace",
  "STYLE_PAGE_FONT_FAMILY_PROPERTY": "--page-font-family-",
  "STYLE_README_PAGE_VALUE_ENTRIES": {
    "readme-page-bg-": "#D8C9A3",
    "readme-page-fg-": "#3A2A14",
    "readme-page-font-family-": "Arial"
  },
  "STYLE_SVG_NAMESPACE_URL": "http://www.w3.org/2000/svg",
  "STYLE_TABLE_COLUMN_EDGE_GRAB_CHARS": 1.5,
  "STYLE_TABLE_FUNCTION_LIST_COLUMN_MAX_CHARS": 48,
  "STYLE_TABLE_FUNCTION_NAME_MAX_CHARS": 20,
  "STYLE_TABLE_LOCATION_COLUMN_MAX_CHARS": 48,
  "STYLE_TEXT_SCROLLBAR_FONT_MULTIPLE": {
    "horizontal": 1,
    "vertical": 1.5
  },
  "STYLE_TEXT_SCROLLBAR_FONT_MULTIPLE_PROPERTY": {
    "horizontal": "--page-text-scrollbar-horizontal-font-multiple-",
    "vertical": "--page-text-scrollbar-vertical-font-multiple-"
  },
  "STYLE_TEXT_SCROLLBAR_THUMB_SHORTEST_CHARS": 4,
  "STYLE_VALUE_ENTRIES": {
    "call-graph-border-width-": "1ch",
    "call-graph-hover-row-z-index-": "1",
    "heat-map-minimap-width-": "110px",
    "heat-map-source-table-line-number-cell-callee-marker-text-": "\"►\"",
    "heat-map-source-ticker-tape-gap-": "1ch",
    "heat-map-tree-node-hover-z-index-": "1",
    "heat-map-tree-node-padding-right-": "1ch",
    "heat-map-tree-node-share-percent-width-": "10ch",
    "heat-map-tree-width-": "40ch",
    "menu-button-padding-inline-": "1ch",
    "menu-pulldown-entry-list-max-height-share-": "0.6",
    "menu-pulldown-entry-list-z-index-": "3",
    "menu-pulldown-entry-padding-inline-": "1ch",
    "menu-status-bar-padding-left-": "1ch",
    "menu-status-bar-padding-right-": "1ch",
    "menu-strip-blank-line-height-": "0.5lh",
    "menu-strip-padding-right-": "1ch",
    "page-body-line-height-": "1.1",
    "page-emphasis-padding-inline-": "1ch",
    "page-inset-block-": "1lh",
    "page-inset-inline-": "2ch",
    "page-line-width-": "0.1em",
    "page-table-cell-padding-inline-": "1ch",
    "page-table-title-tool-tip-z-index-": "2",
    "page-table-title-z-index-": "1",
    "page-text-scrollbar-horizontal-height-": "1lh",
    "page-text-scrollbar-vertical-width-": "1ch",
    "screenshot-z-index-": "3"
  },
  "TABLE_COLUMN_FUNCTION_NAME": "function",
  "TABLE_COLUMN_LINE_NAME": "line",
  "TABLE_COLUMN_LOCATION_NAME": "location",
  "TABLE_COLUMN_SOURCE_NAME": "source",
  "TABLE_DOWNLOAD_URL_PREFIX": "data:image/svg+xml;charset=utf-8,",
  "TABLE_MARKDOWN_COLUMN_NARROWEST_CHARS": 3,
  "TABLE_MARKDOWN_ESCAPE_TEXT": "\\",
  "TABLE_MARKDOWN_PAD_TEXT": " ",
  "TABLE_MARKDOWN_PIPE_TEXT": "|",
  "TABLE_MARKDOWN_RULE_RIGHT_TEXT": ":",
  "TABLE_MARKDOWN_RULE_TEXT": "-",
  "TABLE_RESIZABLE_COLUMN_NAMES": [
    "function",
    "location",
    "source",
    "callers",
    "callees"
  ],
  "TABLE_ROW_COUNT_CHOICES": [
    20,
    50,
    100,
    1000
  ],
  "TEST_LOOPS": 100,
  "TEST_SAMPLES_SIZE": 409600,
  "TEXT_SCROLLBAR_CHEVRON_STEP_CHARS": {
    "horizontal": 6,
    "vertical": 3
  },
  "TEXT_SCROLLBAR_WHEEL_DELTA_PER_NOTCH": 100,
  "TEXT_SCROLLBAR_WHEEL_NOTCH_LINES": 2.5,
  "THEME_TIME_UNIT_ENTRIES": [
    [
      "s",
      1.0
    ],
    [
      "ms",
      0.001
    ],
    [
      "us",
      1e-06
    ],
    [
      "ns",
      1e-09
    ],
    [
      "ps",
      1e-12
    ]
  ],
  "TIMER_ARTIFACTS_ROOT_FORMAT": "%s/timer-artifacts-%s",
  "TIMING_COLUMN_NAMES": [
    "time_per_loop",
    "instructions_per_cycle",
    "loads_per_instruction",
    "branch_miss_ratio",
    "l1d_miss_ratio"
  ],
  "TIMING_COLUMN_STRING_ID_PREFIX": "str_column_",
  "TIMING_COUNTER_RATIOS": [
    [
      "loads_per_instruction",
      "L1-dcache-loads",
      "instructions"
    ]
  ],
  "TIMING_DATA_INDENT_CHARS": 2,
  "TIMING_PERF_STAT_EVENTS": [
    "cycles:u",
    "instructions:u",
    "branches:u",
    "branch-misses:u",
    "L1-dcache-loads:u",
    "L1-dcache-load-misses:u"
  ],
  "TIMING_PERF_STAT_METRICS": [
    [
      "instructions_per_cycle",
      "instructions",
      "insn per cycle",
      1
    ],
    [
      "branch_miss_ratio",
      "branch-misses",
      "of all branches",
      100
    ],
    [
      "l1d_miss_ratio",
      "L1-dcache-load-misses",
      "of all L1-dcache accesses",
      100
    ]
  ],
  "TIMING_PERF_STAT_METRIC_FRACTION_DIGITS": 6,
  "TIMING_PERF_STAT_NUMBER_PATTERN": "[0-9]+(?:\\.[0-9]+)?",
  "TIMING_PERF_STAT_RUNS": 5,
  "TIMING_PERF_STAT_UNCOUNTED_VALUES": [
    "<not counted>",
    "<not supported>"
  ],
  "TIMING_TIME_PER_LOOP_NAME": "time_per_loop",
  "TOOL_INSTALL_COMMANDS": {
    "speedscope": "npm install -g speedscope"
  },
  "TRACE_ADDR2LINE_COMMAND": [
    "addr2line",
    "-f",
    "-C",
    "-e"
  ],
  "TRACE_ADDR2LINE_UNKNOWN_NAME": "??",
  "TRACE_BUILDID_COMMAND": [
    "readelf",
    "-n"
  ],
  "TRACE_BUILDID_KEYWORD": "buildid",
  "TRACE_BUILDID_LABEL": "Build ID",
  "TRACE_BUILD_DIR": "build-instr",
  "TRACE_FUNCTION_EXIT_BIT": 9223372036854775808,
  "TRACE_HEADER_MAGIC": 12379813738877116416,
  "TRACE_HEADER_WORDS": 8,
  "TRACE_LOAD_SEGMENT_COMMAND": [
    "readelf",
    "-lW"
  ],
  "TRACE_LOAD_SEGMENT_KEYWORD": "LOAD",
  "TRACE_MAPS_EXECUTABLE_FLAG": "x",
  "TRACE_OUT_VARIABLE": "PERF_TRACE_OUT",
  "TRACE_RECORD_WORDS": 2,
  "TRACE_SKIP_ALL": 9223372036854775808,
  "TRACE_SKIP_VARIABLE": "PERF_TRACE_SKIP",
  "TREE_OPEN_LEAST_CUMULATIVE_PERCENT": 0.1,
  "VERBOSE": 0,
  "VERBOSE_RAW_LEVEL": 2,
  "VERBOSE_TRACE_LEVEL": 3,
  "WIDGET_KEY_NAMES": {
    "activate": "Enter",
    "click": " ",
    "close": "Escape",
    "down": "ArrowDown",
    "first": "Home",
    "last": "End",
    "left": "ArrowLeft",
    "right": "ArrowRight",
    "up": "ArrowUp"
  }
};
  let applied_values = {};
  // Holds the settings a page opens under, before a framed page's relay.
  let opening_object = written_object;
  let preferences_are_ignored = false;
  let settings_object = null;
  let storage_is_checked = false;

  function deep_freeze(value) {
    if (value === null || typeof value !== "object") return value;
    Object.values(value).forEach(deep_freeze);
    return Object.freeze(value);
  }
  // Reads one setting of the settings given, refusing an unknown one.
  function setting_read(settings_values, setting_name) {
    if (!Object.hasOwn(settings_values, setting_name))
      window.throw_exception_("str_error_internal");
    return settings_values[setting_name];
  }
  // Writes each palette role's color as the root value a stylesheet reads.
  function palette_values_write(settings_values) {
    for (const palette_name of [
      "STYLE_COLOR_LIGHT_MODE",
      "STYLE_COLOR_DARK_MODE",
    ])
      for (const [color, roles] of Object.entries(
        setting_read(settings_values, palette_name),
      ))
        for (const role of roles)
          document.documentElement.style.setProperty("--" + role, color);
  }
  // Writes each root value a stylesheet reads, from the window settings.
  function root_values_write() {
    const root_values = {};
    for (const [name, value] of Object.entries(
      settings_("STYLE_VALUE_ENTRIES"),
    ))
      root_values["--" + name] = value;
    root_values[settings_("STYLE_DESIGN_FONT_FIT_PROPERTY")] = String(
      settings_("STYLE_DESIGN_FONT_FIT_START_MULTIPLE"),
    );
    root_values[settings_("STYLE_DESIGN_FONT_SIZE_PROPERTY")] =
      settings_("STYLE_DESIGN_FONT_SIZE_PX") + "px";
    root_values[settings_("STYLE_DESIGN_VIEWPORT_HEIGHT_PROPERTY")] =
      settings_("STYLE_DESIGN_VIEWPORT_HEIGHT_START_PERCENT") + "vh";
    root_values[
      settings_("STYLE_HEAT_MAP_SOURCE_LINE_NUMBER_MARKER_WIDTH_PROPERTY")
    ] =
      settings_("STYLE_HEAT_MAP_SOURCE_LINE_NUMBER_MARKER_WIDTH_CHARS") + "ch";
    root_values[settings_("STYLE_PAGE_FONT_FAMILY_PROPERTY")] = settings_(
      "STYLE_PAGE_FONT_FAMILY",
    );
    const font_multiples = settings_("STYLE_TEXT_SCROLLBAR_FONT_MULTIPLE");
    for (const [axis_name, property_name] of Object.entries(
      settings_("STYLE_TEXT_SCROLLBAR_FONT_MULTIPLE_PROPERTY"),
    )) {
      if (!Object.hasOwn(font_multiples, axis_name))
        window.throw_exception_("str_error_internal");
      root_values[property_name] = String(font_multiples[axis_name]);
    }
    for (const [name, value] of Object.entries(root_values))
      document.documentElement.style.setProperty(name, value);
    palette_values_write(settings_object);
  }
  // Returns whether settings debugging is on, the top page's query deciding.
  function settings_debug_enabled(written_object) {
    const query_values = written_object.SETTINGS_DEBUG_QUERY_VALUES;
    const query_value = new URLSearchParams(location.search).get(
      written_object.SETTINGS_DEBUG_QUERY_KEY_NAME,
    );
    if (query_value === null) return written_object.SETTINGS_DEBUG_ENABLED;
    if (
      query_value !== query_values.enabled &&
      query_value !== query_values.disabled
    )
      window.throw_exception_(
        "str_error_settings_debug_query_unusable",
        written_object.SETTINGS_DEBUG_QUERY_KEY_NAME,
        query_value,
        query_values.disabled,
        query_values.enabled,
      );
    return query_value === query_values.enabled;
  }
  // Turns the debug query on in place when the top hash applies settings.
  function settings_debug_query_enable(written_object) {
    if (
      settings_applied_part(written_object) === undefined ||
      settings_debug_enabled(written_object)
    )
      return;
    const debug_url = new URL(location.href);
    debug_url.searchParams.set(
      written_object.SETTINGS_DEBUG_QUERY_KEY_NAME,
      written_object.SETTINGS_DEBUG_QUERY_VALUES.enabled,
    );
    history.replaceState(history.state, "", debug_url.href);
  }
  // Returns the hash part applying settings, undefined for none.
  function settings_applied_part(settings_values) {
    const key_prefix =
      setting_read(settings_values, "SETTINGS_DEBUG_HASH_KEY_NAME") + "=";
    return location.hash
      .slice(1)
      .split("&")
      .find((hash_part) => hash_part.startsWith(key_prefix));
  }
  // Returns the settings the top hash applies, an empty object for none.
  function settings_applied_values(written_object) {
    const applied_part = settings_applied_part(written_object);
    if (applied_part === undefined) return {};
    const hash_values = JSON.parse(
      new TextDecoder(undefined, { fatal: true }).decode(
        Uint8Array.fromBase64(
          decodeURIComponent(
            applied_part.slice(applied_part.indexOf("=") + 1),
          ),
        ),
      ),
    );
    if (
      hash_values === null ||
      typeof hash_values !== "object" ||
      Array.isArray(hash_values)
    )
      window.throw_exception_(
        "str_error_settings_values_unusable",
        applied_part,
      );
    for (const setting_name of Object.keys(hash_values)) {
      if (!Object.hasOwn(written_object, setting_name))
        window.throw_exception_("str_error_setting_unknown", setting_name);
    }
    return hash_values;
  }
  // Installs the window settings object, under debug with the hash's applied.
  function settings_install(written_object) {
    if (!is_framed) {
      settings_debug_query_enable(written_object);
      const debug_enabled = settings_debug_enabled(written_object);
      if (debug_enabled) {
        applied_values = settings_applied_values(written_object);
        Object.assign(written_object, applied_values);
      }
      written_object.SETTINGS_DEBUG_ENABLED = debug_enabled;
    }
    settings_object = deep_freeze(written_object);
    root_values_write();
  }
  // Reads one setting of the window settings object, refusing an unknown one.
  function settings_(setting_name) {
    return setting_read(settings_object, setting_name);
  }
  // Reads one setting the page opens under, a framed page's before its relay.
  function settings_opening_(setting_name) {
    return setting_read(opening_object, setting_name);
  }
  function settings_names_() {
    return Object.keys(settings_object);
  }
  // Returns a copy of the settings the top page's hash applied.
  function settings_applied_values_() {
    return { ...applied_values };
  }
  // Loads the scripts a framed page holds, in order, under its settings.
  function held_scripts_load() {
    const held_template = document.getElementById(
      settings_("SETTINGS_HELD_SCRIPT_TEMPLATE_ID"),
    );
    if (!held_template) window.throw_exception_("str_error_internal");
    for (const held_script of held_template.content.querySelectorAll(
      "script",
    )) {
      const loaded_script = document.createElement("script");
      loaded_script.async = false;
      loaded_script.src = held_script.getAttribute("src");
      held_template.before(loaded_script);
    }
  }
  // Relays the window settings object to a framed page asking for it.
  function settings_request_handler(browser_event) {
    const payload = browser_event.data;
    if (
      payload &&
      payload.report_ui ===
        setting_read(opening_object, "SETTINGS_REQUEST_MESSAGE_NAME")
    )
      browser_event.source.postMessage(
        {
          report_ui: setting_read(
            opening_object,
            "SETTINGS_RELAY_MESSAGE_NAME",
          ),
          settings_object,
        },
        "*",
      );
  }
  // Installs the relayed settings object, then loads the held scripts.
  function settings_relay_handler(browser_event) {
    const payload = browser_event.data;
    if (
      browser_event.source !== window.parent ||
      !payload ||
      payload.report_ui !==
        setting_read(opening_object, "SETTINGS_RELAY_MESSAGE_NAME")
    )
      return;
    settings_install(payload.settings_object);
    if (document.readyState !== "loading") held_scripts_load();
    else
      document.addEventListener(
        "DOMContentLoaded",
        window.try_catch_handler_(held_scripts_load),
      );
  }
  function held_scripts_unframed_check() {
    if (document.getElementById(settings_("SETTINGS_HELD_SCRIPT_TEMPLATE_ID")))
      window.throw_exception_("str_error_held_script_unframed");
  }

  // Stores null in every owned key, each preference one the user never set.
  function storage_sweep(owned_keys) {
    for (const storage_key of owned_keys) {
      localStorage.setItem(storage_key, JSON.stringify(null));
    }
  }
  function storage_version_check(settings_values) {
    if (storage_is_checked) return;
    storage_is_checked = true;
    const owned_keys = setting_read(settings_values, "STORAGE_OWNED_KEYS");
    const storage_version = setting_read(settings_values, "STORAGE_VERSION");
    const version_key = setting_read(settings_values, "STORAGE_VERSION_KEY");
    preferences_are_ignored =
      settings_applied_part(settings_values) !== undefined;
    if (preferences_are_ignored) {
      storage_sweep(owned_keys);
      return;
    }
    if (localStorage.getItem(version_key) === storage_version) {
      return;
    }
    storage_sweep(owned_keys);
    localStorage.setItem(version_key, storage_version);
  }
  // Reads a stored preference, null for none or under ignored preferences.
  function stored_value_read(settings_values, storage_key) {
    storage_version_check(settings_values);
    if (preferences_are_ignored) return null;
    return JSON.parse(localStorage.getItem(storage_key));
  }
  const view_storage = {
    preferences_clear() {
      storage_version_check(settings_object);
      storage_sweep(settings_("STORAGE_OWNED_KEYS"));
    },
    value_read(storage_key) {
      return stored_value_read(settings_object, storage_key);
    },
    value_write(storage_key, stored_value) {
      storage_version_check(settings_object);
      if (preferences_are_ignored) return;
      localStorage.setItem(storage_key, JSON.stringify(stored_value));
    },
  };

  // Returns a dark mode query's text as a number, null for none.
  function dark_mode_query_value(settings_values, key_setting_name) {
    const query_value = new URLSearchParams(location.search).get(
      setting_read(settings_values, key_setting_name),
    );
    return query_value === null ? null : Number(query_value);
  }
  // Returns a truthy value when a page opens in dark mode, the one door.
  function dark_mode_opening_enabled(settings_values) {
    if (is_framed)
      return dark_mode_query_value(
        settings_values,
        "DARK_MODE_FRAME_QUERY_KEY_NAME",
      );
    const default_enabled = setting_read(
      settings_values,
      "DARK_MODE_ENABLED_DEFAULT",
    );
    const toggle_value = dark_mode_query_value(
      settings_values,
      "DARK_MODE_TOGGLE_QUERY_KEY_NAME",
    );
    // The query resets the preferences, then toggles on a truthy value.
    if (toggle_value !== null)
      return toggle_value ? !default_enabled : default_enabled;
    const stored_value = stored_value_read(
      settings_values,
      setting_read(settings_values, "STORAGE_KEY_VIEW_DARK_MODE"),
    );
    return stored_value === null ? default_enabled : stored_value;
  }
  function early_fill_enabled(settings_values) {
    return setting_read(
      settings_values,
      "STYLE_PAGE_BACKGROUND_EARLY_FILL_ENABLED",
    );
  }
  // Returns a mode's page background role, refusing one its palette lacks.
  function page_background_role(settings_values, is_enabled) {
    const [role_setting_name, palette_name] = is_enabled
      ? ["STYLE_PAGE_BACKGROUND_DARK_MODE_ROLE", "STYLE_COLOR_DARK_MODE"]
      : ["STYLE_PAGE_BACKGROUND_LIGHT_MODE_ROLE", "STYLE_COLOR_LIGHT_MODE"];
    const role_name = setting_read(settings_values, role_setting_name);
    const palette_roles = Object.values(
      setting_read(settings_values, palette_name),
    ).flat();
    if (!palette_roles.includes(role_name))
      window.throw_exception_(
        "str_error_setting_choice_unknown",
        role_setting_name,
        role_name,
      );
    return role_name;
  }
  // Shows a dark mode on the root, under early fill its page background too.
  function dark_mode_root_show(settings_values, is_enabled) {
    const root_element = document.documentElement;
    root_element.setAttribute(
      setting_read(settings_values, "DARK_MODE_ATTRIBUTE_NAME"),
      setting_read(
        settings_values,
        is_enabled ? "DARK_MODE_ENABLED_VALUE" : "DARK_MODE_DISABLED_VALUE",
      ),
    );
    if (!early_fill_enabled(settings_values)) return;
    root_element.style.background =
      "var(--" + page_background_role(settings_values, is_enabled) + ")";
  }
  // Shows the opening mode and its page background before the body parses.
  function page_early_fill(settings_values) {
    if (!early_fill_enabled(settings_values)) return;
    if (is_framed) palette_values_write(settings_values);
    dark_mode_root_show(
      settings_values,
      dark_mode_opening_enabled(settings_values),
    );
  }

  window.report_dark_mode_ = {
    opening_enabled: () => dark_mode_opening_enabled(settings_object),
    root_show: (is_enabled) =>
      dark_mode_root_show(settings_object, is_enabled),
    toggle_query_value: () =>
      dark_mode_query_value(
        settings_object,
        "DARK_MODE_TOGGLE_QUERY_KEY_NAME",
      ),
  };
  window.report_view_storage_ = view_storage;
  window.settings_ = settings_;
  window.settings_applied_values_ = settings_applied_values_;
  window.settings_names_ = settings_names_;
  window.settings_opening_ = settings_opening_;
  window.addEventListener(
    "message",
    window.try_catch_handler_(settings_request_handler),
  );
  if (is_framed) {
    // Fills under the written settings and those the address applies.
    opening_object = {
      ...written_object,
      ...settings_applied_values(written_object),
    };
    page_early_fill(opening_object);
    window.addEventListener(
      "message",
      window.try_catch_handler_(settings_relay_handler),
    );
    window.parent.postMessage(
      {
        report_ui: setting_read(
          opening_object,
          "SETTINGS_REQUEST_MESSAGE_NAME",
        ),
      },
      "*",
    );
  } else {
    settings_install(written_object);
    page_early_fill(settings_object);
    document.addEventListener(
      "DOMContentLoaded",
      window.try_catch_handler_(held_scripts_unframed_check),
    );
  }
})();
