#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE-MIT.md file.
#
# This comment intentionally blank. No documentation goes here.

usage_show() {
  cat <<'EOF'
test_expected_behavior.sh [debug-flags] [--check-formatting]
    Formats, lints and scans the files scripts/test_whitelist.txt lists,
    runs perf2html_batch.sh over the three reports it cleared, then
    validates and screenshots what it wrote. When screenshots-gold/
    exists, a --regenerate run compares each shot with its same named gold
    shot, naming each difference and writing a compare_ image of it to
    screenshots-diff/, which every run clears and only a difference makes.
    Any fault stops the run where it happened. A difference is no fault:
    the run finishes every stage, then notes it and exits with
    SCREENSHOT_GOLD_DIFFERENCE_EXIT_CODE from settings.sh.
    --check-formatting  Report what would change rather than writing it.

    The debug-flags are the same as the README.md documents.
EOF
}

set -euo pipefail

INVOKED_FROM="$PWD"

. "$(dirname -- "$0")/settings.sh"
. "$(dirname -- "$0")/utility.sh"
. "$(dirname -- "$0")/test_utility.sh"

project_root_check
PERF2HTML_DIR_="$INVOKED_FROM"
_SCRIPT_DIR="$PERF2HTML_DIR_/scripts"
_SCRIPT="$_SCRIPT_DIR/${0##*/}"

_COLUMNS_MAX=79
_CLANG_FORMAT_CONFIG="$PERF2HTML_DIR_/src/.clang-format"
_PRETTIER_CONFIG="$_SCRIPT_DIR/.prettierrc.json"
_PYRIGHT_CONFIG="$_SCRIPT_DIR/pyrightconfig.json"

_PYRIGHT_ALL_CLEAR_LINE='0 errors, 0 warnings, 0 informations'

_SHELL_INDENT=2
_RUFF_CONFIG="$_SCRIPT_DIR/ruff.toml"

_WHITELIST_FILE="$_SCRIPT_DIR/test_whitelist.txt"

_BATCH_SCRIPT_NAME=perf2html_batch.sh
_BUILD_LOCATION_EXECUTABLE_PATH=tests/perf/perf
_BUILD_LOCATION_RELEASE_TREES=build-relwithdebinfo
_BUILD_LOCATION_ROOT_NAME=build
_BUILD_LOCATION_SCRATCH_NAME=test_expected_build_location_scratch
_BUILD_LOCATION_TRACE_TREES=build-instr
_ROWS_FILE_NAME=perf2html.txt
# Chrome for Testing as the puppeteer browsers tool installs it.
_SCREENSHOT_BROWSER_PATH="$HOME/.local/share/chrome-for-testing/chrome"
_SCREENSHOT_BROWSER_PATH+="/linux-157.0.8103.78/chrome-linux64/chrome"
_SCREENSHOT_DIFF_DIR="$PERF2HTML_DIR_/screenshots-diff"
_SCREENSHOT_GOLD_DIR="$PERF2HTML_DIR_/screenshots-gold"
_SCREENSHOT_SCRIPT_NAME=test_screenshot.py
_TEST_LIST_FILE_NAME=test_list.txt
_TIMING_FILE_SUFFIX=.perf-stat.json

_DEFAULT_REPORTS=(
  "$PERF2HTML_DIR_/$REPORT_BASELINE_DIR_NAME"
  "$PERF2HTML_DIR_/$REPORT_MODIFIED_DIR_NAME"
  "$PERF2HTML_DIR_/$REPORT_DIFF_DIR_NAME"
)

