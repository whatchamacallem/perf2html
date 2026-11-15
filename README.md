# perf2html README.md

## Introduction

`perf2html` is a collection of scripts that profile `perf` and generate html
reports about the results.

The latest version and an example report can be found here:

- [Repository](https://github.com/whatchamacallem/perf2html)
- [Example Report](https://whatchamacallem.github.io/perf2html/)

## Table Of Contents

- [Using A Report](#using-a-report)
- [Menu And Keyboard](#menu-and-keyboard)
- [Running The Generator Scripts](#running-the-generator-scripts)
- [Callgrind Counters](#callgrind-counters)
- [Reading A Diff Report](#reading-a-diff-report)
- [Flame Graph (speedscope)](#flame-graph-speedscope)

## Using A Report

The main menu can be operated with the keyboard using the numbers each button
is labelled with. Tab also moves focus forward through interactive elements
(links, buttons, inputs), and Shift+Tab moves backward. This is the primary
navigation system for keyboard-only users, including screen reader users and
switch device users. Enter or Space activates the focused element, and arrow
keys control widgets. Use `+`/`=` or `-` to zoom instead of the browser's
built-in zoom controls.

The HTML will open straight from disk, with no server. Start by opening the top
level `index.html` in the report and then bookmarks will work.

The html app is stateless following REST style. This means the navigation URLs
are immutable (so bookmarks work) and the module URLs used by JavaScript on the
back end are also immutable (so no server is needed and perfect caching is
possible).

A report can also be served from an Ubuntu container with:
`python3 -m http.server 8000`.

## Menu And Keyboard

Some of the settings are stored in the browser and may be reset with the reset
button. Pull-down buttons often support searching by typing or pasting text.

### First menu row

The first row of buttons will have the same number on every page. The number
can be used to select them, and some of them support searching within their
pull-downs by typing or pasting text.

- `perf2html`: Opens the project repository.
- `overview`: Opens a catalogue of tests and the manifest.
- `test`: Selects the test shown.
- `file`: Opens a file. Typing file:line opens that line.
- `function`: Opens the file containing a function. Searchable.
- `database`: Opens a page with a database of functions.
- `flame graph`: Open this test's live call trace.
- `call graph`: Opens a page with a call graph and costs.
- `reset`: Restores default preferences.
- `help`: Opens the help page in a new tab.
- `scale`: Scales the whole report, as do `+`, `-` and `=`.
- `dark` / `light`: Toggles between the light and dark themes.

### Status menu row

These settings may be unique to a given page or shared.

- `lines` / `functions`, on the heat map: Toggles between per line and per
  function counters.
- `counters`, on the heat map and the database: Selects the columns shown.
  Dragging moves them.
- `log scale` / `linear scale`, on the heat map, the database and the call
  graph: Toggles heat colors between a log and linear curve.
- `hottest first` / `alphabetical`, on the heat map: Toggles the file tree's
  sort order.
- `cumulative first` / `hottest first` / `alphabetical`, on the call graph:
  Orders callees by their inclusive cost, their own cost or name.
- `filter`, on the database: Filter the rows with a pattern. Esc clears it.

### Keyboard

Tab moves forward through the first menu row, then the status menu row, then
the page below them, and Shift+Tab moves backward. Tables, trees and the source
code can be navigated with the arrow keys.

- The number keys select the numbered buttons of the first menu row.
- Enter or Space presses the focused button or link.
- A pulldown opens with Enter, Space or typing. The up and down arrow keys move
  through its entries, Enter picks one, Backspace erases the last search
  character and Escape closes it.
- Sliders move with the arrow keys, and Home and End go to their ends.
- `+` or `=` and `-` change the scale.
- Tables can be navigated with the arrow keys. Up and down move between rows,
  left and right between the links of a row, and Home and End go to the first
  and last row. Enter or Space on a row follows its first link.
- Trees can be navigated with the arrow keys. Right opens a branch and left
  closes it.
- The hottest lines can be navigated with the arrow keys.
- On the heat map, Enter on a source line opens or closes its information box,
  and Escape closes it.
- The arrow keys scroll a page when nothing focused uses them.

## Running The Generator Scripts

See `packages.md` for the Ubuntu administrator commands needed to install the
packages required to use the command line tools.

These are the scripts for using `perf2html`. While the scripts directory does
contain a few more interesting files, none of them should be needed to use the
generators.

The project root is `tests/perf2html/` in a curl checkout, or a perf2html
checkout beside a directory named `curl`. The scripts find curl two directories
above the project root when that directory is named `curl`, else beside the
project root, and stop with an error when neither exists. The scripts in
`scripts/` run from the project root.

- `perf2html.sh`: Capture timing data and generate a report.
- `perf2html_diff.sh`: Generate a report about the difference between two
  `perf2html.sh` reports.
- `perf2html_batch.sh`: Generate 3 reports, a baseline version, a modified
  version, and a diff.
- `clean.sh`: Delete every generated file under `tests/perf2html/` and the
  ccache entries the builds made.

Each script's `--help` prints the following.

```txt
perf2html.sh [debug-flags] [--report=DIR] [cmake-flags...]
    Builds RelWithDebInfo, profiles every TESTS_C test under callgrind plus a
    native perf stat timing run and a traced run for the flame graph,
    generates one report.
    --report=NAME     Defaults to perf2html_baseline_report, or
                      perf2html_modified_report when a cmake flag is given.
    --target-dir=DIR  Default directory for reports (default $PWD).
    --txz             Create .txz archives of all reports generated.
                      .txz files may also be used as inputs.
    cmake-flags       Everything else is passed directly to cmake.
```

```txt
perf2html_diff.sh [debug-flags] [--target-dir=DIR] [baseline] [modified] [diff]
    Measures nothing: Compares the counters in two profiling reports and
    generates a diff. Report names default to
    ./perf2html_{baseline,modified,diff}_report. Both baseline and modified
    must be a perf2html.sh report, and both must show the same source code.
    And a diff can't be re-diffed. Reads nothing but the two reports.
    --target-dir=DIR  Default directory for reports (default $PWD).
    --txz             Create .txz archives of all reports generated.
                      .txz files may also be used as inputs.
```

```txt
perf2html_batch.sh [debug-flags] [--target-dir=DIR] [cmake-flags...]
    Profiles baseline, modified and then does a diff of them.
    --target-dir=DIR  Holds the three default-named reports (default $PWD). The
                      batch cannot rename them.
    --txz             Create .txz archives of all reports generated.
                      .txz files may also be used as inputs.
    cmake-flags       Everything else is passed directly to cmake in the
                      modified build (default is -D CMAKE_C_FLAGS=-Os).
```

These are shared developer flags for the iterative development of `perf2html`
itself.

```txt
    --artifacts=TMP   The profiler artifacts directory. Defaults to
                      perf2html_temporary_artifacts/ beside the report
                      directory (inside the target dir for a batch).
    --keep-artifacts  Flushes the report's stale artifacts subdirectory, then
                      keeps this run's recordings, which is what a later
                      --regenerate reuses.
    --regenerate      Rebuilds all pages from the last run's profiler
                      artifacts, re-measuring nothing and keeping them.
    --verbose         Enables diagnostic information in Markdown. Repeating it
                      (--verbose --verbose) increments the verbosity level.
```

## Callgrind Counters

These are the raw counters `callgrind` records and the derived ones this report
adds up from them. They show up as column headers in the heat map, the raw ones
on the database page too, and as choices in the menu's counters pulldown, under
these same names.

| Counter | Meaning                             | Derived from            |
| ------- | ----------------------------------- | ----------------------- |
| `Ir`    | instructions executed               |                         |
| `Dr`    | data reads                          |                         |
| `Dw`    | data writes                         |                         |
| `I1mr`  | L1 instruction cache misses         |                         |
| `D1mr`  | L1 data cache read misses           |                         |
| `D1mw`  | L1 data cache write misses          |                         |
| `ILmr`  | last level instruction cache misses |                         |
| `DLmr`  | last level data cache read misses   |                         |
| `DLmw`  | last level data cache write misses  |                         |
| `Bc`    | conditional branches executed       |                         |
| `Bcm`   | conditional branches mispredicted   |                         |
| `Bi`    | indirect branches executed          |                         |
| `Bim`   | indirect branches mispredicted      |                         |
| `D1m`   | L1 data cache misses                | `D1mr + D1mw`           |
| `DLm`   | last level data cache misses        | `DLmr + DLmw`           |
| `L1m`   | L1 cache misses, all                | `I1mr + D1mr + D1mw`    |
| `LLm`   | last level cache misses, all        | `ILmr + DLmr + DLmw`    |
| `Bm`    | branches mispredicted, all          | `Bcm + Bim`             |
| `CEst`  | cycle estimate                      | `Ir + 10 L1m + 100 LLm` |

`CEst` weights a miss by roughly what it costs and is used by default.

See the [callgrind](https://valgrind.org/docs/manual/cl-manual.html) docs.

Callgrind is GPL Version 3, 29 June 2007.

## Reading A Diff Report

### Regular Report

A regular report contains a suite of tests that can be explored using a menu.
There is heat map data, call graph data, and a flame graph.

A regular report shows you each counter selected in the menu's counters
pulldown, a total for each and a percentage of that total. Every percentage of
a file, function or line is its cost as a share of the test's global cost.

```txt
| example     |       % |
| ----------- | ------: |
| 1 / 50000   |  ≈0.00% |
| 1 / 5000    |   0.02% |
| 500 / 5000  |  10.00% |
| 5000 / 5000 | 100.00% |
```

### Diff Report

A diff report uses percentages the same way a stock market ticker does. Every
number in it is the modified profile minus the baseline one, per function, file
and line, and every share divides that difference by the same thing's own
baseline count. So a share says how much this line moved against what it used
to cost, not what part of the report it is. Half as long is `▼-50.00%`, twice
as long is `▲100.00%`, and smaller is better.

```txt
| delta              |           % |
| ------------------ | ----------: |
| 0 -> 1000          |   ▲      ∞% |
| 1000 -> 1000       |             |
| 1000 -> 1000000    |   ▲ 999.00x |
| 1000 -> 1001000    |   ▲     ≈∞% |
| 1000 -> 101000     |   ▲ 100.00x |
| 1000 -> 2000       |   ▲ 100.00% |
| 1000 -> 2010       |   ▲   1.01x |
| 1000 -> 900        |   ▼ -10.00% |
| 5000 -> 0          |   ▼-100.00% |
| 5000000 -> 4999999 |   ▼  ≈0.00% |
| 5000000 -> 5000001 |   ▲  ≈0.00% |
| 90 -> 100          |   ▲  11.11% |
```

## Flame Graph (speedscope)

The flame graph is a recording, not a model: every box is one call that
happened, as wide as it took. The test runs in a build with
`-finstrument-functions`, where a hook (`tests/perf2html/src/cyg_callback.c`)
reads the CPU's time stamp counter at every function entry and exit from the
entry of `main` on. "Time Order" is the order the calls were made in.

A diff has no flame graph: a trace neither adds up nor subtracts.

Scroll to pan and pinch or Cmd/Ctrl+scroll to zoom, on both the minimap and the
main view. Click a frame for its stats.

The keybindings are:

- +: zoom in
- -: zoom out
- 0: zoom out to see the entire profile
- w/a/s/d or arrow keys: pan around the profile
- r: Collapse recursion in the flamegraphs
- Cmd+S/Ctrl+S to save the current profile
- Cmd+O/Ctrl+O to open a new profile
- n: Go to next profile/thread if one is available
- p: Go to previous profile/thread if one is available
- t: Open the profile/thread selector if available
- Cmd+F/Ctrl+F: to open search. While open, Enter and Shift+Enter cycle through
  results

[speedscope](https://github.com/jlfwong/speedscope) is Copyright (c) 2018+
Jamie Wong and contributors. `speedscope` is an upstream project and is not
affiliated with the `perf2html` project.
