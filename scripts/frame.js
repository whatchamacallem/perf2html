// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE-MIT.md file.

window.try_catch_handler_(function () {
  "use strict";

  const DARK_MODE_FRAME_QUERY_KEY_NAME = settings_(
    "DARK_MODE_FRAME_QUERY_KEY_NAME",
  );
  const DARK_MODE_TOGGLE_QUERY_KEY_NAME = settings_(
    "DARK_MODE_TOGGLE_QUERY_KEY_NAME",
  );
  const REGULAR_REPORT_VIEW_KEYS = settings_("REGULAR_REPORT_VIEW_KEYS");
  const SCREENSHOT_MENU_KEY_NUMBER = settings_("SCREENSHOT_MENU_KEY_NUMBER");
  const VIEW_UNSUPPORTED_USER_AGENT_TOKENS = settings_(
    "VIEW_UNSUPPORTED_USER_AGENT_TOKENS",
  );

  const home_panel = window.report_ui_.home_panel;
  const loaded_hash = location.hash;
  const loaded_menu_entry_number = new URLSearchParams(location.search).get(
    SCREENSHOT_MENU_KEY_NUMBER,
  );
  const menu_strip = document.getElementById("menu-");
  const counter_names = JSON.parse(
    menu_strip.getAttribute("data-counter-names-"),
  );
  const is_regular_report =
    menu_strip.getAttribute("data-regular-report-") === "1";
  const test_names = JSON.parse(menu_strip.getAttribute("data-test-names-"));
  const view_frame = window.report_ui_.view_frame;

  let current_address = null;
  let focused_path_entries = [];
  let function_location = null;
  // The loaded page's dark mode query, which that page's new hashes keep.
  let loaded_mode_query = "";
  let loaded_page_href = "";
  let loaded_view_href = "";
  let view_mode_link = null;

  function address_now() {
    return current_address;
  }
  // Returns the focused path entries the call graph last sent, root first.
  function focused_path_now() {
    return focused_path_entries;
  }
  // Returns the function location the heat map last sent, null before one.
  function function_location_now() {
    return function_location;
  }
  // Returns the drawn address and other mode place the heat map last sent.
  function view_mode_link_now() {
    return view_mode_link;
  }
  // Returns whether this report holds a view's page, a diff holding fewer.
  function view_has_page(view_key) {
    return is_regular_report || !REGULAR_REPORT_VIEW_KEYS.includes(view_key);
  }
  // Returns whether this browser runs a view, as its user agent string tells.
  function view_browser_runs(view_key) {
    if (!Object.hasOwn(VIEW_UNSUPPORTED_USER_AGENT_TOKENS, view_key))
      return true;
    return !VIEW_UNSUPPORTED_USER_AGENT_TOKENS[view_key].some((agent_token) =>
      navigator.userAgent.includes(agent_token),
    );
  }
  // Returns the query's menu entry number while the loaded address shows.
  function menu_entry_number_now() {
    return location.hash === loaded_hash ? loaded_menu_entry_number : null;
  }
  function address_check(parsed_address) {
    if (
      parsed_address.test !== null &&
      !test_names.includes(parsed_address.test)
    )
      window.throw_exception_(
        "str_error_hash_test_unknown",
        parsed_address.test,
      );
    if (!view_has_page(parsed_address.view))
      window.throw_exception_(
        "str_error_hash_view_page_missing",
        parsed_address.view,
      );
    if (!view_browser_runs(parsed_address.view))
      window.throw_exception_(
        "str_error_hash_view_browser_unsupported",
        parsed_address.view,
      );
  }
  // Drops the dark mode toggle query, applied once at load, as a user moves.
  function toggle_query_drop() {
    const shown_url = new URL(location.href);
    if (!shown_url.searchParams.has(DARK_MODE_TOGGLE_QUERY_KEY_NAME)) return;
    shown_url.searchParams.delete(DARK_MODE_TOGGLE_QUERY_KEY_NAME);
    history.replaceState(history.state, "", shown_url.href);
  }
  // Loads a new view page into the frame, clearing the focused path it held.
  function view_page_load(shown_address) {
    const page_href = window.report_ui_.address.page_href(shown_address);
    const view_href = page_href + location.hash;
    if (view_href === loaded_view_href) return;
    const is_new_page = page_href !== loaded_page_href;
    // A new page opens in the dark mode shown, before its first paint.
    if (is_new_page)
      loaded_mode_query = new URLSearchParams({
        [DARK_MODE_FRAME_QUERY_KEY_NAME]: Number(
          Boolean(window.report_ui_.dark_mode_enabled_now_()),
        ),
      }).toString();
    // The loaded page takes a new hash in place, its query kept as loaded.
    view_frame.contentWindow.location.replace(
      page_href + "?" + loaded_mode_query + location.hash,
    );
    loaded_page_href = page_href;
    loaded_view_href = view_href;
    focused_path_entries = [];
    // The new page claims the top page's sideways scroll at its first draw.
    if (is_new_page) window.report_ui_.page_scroll.claim_set("frame", false);
  }
  // Drops the hidden frame's page, which no later view shows again.
  function view_page_unload() {
    if (!loaded_view_href) return;
    // A frame put back holds the empty page a frame opens with, painting none.
    const frame_parent = view_frame.parentNode,
      frame_next_sibling = view_frame.nextSibling;
    view_frame.remove();
    frame_parent.insertBefore(view_frame, frame_next_sibling);
    loaded_page_href = "";
    loaded_view_href = "";
  }
  // Shows the address a hash change brings, the toggle query dropped first.
  function hash_change_show() {
    toggle_query_drop();
    view_show();
  }
  // Shows the address the page's hash holds.
  function view_show() {
    const shown_address = window.report_ui_.address.of_hash(location.hash);
    address_check(shown_address);
    current_address = shown_address;
    if (shown_address.view !== null) view_page_load(shown_address);
    window.report_menu_.address_show();
    if (shown_address.view === null) {
      const frame_had_focus = document.activeElement === view_frame;
      view_frame.hidden = true;
      view_page_unload();
      window.report_overview_.heat_colors_apply();
      home_panel.hidden = false;
      window.report_ui_.page_scroll.lend_show();
      window.report_ui_.layout_refresh(home_panel);
      if (frame_had_focus) {
        const tab_stops = home_panel.querySelectorAll('[tabindex="0"]');
        window.report_ui_.tab_stop_move(
          null,
          tab_stops[tab_stops.length - 1],
          true,
        );
      }
      return;
    }
    const home_had_focus = home_panel.contains(document.activeElement);
    home_panel.hidden = true;
    view_frame.hidden = false;
    window.report_ui_.page_scroll.lend_show();
    page_scroll_post();
    if (home_had_focus) view_frame.focus();
  }
  // Shows a requested hash.
  function address_request(requested_hash) {
    toggle_query_drop();
    if (requested_hash !== (location.hash || "#")) {
      location.hash = requested_hash;
      return;
    }
    view_show();
    if (current_address.view !== null) view_post("recenter");
  }
  // Posts a message down carrying the dark mode, status and preferences.
  function view_post(message_name, message_fields = {}) {
    if (message_name === "layout_reset")
      window.report_ui_.layout_reset(home_panel);
    if (loaded_view_href)
      view_frame.contentWindow.postMessage(
        {
          report_ui: message_name,
          dark_mode_enabled: window.report_ui_.dark_mode_enabled_now_(),
          status_bar_text: window.report_ui_.status_bar_text_now(),
          view_preferences: window.report_preferences_.now(),
          ...message_fields,
        },
        "*",
      );
  }
  // Shows the shown view's chained bar the top page's sideways scroll.
  function page_scroll_post() {
    if (
      window.report_ui_.page_scroll.is_claimed("frame") &&
      !view_frame.hidden
    )
      view_post("page_scroll_show", window.report_ui_.page_scroll.state());
  }
  // Holds the focused path the view sent, then draws the menu with it.
  function focused_path_set(path_entries) {
    focused_path_entries = path_entries;
    window.report_menu_.menu_render();
  }
  // Holds the function location the view sent, then draws the menu with it.
  function function_location_set(sent_location) {
    function_location = sent_location;
    window.report_menu_.menu_render();
  }
  // Holds the view mode link the view sent, then draws the menu with it.
  function view_mode_link_set(sent_link) {
    view_mode_link = sent_link;
    window.report_menu_.menu_render();
  }
  function view_message_handler(message_event) {
    const message_data = message_event.data;
    if (message_event.source !== view_frame.contentWindow || !message_data)
      return;
    const message_tag = message_data.report_ui;
    if (message_tag === "address_request") address_request(message_data.hash);
    else if (message_tag === "call_graph_cutoff_choose")
      window.report_menu_.call_graph_cutoff_choose(message_data.cutoff_depth);
    else if (message_tag === "counter_line_move")
      window.report_menu_.counter_line_move(
        message_data.list_key,
        message_data.line_name,
        message_data.anchor_name,
        message_data.lands_after,
      );
    else if (message_tag === "dark_mode_request") view_post("dark_mode_show");
    else if (message_tag === "focused_path_set")
      focused_path_set(message_data.path_entries);
    else if (message_tag === "function_location_set")
      function_location_set(message_data.function_location);
    else if (message_tag === "heat_sort_toggle")
      window.report_menu_.heat_sort_toggle();
    else if (message_tag === "menu_key_pressed")
      window.report_menu_.menu_key_handler(
        message_data.key,
        message_data.repeat,
      );
    else if (message_tag === "page_scroll_claim") {
      window.report_ui_.page_scroll.claim_set(
        "frame",
        message_data.is_claimed,
      );
      page_scroll_post();
    } else if (message_tag === "page_scroll_set")
      window.report_ui_.page_scroll.offset_set(
        message_data.page_scroll_offset,
      );
    else if (message_tag === "view_mode_link_set")
      view_mode_link_set(message_data.view_mode_link);
    else if (
      message_tag !== undefined &&
      message_tag !== "report_error" &&
      message_tag !== "settings_request"
    )
      window.throw_exception_("str_error_internal");
  }

  function activate() {
    window.addEventListener(
      "hashchange",
      window.try_catch_handler_(hash_change_show),
    );
    window.addEventListener(
      "message",
      window.try_catch_handler_(view_message_handler),
    );
    window.report_ui_.page_scroll.change_listen(page_scroll_post);
    view_show();
    window.page_drawn_mark_();
  }

  window.report_frame_ = {
    activate,
    address_now,
    address_request,
    counter_names,
    focused_path_now,
    function_location_now,
    menu_entry_number_now,
    test_names,
    view_browser_runs,
    view_has_page,
    view_mode_link_now,
    view_post,
  };
})();