tools_resolve() {
  local _missing=() _line _pillow_check
  local _admin="$PERF2HTML_DIR_/$ADMIN_INSTRUCTIONS_FILE_NAME"
  _SHFMT="$(tool_find shfmt)" || _missing+=(shfmt)
  _RUFF="$(tool_find ruff)" || _missing+=(ruff)
  _CLANG_FORMAT="$(tool_find clang-format)" || _missing+=(clang-format)
  _PRETTIER="$(tool_find prettier)" || _missing+=(prettier)
  _PYRIGHT="$(tool_find pyright)" || _missing+=(pyright)
  _SCREENSHOT_BROWSER="$_SCREENSHOT_BROWSER_PATH"
  [ -x "$_SCREENSHOT_BROWSER" ] || _missing+=("$_SCREENSHOT_BROWSER")
  _pillow_check='from importlib.util import find_spec'
  _pillow_check+='; raise SystemExit(not find_spec("PIL"))'
  python3 -c "$_pillow_check" || _missing+=(pillow)
  toolchain_missing_list _missing
  _line="error: ${#_missing[@]} tool(s) missing, so nothing is verified:"
  [ "${#_missing[@]}" = 0 ] || error_exit 127 \
    "$_line ${_missing[*]}, install commands in $_admin"
  readme_converter_resolve
}

subprocess_run() {
  local _exit_code=0
  command_item_print "$*"
  "$@" || _exit_code=$?
  [ "$_exit_code" = 0 ] \
    || error_exit "$_exit_code" "error: exit $_exit_code from: $*"
}

whitelist_expand() {
  local _glob _match _line=0 _found=() _matches=()

  if [ ! -f "$_WHITELIST_FILE" ]; then
    error_exit 1 "error: $_WHITELIST_FILE: not found, so nothing is enforced"
  fi

  while IFS= read -r _glob || [ -n "$_glob" ]; do
    _line=$((_line + 1))
    if [[ -z "$_glob" || "$_glob" == '#'* || "$_glob" == *[[:space:]]* ]]; then
      error_exit 1 "error: $_WHITELIST_FILE:$_line: not one glob: '$_glob'"
    fi

    mapfile -t _matches < <(compgen -G "$PERF2HTML_DIR_/$_glob")
    for _match in "${_matches[@]}"; do
      if [ ! -f "$_match" ]; then
        error_exit 1 \
          "error: $_WHITELIST_FILE:$_line: $_glob matches $_match, not a file"
      fi
    done
    _found+=("${_matches[@]}")
  done <"$_WHITELIST_FILE"

  if [ "${#_found[@]}" = 0 ]; then
    error_exit 1 \
      "error: $_WHITELIST_FILE: matches no file, so nothing is enforced"
  fi

  mapfile -t _WHITELISTED_FILES < <(printf '%s\n' "${_found[@]}" \
    | LC_ALL=C sort -u)
  log_verbose "whitelist: ${#_WHITELISTED_FILES[@]} file(s)"
}

files() {
  local _file _extension

  for _file in "${_WHITELISTED_FILES[@]}"; do
    for _extension in "$@"; do
      if [[ "$_file" == *"$_extension" ]]; then
        printf '%s\n' "$_file"
        break
      fi
    done
  done
}

format_shell() {
  local _files
  mapfile -t _files < <(files .sh)

  heading_print shfmt
  if [ "${#_files[@]}" = 0 ]; then
    log_verbose "shfmt: no files"
    return 0
  fi

  if [ "$_CHECK" = 1 ]; then
    subprocess_run "$_SHFMT" -i "$_SHELL_INDENT" -bn -ci -ln bash -d \
      "${_files[@]}"
  else
    subprocess_run "$_SHFMT" -i "$_SHELL_INDENT" -bn -ci -ln bash -w \
      "${_files[@]}"
  fi
}

format_python() {
  local _files
  mapfile -t _files < <(files .py)

  heading_print ruff
  if [ "${#_files[@]}" = 0 ]; then
    log_verbose "ruff: no files"
    return 0
  fi

  quiet_switch_set ruff
  if [ "$_CHECK" = 1 ]; then
    subprocess_run "$_RUFF" format --config "$_RUFF_CONFIG" \
      "${QUIET_SWITCH[@]}" --diff "${_files[@]}"
  else
    subprocess_run "$_RUFF" format --config "$_RUFF_CONFIG" \
      "${QUIET_SWITCH[@]}" "${_files[@]}"
  fi

  if [ "$_CHECK" = 1 ]; then
    subprocess_run "$_RUFF" check --config "$_RUFF_CONFIG" \
      "${QUIET_SWITCH[@]}" "${_files[@]}"
  else
    subprocess_run "$_RUFF" check --config "$_RUFF_CONFIG" \
      "${QUIET_SWITCH[@]}" --fix "${_files[@]}"
  fi
}

