#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE-MIT.md file.
#
# This comment intentionally blank. No documentation goes here.

usage_show() {
  cat <<'EOF'
publish.sh [--help] report
    Makes a report directory again through perf2html.sh --regenerate --txz or
    perf2html_diff.sh --txz, refuses an archive unlike that report, then force
    pushes the report to the gh-pages branch of origin as one commit with no
    parent, replacing that branch. Then purges that commit and every other
    unreachable object from this repository. No other branch, the index and
    the working tree are left alone. A report name not starting with / or ~/
    sits under $PWD. --help is the only option.
EOF
}

set -euo pipefail

INVOKED_FROM="$PWD"
cd -- "$(dirname -- "$0")/.."

. ./scripts/settings.sh
. ./scripts/utility.sh

args_parse() {
  case "$#:${1-}" in
    1:-h | 1:--help)
      usage_show
      exit 0
      ;;
    ?:-*) error_exit 2 "error: unknown option: $1" ;;
    1:*) ;;
    *) error_exit 2 "error: publish.sh takes one report, got $#: $*" ;;
  esac
  _REPORT_DIR="$(absolute_path "$1")"
  manifest_verify "$_REPORT_DIR" published "$REPORT_MANIFEST_VERSION_FULL" \
    "$REPORT_MANIFEST_VERSION_DIFF"
}

# Writes the report as a commit with no parent, through a temporary index.
commit_write() {
  local _empty_file _message _checksum
  _checksum="$(manifest_value "$_REPORT_DIR/MANIFEST.txt" \
    "$REPORT_MANIFEST_CHECKSUM_LABEL")"
  printf -v _message "$PUBLISH_COMMIT_MESSAGE_FORMAT" \
    "${_REPORT_DIR##*/}" "$_checksum"
  # The force keeps an ignore pattern from dropping a file of the report.
  GIT_WORK_TREE="$_REPORT_DIR" git add -A -f
  # A report's checksum covers its files, so this enters the index alone.
  _empty_file="$(git hash-object -w --stdin </dev/null)"
  git update-index --add --cacheinfo "$PUBLISH_JEKYLL_DISABLE_FILE_MODE" \
    "$_empty_file" "$PUBLISH_JEKYLL_DISABLE_FILE_NAME"
  _COMMIT_OBJECT="$(git commit-tree "$(git write-tree)" -m "$_message")"
}

# Refuses an archive unlike its report, by a file's name or by a file's bytes.
report_archive_check() {
  local _report_archive="$_REPORT_DIR$REPORT_RAW_ARCHIVE_SUFFIX"
  local _report_parent _report_name
  _report_parent="$(dirname -- "$_REPORT_DIR")"
  _report_name="$(basename -- "$_REPORT_DIR")"
  diff <(tar -tJf "$_report_archive" | sed 's:/$::' | LC_ALL=C sort) \
    <(cd -- "$_report_parent" && find "$_report_name" | LC_ALL=C sort) \
    || error_exit 1 "error: $_report_archive and its report name other files"
  (cd -- "$_report_parent" && tar -xJf "$_report_archive" \
    --to-command='cmp - "$TAR_FILENAME"') \
    || error_exit 1 "error: $_report_archive and its report hold other bytes"
}

# Makes the report again through the script making its kind, always `--txz`.
report_make() {
  local _manifest_version
  _manifest_version="$(head -1 "$_REPORT_DIR/MANIFEST.txt")"
  if [ "$_manifest_version" = "$REPORT_MANIFEST_VERSION_DIFF" ]; then
    ./perf2html_diff.sh --txz "--target-dir=$(dirname -- "$_REPORT_DIR")" \
      "$REPORT_BASELINE_DIR_NAME" "$REPORT_MODIFIED_DIR_NAME" "$_REPORT_DIR"
  else
    ./perf2html.sh --regenerate --txz "--report=$_REPORT_DIR"
  fi >/dev/null
}

args_parse "$@"

report_make
report_archive_check

_INDEX_FILE="$(mktemp -u)"
trap 'rm -f -- "$_INDEX_FILE"' EXIT

export GIT_INDEX_FILE="$_INDEX_FILE"
commit_write
git push -q --force "$PUBLISH_REMOTE_NAME" \
  "$_COMMIT_OBJECT:refs/heads/$PUBLISH_BRANCH_NAME"
unset GIT_INDEX_FILE

git update-ref -d "refs/remotes/$PUBLISH_REMOTE_NAME/$PUBLISH_BRANCH_NAME"
git prune --expire=now
