// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE-MIT.md file.

window.try_catch_handler_(function () {
  "use strict";

  const CALLGRIND_FILE_DATA_ERROR_CODE = settings_(
    "CALLGRIND_FILE_DATA_ERROR_CODE",
  );
  const COUNTER_LIST_CALLEES_LINE_NAME = settings_(
    "COUNTER_LIST_CALLEES_LINE_NAME",
  );
  const COUNTER_LIST_CALLERS_LINE_NAME = settings_(
    "COUNTER_LIST_CALLERS_LINE_NAME",
  );
  const COUNTER_LIST_CALLS_LINE_NAME = settings_(
    "COUNTER_LIST_CALLS_LINE_NAME",
  );
  const DATABASE_CELL_SEPARATOR_TEXT = settings_(
    "DATABASE_CELL_SEPARATOR_TEXT",
  );
  const HEAT_MAP_DOWNLOAD_FILE_NAME_SUFFIX = settings_(
    "HEAT_MAP_DOWNLOAD_FILE_NAME_SUFFIX",
  );
  const HEAT_MAP_INFORMATION_BOX_FUNCTION_SEPARATOR_TEXT = settings_(
    "HEAT_MAP_INFORMATION_BOX_FUNCTION_SEPARATOR_TEXT",
  );
  const HEAT_MAP_MINIMAP_VIEWPORT_BOX_SMALLEST_PX = settings_(
    "HEAT_MAP_MINIMAP_VIEWPORT_BOX_SMALLEST_PX",
  );
  const HEAT_MAP_MODEL_DIR_NAME = settings_("HEAT_MAP_MODEL_DIR_NAME");
  const HEAT_MAP_SOURCE_CALL_SITE_MARKER_TEXT = settings_(
    "HEAT_MAP_SOURCE_CALL_SITE_MARKER_TEXT",
  );
  const HEAT_MAP_SOURCE_FUNCTION_ENTRY_MARKER_TEXT = settings_(
    "HEAT_MAP_SOURCE_FUNCTION_ENTRY_MARKER_TEXT",
  );
  const HEAT_MAP_SOURCE_SHOWN_LINE_ROWS_ABOVE = settings_(
    "HEAT_MAP_SOURCE_SHOWN_LINE_ROWS_ABOVE",
  );
  const HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_LEAST_SHARE = settings_(
    "HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_LEAST_SHARE",
  );
  const HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_MAX_COUNT = settings_(
    "HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_MAX_COUNT",
  );
  const HEAT_MAP_SOURCE_TAB_SIZE_CHARS = settings_(
    "HEAT_MAP_SOURCE_TAB_SIZE_CHARS",
  );
  const HEAT_MAP_SOURCE_VIEW_WIDTH_CHARS = settings_(
    "HEAT_MAP_SOURCE_VIEW_WIDTH_CHARS",
  );
  const HEAT_MAP_TREE_BRANCH_LAST_TEXT = settings_(
    "HEAT_MAP_TREE_BRANCH_LAST_TEXT",
  );
  const HEAT_MAP_TREE_BRANCH_MIDDLE_TEXT = settings_(
    "HEAT_MAP_TREE_BRANCH_MIDDLE_TEXT",
  );
  const HEAT_MAP_TREE_BRANCH_PASS_TEXT = settings_(
    "HEAT_MAP_TREE_BRANCH_PASS_TEXT",
  );
  const HEAT_MAP_TREE_CLOSED_TEXT = settings_("HEAT_MAP_TREE_CLOSED_TEXT");
  const HEAT_MAP_TREE_FILE_TEXT = settings_("HEAT_MAP_TREE_FILE_TEXT");
  const HEAT_MAP_TREE_OPEN_TEXT = settings_("HEAT_MAP_TREE_OPEN_TEXT");
  const HEAT_MAP_VIEW_ENTRY = settings_("HEAT_MAP_VIEW_ENTRY");
  const RANKING_COUNTER_NAME = settings_("RANKING_COUNTER_NAME");
  const REPORT_SOURCES_DIR_NAME = settings_("REPORT_SOURCES_DIR_NAME");
  const STYLE_HEAT_MAP_SOURCE_BOX_ROOM_PROPERTY = settings_(
    "STYLE_HEAT_MAP_SOURCE_BOX_ROOM_PROPERTY",
  );
  const STYLE_TABLE_FUNCTION_LIST_COLUMN_MAX_CHARS = settings_(
    "STYLE_TABLE_FUNCTION_LIST_COLUMN_MAX_CHARS",
  );
  const TABLE_COLUMN_LINE_NAME = settings_("TABLE_COLUMN_LINE_NAME");
  const TABLE_COLUMN_SOURCE_NAME = settings_("TABLE_COLUMN_SOURCE_NAME");
  const WIDGET_KEY_NAMES = settings_("WIDGET_KEY_NAMES");
  if (!window.report_source_database_)
    window.throw_exception_("str_error_internal");
  const source_database = window.report_source_database_;
  let profile_model = null,
    file_table = null,
    function_table = null,
    shown_test_name = null;
  // Holds the tree and its bar, hung from the source table's first title.
  const tree_track = document.getElementById("heat-map-tree-track-template-")
    .content.firstElementChild;
  const tree_panel = tree_track.querySelector("#heat-map-tree-");
  const main_panel = document.getElementById("heat-map-main-");
  const ticker_tape_box = document.getElementById("heat-map-ticker-tape-box-");
  const minimap_panel = document.getElementById("heat-map-minimap-");
  const minimap_box = document.getElementById("heat-map-minimap-box-");
  const minimap_viewport = document.getElementById(
    "heat-map-minimap-viewport-",
  );
  let current_file_path = null;
  tree_panel.setAttribute(
    "aria-label",
    window.ui_strings_.text("str_heat_map_tree_label"),
  );
  main_panel.setAttribute(
    "aria-label",
    window.ui_strings_.text("str_heat_map_main_label"),
  );
  document.title = window.ui_strings_.text("str_view_heat_map");

  const vector_at = (cost_vector, index) =>
    cost_vector && index < cost_vector.length ? cost_vector[index] : 0;
  let counter_list = null,
    ranking_counter = null;
  const counter_find = (key) =>
    counter_list.find((counter) => counter.key === key);

  const text = window.ui_strings_.text;
  const text_fill = window.ui_strings_.text_fill;
  const render_element = window.render_element_;
  const render_html_escape = window.render_html_escape_;
  const render_menu_button = window.render_menu_button_;
  let active_scale = null,
    shown_line_names = null,
    // Holds whether the address shows its functions' costs, not its lines'.
    shows_functions = null,
    sort_mode = null;
  const counter_label = (counter) =>
    report_preferences_.counter_label(counter.key);
  function counters_build() {
    counter_list = report_preferences_.counter_readers(
      profile_model.heatMapTotals.counters,
      profile_model.heatMapTotals.derived,
    );
    ranking_counter = counter_find(RANKING_COUNTER_NAME);
  }
  const ranking_value = (cost_vector) => ranking_counter.get(cost_vector);
  const absolute = Math.abs;

  // Takes the relayed preferences: the columns, the scale and the order.
  function preferences_handler() {
    const view_preferences = report_preferences_.now();
    shown_line_names = report_preferences_.shown_line_names(
      HEAT_MAP_VIEW_ENTRY[0],
    );
    const scale_choices = report_preferences_.heat_scale_choices();
    active_scale = scale_choices.find(
      (choice) => choice.value === view_preferences.heat_scale_value,
    );
    if (!active_scale) window.throw_exception_("str_error_internal");
    sort_mode = view_preferences.heat_sort_mode;
  }

  // Returns a value as a share of the test's total of the counter.
  const share_of_test = (value, counter) =>
    report_ui_.share_of_test(
      value,
      counter.get(profile_model.heatMapTotals.totals),
    );
  let share_text = report_ui_.percent_text;

  let human_text = report_ui_.human_text;
  const cell_number = (value) => ({
    text: human_text(value),
  });
  let TICKER_TAPE_HEADING = text("str_ticker_tape_heading_self");
  let HAS_CALL_GRAPH = null;

  let IS_DIFF = null;
  let function_baselines = null,
    file_baselines = null;
  let counter_baseline = () => null;
  let SHARE_LABEL = text("str_column_test_share");
  // Returns a file's, function's or line's share, a diff's of its baseline.
  let counter_share = (value, counter, baseline_cost) =>
    share_of_test(value, counter);
  function report_kind_set(first_model) {
    IS_DIFF = !!first_model.heatMapTotals.diff;
    if (IS_DIFF) {
      share_text = report_ui_.signed_percent_text;
      human_text = report_ui_.signed_human_text;
      TICKER_TAPE_HEADING = text("str_ticker_tape_heading_diff");
      SHARE_LABEL = text("str_column_baseline_share");
      counter_baseline = (cost_vector, counter) => {
        if (!cost_vector) return null;
        const baseline_cost = absolute(counter.get(cost_vector));
        return baseline_cost ? baseline_cost : null;
      };
      counter_share = (value, counter, baseline_cost) =>
        report_ui_.diff_share(value, baseline_cost);
    }
  }
  const baseline = (cost_vector) =>
    counter_baseline(cost_vector, ranking_counter);
  const ranking_share = (value, baseline_cost) =>
    counter_share(value, ranking_counter, baseline_cost);
  const ranking_share_text = (value, baseline_cost) =>
    share_text(ranking_share(value, baseline_cost));
  const line_baseline_vector = (file_path, line_number) => {
    const baseline_table =
      file_table[file_path] && file_table[file_path].baseline;
    return (baseline_table && baseline_table[line_number]) || null;
  };
  const line_baseline = (file_path, line_number) =>
    baseline(line_baseline_vector(file_path, line_number));
  const line_counter_baseline = (file_path, line_number, counter) =>
    counter_baseline(line_baseline_vector(file_path, line_number), counter);
  const file_counter_baseline = (file_path, counter) =>
    counter_baseline(file_baselines[file_path], counter);
  const file_baseline = (file_path) =>
    file_counter_baseline(file_path, ranking_counter);

  // Writes the heat colors of a cell by its share, on the chosen curve.
  const heat_style = (percent) =>
    report_ui_.heat_cell_style(percent, active_scale.curve, IS_DIFF);

  // Writes a call count as a number, in its column's own color.
  const call_count_cell = (call_count) =>
    call_count ? cell_number(call_count) : "";

  // Writes the hash of a file or a line, in the view mode given.
  const hash_for_line = (file_path, line, line_shows_functions) =>
    report_ui_.address.hash({
      test: shown_test_name,
      view: HEAT_MAP_VIEW_ENTRY[0],
      file: file_path,
      line: line || null,
      functions: line_shows_functions,
    });
  const hash_for_function = (name) =>
    report_ui_.address.function_hash(shown_test_name, name, true);
  // Returns the indexes of the functions a line declares, in name order.
  function declared_functions(file_path, line_number) {
    const file_lines = entry_line_index[file_path];
    return (file_lines && file_lines[line_number]) || [];
  }
  // Lists the lines of a file with a cost or a function, in line order.
  function known_lines(file_path) {
    const line_keys = new Set([
      ...Object.keys(file_table[file_path].lines),
      ...Object.keys(entry_line_index[file_path] || {}),
    ]);
    return [...line_keys]
      .map(Number)
      .sort((line_a, line_b) => line_a - line_b);
  }
  // Returns a line's hash in the shown mode, its costliest function's if any.
  function hash_for_location(file_path, line_number) {
    const function_indexes = declared_functions(file_path, line_number);
    if (!function_indexes.length)
      return hash_for_line(file_path, line_number, shows_functions);
    const self_cost = (function_index) =>
      absolute(ranking_value(function_table[function_index].self));
    const costliest_index = function_indexes.reduce(
      (kept_index, function_index) =>
        self_cost(function_index) > self_cost(kept_index)
          ? function_index
          : kept_index,
    );
    return report_ui_.address.function_hash(
      shown_test_name,
      function_table[costliest_index].name,
      shows_functions,
    );
  }
  // Adds cost vectors counter by counter.
  function cost_vectors_add(cost_vectors) {
    const vector_length = Math.max(
      ...cost_vectors.map((cost_vector) => cost_vector.length),
    );
    const summed_vector = [];
    for (let counter_index = 0; counter_index < vector_length; counter_index++)
      summed_vector.push(
        cost_vectors.reduce(
          (running_total, cost_vector) =>
            running_total + vector_at(cost_vector, counter_index),
          0,
        ),
      );
    return summed_vector;
  }
  // Sums the functions a line declares: self, calls and a diff's baselines.
  function declared_costs(function_indexes) {
    const vector_sum = (cost_vector_of) =>
      cost_vectors_add(function_indexes.map(cost_vector_of));
    return {
      self: vector_sum((index) => function_table[index].self),
      calls: vector_sum((index) => function_table[index].calls),
      baseline: IS_DIFF
        ? vector_sum((index) => function_baselines[index])
        : null,
    };
  }
  function function_name(index) {
    return index != null && function_table[index]
      ? function_table[index].name
      : text("str_function_name_unknown");
  }
  // Names the functions costing a line, one for most lines.
  function function_names(function_indexes) {
    return function_indexes
      .map(function_name)
      .join(DATABASE_CELL_SEPARATOR_TEXT);
  }

  function source_text(file_path) {
    const file = file_table[file_path];
    if (!file || file.source === null) return null;
    const sources = window.report_sources_;
    if (!sources || !Object.hasOwn(sources, file_path))
      window.throw_exception_("str_error_internal");
    return sources[file_path];
  }
  // Returns whether the file's source ran, else loads that source and routes.
  function sources_ready(file_path) {
    const script_name = file_table[file_path].source;
    if (script_name === null || source_scripts_loaded.has(script_name))
      return true;
    if (source_scripts_loading.has(script_name)) return false;
    source_scripts_loading.add(script_name);
    const source_script = document.createElement("script");
    source_script.src = report_ui_.address.file_href(
      REPORT_SOURCES_DIR_NAME + "/" + script_name,
    );
    source_script.addEventListener(
      "load",
      window.try_catch_handler_(() => {
        source_scripts_loading.delete(script_name);
        source_scripts_loaded.add(script_name);
        if (source_scripts_loading.size) return;
        rendered_key = "";
        route_render();
      }),
    );
    document.head.append(source_script);
    return false;
  }

  // Returns whether the heat map shows a line, one of a file with source.
  const line_is_shown = (file_path, line) =>
    line && file_table[file_path] && file_table[file_path].source !== null;
  // Writes a cell linking a line's own address, never its function's.
  function line_link_cell(file_path, line, text) {
    if (!line_is_shown(file_path, line)) return { text };
    return { text, href: hash_for_line(file_path, line, false) };
  }

  const function_is_linkable = (function_index) =>
    function_index != null &&
    function_table[function_index] &&
    line_is_shown(
      function_table[function_index].file,
      function_table[function_index].line,
    );
  // Writes a cell naming a function, linking its address when it has a line.
  function function_link_cell(function_index) {
    const name = function_name(function_index);
    if (!function_is_linkable(function_index)) return { text: name };
    return { text: name, href: hash_for_function(name) };
  }

  // Holds the source table's first column, the tree and the bar sizing it.
  const TREE_COLUMN = {
    label: text("str_heat_map_tree_label"),
    is_sized_by_bar: true,
  };
  // Asks the top page for the other tree order at a click on the tree's title.
  function title_press(pressed_column) {
    if (pressed_column !== TREE_COLUMN) return;
    report_ui_.heat_sort_toggle_send();
  }
  // Writes the cell of one selected counter, its share heat colored.
  const secondary_cell = (percent) => ({
    text: percent ? share_text(percent) : "",
    style: heat_style(percent),
  });

  let tree_root = null;
  // Builds the tree of the test's files, each costing its ranking count.
  function tree_build() {
    const root = { name: "", path: "", dirs: new Map(), files: [], self: 0 };
    function node_insert(file_path, self_cost, baseline_cost, cold) {
      const path_parts = file_path.split("/");
      let tree_node = root;
      for (
        let part_index = 0;
        part_index < path_parts.length - 1;
        part_index++
      ) {
        const segment = path_parts[part_index];
        if (!tree_node.dirs.has(segment)) {
          tree_node.dirs.set(segment, {
            name: segment,
            path: tree_node.path ? tree_node.path + "/" + segment : segment,
            dirs: new Map(),
            files: [],
            self: 0,
            base: 0,
          });
        }
        tree_node = tree_node.dirs.get(segment);
      }
      tree_node.files.push({
        name: path_parts[path_parts.length - 1],
        path: file_path,
        dirs: new Map(),
        files: [],
        self: self_cost,
        base: baseline_cost,
        cold,
        zero: self_cost === 0,
      });
    }
    for (const file_path of Object.keys(file_table)) {
      node_insert(
        file_path,
        ranking_value(file_table[file_path].self),
        file_baseline(file_path),
        false,
      );
    }
    for (const file_path of profile_model.cold) {
      node_insert(file_path, 0, null, true);
    }
    // Sums each subtree, its baseline null when none of its nodes has one.
    (function subtree_sum(tree_node) {
      let running_total = 0;
      for (const directory_node of tree_node.dirs.values())
        running_total += subtree_sum(directory_node);
      for (const file of tree_node.files) running_total += file.self;
      const child_nodes = [...tree_node.dirs.values(), ...tree_node.files];
      const baseline_costs = child_nodes
        .map((child_node) => child_node.base)
        .filter((baseline_cost) => baseline_cost !== null);
      tree_node.self = running_total;
      // A folder has no samples when no file below it has any.
      tree_node.zero = child_nodes.every((child_node) => child_node.zero);
      tree_node.base = baseline_costs.length
        ? baseline_costs.reduce(
            (baseline_sum, baseline_cost) => baseline_sum + baseline_cost,
          )
        : null;
      return running_total;
    })(root);
    // Joins a folder holding one folder and no file with it, as one node.
    (function chains_join(tree_node) {
      const joined_directories = new Map();
      for (let directory_node of tree_node.dirs.values()) {
        while (
          directory_node.files.length === 0 &&
          directory_node.dirs.size === 1
        ) {
          const [only_directory] = directory_node.dirs.values();
          directory_node = {
            ...only_directory,
            name: directory_node.name + "/" + only_directory.name,
          };
        }
        chains_join(directory_node);
        joined_directories.set(directory_node.name, directory_node);
      }
      tree_node.dirs = joined_directories;
    })(root);
    return root;
  }
  const expanded_directories = new Set(),
    expanded_cold_groups = new Set();
  // Orders tree nodes by heat when that sort is chosen, else by name.
  function node_compare(node_a, node_b) {
    const by_heat =
      sort_mode === "heat" ? absolute(node_b.self) - absolute(node_a.self) : 0;
    return by_heat || node_a.name.localeCompare(node_b.name);
  }
  // Returns the mark of a node with children, open or closed.
  const node_mark = (is_expanded) =>
    is_expanded ? HEAT_MAP_TREE_OPEN_TEXT : HEAT_MAP_TREE_CLOSED_TEXT;
  // Returns a child's branch and its children's bars, none at the top level.
  function child_branch_texts(depth, parent_bars_text, is_last) {
    if (depth === 0) return { branch_text: "", bars_text: "" };
    return {
      branch_text:
        parent_bars_text +
        (is_last
          ? HEAT_MAP_TREE_BRANCH_LAST_TEXT
          : HEAT_MAP_TREE_BRANCH_MIDDLE_TEXT),
      bars_text:
        parent_bars_text +
        (is_last
          ? " ".repeat(HEAT_MAP_TREE_BRANCH_PASS_TEXT.length)
          : HEAT_MAP_TREE_BRANCH_PASS_TEXT),
    };
  }
  const treeitem_attributes = (node_level) => ({
    role: "treeitem",
    "aria-level": node_level,
    tabindex: -1,
  });
  // Writes the branch, name and share spans that one tree node holds.
  const tree_node_inner_markup = (branch_text, name_text, share_shown) =>
    render_element(
      "span",
      { class: "heat-map-tree-node-branch-" },
      render_html_escape(branch_text + " "),
    ) +
    render_element(
      "span",
      { class: "heat-map-tree-node-name-" },
      render_html_escape(name_text),
    ) +
    render_element(
      "span",
      { class: "heat-map-tree-node-share-percent-" },
      render_html_escape(share_shown),
    );
  function tree_render() {
    // Writes the heat colors of a node.
    const node_heat_style = (tree_node) =>
      heat_style(ranking_share(tree_node.self, tree_node.base));
    // Writes the share of a node.
    const node_share_text = (tree_node) =>
      ranking_share_text(tree_node.self, tree_node.base);
    // Writes a node's children, each after its ancestors' bars and branch.
    function nodes_emit(tree_node, depth, bars_text) {
      const output_parts = [];
      const directories = [...tree_node.dirs.values()].sort(node_compare);
      const file_list = [...tree_node.files].sort(node_compare);
      // A folder with no samples lists its files with no group around them.
      const zero_cost_files = tree_node.zero
        ? []
        : file_list.filter((file) => file.zero);
      const sampled_files = file_list.filter(
        (file) => !zero_cost_files.includes(file),
      );
      const last_index =
        directories.length +
        sampled_files.length +
        (zero_cost_files.length ? 1 : 0) -
        1;
      directories.forEach((directory_node, child_index) => {
        const is_expanded = expanded_directories.has(directory_node.path);
        const heat_style_attribute = node_heat_style(directory_node);
        const branch_texts = child_branch_texts(
          depth,
          bars_text,
          child_index === last_index,
        );
        output_parts.push(
          render_element(
            "div",
            {
              class:
                "heat-map-tree-node-" + (heat_style_attribute ? " heat-" : ""),
              ...treeitem_attributes(depth + 1),
              "aria-expanded": String(is_expanded),
              "data-dir-": directory_node.path,
              ...(heat_style_attribute ? { style: heat_style_attribute } : {}),
            },
            tree_node_inner_markup(
              branch_texts.branch_text + node_mark(is_expanded),
              directory_node.name + "/",
              node_share_text(directory_node),
            ),
          ),
        );
        output_parts.push(
          render_element(
            "div",
            {
              class:
                "heat-map-tree-node-child-group-" +
                (is_expanded ? " open-" : ""),
              role: "group",
            },
            nodes_emit(directory_node, depth + 1, branch_texts.bars_text),
          ),
        );
      });
      const file_row_emit = (file, node_level, branch_text) => {
        const is_selected = file.path === current_file_path;
        const heat_style_attribute = file.cold ? "" : node_heat_style(file);
        return render_element(
          "div",
          {
            class:
              "heat-map-tree-node- file-" +
              (file.cold ? " cold-" : "") +
              (heat_style_attribute ? " heat-" : "") +
              (is_selected ? " selected-" : ""),
            ...treeitem_attributes(node_level),
            ...(is_selected ? { "aria-selected": "true" } : {}),
            "data-file-": file.path,
            ...(heat_style_attribute ? { style: heat_style_attribute } : {}),
          },
          tree_node_inner_markup(
            branch_text + HEAT_MAP_TREE_FILE_TEXT,
            file.name,
            node_share_text(file),
          ),
        );
      };
      sampled_files.forEach((file, file_index) => {
        const branch_texts = child_branch_texts(
          depth,
          bars_text,
          directories.length + file_index === last_index,
        );
        output_parts.push(
          file_row_emit(file, depth + 1, branch_texts.branch_text),
        );
      });
      if (zero_cost_files.length) {
        const is_expanded = expanded_cold_groups.has(tree_node.path);
        const branch_texts = child_branch_texts(depth, bars_text, true);
        output_parts.push(
          render_element(
            "div",
            {
              class: "heat-map-tree-node- more-",
              ...treeitem_attributes(depth + 1),
              "aria-expanded": String(is_expanded),
              "data-more-": tree_node.path,
            },
            tree_node_inner_markup(
              branch_texts.branch_text + node_mark(is_expanded),
              text("str_no_samples"),
              "",
            ),
          ),
        );
        if (is_expanded) {
          output_parts.push(
            render_element(
              "div",
              {
                class: "heat-map-tree-node-child-group- open-",
                role: "group",
              },
              zero_cost_files
                .map((file, file_index) =>
                  file_row_emit(
                    file,
                    depth + 2,
                    child_branch_texts(
                      depth + 1,
                      branch_texts.bars_text,
                      file_index === zero_cost_files.length - 1,
                    ).branch_text,
                  ),
                )
                .join(""),
            ),
          );
        }
      }
      return output_parts.join("");
    }
    const tree_had_focus =
      document.hasFocus() && tree_panel.contains(document.activeElement);
    tree_panel.innerHTML = nodes_emit(tree_root, 0, "");
    tree_tab_stop_place(tree_had_focus);
  }
  // Reads the tree's focus and scroll before the main box draws again.
  function tree_state_read() {
    return {
      had_focus:
        document.hasFocus() && tree_panel.contains(document.activeElement),
      scroll_top: tree_panel.scrollTop,
    };
  }
  // Hangs the tree from the drawn table's first title, its state kept.
  function tree_track_place(tree_state) {
    main_panel
      .querySelector("table.heat-map-source-table- > thead > tr > th")
      .append(tree_track);
    tree_render();
    // A moved tree starts at its top, so only a kept scroll lays it out.
    if (tree_state.scroll_top) tree_panel.scrollTop = tree_state.scroll_top;
    if (tree_state.had_focus) tree_tab_stop_place(true);
  }
  let tree_focus_selector = null;
  const TREE_NODE_KEY_ATTRIBUTE_NAMES = [
    "data-dir-",
    "data-file-",
    "data-more-",
  ];
  function tree_node_selector(tree_node) {
    const key_attribute_name = TREE_NODE_KEY_ATTRIBUTE_NAMES.find(
      (attribute_name) => tree_node.hasAttribute(attribute_name),
    );
    const key_value = CSS.escape(tree_node.getAttribute(key_attribute_name));
    return `.heat-map-tree-node-[${key_attribute_name}="${key_value}"]`;
  }
  function tree_visible_nodes() {
    return [...tree_panel.querySelectorAll(".heat-map-tree-node-")].filter(
      (tree_node) =>
        !tree_node.closest(".heat-map-tree-node-child-group-:not(.open-)"),
    );
  }
  function tree_parent(tree_node) {
    const holding_group = tree_node.parentElement.closest(
      ".heat-map-tree-node-child-group-",
    );
    return holding_group ? holding_group.previousElementSibling : null;
  }
  const tree_first_child = (tree_node) =>
    tree_node.nextElementSibling.querySelector(
      ":scope > .heat-map-tree-node-",
    );
  function tree_tab_stop_place(takes_focus) {
    const visible_nodes = tree_visible_nodes();
    const candidate_nodes = [
      takes_focus && tree_focus_selector
        ? tree_panel.querySelector(tree_focus_selector)
        : null,
      tree_panel.querySelector(".heat-map-tree-node-.selected-"),
      visible_nodes[0],
    ];
    const tab_stop = candidate_nodes.find((candidate_node) =>
      visible_nodes.includes(candidate_node),
    );
    if (tab_stop) report_ui_.tab_stop_move(null, tab_stop, takes_focus);
  }
  function tree_key_handler(key_event, key_name, tree_node) {
    if (report_ui_.widget_key.activates(key_name)) {
      key_event.preventDefault();
      if (!key_event.repeat) tree_node.click();
      return;
    }
    const visible_nodes = tree_visible_nodes();
    const node_index = visible_nodes.indexOf(tree_node);
    const is_open = tree_node.getAttribute("aria-expanded") === "true";
    const is_closed = tree_node.getAttribute("aria-expanded") === "false";
    let next_node = null;
    switch (key_name) {
      case WIDGET_KEY_NAMES.down:
        next_node = visible_nodes[node_index + 1];
        break;
      case WIDGET_KEY_NAMES.first:
        next_node = visible_nodes[0];
        break;
      case WIDGET_KEY_NAMES.last:
        next_node = visible_nodes[visible_nodes.length - 1];
        break;
      case WIDGET_KEY_NAMES.left:
        if (is_open) tree_node.click();
        else next_node = tree_parent(tree_node);
        break;
      case WIDGET_KEY_NAMES.right:
        if (is_closed) tree_node.click();
        else if (is_open) next_node = tree_first_child(tree_node);
        break;
      case WIDGET_KEY_NAMES.up:
        next_node = visible_nodes[node_index - 1];
        break;
      default:
        return;
    }
    key_event.preventDefault();
    if (next_node) report_ui_.tab_stop_move(tree_node, next_node, true);
  }
  tree_panel.addEventListener(
    "focusin",
    window.try_catch_handler_((focus_event) => {
      const tree_node = focus_event.target.closest(".heat-map-tree-node-");
      if (!tree_node) return;
      tree_focus_selector = tree_node_selector(tree_node);
      report_ui_.tab_stop_move(
        tree_panel.querySelector('.heat-map-tree-node-[tabindex="0"]'),
        tree_node,
        false,
      );
    }),
  );
  tree_panel.addEventListener(
    "keydown",
    window.try_catch_handler_((key_event) => {
      const key_name = report_ui_.widget_key.of(key_event);
      const tree_node = key_event.target.closest(".heat-map-tree-node-");
      if (key_name && tree_node)
        tree_key_handler(key_event, key_name, tree_node);
    }),
  );
  tree_panel.addEventListener(
    "click",
    window.try_catch_handler_((click_event) => {
      const tree_node = click_event.target.closest(".heat-map-tree-node-");
      if (!tree_node) return;
      if (tree_node.getAttribute("data-dir-") != null) {
        const file_path = tree_node.getAttribute("data-dir-");
        if (expanded_directories.has(file_path)) {
          expanded_directories.delete(file_path);
        } else expanded_directories.add(file_path);
        tree_render();
        if (expanded_directories.has(file_path)) group_opening_show(tree_node);
      } else if (tree_node.getAttribute("data-more-") != null) {
        const file_path = tree_node.getAttribute("data-more-");
        if (expanded_cold_groups.has(file_path)) {
          expanded_cold_groups.delete(file_path);
        } else expanded_cold_groups.add(file_path);
        tree_render();
        if (expanded_cold_groups.has(file_path)) group_opening_show(tree_node);
      } else if (tree_node.getAttribute("data-file-") != null) {
        if (tree_node.classList.contains("cold-")) return;
        report_ui_.address.request(
          hash_for_line(
            tree_node.getAttribute("data-file-"),
            null,
            shows_functions,
          ),
        );
      }
    }),
  );
  function group_opening_show(clicked_node) {
    const opened_node = tree_panel.querySelector(
      tree_node_selector(clicked_node),
    );
    const tree_rect = design_rect(tree_panel);
    const group_rect = design_rect(opened_node.nextElementSibling);
    if (group_rect.bottom <= tree_rect.top + tree_panel.clientHeight) return;
    tree_panel.scrollTop += group_rect.top - tree_rect.top;
  }
  // Opens every folder above a file and any no samples group holding it.
  function tree_reveal(file_path) {
    // Returns the file a node holds itself, none when a folder below holds it.
    const held_file = (holding_node) =>
      holding_node.files.find((file) => file.path === file_path);
    let tree_node = tree_root;
    while (!held_file(tree_node)) {
      tree_node = [...tree_node.dirs.values()].find((directory_node) =>
        file_path.startsWith(directory_node.path + "/"),
      );
      expanded_directories.add(tree_node.path);
    }
    if (held_file(tree_node).zero && !tree_node.zero)
      expanded_cold_groups.add(tree_node.path);
  }
  // Scrolls the tree until the selected node sits inside the shown part.
  function tree_selected_show() {
    const selected_node = tree_panel.querySelector(
      ".heat-map-tree-node-.selected-",
    );
    const tree_rect = design_rect(tree_panel);
    const node_rect = design_rect(selected_node);
    const box_bottom_px = tree_rect.top + tree_panel.clientHeight;
    if (node_rect.top < tree_rect.top)
      tree_panel.scrollTop -= tree_rect.top - node_rect.top;
    else if (node_rect.bottom > box_bottom_px)
      tree_panel.scrollTop += node_rect.bottom - box_bottom_px;
  }

  let entry_line_index = null;
  // Holds each function's callees by its index, each row the call's site.
  let function_callees = null;

  // Writes the hottest source rows of a file, of the counter source shown.
  function hottest_lines_render(file_path, source_rows) {
    const tape_lines = source_rows
      .filter(
        (source_row) =>
          source_row.costs &&
          absolute(source_row.self_percent) >=
            HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_LEAST_SHARE,
      )
      .sort(
        (tape_line_a, tape_line_b) =>
          absolute(tape_line_b.self_cost) - absolute(tape_line_a.self_cost),
      )
      .slice(0, HEAT_MAP_SOURCE_TICKER_TAPE_ENTRY_MAX_COUNT);
    if (!tape_lines.length) return "";
    // A tape of lines links each line, a tape of functions each function.
    const entry_hash = shows_functions
      ? hash_for_location
      : (tape_file_path, line_number) =>
          hash_for_line(tape_file_path, line_number, false);
    return render_element(
      "div",
      {
        class: "heat-map-source-ticker-tape-",
        role: "toolbar",
        "aria-label": TICKER_TAPE_HEADING,
      },
      tape_lines
        .map((tape_line, entry_index) =>
          render_menu_button(
            "link",
            render_html_escape(
              text_fill("str_ticker_tape_entry", {
                line: tape_line.line_number,
                share: share_text(tape_line.self_percent),
              }),
            ),
            {
              tag_name: "a",
              href: entry_hash(file_path, tape_line.line_number),
              class_names: ["heat-map-source-ticker-tape-entry-"],
              attributes: {
                tabindex: entry_index ? -1 : 0,
                style: tape_line.heat_style_attribute,
              },
            },
          ),
        )
        .join(""),
    );
  }

  // Returns what a box's counter rows read: a line, its functions or a file.
  function box_counter_source(
    file_path,
    line_number,
    line_costs,
    function_costs,
  ) {
    if (line_costs)
      return {
        cost_vector: line_costs[0],
        self_label: text("str_line_self"),
        percent: (value, counter) =>
          counter_share(
            value,
            counter,
            line_counter_baseline(file_path, line_number, counter),
          ),
      };
    if (function_costs)
      return {
        cost_vector: function_costs.self,
        self_label: text("str_column_self"),
        percent: (value, counter) =>
          counter_share(
            value,
            counter,
            counter_baseline(function_costs.baseline, counter),
          ),
      };
    return {
      cost_vector: file_table[file_path].self,
      self_label: text("str_column_self"),
      percent: (value, counter) =>
        counter_share(
          value,
          counter,
          file_counter_baseline(file_path, counter),
        ),
    };
  }
  // Lists the counter table of a box, a line's calls rows after its counters.
  function box_counter_table(
    file_path,
    line_number,
    line_costs,
    function_costs,
  ) {
    const counter_source = box_counter_source(
      file_path,
      line_number,
      line_costs,
      function_costs,
    );
    const columns = [
      { label: text("str_column_counter") },
      { label: SHARE_LABEL, numeric: true },
      { label: text("str_column_count"), numeric: true },
    ];
    const listed_counters = [
      ranking_counter,
      ...counter_list
        .filter(
          (counter) =>
            !counter.derived &&
            counter !== ranking_counter &&
            counter.get(counter_source.cost_vector),
        )
        .sort((counter_a, counter_b) =>
          counter_a.key.localeCompare(counter_b.key),
        ),
    ];
    const rows = listed_counters.map((counter, row_index) => {
      const counter_value = counter.get(counter_source.cost_vector);
      return [
        {
          text:
            (row_index ? "" : counter_source.self_label + " ") +
            counter_label(counter),
        },
        counter_value
          ? share_text(counter_source.percent(counter_value, counter))
          : "",
        counter_value ? cell_number(counter_value) : "",
      ];
    });
    const call_cost = line_costs ? ranking_value(line_costs[1]) : 0;
    if (call_cost) {
      rows.push([
        { text: text("str_column_calls") },
        ranking_share_text(call_cost, line_baseline(file_path, line_number)),
        cell_number(call_cost),
      ]);
      rows.push([
        { text: text("str_column_call_count") },
        "",
        call_count_cell(line_costs[2]),
      ]);
    }
    return { columns, rows };
  }
  // Lists the runs of lines of one line's functions, each broken by others'.
  function function_line_runs(function_indexes) {
    const own_file_path = function_table[function_indexes[0]].file;
    const is_listed = (function_index) =>
      function_indexes.includes(function_index);
    const file_paths = [
      own_file_path,
      ...Object.keys(file_table)
        .filter((other_path) => other_path !== own_file_path)
        .sort(),
    ];
    const line_runs = [];
    for (const file_path of file_paths) {
      const line_functions = file_table[file_path].lineFunctions;
      let open_run = null,
        follows_declaration = false;
      for (const line_number of known_lines(file_path)) {
        const counted_indexes = line_functions[line_number] || [];
        const declared_indexes = declared_functions(file_path, line_number);
        const is_own = counted_indexes.some(is_listed);
        // The functions' own declared line starts the block following it.
        if (declared_indexes.some(is_listed)) {
          open_run = null;
          follows_declaration = true;
        } else if (
          !is_own &&
          (counted_indexes.length || declared_indexes.length)
        ) {
          open_run = null;
          follows_declaration = false;
        }
        if (!is_own) continue;
        if (open_run) {
          open_run.last_line = line_number;
          continue;
        }
        open_run = {
          file_path,
          first_line: line_number,
          last_line: line_number,
          follows_declaration,
        };
        follows_declaration = false;
        line_runs.push(open_run);
      }
    }
    return line_runs;
  }
  // Writes a run of lines as its range, a run of one line as that line.
  const line_run_text = (line_run) =>
    line_run.first_line === line_run.last_line
      ? String(line_run.first_line)
      : text_fill("str_line_range", {
          first: line_run.first_line,
          last: line_run.last_line,
        });
  // Lists the titles of a calls table part, the caller's or the callee's.
  const calls_columns = (function_label_id) => [
    { label: text("str_column_calls"), numeric: true },
    { label: text(function_label_id) },
    { label: text("str_column_call_site") },
  ];
  // Renders a box's calls as one table: its callers, then its callees.
  function calls_table_render(caller_rows, callee_rows) {
    const callee_columns = calls_columns("str_column_callee");
    // Each part's titles lead its rows, a part with no rows left out.
    const columns = caller_rows.length
      ? calls_columns("str_column_caller")
      : callee_columns;
    const rows = [
      ...caller_rows,
      ...(caller_rows.length && callee_rows.length
        ? [{ title_columns: callee_columns }]
        : []),
      ...callee_rows,
    ];
    return {
      markup: report_ui_.render_table("heat.detail.calls", columns, rows, {
        // A row links where its linking cell does, a function or a line.
        row_href: rows.map((row) =>
          row.title_columns ? "" : row.map((cell) => cell.href).find(Boolean),
        ),
      }),
      text: report_ui_.table_markdown(columns, rows),
    };
  }
  // Sums the call rows of one function and call site, the most calls first.
  function call_rows_merge(call_rows) {
    const merged_rows = new Map();
    for (const call_row of call_rows) {
      const [function_index, call_file, call_line, , call_count] = call_row;
      const row_key = JSON.stringify([function_index, call_file, call_line]);
      const merged_row = merged_rows.get(row_key);
      if (merged_row) merged_row.call_count += call_count;
      else
        merged_rows.set(row_key, {
          function_index,
          call_file,
          call_line,
          call_count,
        });
    }
    return [...merged_rows.values()].sort(
      (row_a, row_b) => row_b.call_count - row_a.call_count,
    );
  }
  // Writes a calls row: its count, its linked function and the call's site.
  const call_row_cells = (call_row) => [
    call_count_cell(call_row.call_count),
    function_link_cell(call_row.function_index),
    { text: report_ui_.location_text(call_row.call_file, call_row.call_line) },
  ];
  // Renders the part of a box of a line's functions: lines, then calls.
  function function_part_render(function_indexes) {
    const call_rows_of = (rows_of_function) =>
      call_rows_merge(function_indexes.flatMap(rows_of_function));
    const callers = call_rows_of((index) => function_table[index].callers);
    const callees = call_rows_of((index) => function_callees[index]);
    let markup = "";
    const text_parts = [];
    // The lines' table, left out when they are one block after the function.
    const line_runs = function_line_runs(function_indexes);
    if (
      line_runs.length &&
      !(line_runs.length === 1 && line_runs[0].follows_declaration)
    ) {
      const columns = [
        { label: text("str_column_file") },
        { label: text("str_column_lines") },
      ];
      const rows = line_runs.map((line_run) => [
        { text: line_run.file_path },
        line_link_cell(
          line_run.file_path,
          line_run.first_line,
          line_run_text(line_run),
        ),
      ]);
      markup += report_ui_.render_table("heat.detail.lines", columns, rows, {
        row_href: rows.map((row) => row[1].href),
      });
      text_parts.push(report_ui_.table_markdown(columns, rows));
    }
    // A recording with calls says so where a function's callers would show.
    if (!callers.length && HAS_CALL_GRAPH) {
      const none = text("str_no_caller");
      markup += render_element("div", {}, render_html_escape(none));
      text_parts.push(none);
    }
    if (callers.length || callees.length) {
      const calls_table = calls_table_render(
        callers.map(call_row_cells),
        callees.map(call_row_cells),
      );
      markup += calls_table.markup;
      text_parts.push(calls_table.text);
    }
    return { markup, text_parts };
  }

  // Renders the box of a file, or a line's when given, with its heading.
  function information_box_render(file_path, line_number) {
    const file = file_table[file_path];
    const declared_indexes = line_number
      ? declared_functions(file_path, line_number)
      : [];
    // A line holding both its own costs and a function's shows the mode's.
    const shows_function =
      declared_indexes.length > 0 &&
      (!file.lines[line_number] || shows_functions);
    const function_indexes = shows_function ? declared_indexes : [];
    const function_costs = shows_function
      ? declared_costs(function_indexes)
      : null;
    const line_costs =
      line_number && !shows_function
        ? file.lines[line_number] || [[], [], 0]
        : null;
    const line_function_indexes =
      (line_number && file.lineFunctions[line_number]) || [];
    const counter_table = box_counter_table(
      file_path,
      line_number,
      line_costs,
      function_costs,
    );
    const location_text = report_ui_.location_text(file_path, line_number);
    // A function's box names its line's functions, a line's those costing it.
    const title_names = function_indexes.length
      ? function_indexes
          .map(function_name)
          .sort()
          .join(HEAT_MAP_INFORMATION_BOX_FUNCTION_SEPARATOR_TEXT)
      : function_names(line_function_indexes);
    const title_text = title_names
      ? text_fill("str_information_box_title", {
          location: location_text,
          function: title_names,
        })
      : location_text;
    const note_texts = [];
    if (!line_number && file.group === CALLGRIND_FILE_DATA_ERROR_CODE)
      note_texts.push(text_fill("str_not_in_repo", { path: file.raw }));
    if (!line_number && source_text(file_path) == null)
      note_texts.push(text("str_source_unavailable"));
    // The body is all the image draws, its strip filled once it is placed.
    let body_markup = render_element(
      "div",
      { class: "heat-map-source-information-box-strip-" },
      "",
    );
    body_markup += report_ui_.render_table(
      "heat.detail.stats",
      counter_table.columns,
      counter_table.rows,
      {},
    );
    // A blank line parts the notes from the counters table.
    if (note_texts.length) body_markup += render_element("br", {}, null);
    for (const note_text of note_texts) {
      body_markup += render_element(
        "div",
        { class: "heat-map-source-information-box-note-" },
        render_html_escape(note_text),
      );
    }
    const text_parts = [
      title_text +
        "\n" +
        report_ui_.table_markdown(counter_table.columns, counter_table.rows),
      ...note_texts,
    ];
    if (function_indexes.length) {
      const function_part = function_part_render(function_indexes);
      body_markup += function_part.markup;
      text_parts.push(...function_part.text_parts);
    }
    // The calls a line's box shows end it, each row linking its callee's line.
    const callees = line_costs
      ? (file.callees[line_number] || [])
          .slice()
          .sort(
            (callee_a, callee_b) =>
              ranking_value(callee_b[3]) - ranking_value(callee_a[3]),
          )
      : [];
    if (callees.length) {
      const callee_rows = callees.map(
        ([callee_index, call_file, call_line, , call_count]) => [
          call_count_cell(call_count),
          { text: function_name(callee_index) },
          line_link_cell(
            call_file,
            call_line,
            report_ui_.location_text(call_file, call_line),
          ),
        ],
      );
      const calls_table = calls_table_render([], callee_rows);
      body_markup += calls_table.markup;
      text_parts.push(calls_table.text);
    }
    // A line in one function links it as "function", in several by name.
    const linked_indexes = function_indexes.length
      ? []
      : line_function_indexes.filter(function_is_linkable);
    const link_entries = linked_indexes.map((function_index) =>
      report_ui_.strip.entry_make(
        String(function_index),
        "link",
        line_function_indexes.length === 1
          ? text("str_information_box_function")
          : function_name(function_index),
        { href: hash_for_function(function_table[function_index].name) },
      ),
    );
    // A line in several functions is titled by its links to them alone.
    const is_titled =
      function_indexes.length > 0 || line_function_indexes.length < 2;
    return {
      markup: render_element(
        "div",
        { class: "heat-map-source-information-box-" },
        render_element(
          "div",
          { class: "heat-map-source-information-box-body-" },
          body_markup,
        ),
      ),
      copy_text: text_parts.join("\n\n"),
      heading_entries: [
        ...(is_titled
          ? [report_ui_.strip.entry_make("title", "text", title_text, {})]
          : []),
        ...link_entries,
      ],
    };
  }
  // Draws a box in its cell, then its strip: heading, copy and close.
  function information_box_place(box_cell, file_path, line_number) {
    const information_box = information_box_render(file_path, line_number);
    box_cell.innerHTML = information_box.markup;
    const box_element = box_cell.firstElementChild;
    const close_entries = line_number
      ? [
          report_ui_.strip.entry_make(
            "close",
            "action",
            text("str_information_box_close"),
            { on_activate: () => detail_close(box_cell.parentElement) },
          ),
        ]
      : [];
    report_ui_.strip.render(
      box_element.querySelector(".heat-map-source-information-box-strip-"),
      [
        ...information_box.heading_entries,
        report_ui_.strip.copy_entry_make(
          () => information_box.copy_text,
          box_element.querySelector(".heat-map-source-information-box-body-"),
          shown_test_name + HEAT_MAP_DOWNLOAD_FILE_NAME_SUFFIX,
          report_ui_.location_text(file_path, line_number),
        ),
        ...close_entries,
      ],
      [],
    );
  }

  // Expands each tab to its stop, so a clip counts the columns shown.
  function tabs_expand(line_text) {
    let expanded_text = "";
    for (const character of line_text) {
      if (character !== "\t") expanded_text += character;
      else
        expanded_text += " ".repeat(
          HEAT_MAP_SOURCE_TAB_SIZE_CHARS -
            (expanded_text.length % HEAT_MAP_SOURCE_TAB_SIZE_CHARS),
        );
    }
    return expanded_text;
  }
  const file_box_row = () =>
    main_panel.querySelector("tr.heat-map-source-file-information-row-");
  // Writes a box's row, the tree's column left clear, its box cell the rest.
  const box_row_markup = (row_class, column_count) =>
    render_element(
      "tr",
      { class: row_class },
      render_element("td", {}, "") +
        render_element("td", { colspan: column_count - 1 }, ""),
    );
  // Opens the file's box above its first line, as wide as a line's box.
  function file_box_place(file_path) {
    const table_element = main_panel.querySelector(
      "table.heat-map-source-table-",
    );
    table_element.tBodies[0].insertAdjacentHTML(
      "afterbegin",
      box_row_markup(
        "heat-map-source-file-information-row-",
        table_element.tHead.rows[0].cells.length,
      ),
    );
    information_box_place(file_box_row().cells[1], file_path, 0);
  }
  // Widens the source column by what a box outgrows the titles, every chunk.
  function box_rooms_fit() {
    const table_element = main_panel.querySelector(
      "table.heat-map-source-table-",
    );
    // The sizer rows hold the room, so a change restyles them alone.
    const sizer_rows = table_element.querySelectorAll(
      ":scope > :is(thead, tbody)" +
        " > tr.table-sizer-row-:not(.table-title-copy-)",
    );
    const room_set = (room_text) => {
      for (const sizer_row of sizer_rows)
        sizer_row.style.setProperty(
          STYLE_HEAT_MAP_SOURCE_BOX_ROOM_PROPERTY,
          room_text,
        );
    };
    // A held room widens the titles, so it goes before the widths are read.
    if (
      sizer_rows[0].style.getPropertyValue(
        STYLE_HEAT_MAP_SOURCE_BOX_ROOM_PROPERTY,
      )
    )
      room_set("");
    const title_row = table_element.tHead.rows[0];
    const source_title = [...title_row.cells].find(
      (title_cell) =>
        title_cell.getAttribute("data-column-name-") ===
        TABLE_COLUMN_SOURCE_NAME,
    );
    let room_px = 0;
    for (const box_row of table_element.querySelectorAll(
      ":scope > tbody > :is(" +
        "tr.heat-map-source-line-detail-row-," +
        " tr.heat-map-source-file-information-row-)",
    )) {
      const outgrown_px =
        design_rect(box_row).width - design_rect(title_row).width;
      if (outgrown_px > 0)
        room_px = Math.max(
          room_px,
          design_rect(source_title).width + outgrown_px,
        );
    }
    if (room_px) room_set(room_px + "px");
  }

  function file_render(file_path) {
    const file = file_table[file_path];
    if (!file) window.throw_exception_("str_error_internal");
    const is_first_view = current_file_path !== file_path,
      kept_scroll_top = is_first_view ? 0 : main_panel.scrollTop;
    current_file_path = file_path;
    const file_source = source_text(file_path);
    // A file with no source shows its box alone, right of the tree's column.
    if (file_source == null) {
      source_replace(
        render_element(
          "div",
          { class: "heat-map-source-box-alone-" },
          tree_table_markup([TREE_COLUMN], []) + render_element("div", {}, ""),
        ),
      );
      const box_cell = main_panel.querySelector(
        ".heat-map-source-box-alone- > div",
      );
      information_box_place(box_cell, file_path, 0);
      report_ui_.layout_activate(box_cell);
      return;
    }
    const source_calls_cell = (source_row) => {
      const calls_percent = source_row.share(
        source_row.calls,
        ranking_counter,
      );
      return {
        text: source_row.calls ? share_text(calls_percent) : "",
        style: heat_style(calls_percent),
      };
    };
    // Writes a row's callers or callees, hottest first, each by its share.
    const source_function_list_cell = (call_rows, clip_chars) =>
      report_ui_.function_list_cell(
        call_rows
          .slice()
          .sort(
            (call_a, call_b) =>
              ranking_value(call_b[3]) - ranking_value(call_a[3]),
          )
          .map(([function_index, , , cost_vector]) => ({
            name: function_name(function_index),
            href: function_is_linkable(function_index)
              ? hash_for_function(function_table[function_index].name)
              : "",
            share_text: share_text(
              share_of_test(ranking_value(cost_vector), ranking_counter),
              false,
            ),
          })),
        clip_chars,
      );
    // Makes the part of the callers or the callees line, the calls listed.
    const source_function_list_part = (line_name, call_rows_of) => ({
      column: {
        ...report_preferences_.line_column(line_name),
        clip: STYLE_TABLE_FUNCTION_LIST_COLUMN_MAX_CHARS,
      },
      cell: (source_row, clip_chars) =>
        source_function_list_cell(call_rows_of(source_row), clip_chars),
    });
    // Holds the part of each line of calls, none for a report with no calls.
    const call_parts = HAS_CALL_GRAPH
      ? {
          [COUNTER_LIST_CALLEES_LINE_NAME]: source_function_list_part(
            COUNTER_LIST_CALLEES_LINE_NAME,
            (source_row) => source_row.callees,
          ),
          [COUNTER_LIST_CALLERS_LINE_NAME]: source_function_list_part(
            COUNTER_LIST_CALLERS_LINE_NAME,
            (source_row) => source_row.callers,
          ),
          [COUNTER_LIST_CALLS_LINE_NAME]: {
            column: report_preferences_.line_column(
              COUNTER_LIST_CALLS_LINE_NAME,
            ),
            cell: source_calls_cell,
          },
        }
      : {
          [COUNTER_LIST_CALLEES_LINE_NAME]: null,
          [COUNTER_LIST_CALLERS_LINE_NAME]: null,
          [COUNTER_LIST_CALLS_LINE_NAME]: null,
        };
    // Makes the part of a shown counter, the ranking counter's the self costs.
    function source_counter_part(counter_name) {
      if (counter_name === RANKING_COUNTER_NAME)
        return {
          column: report_preferences_.line_column(counter_name),
          cell: (source_row) => ({
            text: source_row.self_cost
              ? share_text(source_row.self_percent)
              : "",
            style: source_row.heat_style_attribute,
          }),
        };
      const secondary = counter_find(counter_name);
      if (!secondary) window.throw_exception_("str_error_internal");
      return {
        column: report_preferences_.line_column(counter_name),
        cell: (source_row) => {
          if (!source_row.costs) return "";
          const counter_value = secondary.get(source_row.costs[0]);
          return secondary_cell(source_row.share(counter_value, secondary));
        },
      };
    }
    const line_parts = report_preferences_.shown_line_parts(
      HEAT_MAP_VIEW_ENTRY[0],
      source_counter_part,
      call_parts,
    );

    const source_rows = [],
      attrs = [];
    const source_row_emit = (line_number, text) => {
      const line_costs = file.lines[line_number] || null;
      const function_indexes = declared_functions(file_path, line_number);
      // A function line holds its functions' costs, summed, beside its own.
      const function_costs = function_indexes.length
        ? declared_costs(function_indexes)
        : null;
      const function_row_costs = function_costs
        ? [function_costs.self, function_costs.calls]
        : null;
      // Each cell of a row reads the one source the view mode shows.
      const row_costs = shows_functions ? function_row_costs : line_costs;
      const hidden_costs = shows_functions ? line_costs : function_row_costs;
      const row_share = (value, counter) =>
        counter_share(
          value,
          counter,
          shows_functions && function_costs
            ? counter_baseline(function_costs.baseline, counter)
            : line_counter_baseline(file_path, line_number, counter),
        );
      const self_cost = row_costs ? ranking_value(row_costs[0]) : 0,
        calls = row_costs ? ranking_value(row_costs[1]) : 0;
      const self_percent = row_share(self_cost, ranking_counter);
      const heat_style_attribute = heat_style(self_percent);
      // A row of hidden costs alone takes the menu's colors, still clickable.
      const class_names = [
        (row_costs || hidden_costs) && line_number ? "clickable-" : "",
        function_indexes.length ? "function-entry-" : "",
        !row_costs && hidden_costs ? "other-counter-source-" : "",
      ]
        .filter(Boolean)
        .join(" ");
      // A line making a call shows the call chevron, else an entry's chevron.
      const marker_text = file.callees[line_number]
        ? HEAT_MAP_SOURCE_CALL_SITE_MARKER_TEXT
        : function_indexes.length
          ? HEAT_MAP_SOURCE_FUNCTION_ENTRY_MARKER_TEXT
          : "";
      attrs.push({
        id: `L${line_number}-`,
        ...(class_names ? { class: class_names } : {}),
        "data-line-number-": line_number,
      });
      source_rows.push({
        calls,
        callees: (!shows_functions && file.callees[line_number]) || [],
        callers: shows_functions
          ? function_indexes.flatMap(
              (function_index) => function_table[function_index].callers,
            )
          : [],
        costs: row_costs,
        heat_style_attribute,
        line_number,
        marker_text,
        self_cost,
        self_percent,
        share: row_share,
        text,
      });
    };
    const source_lines = file_source.split("\n");
    if (source_lines.length && source_lines[source_lines.length - 1] === "") {
      source_lines.pop();
    }
    for (let line_index = 0; line_index < source_lines.length; line_index++) {
      source_row_emit(line_index + 1, source_lines[line_index]);
    }
    for (const line_number of known_lines(file_path)) {
      if (line_number > source_lines.length)
        source_row_emit(line_number, text("str_source_beyond_end"));
    }

    const line_number_column = {
      label: text("str_column_line"),
      name: TABLE_COLUMN_LINE_NAME,
      numeric: true,
      cls: "heat-map-source-table-line-number-cell-",
    };
    // Each line fills the column, a chevron left and the number right.
    const line_number_column_chars = source_rows.reduce(
      (widest_chars, source_row) =>
        Math.max(
          widest_chars,
          source_row.marker_text.length +
            String(source_row.line_number).length,
        ),
      line_number_column.label.length,
    );
    const source_column = {
      label: text("str_column_source"),
      name: TABLE_COLUMN_SOURCE_NAME,
      clip: HEAT_MAP_SOURCE_VIEW_WIDTH_CHARS,
      cls: "heat-map-source-table-code-cell-",
    };
    // Holds the parts no line of the counters list shows, first until moved.
    const fixed_parts = [
      { column: TREE_COLUMN, cell: () => "" },
      {
        column: line_number_column,
        cell: (source_row) => ({
          text:
            source_row.marker_text +
            String(source_row.line_number).padStart(
              line_number_column_chars - source_row.marker_text.length,
            ),
          style: source_row.heat_style_attribute,
        }),
      },
      {
        column: source_column,
        cell: (source_row) => ({
          text: tabs_expand(source_row.text),
          style: source_row.heat_style_attribute,
        }),
      },
    ];
    const column_parts = [...fixed_parts, ...line_parts];
    const markup = report_ui_.render_record_table(
      "heat.src",
      column_parts,
      source_rows,
      {
        row_attributes: attrs,
        cls: "heat-map-source-table-",
        counter_list_key: HEAT_MAP_VIEW_ENTRY[0],
        is_chunked: true,
        on_redraw: source_redraw,
        on_sort: (column_index) =>
          title_press(column_parts[column_index].column),
        sorted_column_index: null,
      },
    );
    const tree_state = tree_state_read();
    main_panel.innerHTML = render_element(
      "div",
      { class: "heat-map-source-" },
      markup,
    );
    file_box_place(file_path);
    ticker_tape_box.innerHTML = hottest_lines_render(file_path, source_rows);
    tree_track_place(tree_state);
    report_ui_.table_rows.attach(
      main_panel.querySelector("table.heat-map-source-table-"),
      "tr[data-line-number-]",
    );
    // The minimap's column is decided before the bars draw for it.
    minimap_build();
    report_ui_.layout_activate(main_panel);
    main_panel.scrollTop = kept_scroll_top;
    minimap_sync();
  }

  // Shows the file box at the top of the view.
  function file_box_show() {
    main_panel.scrollTop = 0;
    minimap_sync();
  }
  // Shows the drawn address again: its file's tree node, then the file box.
  function file_address_show(file_path, line) {
    tree_reveal(file_path);
    tree_render();
    tree_selected_show();
    if (!line) file_box_show();
  }

  function design_rect(element) {
    const rect = element.getBoundingClientRect();
    return {
      bottom: report_ui_.design_px(rect.bottom),
      height: report_ui_.design_px(rect.height),
      top: report_ui_.design_px(rect.top),
      width: report_ui_.design_px(rect.width),
    };
  }

  function row_is_visible(row_element) {
    const row_rect = design_rect(row_element);
    const main_rect = design_rect(main_panel);
    return (
      row_rect.top >=
        main_rect.top + covered_height(row_element.closest("table")) &&
      row_rect.bottom <= main_rect.top + main_panel.clientHeight
    );
  }

  function covered_height(table_element) {
    return design_rect(table_element.tHead.rows[0].cells[0]).height;
  }

  // Scrolls a row to lie the set count of its own heights below the titles.
  function row_top_place(row_element) {
    const cover = covered_height(row_element.closest("table"));
    const row_rect = design_rect(row_element);
    const main_rect = design_rect(main_panel);
    main_panel.scrollTop +=
      row_rect.top -
      main_rect.top -
      cover -
      HEAT_MAP_SOURCE_SHOWN_LINE_ROWS_ABOVE * row_rect.height;
  }

  let scale_factor = 1,
    clone_height_px = 0,
    clone_line_count = 0,
    clone_line_height_px = 0,
    clone_box_row = null,
    minimap_build_number = 0;
  // Sizes the minimap again as the source's rows take their drawn heights.
  const source_resize_observer = new ResizeObserver(
    window.try_catch_handler_(() => minimap_size()),
  );
  // Empties the minimap, its column kept until a build or a clear decides.
  function minimap_empty() {
    minimap_build_number++;
    source_resize_observer.disconnect();
    minimap_box.innerHTML = "";
    minimap_viewport.hidden = true;
  }
  function minimap_clear() {
    minimap_empty();
    minimap_panel.classList.add("empty-");
  }
  // Holds the room of a source taller than the view, filled before the paint.
  function minimap_build() {
    minimap_empty();
    const table_element = main_panel.querySelector(
      "table.heat-map-source-table-",
    );
    const source_top_px = design_rect(
      main_panel.querySelector(".heat-map-source-"),
    ).top;
    // The minimap's column widens the source alone, so its height holds.
    const is_taller =
      design_rect(table_element).bottom - source_top_px >
      main_panel.clientHeight;
    minimap_panel.classList.toggle("empty-", !is_taller);
    if (!is_taller) return;
    source_resize_observer.observe(table_element);
    minimap_fill_request();
  }
  // Fills a shown minimap before the paint, a later request replacing it.
  function minimap_fill_request() {
    if (minimap_panel.classList.contains("empty-")) return;
    const build_number = ++minimap_build_number;
    requestAnimationFrame(
      window.try_catch_handler_(() => {
        if (build_number === minimap_build_number)
          minimap_fill(
            main_panel.querySelector("table.heat-map-source-table-"),
          );
      }),
    );
  }
  // Writes the source's lines as one block, a colored line its band.
  function minimap_fill(table_element) {
    const line_markups = [];
    let box_row = null;
    for (const source_row of table_element.querySelectorAll(
      ":scope > tbody > :is(tr[data-line-number-]," +
        " tr.heat-map-source-line-detail-row-)",
    )) {
      // A line's open box is a gap in the minimap, sized once it is drawn.
      if (!source_row.hasAttribute("data-line-number-")) {
        box_row = source_row;
        line_markups.push(
          render_element("span", { class: "heat-map-minimap-box-gap-" }, ""),
        );
        continue;
      }
      const code_cell = source_row.querySelector(
        ":scope > td.heat-map-source-table-code-cell-",
      );
      // An empty line draws no line box, as an empty cell has no height.
      if (!code_cell.textContent) continue;
      const line_markup = render_html_escape(code_cell.textContent);
      const cell_style = code_cell.getAttribute("style");
      const band_attributes = cell_style
        ? { class: "heat-map-minimap-band-", style: cell_style }
        : code_cell.parentElement.classList.contains("other-counter-source-")
          ? { class: "heat-map-minimap-band- other-counter-source-" }
          : null;
      line_markups.push(
        band_attributes
          ? render_element("span", band_attributes, line_markup)
          : line_markup,
      );
    }
    minimap_box.innerHTML = render_element("pre", {}, line_markups.join("\n"));
    clone_line_count = line_markups.length;
    clone_line_height_px =
      minimap_box.firstElementChild.offsetHeight / clone_line_count;
    clone_box_row = box_row;
    minimap_viewport.hidden = false;
    minimap_size();
  }
  // Sizes a filled minimap to the source's rows as drawn, then lays it out.
  function minimap_size() {
    if (minimap_viewport.hidden) return;
    const clone_element = minimap_box.firstElementChild;
    // The gap holds the box at the scale the minimap holds the source lines.
    if (clone_box_row) {
      const box_height_px = design_rect(clone_box_row).height;
      const source_height_px = geometry_measure().rows - box_height_px;
      clone_element.querySelector(".heat-map-minimap-box-gap-").style.height =
        (box_height_px * (clone_line_count - 1) * clone_line_height_px) /
          source_height_px +
        "px";
    }
    clone_height_px = clone_element.offsetHeight;
    minimap_layout();
  }

  function minimap_layout() {
    if (minimap_viewport.hidden) return;
    const band_width_px = minimap_panel.clientWidth,
      band_height_px = minimap_panel.clientHeight;
    scale_factor = Math.min(
      1,
      band_width_px /
        (HEAT_MAP_SOURCE_VIEW_WIDTH_CHARS *
          report_ui_.design_character_width_px),
      band_height_px / clone_height_px,
    );
    minimap_box.style.transform = `scale(${scale_factor})`;
    minimap_box.style.transformOrigin = "top left";
    minimap_box.style.width = band_width_px / scale_factor + "px";
    minimap_sync();
  }

  function geometry_measure() {
    const table_element = main_panel.querySelector(
      "table.heat-map-source-table-",
    );
    const main = design_rect(main_panel);
    const body_bottom_px = design_rect(table_element).bottom;
    // The rows the minimap clones start below the file box's row, a box too.
    const code_top_px = design_rect(file_box_row()).bottom;
    const clone_body = {
      height: body_bottom_px - code_top_px,
      top: code_top_px,
    };
    const rows = clone_body.height;
    const rows_above = (y_position_px) =>
      Math.max(0, Math.min(rows, y_position_px - clone_body.top));
    return {
      rows,
      above: rows_above,
      cover: covered_height(table_element),
      body: clone_body,
      top: main.top,
      bottom: main.top + main_panel.clientHeight,
      head: design_rect(table_element.tHead.rows[0].cells[0]).bottom,
    };
  }
  function minimap_sync() {
    if (minimap_viewport.hidden) return;
    const geometry = geometry_measure(),
      scaled_height_px = clone_height_px * scale_factor;
    const row_start = geometry.above(geometry.head),
      row_end = geometry.above(geometry.bottom);
    const box_height_px = Math.max(
      HEAT_MAP_MINIMAP_VIEWPORT_BOX_SMALLEST_PX,
      (scaled_height_px * (row_end - row_start)) / geometry.rows,
    );
    const box_top_px = Math.min(
      scaled_height_px - box_height_px,
      (scaled_height_px * row_start) / geometry.rows,
    );
    minimap_viewport.style.top = Math.max(0, box_top_px) + "px";
    minimap_viewport.style.height = box_height_px + "px";
  }

  function scroll_to_row(row) {
    const geometry = geometry_measure();
    row = Math.max(0, Math.min(geometry.rows, row));
    const y_position_px =
      geometry.body.top -
      geometry.top +
      main_panel.scrollTop +
      row -
      geometry.cover;
    const maximum_scroll_px =
      main_panel.scrollHeight - main_panel.clientHeight;
    main_panel.scrollTop = Math.max(
      0,
      Math.min(maximum_scroll_px, y_position_px),
    );
  }
  main_panel.addEventListener(
    "scroll",
    window.try_catch_handler_(minimap_sync),
  );
  // Centres the view on a pressed row outside the box, then drags the box.
  minimap_panel.addEventListener(
    "pointerdown",
    window.try_catch_handler_((press_event) => {
      if (press_event.button || minimap_viewport.hidden) return;
      press_event.preventDefault();
      const scaled_height_px = clone_height_px * scale_factor;
      if (!minimap_viewport.contains(press_event.target)) {
        const geometry = geometry_measure();
        const pressed_px =
          report_ui_.design_px(press_event.clientY) -
          design_rect(minimap_box).top;
        scroll_to_row(
          (pressed_px / scaled_height_px) * geometry.rows -
            (main_panel.clientHeight - geometry.cover) / 2,
        );
        minimap_sync();
      }
      const start_top_px = minimap_viewport.offsetTop;
      minimap_viewport.classList.add("drag-");
      minimap_panel.setPointerCapture(press_event.pointerId);
      const pointer_move = window.try_catch_handler_((move_event) => {
        if (move_event.pointerId !== press_event.pointerId) return;
        scroll_to_row(
          ((start_top_px +
            report_ui_.design_px(move_event.clientY - press_event.clientY)) /
            scaled_height_px) *
            geometry_measure().rows,
        );
      });
      const pointer_release = window.try_catch_handler_((release_event) => {
        if (release_event.pointerId !== press_event.pointerId) return;
        minimap_viewport.classList.remove("drag-");
        report_ui_.listeners_bind(
          minimap_panel,
          pointer_move,
          pointer_release,
          false,
        );
      });
      report_ui_.listeners_bind(
        minimap_panel,
        pointer_move,
        pointer_release,
        true,
      );
    }),
  );

  function detail_line() {
    const detail_row = main_panel.querySelector(
      "tr.heat-map-source-line-detail-row-",
    );
    if (!detail_row) return 0;
    return +detail_row.previousElementSibling.getAttribute(
      "data-line-number-",
    );
  }

  // Shows a line, its box open below it, its row at a kept top if given.
  function detail_set(line, kept_top) {
    if (line === detail_line()) return;
    for (const detail_row of main_panel.querySelectorAll(
      "tr.heat-map-source-line-detail-row-",
    )) {
      detail_row.remove();
    }
    const row = line ? document.getElementById("L" + line + "-") : null;
    if (row) detail_open(current_file_path, line, row);
    box_rooms_fit();
    if (row) {
      report_ui_.table_rows.tab_stop_set(row, false);
      if (kept_top !== null)
        main_panel.scrollTop += design_rect(row).top - kept_top;
      else line_show(line);
    }
    minimap_fill_request();
  }
  // Places a line near the view's top when the line is out of view.
  function line_show(line) {
    const row = document.getElementById("L" + line + "-");
    if (!row_is_visible(row)) row_top_place(row);
  }
  // Jumps to a box row's address, its line placed only when out of view.
  function box_row_jump(jump_hash) {
    const shown_hash = report_ui_.address.hash(
      report_ui_.address.of_hash(location.hash),
    );
    if (jump_hash !== shown_hash) {
      jumped_hash = jump_hash;
      report_ui_.address.request(jump_hash);
      return;
    }
    // The address shown stays, its line's row taking the focus a jump gives.
    line_show(rendered_line);
    minimap_sync();
    report_ui_.table_rows.tab_stop_set(
      document.getElementById("L" + rendered_line + "-"),
      true,
    );
  }
  function detail_close(detail_row) {
    report_ui_.table_rows.tab_stop_set(
      detail_row.previousElementSibling,
      true,
    );
    detail_row.remove();
    box_rooms_fit();
    minimap_fill_request();
  }
  // Opens a line's box below its row.
  function detail_open(file_path, line_number, row) {
    row.insertAdjacentHTML(
      "afterend",
      box_row_markup("heat-map-source-line-detail-row-", row.cells.length),
    );
    const detail_row = row.nextElementSibling;
    information_box_place(detail_row.cells[1], file_path, line_number);
    report_ui_.layout_activate(detail_row);
  }
  main_panel.addEventListener(
    "click",
    window.try_catch_handler_((click_event) => {
      // A box table's row, its link too, jumps from here, not from the page.
      const jump_hash =
        click_event.target.closest(
          ".heat-map-source-information-box- tr.row-link-",
        ) && report_ui_.address.link_hash(click_event);
      if (jump_hash) {
        click_event.preventDefault();
        return box_row_jump(jump_hash);
      }
      if (click_event.target.closest("a")) return;
      const row = click_event.target.closest("tr.clickable-");
      if (row && current_file_path) {
        const line_number = +row.getAttribute("data-line-number-");
        const row_top = design_rect(row).top;
        // A pressed line's box opens with its row left where it lies.
        if (line_number === detail_line())
          detail_close(row.nextElementSibling);
        else if (line_number === rendered_line)
          detail_set(line_number, row_top);
        else {
          pressed_row_place = { line: line_number, top: row_top };
          report_ui_.address.request(
            hash_for_location(current_file_path, line_number),
          );
        }
      }
    }),
  );
  function ticker_tape_key_handler(key_event, key_name, ticker_tape_entry) {
    if (report_ui_.widget_key.activates(key_name)) {
      key_event.preventDefault();
      if (!key_event.repeat) ticker_tape_entry.click();
      return;
    }
    const tape_entries = [
      ...ticker_tape_entry.parentElement.querySelectorAll(
        ".heat-map-source-ticker-tape-entry-",
      ),
    ];
    const entry_index = tape_entries.indexOf(ticker_tape_entry);
    let next_index = 0;
    switch (key_name) {
      case WIDGET_KEY_NAMES.down:
      case WIDGET_KEY_NAMES.right:
        next_index = entry_index + 1;
        break;
      case WIDGET_KEY_NAMES.first:
        next_index = 0;
        break;
      case WIDGET_KEY_NAMES.last:
        next_index = tape_entries.length - 1;
        break;
      case WIDGET_KEY_NAMES.left:
      case WIDGET_KEY_NAMES.up:
        next_index = entry_index - 1;
        break;
      default:
        return;
    }
    key_event.preventDefault();
    const next_entry = tape_entries[next_index];
    if (next_entry)
      report_ui_.tab_stop_move(ticker_tape_entry, next_entry, true);
  }
  ticker_tape_box.addEventListener(
    "focusin",
    window.try_catch_handler_((focus_event) => {
      const ticker_tape_entry = focus_event.target;
      report_ui_.tab_stop_move(
        ticker_tape_entry.parentElement.querySelector(
          ':scope > [tabindex="0"]',
        ),
        ticker_tape_entry,
        false,
      );
    }),
  );
  ticker_tape_box.addEventListener(
    "keydown",
    window.try_catch_handler_((key_event) => {
      const key_name = report_ui_.widget_key.of(key_event);
      if (key_name)
        ticker_tape_key_handler(key_event, key_name, key_event.target);
    }),
  );
  main_panel.addEventListener(
    "keydown",
    window.try_catch_handler_((key_event) => {
      const key_name = report_ui_.widget_key.of(key_event);
      if (key_name !== WIDGET_KEY_NAMES.close) return;
      const detail_row = main_panel.querySelector(
        "tr.heat-map-source-line-detail-row-",
      );
      if (!detail_row) return;
      const is_in_detail =
        detail_row.contains(key_event.target) ||
        detail_row.previousElementSibling === key_event.target;
      if (!is_in_detail) return;
      key_event.preventDefault();
      detail_close(detail_row);
    }),
  );

  const source_scripts_loaded = new Set();
  const source_scripts_loading = new Set();
  let rendered_line = 0;
  // Holds the line a press asked for and the top its row lay at, else null.
  let pressed_row_place = null;
  // Holds the address a box row jumped to until its route draws it, else null.
  let jumped_hash = null;
  let rendered_key = "";
  let routed_hash = null;
  let is_routing = false;
  let load_render_log = null;
  // Builds the tree, each top level folder with samples open.
  function ranking_tree_build() {
    tree_root = tree_build();
    for (const directory_node of tree_root.dirs.values())
      if (!directory_node.zero) expanded_directories.add(directory_node.path);
  }
  // Renders again what relayed preferences change, the first relay routing.
  function preferences_apply() {
    if (!is_routing) {
      is_routing = true;
      window.addEventListener(
        "hashchange",
        window.try_catch_handler_(route_render),
      );
      route_render();
      return;
    }
    if (profile_model === null) return;
    const tree_sort_mode = sort_mode,
      kept_key = rendered_key;
    preferences_handler();
    route_render();
    if (rendered_key === kept_key && sort_mode !== tree_sort_mode)
      tree_render();
  }
  // Takes a relayed message, rendering again when its preferences changed.
  function relay_handler(message_data) {
    if (report_preferences_.relay_handler(message_data)) preferences_apply();
  }
  // Writes the note of a file or function the test recorded no samples for.
  const no_samples_note_markup = (unsampled_name) =>
    render_html_escape(
      text_fill("str_no_samples_in_test", { name: unsampled_name }),
    );
  // Writes a table led by the tree's column, as the source table is.
  const tree_table_markup = (tree_columns, tree_rows) =>
    report_ui_.render_table("heat.note", tree_columns, tree_rows, {
      cls: "heat-map-source-table-",
      on_sort: (column_index) => title_press(tree_columns[column_index]),
      sorted_column_index: null,
    });
  // Shows markup in place of a file's source, the tree kept in its column.
  function source_replace(panel_markup) {
    ticker_tape_box.replaceChildren();
    const tree_state = tree_state_read();
    main_panel.innerHTML = panel_markup;
    main_panel.scrollTop = 0;
    tree_track_place(tree_state);
    report_ui_.layout_activate(main_panel);
    minimap_clear();
  }
  // Shows a note in place of a file's source, the tree kept in its column.
  function unavailable_note_render(note_markup) {
    current_file_path = null;
    source_replace(
      tree_table_markup(
        [TREE_COLUMN, { label: text("str_column_source") }],
        [["", { html: note_markup }]],
      ),
    );
  }
  function main_focus_restore(main_had_focus) {
    if (!main_had_focus || main_panel.contains(document.activeElement)) return;
    const addressed_row = rendered_line
      ? document.getElementById("L" + rendered_line + "-")
      : null;
    if (addressed_row) report_ui_.table_rows.tab_stop_set(addressed_row, true);
    else main_panel.focus({ preventScroll: true });
  }
  function route_render() {
    // The tree in the main box keeps its own focus through a draw.
    const main_had_focus =
      document.hasFocus() &&
      main_panel.contains(document.activeElement) &&
      !tree_panel.contains(document.activeElement);
    const page_address = report_ui_.address.of_hash(location.hash);
    if (page_address.view !== HEAT_MAP_VIEW_ENTRY[0])
      window.throw_exception_("str_error_internal");
    if (profile_model === null || page_address.test !== shown_test_name) {
      model_load(page_address.test);
      return;
    }
    shows_functions = page_address.functions;
    const pressed_place = pressed_row_place;
    pressed_row_place = null;
    const is_new_address = location.hash !== routed_hash,
      is_detail_closed = !is_new_address && !detail_line(),
      previous_file_path = current_file_path;
    let file = page_address.file,
      line = page_address.line === null ? 0 : page_address.line,
      fn = page_address.function;
    let note_markup = "";
    if (fn) {
      const function_entry = function_table.find(
        (candidate) => candidate.name === fn,
      );
      if (
        function_entry &&
        line_is_shown(function_entry.file, function_entry.line)
      ) {
        file = function_entry.file;
        line = function_entry.line;
      } else if (source_database.functions.includes(fn)) {
        note_markup = no_samples_note_markup(fn);
      } else {
        window.throw_exception_("str_error_hash_function_unknown", fn);
      }
    } else if (!file_table[file]) {
      if (!source_database.files.includes(file)) {
        window.throw_exception_("str_error_hash_file_unknown", file);
      }
      note_markup = no_samples_note_markup(file);
    }
    if (!note_markup && !sources_ready(file)) return;
    routed_hash = location.hash;
    const is_jump = jumped_hash === report_ui_.address.hash(page_address);
    jumped_hash = null;
    if (is_new_address && fn && !note_markup)
      report_ui_.function_location_send({
        test: page_address.test,
        function: fn,
        file,
        line,
      });
    if (note_markup) {
      rendered_key = "";
      unavailable_note_render(note_markup);
      rendered_line = line;
      main_focus_restore(main_had_focus);
      load_render_finish();
      return;
    }

    // A new file draws its source and the tree, so its tree node opens first.
    const moves_tree = is_new_address && file !== previous_file_path;
    if (moves_tree) tree_reveal(file);
    const key = [
      file,
      active_scale.value,
      shows_functions,
      ...shown_line_names,
    ].join("\n");
    const is_drawn = key !== rendered_key;
    if (is_drawn) {
      rendered_key = key;
      file_render(file);
    }
    if (line && !main_panel.querySelector(`tr[data-line-number-="${line}"]`))
      window.throw_exception_("str_error_hash_line_unknown", file, line);
    // A new line box fits the boxes' room, else a drawn source fits it here.
    if (!is_detail_closed && line !== detail_line())
      detail_set(
        line,
        pressed_place && pressed_place.line === line
          ? pressed_place.top
          : null,
      );
    else if (is_drawn && source_text(file) != null) box_rooms_fit();
    // A jump's line already open is placed as a newly opened one is.
    if (is_jump && line) {
      line_show(line);
      minimap_sync();
    }
    if (moves_tree) tree_selected_show();
    if (is_new_address && !line) file_box_show();
    rendered_line = line;
    main_focus_restore(main_had_focus);
    load_render_finish();
  }
  // Draws the source again for a new clip or column place, its open line kept.
  function source_redraw() {
    rendered_key = "";
    route_render();
  }
  // Logs the view's load render once the first route has drawn.
  function load_render_finish() {
    if (load_render_log === null) return;
    load_render_log();
    load_render_log = null;
  }
  function model_load(test_name) {
    const held_models = window.report_heat_map_models_;
    if (held_models && held_models[test_name]) {
      model_switch(test_name, held_models[test_name]);
      route_render();
      return;
    }
    const model_script = document.createElement("script");
    model_script.src =
      HEAT_MAP_MODEL_DIR_NAME + "/" + encodeURIComponent(test_name) + ".js";
    model_script.addEventListener(
      "error",
      window.try_catch_handler_(() => {
        window.throw_exception_("str_error_internal");
      }),
    );
    model_script.addEventListener(
      "load",
      window.try_catch_handler_(() => {
        const loaded_models = window.report_heat_map_models_;
        if (!loaded_models || !loaded_models[test_name])
          window.throw_exception_("str_error_internal");
        route_render();
      }),
    );
    document.head.append(model_script);
  }
  function model_switch(test_name, test_model) {
    if (IS_DIFF === null) report_kind_set(test_model);
    shown_test_name = test_name;
    profile_model = test_model;
    file_table = test_model.files;
    function_table = test_model.functions;
    function_baselines = test_model.functionBaseline || [];
    file_baselines = test_model.fileBaseline || {};
    HAS_CALL_GRAPH = function_table.some(
      (function_entry) => function_entry.callers.length > 0,
    );
    entry_line_index = {};
    function_table.forEach((function_entry, index) => {
      if (!function_entry.line) return;
      entry_line_index[function_entry.file] =
        entry_line_index[function_entry.file] || {};
      const file_lines = entry_line_index[function_entry.file];
      file_lines[function_entry.line] = file_lines[function_entry.line] || [];
      file_lines[function_entry.line].push(index);
    });
    // A caller's row of a function is that caller's callee row of it.
    function_callees = function_table.map(() => []);
    function_table.forEach((function_entry, callee_index) => {
      for (const [caller_index, ...call_fields] of function_entry.callers)
        function_callees[caller_index].push([callee_index, ...call_fields]);
    });
    counters_build();
    expanded_directories.clear();
    expanded_cold_groups.clear();
    current_file_path = null;
    rendered_key = "";
    preferences_handler();
    ranking_tree_build();
  }
  function address_recenter() {
    if (!current_file_path) {
      rendered_key = "";
      routed_hash = null;
      route_render();
      return;
    }
    file_address_show(current_file_path, rendered_line);
    if (!rendered_line) return;
    detail_set(rendered_line, null);
    row_top_place(document.getElementById("L" + rendered_line + "-"));
  }

  report_ui_.view_activate({
    forwards_input: true,
    load_render_defer: (render_log) => {
      load_render_log = render_log;
    },
    recenter: address_recenter,
    relay_handler,
  });

  report_ui_.resize_settle_register(minimap_layout);
})();