format_c() {
  local _files
  mapfile -t _files < <(files .c .h)

  heading_print clang-format
  if [ "${#_files[@]}" = 0 ]; then
    log_verbose "clang-format: no files"
    return 0
  fi

  if [ "$_CHECK" = 1 ]; then
    subprocess_run "$_CLANG_FORMAT" --style=file:"$_CLANG_FORMAT_CONFIG" \
      --dry-run --Werror "${_files[@]}"
  else
    subprocess_run "$_CLANG_FORMAT" --style=file:"$_CLANG_FORMAT_CONFIG" \
      -i "${_files[@]}"
  fi
}

format_prettier() {
  local _files
  mapfile -t _files < <(files .md .js .css .html)

  heading_print prettier
  if [ "${#_files[@]}" = 0 ]; then
    log_verbose "prettier: no files"
    return 0
  fi

  quiet_switch_set prettier
  if [ "$_CHECK" = 1 ]; then
    subprocess_run "$_PRETTIER" --config "$_PRETTIER_CONFIG" \
      "${QUIET_SWITCH[@]}" --check "${_files[@]}"
  else
    subprocess_run "$_PRETTIER" --config "$_PRETTIER_CONFIG" \
      "${QUIET_SWITCH[@]}" --write "${_files[@]}"
  fi
}

lint_run() {
  local _files
  mapfile -t _files < <(files .py)

  heading_print pyright
  if [ "${#_files[@]}" = 0 ]; then
    log_verbose "pyright: no files"
    return 0
  fi

  if [ "$VERBOSE" -ge 1 ] && [ "$VERBOSE" -lt "$VERBOSE_RAW_LEVEL" ]; then
    pyright_filtered_run "$_PYRIGHT" --project "$_PYRIGHT_CONFIG" \
      "${_files[@]}"
  else
    subprocess_run "$_PYRIGHT" --project "$_PYRIGHT_CONFIG" "${_files[@]}" >&2
  fi
}

pyright_filtered_run() {
  local _statuses=(0 0)
  local _filter=(grep --line-buffered -v -x)
  local _filter_shown="${_filter[*]} '$_PYRIGHT_ALL_CLEAR_LINE'"
  command_item_print "$* | $_filter_shown"
  "$@" | "${_filter[@]}" "$_PYRIGHT_ALL_CLEAR_LINE" \
    || _statuses=("${PIPESTATUS[@]}")
  [ "${_statuses[0]}" = 0 ] || error_exit "${_statuses[0]}" \
    "error: exit ${_statuses[0]} from: $*"
  [ "${_statuses[1]}" -le 1 ] || error_exit "${_statuses[1]}" \
    "error: exit ${_statuses[1]} from: $_filter_shown"
}

long_lines_report() {
  local _over _count _grep_exit=0
  # Counts characters, as a UTF 8 locale makes grep read them.
  _over="$(LC_ALL=C.UTF-8 grep -nE "^.{$((_COLUMNS_MAX + 1))}" \
    "${_WHITELISTED_FILES[@]}")" || _grep_exit=$?
  [ "$_grep_exit" -le 1 ] \
    || error_exit "$_grep_exit" "error: exit $_grep_exit from the columns grep"

  if [ -z "$_over" ]; then
    log_verbose "columns: none over $_COLUMNS_MAX"
    return 0
  fi

  _count="$(echo "$_over" | grep -c '')"
  error_exit 1 "error: $_count line(s) over $_COLUMNS_MAX columns:" "$_over"
}

report_version() {
  head -n 1 "$1/MANIFEST.txt"
}

