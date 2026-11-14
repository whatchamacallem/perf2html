// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE-MIT.md file.

window.try_catch_handler_(function () {
  "use strict";

  const CALL_GRAPH_BRANCH_FIRST_TEXT = settings_(
    "CALL_GRAPH_BRANCH_FIRST_TEXT",
  );
  const CALL_GRAPH_BRANCH_LAST_TEXT = settings_("CALL_GRAPH_BRANCH_LAST_TEXT");
  const CALL_GRAPH_BRANCH_MIDDLE_TEXT = settings_(
    "CALL_GRAPH_BRANCH_MIDDLE_TEXT",
  );
  const CALL_GRAPH_BRANCH_ONLY_TEXT = settings_("CALL_GRAPH_BRANCH_ONLY_TEXT");
  const CALL_GRAPH_BRANCH_PASS_TEXT = settings_("CALL_GRAPH_BRANCH_PASS_TEXT");
  const CALL_GRAPH_CLOSED_TEXT = settings_("CALL_GRAPH_CLOSED_TEXT");
  const CALL_GRAPH_LINE_TEXT = settings_("CALL_GRAPH_LINE_TEXT");
  const CALL_GRAPH_MOST_DRAWN_NODES = settings_("CALL_GRAPH_MOST_DRAWN_NODES");
  const CALL_GRAPH_PAD_TEXT = settings_("CALL_GRAPH_PAD_TEXT");
  const NUMBER_FRACTION_DIGITS = settings_("NUMBER_FRACTION_DIGITS");
  const NUMBER_MULTIPLE_SUFFIX_TEXT = settings_("NUMBER_MULTIPLE_SUFFIX_TEXT");
  const STYLE_TABLE_CHUNK_ROWS_PROPERTY = settings_(
    "STYLE_TABLE_CHUNK_ROWS_PROPERTY",
  );
  const TABLE_CHUNK_ROW_COUNT = settings_("TABLE_CHUNK_ROW_COUNT");

  const render_character_cells = window.render_character_cells_;
  const render_element = window.render_element_;
  const render_html_escape = window.render_html_escape_;
  const CALL_GRAPH_CUTOFF_STOP_ROOTS =
    window.report_preferences_.call_graph_cutoff_stop_roots;
  // Holds the width of a multiple at full precision, zero's.
  const MULTIPLE_WIDTH_CHARS = window.report_ui_.fixed_text(
    0,
    NUMBER_FRACTION_DIGITS,
  ).length;
  const MULTIPLE_COLUMN = { class: "call-graph-multiple-" };
  const SHARE_COLUMN = { class: "call-graph-share-" };
  const SYMBOL_COLUMN = { class: "call-graph-symbol-" };
  // Holds a group's columns in order, each with the attributes of its cells.
  const GROUP_COLUMNS = [{}, MULTIPLE_COLUMN, SHARE_COLUMN, SYMBOL_COLUMN];
  // Writes a share cell, the share on its heat color, empty for no share.
  function share_cell_markup(share_percent) {
    if (!share_percent) return render_element("td", SHARE_COLUMN, "");
    return render_element(
      "td",
      {
        ...SHARE_COLUMN,
        style: window.report_ui_.heat_cell_style(
          share_percent,
          heat_curve_name,
          false,
        ),
      },
      render_html_escape(window.report_ui_.percent_text(share_percent)),
    );
  }
  // Marks a layout group a branch passes through, holding no node.
  const PASS_PLACE = {};
  const page_scroll_box = document.getElementById("call-graph-page-");
  const page_heading = page_scroll_box.querySelector(".page-heading-");
  const shown_test_name = window.report_ui_.address.of_hash(
    location.hash,
  ).test;
  const graph_table = document.getElementById("call-graph-table-");
  const call_graph_model = JSON.parse(graph_table.getAttribute("data-model-"));
  const graph_head = window.render_element_of_(
    render_element("thead", {}, ""),
  );
  // Holds the chunks of rows, each laid out only while it nears the view.
  const graph_bodies = [];
  // Writes a sizer row, its cells each column's widest, so chunks line up.
  const sizer_row_markup = (sizer_cells_markup) =>
    render_element(
      "tr",
      { class: "table-sizer-row-", "aria-hidden": "true" },
      sizer_cells_markup,
    );

  // Reads one function's row, its calls summed below.
  function function_record_read(function_row) {
    return {
      name: function_row[0],
      self_cost: function_row[1],
      is_linked: function_row[2],
      invocation_count: 0,
      callee_edges: [],
    };
  }
  // Reads one call edge from its row.
  function call_edge_read(edge_row) {
    return {
      caller_index: edge_row[0],
      callee_index: edge_row[1],
      calls: edge_row[2],
      call_line: edge_row[3],
      inclusive_cost: edge_row[4],
    };
  }
  // Reads one root from its row.
  function call_root_read(root_row) {
    return { function_index: root_row[0], calls: root_row[1] };
  }
  // Reads one branch from its row, its path from the branch it hangs from.
  function call_branch_read(branch_row, read_branches) {
    const parent_index = branch_row[0];
    return {
      node_path:
        parent_index === null
          ? [branch_row[1]]
          : [...read_branches[parent_index].node_path, branch_row[1]],
      inclusive_cost: branch_row[2],
    };
  }
  const function_records = call_graph_model.functions.map(
    function_record_read,
  );
  const call_roots = call_graph_model.roots.map(call_root_read);
  const test_total = call_graph_model.test_total;
  for (const call_root of call_roots)
    function_records[call_root.function_index].invocation_count +=
      call_root.calls;
  for (const call_edge of call_graph_model.edges.map(call_edge_read)) {
    function_records[call_edge.caller_index].callee_edges.push(call_edge);
    function_records[call_edge.callee_index].invocation_count +=
      call_edge.calls;
  }
  const call_branches = [];
  for (const branch_row of call_graph_model.branches)
    call_branches.push(call_branch_read(branch_row, call_branches));
  // Lists each branch drawing a node, a root branch drawing none.
  const node_branches = call_branches.filter(
    (call_branch) => call_branch.node_path.length > 1,
  );
  // Holds each drawn branch's cost, the inclusive cost of its own calls.
  const branch_costs = new Map(
    node_branches.map((call_branch) => [
      path_key(call_branch.node_path),
      call_branch.inclusive_cost,
    ]),
  );

  // Returns a function's self cost as a percent of the test's total cost.
  function self_share_of_test(function_record) {
    return window.report_ui_.share_of_test(
      function_record.self_cost,
      test_total,
    );
  }
  // Returns an edge's calls per invocation of its caller, null for none.
  function edge_multiple(call_edge) {
    const caller_count =
      function_records[call_edge.caller_index].invocation_count;
    return caller_count ? call_edge.calls / caller_count : null;
  }
  // Orders two edges by their callees' names.
  function name_order(edge_a, edge_b) {
    return function_records[edge_a.callee_index].name.localeCompare(
      function_records[edge_b.callee_index].name,
    );
  }
  // Orders a caller's edges by their calls' cumulative cost, line, then name.
  function cumulative_order(edge_a, edge_b) {
    return (
      edge_b.inclusive_cost - edge_a.inclusive_cost ||
      edge_a.call_line - edge_b.call_line ||
      name_order(edge_a, edge_b)
    );
  }
  // Orders a caller's edges by their callees' self cost, then cumulative.
  function heat_order(edge_a, edge_b) {
    return (
      function_records[edge_b.callee_index].self_cost -
        function_records[edge_a.callee_index].self_cost ||
      cumulative_order(edge_a, edge_b)
    );
  }
  // Holds the edge order of each call graph sort, by its value.
  const SORT_ORDERS = {
    cumulative: cumulative_order,
    heat: heat_order,
    name: name_order,
  };
  // Orders a node's shown edges by the chosen sort.
  function edges_sort(callee_edges) {
    if (!Object.hasOwn(SORT_ORDERS, sort_mode))
      window.throw_exception_("str_error_internal");
    return callee_edges.toSorted(SORT_ORDERS[sort_mode]);
  }

  // Returns the key of a node's path in the open set.
  function path_key(node_path) {
    return JSON.stringify(node_path);
  }
  // Returns the record of the function a node's path ends at.
  function path_function(node_path) {
    return function_records[node_path.at(-1)];
  }
  // Lists the edges a node's path shows, each callee already on it skipped.
  function shown_callee_edges(node_path) {
    return path_function(node_path).callee_edges.filter(
      (call_edge) => !node_path.includes(call_edge.callee_index),
    );
  }
  // Returns a branch's cost, zero for a call the branch never made.
  function branch_cost(node_path) {
    return branch_costs.get(path_key(node_path)) ?? 0;
  }
  // Returns the cutoff percent, the chosen stop's root squared.
  function cutoff_percent() {
    return cutoff_root * cutoff_root;
  }
  // Returns whether a shown child costs the cutoff percent of the test.
  function branch_opens(node_path) {
    return shown_callee_edges(node_path).some(
      (call_edge) =>
        window.report_ui_.share_of_test(
          branch_cost([...node_path, call_edge.callee_index]),
          test_total,
        ) >= cutoff_percent(),
    );
  }
  // Returns a fresh open set, each function open only at its costliest branch.
  function call_graph_open_set() {
    const costliest_branches = new Map();
    for (const call_branch of node_branches) {
      const function_index = call_branch.node_path.at(-1);
      const known_branch = costliest_branches.get(function_index);
      // A tie keeps the first branch, the earliest by its path's names.
      if (
        !known_branch ||
        call_branch.inclusive_cost > known_branch.inclusive_cost
      )
        costliest_branches.set(function_index, call_branch);
    }
    return new Set(
      [...costliest_branches.values()]
        .filter((call_branch) => branch_opens(call_branch.node_path))
        .map((call_branch) => path_key(call_branch.node_path)),
    );
  }
  let button_graph_nodes = new WeakMap(),
    cell_symbol_buttons = new WeakMap(),
    cutoff_root = null,
    drawn_rows = new Map(),
    heat_curve_name = null,
    open_path_keys = null,
    path_symbol_buttons = new Map(),
    rendered_preferences_text = null,
    selected_function = null,
    sort_mode = null;

  // Lists a path's shown children by the chosen sort, each with its branch.
  function path_children(node_path) {
    const shown_edges = edges_sort(shown_callee_edges(node_path));
    const last_index = shown_edges.length - 1;
    return shown_edges.map((call_edge, child_index) => ({
      node_path: [...node_path, call_edge.callee_index],
      call_edge,
      branch_text:
        child_index === 0
          ? last_index === 0
            ? CALL_GRAPH_BRANCH_ONLY_TEXT
            : CALL_GRAPH_BRANCH_FIRST_TEXT
          : child_index < last_index
            ? CALL_GRAPH_BRANCH_MIDDLE_TEXT
            : CALL_GRAPH_BRANCH_LAST_TEXT,
    }));
  }
  // Returns whether a node is open.
  function node_is_open(graph_node) {
    return open_path_keys.has(path_key(graph_node.node_path));
  }
  // Returns whether a node is closed and has shown children to open.
  function node_is_closed(graph_node) {
    return (
      !node_is_open(graph_node) &&
      shown_callee_edges(graph_node.node_path).length > 0
    );
  }

  // Places every drawn node in a row and a group, one group per depth.
  function graph_layout() {
    const layout_rows = [];
    const next_free_rows = [];
    let placed_node_count = 0;
    // Places a path's children from a row, their branch passing between them.
    function children_place(node_path, least_row) {
      const child_rows = path_children(node_path).map((child_node) =>
        node_place(child_node, least_row),
      );
      for (
        let pass_row = child_rows[0] + 1;
        pass_row < child_rows.at(-1);
        pass_row++
      )
        if (!child_rows.includes(pass_row))
          layout_rows[pass_row][node_path.length - 1] = PASS_PLACE;
    }
    // Places a node, then its children when open, and returns its row.
    function node_place(graph_node, least_row) {
      placed_node_count++;
      // A count refuses the draw alike at any speed, before the page stalls.
      if (placed_node_count > CALL_GRAPH_MOST_DRAWN_NODES)
        window.throw_exception_(
          "str_error_call_graph_too_large",
          shown_test_name,
          CALL_GRAPH_MOST_DRAWN_NODES,
        );
      const group_index = graph_node.node_path.length - 2;
      const is_open = node_is_open(graph_node);
      // An open node sits below every branch right of it, any other beside.
      const node_row = Math.max(
        least_row,
        ...next_free_rows.slice(
          group_index,
          is_open ? next_free_rows.length : group_index + 1,
        ),
      );
      (layout_rows[node_row] ??= [])[group_index] = graph_node;
      next_free_rows[group_index] = node_row + 1;
      // A row keeps a group right of a closed node, its mark's place if empty.
      if (node_is_closed(graph_node))
        layout_rows[node_row].length = Math.max(
          layout_rows[node_row].length,
          group_index + 2,
        );
      if (is_open) children_place(graph_node.node_path, node_row);
      return node_row;
    }
    // A root draws no node, its calls starting below every drawn row.
    for (const call_root of call_roots)
      children_place(
        [call_root.function_index],
        Math.max(0, ...next_free_rows),
      );
    // Every row holds every group, so each column runs the table's height.
    const group_count = Math.max(
      ...layout_rows.map((layout_row) => layout_row.length),
    );
    for (const layout_row of layout_rows) layout_row.length = group_count;
    return layout_rows;
  }

  // Returns whether a row's closed node has its mark in the empty place right.
  function mark_fits_right(layout_row, group_index) {
    const layout_place = layout_row[group_index];
    return (
      layout_place !== undefined &&
      layout_place !== PASS_PLACE &&
      node_is_closed(layout_place) &&
      layout_row[group_index + 1] === undefined
    );
  }
  // Returns a place's branch text: a node's or a passing branch's.
  function place_branch_text(layout_place) {
    if (layout_place === PASS_PLACE) return CALL_GRAPH_BRANCH_PASS_TEXT;
    return layout_place.branch_text;
  }
  // Returns a placed node's name and bar end texts, and whether bars follow.
  function symbol_parts(layout_row, group_index) {
    const graph_node = layout_row[group_index];
    const name_text =
      CALL_GRAPH_PAD_TEXT +
      path_function(graph_node.node_path).name +
      CALL_GRAPH_PAD_TEXT;
    if (node_is_open(graph_node) || mark_fits_right(layout_row, group_index))
      return { name_text, has_bars: true, end_text: "" };
    if (node_is_closed(graph_node))
      return {
        name_text,
        has_bars: true,
        end_text: CALL_GRAPH_CLOSED_TEXT + CALL_GRAPH_PAD_TEXT,
      };
    return { name_text, has_bars: false, end_text: "" };
  }
  // Returns the fewest characters a placed node's symbol takes, one bar long.
  function symbol_least_width(layout_row, group_index) {
    const symbol_part = symbol_parts(layout_row, group_index);
    if (!symbol_part.has_bars) return symbol_part.name_text.length;
    return (
      symbol_part.name_text.length +
      CALL_GRAPH_LINE_TEXT.length +
      symbol_part.end_text.length
    );
  }
  // Lists each group's symbol column width, its widest symbol's characters.
  function symbol_column_widths(layout_rows) {
    const column_widths = new Array(layout_rows[0].length).fill(0);
    for (const layout_row of layout_rows)
      layout_row.forEach((layout_place, group_index) => {
        if (layout_place === undefined || layout_place === PASS_PLACE) return;
        column_widths[group_index] = Math.max(
          column_widths[group_index],
          symbol_least_width(layout_row, group_index),
        );
      });
    return column_widths;
  }
  // Writes a node's symbol, a button if it toggles, its bars to the width.
  function symbol_markup(layout_row, group_index, symbol_width) {
    const graph_node = layout_row[group_index];
    const symbol_part = symbol_parts(layout_row, group_index);
    const name_markup = render_html_escape(symbol_part.name_text);
    const shown_name_markup =
      shown_callee_edges(graph_node.node_path).length > 0
        ? window.render_menu_button_("action", name_markup, {
            tag_name: "span",
          })
        : name_markup;
    if (!symbol_part.has_bars) return shown_name_markup;
    const bar_width =
      symbol_width -
      symbol_part.name_text.length -
      symbol_part.end_text.length;
    return (
      shown_name_markup +
      render_html_escape(CALL_GRAPH_LINE_TEXT.repeat(bar_width)) +
      render_character_cells(symbol_part.end_text)
    );
  }
  // Returns a multiple with the most fraction digits its width holds.
  function multiple_text(calls_multiple) {
    let digit_count = NUMBER_FRACTION_DIGITS;
    let fitted_text = window.report_ui_.fixed_text(
      calls_multiple,
      digit_count,
    );
    while (digit_count > 0 && fitted_text.length > MULTIPLE_WIDTH_CHARS) {
      digit_count--;
      fitted_text = window.report_ui_.fixed_text(calls_multiple, digit_count);
    }
    return fitted_text;
  }
  // Writes a node's calls multiple and its suffix between pads, if it has one.
  function multiple_markup(graph_node) {
    const calls_multiple = edge_multiple(graph_node.call_edge);
    if (calls_multiple === null) return "";
    return render_html_escape(
      CALL_GRAPH_PAD_TEXT +
        multiple_text(calls_multiple) +
        NUMBER_MULTIPLE_SUFFIX_TEXT +
        CALL_GRAPH_PAD_TEXT,
    );
  }
  // Writes a layout row's cells, one empty cell spanning each run of empties.
  function layout_row_markup(layout_row, symbol_widths) {
    let row_markup = "";
    let empty_span = 0;
    // Adds cells after the empty cell of the run before them, if any.
    function cells_add(cells_markup) {
      if (empty_span)
        row_markup += render_element("td", { colspan: empty_span }, "");
      empty_span = 0;
      row_markup += cells_markup;
    }
    for (let group_index = 0; group_index < layout_row.length; group_index++) {
      const layout_place = layout_row[group_index];
      // A closed node's mark takes the empty branch cell right of it.
      if (mark_fits_right(layout_row, group_index - 1))
        cells_add(
          render_element(
            "td",
            {},
            render_character_cells(CALL_GRAPH_CLOSED_TEXT),
          ),
        );
      else if (layout_place === undefined) empty_span++;
      else
        cells_add(
          render_element(
            "td",
            {},
            render_html_escape(place_branch_text(layout_place)),
          ),
        );
      if (layout_place === undefined || layout_place === PASS_PLACE) {
        empty_span += GROUP_COLUMNS.length - 1;
        continue;
      }
      cells_add(
        render_element("td", MULTIPLE_COLUMN, multiple_markup(layout_place)) +
          share_cell_markup(
            self_share_of_test(path_function(layout_place.node_path)),
          ) +
          render_element(
            "td",
            SYMBOL_COLUMN,
            symbol_markup(layout_row, group_index, symbol_widths[group_index]),
          ),
      );
    }
    cells_add("");
    return row_markup;
  }
  // Lists a row's cells by the column each starts at.
  function row_column_cells(graph_row) {
    const column_cells = [];
    let column_index = 0;
    for (const row_cell of graph_row.cells) {
      column_cells[column_index] = row_cell;
      column_index += row_cell.colSpan;
    }
    return column_cells;
  }
  // Writes the head row of no height, a cell per column, for each group held.
  function head_draw(group_count) {
    const column_count = group_count * GROUP_COLUMNS.length;
    if (graph_head.rows[0]?.cells.length === column_count) return;
    graph_head.innerHTML =
      render_element(
        "tr",
        {},
        GROUP_COLUMNS.map((group_column) =>
          render_element("td", group_column, ""),
        )
          .join("")
          .repeat(group_count),
      ) + sizer_row_markup("");
  }
  // Ranks a cell's width: its characters, then a button's edge lines.
  const cell_width_rank = (graph_cell) =>
    2 * graph_cell.textContent.length +
    (graph_cell.querySelector(".menu-button-") ? 1 : 0);
  // Writes each column's widest one column cell, an empty cell for none.
  function sizer_cells_markup(widest_cells, group_count) {
    let cells_markup = "";
    for (
      let column_index = 0;
      column_index < group_count * GROUP_COLUMNS.length;
      column_index++
    )
      cells_markup += widest_cells[column_index]
        ? widest_cells[column_index].outerHTML
        : render_element(
            "td",
            GROUP_COLUMNS[column_index % GROUP_COLUMNS.length],
            "",
          );
    return cells_markup;
  }
  // Writes every sizer row whose cells differ from the widest cells now.
  function sizer_rows_draw(cells_markup) {
    for (const sizer_row of graph_table.querySelectorAll(
      ":scope > :is(thead, tbody) > tr.table-sizer-row-",
    ))
      if (sizer_row.innerHTML !== cells_markup)
        sizer_row.innerHTML = cells_markup;
  }
  // Puts the rows in their chunks in order, moving only a row out of place.
  function rows_place(graph_rows) {
    const chunk_count = Math.max(
      1,
      Math.ceil(graph_rows.length / TABLE_CHUNK_ROW_COUNT),
    );
    while (graph_bodies.length < chunk_count) {
      const graph_body = window.render_element_of_(
        render_element("tbody", {}, sizer_row_markup("")),
      );
      graph_table.append(graph_body);
      graph_bodies.push(graph_body);
    }
    while (graph_bodies.length > chunk_count) graph_bodies.pop().remove();
    graph_bodies.forEach((graph_body, chunk_index) => {
      const chunk_start = chunk_index * TABLE_CHUNK_ROW_COUNT;
      const chunk_rows = graph_rows.slice(
        chunk_start,
        chunk_start + TABLE_CHUNK_ROW_COUNT,
      );
      // A row a later chunk holds moves on when that chunk takes it.
      let next_row = graph_body.rows[0].nextElementSibling;
      for (const graph_row of chunk_rows) {
        if (graph_row === next_row) next_row = next_row.nextElementSibling;
        else graph_body.insertBefore(graph_row, next_row);
      }
      graph_body.style.setProperty(
        STYLE_TABLE_CHUNK_ROWS_PROPERTY,
        String(chunk_rows.length),
      );
    });
  }
  // Draws every layout row, making only a row whose markup changed.
  function graph_render() {
    button_graph_nodes = new WeakMap();
    cell_symbol_buttons = new WeakMap();
    path_symbol_buttons = new Map();
    const layout_rows = graph_layout();
    const symbol_widths = symbol_column_widths(layout_rows);
    const stale_rows = drawn_rows;
    drawn_rows = new Map();
    const widest_cells = [];
    const row_markups = layout_rows.map((layout_row) =>
      render_element("tr", {}, layout_row_markup(layout_row, symbol_widths)),
    );
    const kept_rows = row_markups.map((row_markup) =>
      stale_rows.get(row_markup)?.shift(),
    );
    // The rows no draw kept are made together, from one parse.
    const made_template = document.createElement("template");
    made_template.innerHTML = row_markups
      .filter((row_markup, row_index) => !kept_rows[row_index])
      .join("");
    const made_rows = [...made_template.content.children];
    if (made_rows.length !== kept_rows.filter((kept_row) => !kept_row).length)
      window.throw_exception_("str_error_internal");
    let made_count = 0;
    const graph_rows = layout_rows.map((layout_row, row_index) => {
      const row_markup = row_markups[row_index];
      const graph_row = kept_rows[row_index] ?? made_rows[made_count++];
      if (!drawn_rows.has(row_markup)) drawn_rows.set(row_markup, []);
      drawn_rows.get(row_markup).push(graph_row);
      const column_cells = row_column_cells(graph_row);
      layout_row.forEach((layout_place, group_index) => {
        if (layout_place === PASS_PLACE) return;
        // A node's cells end with the next group's branch cell if its mark's.
        const node_cells = column_cells.slice(
          group_index * GROUP_COLUMNS.length,
          (group_index + 1) * GROUP_COLUMNS.length +
            (mark_fits_right(layout_row, group_index) ? 1 : 0),
        );
        const symbol_button = node_cells
          .map((node_cell) => node_cell.querySelector(".menu-button-"))
          .find((found_button) => found_button);
        if (!symbol_button) return;
        path_symbol_buttons.set(
          path_key(layout_place.node_path),
          symbol_button,
        );
        button_graph_nodes.set(symbol_button, layout_place);
        // Each of a symbol's cells takes the click its button takes.
        for (const node_cell of node_cells) {
          node_cell.classList.add("clickable-");
          cell_symbol_buttons.set(node_cell, symbol_button);
        }
      });
      column_cells.forEach((column_cell, column_index) => {
        const widest_cell = widest_cells[column_index];
        if (
          column_cell.colSpan === 1 &&
          (!widest_cell ||
            cell_width_rank(column_cell) > cell_width_rank(widest_cell))
        )
          widest_cells[column_index] = column_cell;
      });
      return graph_row;
    });
    for (const stale_row of [...stale_rows.values()].flat())
      stale_row.remove();
    const group_count = layout_rows[0].length;
    head_draw(group_count);
    rows_place(graph_rows);
    sizer_rows_draw(sizer_cells_markup(widest_cells, group_count));
    window.report_ui_.layout_activate();
  }

  // Asks the top page for the cutoff of the stop the slider reaches.
  function cutoff_stop_choose(cutoff_stop) {
    window.report_ui_.call_graph_cutoff_choose_send(
      CALL_GRAPH_CUTOFF_STOP_ROOTS[cutoff_stop],
    );
  }
  // Shows the cutoff slider, then the selected function, after the copy.
  function heading_tail_show() {
    const cutoff_entry = window.report_ui_.strip.entry_make(
      "cutoff",
      "action",
      window.ui_strings_.text("str_call_graph_cutoff"),
      {
        is_widget: true,
        widget_text: window.report_ui_.strip.slider_text(
          CALL_GRAPH_CUTOFF_STOP_ROOTS.indexOf(cutoff_root),
          CALL_GRAPH_CUTOFF_STOP_ROOTS.length - 1,
        ),
        on_stop_choose: cutoff_stop_choose,
      },
    );
    // A function the heat map cannot show, having no line, is no link.
    const selected_entries =
      selected_function === null
        ? []
        : [
            window.report_ui_.strip.entry_make(
              "selected_function",
              selected_function.is_linked ? "link" : "label",
              selected_function.name,
              selected_function.is_linked
                ? {
                    href: window.report_ui_.address.function_hash(
                      shown_test_name,
                      selected_function.name,
                      true,
                    ),
                  }
                : {},
            ),
          ];
    window.report_ui_.page_heading_tail_set(page_heading, [
      cutoff_entry,
      ...selected_entries,
    ]);
  }
  // Opens or closes a symbol's node, draws again and selects it.
  function node_toggle(symbol_button) {
    const graph_node = button_graph_nodes.get(symbol_button);
    selected_function = path_function(graph_node.node_path);
    heading_tail_show();
    const node_key = path_key(graph_node.node_path);
    if (open_path_keys.has(node_key)) open_path_keys.delete(node_key);
    else open_path_keys.add(node_key);
    const had_focus = document.activeElement === symbol_button;
    graph_render();
    // The redraw replaced the button, so its new one takes the focus.
    if (had_focus)
      path_symbol_buttons.get(node_key).focus({ preventScroll: true });
    window.report_ui_.focused_path_send([selected_function.name]);
  }
  // Returns the symbol button of the cell an input reached, if any.
  function symbol_button_of(browser_event) {
    return cell_symbol_buttons.get(browser_event.target.closest("td"));
  }

  // Takes the relayed preferences: the heat curve, the sort and the cutoff.
  function preferences_handler() {
    const view_preferences = window.report_preferences_.now();
    const scale_choice = window.report_preferences_
      .heat_scale_choices()
      .find(
        (offered_choice) =>
          offered_choice.value === view_preferences.heat_scale_value,
      );
    if (!scale_choice) window.throw_exception_("str_error_internal");
    heat_curve_name = scale_choice.curve;
    sort_mode = view_preferences.call_graph_sort_mode;
    const taken_cutoff_root = cutoff_root;
    cutoff_root = view_preferences.call_graph_cutoff_root;
    // Logs each cutoff the view takes, the first at page load included.
    if (cutoff_root !== taken_cutoff_root)
      console.log(
        window.ui_strings_.text_fill("str_call_graph_cutoff_log", {
          percent: window.report_ui_.percent_text(cutoff_percent()),
        }),
      );
  }
  // Draws the graph and its heading's tail when the preferences change it.
  function preferences_apply() {
    const opened_cutoff_root = cutoff_root;
    preferences_handler();
    // A new cutoff, the page's first included, opens a fresh open set.
    if (cutoff_root !== opened_cutoff_root)
      open_path_keys = call_graph_open_set();
    const preferences_text = JSON.stringify([
      heat_curve_name,
      sort_mode,
      cutoff_root,
    ]);
    if (preferences_text === rendered_preferences_text) return;
    rendered_preferences_text = preferences_text;
    graph_render();
    heading_tail_show();
  }
  // Opens a fresh open set, draws every row and clears the selection.
  function view_reset() {
    preferences_handler();
    open_path_keys = call_graph_open_set();
    selected_function = null;
    // Forgets the drawn preferences, so the graph draws again.
    rendered_preferences_text = null;
    preferences_apply();
    window.report_ui_.focused_path_send([]);
  }
  // Takes a relayed message: a view reset, else a change of its preferences.
  function relay_handler(message_data) {
    const is_changed = window.report_preferences_.relay_handler(message_data);
    if (message_data.report_ui === "view_reset") view_reset();
    else if (is_changed) preferences_apply();
  }
  // Shows the page from its top left when its address is followed again.
  function page_top_show() {
    page_scroll_box.scrollTo(0, 0);
  }

  graph_table.classList.add("table-chunked-");
  graph_table.append(graph_head);
  graph_table.addEventListener(
    "click",
    window.try_catch_handler_((click_event) => {
      const symbol_button = symbol_button_of(click_event);
      if (symbol_button) node_toggle(symbol_button);
    }),
  );
  graph_table.addEventListener(
    "keydown",
    window.try_catch_handler_((key_event) => {
      const symbol_button = symbol_button_of(key_event);
      if (
        !symbol_button ||
        !window.report_ui_.widget_key.activates(
          window.report_ui_.widget_key.of(key_event),
        )
      )
        return;
      key_event.preventDefault();
      if (!key_event.repeat) node_toggle(symbol_button);
    }),
  );
  window.report_ui_.view_activate({
    forwards_input: true,
    recenter: page_top_show,
    relay_handler,
  });
})();