test_expected_report_check_run() {
  local _path _args _flags=("${VERBOSE_FLAGS[@]}")

  heading_print test_report.py
  for _path in "${_DEFAULT_REPORTS[@]}"; do
    manifest_verify "$_path" "$(basename "$_path")" \
      "$REPORT_MANIFEST_VERSION_FULL" "$REPORT_MANIFEST_VERSION_DIFF"

    _args=("$_path")
    if [ "$(report_version "$_path")" = "$REPORT_MANIFEST_VERSION_DIFF" ]; then
      _args+=(--diff
        "--baseline=$PERF2HTML_DIR_/$REPORT_BASELINE_DIR_NAME"
        "--modified=$PERF2HTML_DIR_/$REPORT_MODIFIED_DIR_NAME")
    fi

    subprocess_run python3 "$_SCRIPT_DIR/test_report.py" "${_flags[@]}" \
      "${_args[@]}"
  done
}

# Refuses a directory holding a file that names the build directory.
test_expected_build_location_unnamed_check() {
  local _directory="$1" _build_directory="$2" _named _exit_code=0
  _named="$(grep -rlF "$_build_directory/" "$_directory")" || _exit_code=$?
  [ "$_exit_code" = 1 ] || error_exit 1 "error: grep exit $_exit_code, \
$_directory names $_build_directory in: $_named"
}

# Checks the trees lie under the invocation point and no output names that.
test_expected_build_location_check() {
  local _name _path _manifest _executable _tree _recorded _archive
  local _trace _build_directory _scratch

  heading_print "build tree location"
  _build_directory="$(realpath -- \
    "$PERF2HTML_BUILD_ROOT/$_BUILD_LOCATION_ROOT_NAME")"
  _scratch="$_build_directory/$_BUILD_LOCATION_SCRATCH_NAME"

  for _name in "$REPORT_BASELINE_DIR_NAME" "$REPORT_MODIFIED_DIR_NAME"; do
    _path="$PERF2HTML_DIR_/$_name"
    _manifest="$_path/MANIFEST.txt"
    _executable="$(header_row "$_manifest" executable)"
    case "$_executable" in
      "$_BUILD_LOCATION_RELEASE_TREES"/*/"$_BUILD_LOCATION_EXECUTABLE_PATH") ;;
      *) error_exit 1 "error: $_manifest names the executable $_executable" ;;
    esac
    [ -f "$_build_directory/$_executable" ] || error_exit 1 \
      "error: $_name has no executable at $_build_directory/$_executable"

    _tree="${_executable#"$_BUILD_LOCATION_RELEASE_TREES"/}"
    _tree="${_tree%%/*}"
    _trace="$_build_directory/$_BUILD_LOCATION_TRACE_TREES/$_tree"
    _trace+="/$_BUILD_LOCATION_EXECUTABLE_PATH"
    [ -f "$_trace" ] || error_exit 1 \
      "error: $_name has no traced executable at $_trace"

    _recorded="$(header_row "$_manifest" recorded)"
    raw_data_archive_path _archive "$_path" "${_recorded%% *}"
    rm -rf "$_scratch"
    mkdir "$_scratch"
    tar xJf "$_archive" -C "$_scratch"
    test_expected_build_location_unnamed_check "$_scratch" "$_build_directory"
    rm -r "$_scratch"
  done

  for _path in "${_DEFAULT_REPORTS[@]}"; do
    test_expected_build_location_unnamed_check "$_path" "$_build_directory"
  done
  log_verbose "build trees: under $_build_directory, named by no output"
}

test_source_scan_run() {
  heading_print test_source_scan.py
  subprocess_run python3 "$_SCRIPT_DIR/test_source_scan.py" \
    "${VERBOSE_FLAGS[@]}" \
    "${_WHITELISTED_FILES[@]}"
}

batch_run() {
  local _flags=("${VERBOSE_FLAGS[@]}") _shown _exit_code=0

  if [ "$_REGENERATE" = 1 ]; then _flags+=(--regenerate); fi

  if [ "$_KEEP_ARTIFACTS" = 1 ]; then _flags+=(--keep-artifacts); fi

  _shown="$_BATCH_SCRIPT_NAME ${_flags[*]} --target-dir=$PERF2HTML_DIR_"

  log_verbose "$_shown"

  "$PERF2HTML_DIR_/$_BATCH_SCRIPT_NAME" "${_flags[@]}" \
    "--target-dir=$PERF2HTML_DIR_" || _exit_code=$?
  [ "$_exit_code" = 0 ] \
    || error_exit "$_exit_code" "error: exit $_exit_code from: $_shown"
}

# Sets `_SCREENSHOT_COMMAND` to the screenshot script command for one report.
screenshot_command_set() {
  local _name="$1" _path _prefix _args
  shift
  _path="$PERF2HTML_DIR_/$_name"

  _prefix="${_name#perf2html_}"
  _prefix="${_prefix%_report}_"

  _args=("$_path" "$_prefix")
  if [ "$(report_version "$_path")" = "$REPORT_MANIFEST_VERSION_DIFF" ]; then
    _args+=(--diff)
  fi

  _SCREENSHOT_COMMAND=(python3 "$_SCRIPT_DIR/$_SCREENSHOT_SCRIPT_NAME"
    "${VERBOSE_FLAGS[@]}" "--build-root=$PERF2HTML_BUILD_ROOT"
    "${_args[@]}" "$@")
}

screenshots_run() {
  local _name _exit_code _failure_code=0 _exit_codes=()

  heading_print "$_SCREENSHOT_SCRIPT_NAME"
  for _name in "$REPORT_MODIFIED_DIR_NAME" "$REPORT_DIFF_DIR_NAME"; do
    screenshot_command_set "$_name" "--browser=$_SCREENSHOT_BROWSER"
    # The verbose lines go to the Markdown log on stderr, as blocks of text.
    subprocess_run "${_SCREENSHOT_COMMAND[@]}" >&2
    VERBOSE_BLOCK_PRINTED=loose
  done

  # A measuring run changes the recorded values the golden screenshots show.
  if [ "$_REGENERATE" != 1 ]; then
    log_verbose "screenshots: measured, not compared without --regenerate"
    return 0
  fi

  # The golden screenshots are a developer's own and optional.
  if [ -d "$_SCREENSHOT_GOLD_DIR" ]; then
    # Both reports are compared before either exit code fails the run.
    for _name in "$REPORT_MODIFIED_DIR_NAME" "$REPORT_DIFF_DIR_NAME"; do
      screenshot_command_set "$_name" --compare-only \
        --compare-gold "$_SCREENSHOT_GOLD_DIR" \
        --compare-out "$_SCREENSHOT_DIFF_DIR"
      _exit_code=0
      command_item_print "${_SCREENSHOT_COMMAND[*]}"
      "${_SCREENSHOT_COMMAND[@]}" || _exit_code=$?
      _exit_codes+=("$_name=$_exit_code")
      if [ "$_failure_code" = 0 ]; then
        _failure_code="$_exit_code"
      fi
    done
    [ "$_failure_code" = 0 ] || error_exit "$_failure_code" \
      "error: $_SCREENSHOT_SCRIPT_NAME exit codes: ${_exit_codes[*]}"
  else
    log_verbose "screenshots: no $_SCREENSHOT_GOLD_DIR, not compared"
  fi
}

regenerate_refuse() {
  error_exit 2 "error: --regenerate cannot reuse the recordings: $1"
}

header_row() {
  sed -n "s/^$2=//p" "$1" | head -1
}

regenerate_check() {
  [ "$_REGENERATE" = 1 ] || return 0

  local _artifacts="$PERF2HTML_DIR_/$ARTIFACTS_NAME"
  if [ ! -d "$_artifacts" ]; then
    regenerate_refuse "no recordings at $_artifacts"
  fi

  local _name _report_artifacts _rows _recorded _binary _newest _test_list
  local _test _timing _tests=() _recorded_times=()
  for _name in "$REPORT_BASELINE_DIR_NAME" "$REPORT_MODIFIED_DIR_NAME"; do
    _report_artifacts="$_artifacts/$_name"
    if [ ! -d "$_report_artifacts" ]; then
      regenerate_refuse "$_name has no recordings at $_report_artifacts"
    fi
    _rows="$_report_artifacts/$_ROWS_FILE_NAME"
    if [ ! -f "$_rows" ]; then
      regenerate_refuse "$_name has no recordings, $_rows is missing"
    fi

    _recorded="$(header_row "$_rows" recorded)"
    _recorded="${_recorded%% *}"
    if [ -z "$_recorded" ]; then
      regenerate_refuse "$_name records no recorded= row in $_rows"
    fi

    _test_list="$_report_artifacts/$_TEST_LIST_FILE_NAME"
    if [ ! -s "$_test_list" ]; then
      regenerate_refuse "$_name lists no test in $_test_list"
    fi
    mapfile -t _tests <"$_test_list"
    _newest="$_report_artifacts/${_tests[0]}$_TIMING_FILE_SUFFIX"
    for _test in "${_tests[@]}"; do
      _timing="$_report_artifacts/$_test$_TIMING_FILE_SUFFIX"
      if [ ! -f "$_timing" ]; then
        regenerate_refuse "$_name has no recording $_timing"
      fi
      if [ "$_timing" -nt "$_newest" ]; then
        _newest="$_timing"
      fi
    done
    _recorded_times+=("$_recorded")

    _binary="$(header_row "$_rows" executable)"
    if [ -z "$_binary" ]; then
      regenerate_refuse "$_name records no executable= row in $_rows"
    fi
    _binary="$PERF2HTML_BUILD_ROOT/$_BUILD_LOCATION_ROOT_NAME/${_binary%% *}"
    if [ ! -f "$_binary" ]; then
      regenerate_refuse "$_name has no executable at $_binary"
    fi

    if [ "$_binary" -nt "$_newest" ]; then
      regenerate_refuse "$_name: perf was re-linked after its recordings"
    fi
  done

  log_verbose "regenerate: reusing the runs recorded at" \
    "${_recorded_times[0]} and ${_recorded_times[1]}"
}

clear_overwritten_folders() {
  local _path _archive

  for _path in "${_DEFAULT_REPORTS[@]}"; do
    rm -rf "$_path" \
      || error_exit 1 "error: could not remove the previous report: $_path"

    _archive="$_path$REPORT_RAW_ARCHIVE_SUFFIX"
    rm -f "$_archive" || error_exit 1 \
      "error: could not remove the previous archive: $_archive"
  done
  log_verbose "cleared ${#_DEFAULT_REPORTS[@]} report(s)"

  rm -rf "$_SCREENSHOT_DIFF_DIR" || error_exit 1 \
    "error: could not remove the previous shot diffs: $_SCREENSHOT_DIFF_DIR"
}

args_parse() {
  _CHECK=0
  _KEEP_ARTIFACTS=0
  _REGENERATE=0

  while [ $# -gt 0 ]; do
    case "$1" in
      -h | --help)
        usage_show
        exit 0
        ;;
      --check-formatting)
        _CHECK=1
        shift
        ;;
      --keep-artifacts)
        _KEEP_ARTIFACTS=1
        shift
        ;;
      --regenerate)
        _REGENERATE=1
        shift
        ;;
      --verbose)
        VERBOSE=$((VERBOSE + 1))
        shift
        ;;
      *)
        error_exit 2 "error: unknown option: $1"
        ;;
    esac
  done
}

main() {
  args_parse "$@"
  verbose_begin
  title_print "$_SCRIPT" "$@"
  whitelist_expand
  regenerate_check
  tools_resolve
  clear_overwritten_folders
  format_shell
  format_python
  format_c
  format_prettier
  long_lines_report
  test_source_scan_run
  lint_run
  batch_run
  test_expected_report_check_run
  test_expected_build_location_check
  screenshots_run
  # Only a shot differing from its gold twin makes the shot diffs directory.
  if [ -d "$_SCREENSHOT_DIFF_DIR" ]; then
    screenshot_gold_notice "$_SCREENSHOT_GOLD_DIR" "$_SCREENSHOT_DIFF_DIR"
    exit "$SCREENSHOT_GOLD_DIFFERENCE_EXIT_CODE"
  fi
}

main "$@"
