# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE-MIT.md file.

from __future__ import annotations

from typing import Any

import html.entities, os, re

# Holds an error report's text, the first line of its message a group.
ERROR_REPORT_PATTERN_TEXT = (
    r"perf2html error\n\n(?:[a-z]+ +[^\n]*\n)+\n([^\n]*)"
)

# The page each tab opens on, which a frame shows before its own page.
BLANK_PAGE_URL = "about:blank"

# The descriptors the browser reads commands from and writes replies to.
BROWSER_PIPE_COMMAND_FD = 3
BROWSER_PIPE_MESSAGE_END = b"\0"
BROWSER_PIPE_READ_BYTES = 1 << 20
BROWSER_PIPE_REPLY_FD = 4
# Lies above every descriptor a child holds while its pipe ends move.
BROWSER_PIPE_SPARE_FD = 10

# Writes a timed paste's text to the clipboard, as a copy before it did.
CLICK_CLIPBOARD_WRITE_FUNCTION = (
    "(pasted_text) => navigator.clipboard.writeText(pasted_text)"
)
# Holds each key a step presses as the WebDriver key values Firefox takes.
CLICK_FIREFOX_KEY_VALUES: dict[str, tuple[str, ...]] = {
    "+": ("", "+"),
    "-": ("-",),
    "1": ("1",),
    "2": ("2",),
    "5": ("5",),
    "=": ("=",),
    "ArrowDown": ("",),
    "ArrowLeft": ("",),
    "ArrowRight": ("",),
    "ArrowUp": ("",),
    "Backspace": ("",),
    "End": ("",),
    "Enter": ("",),
    "Escape": ("",),
    "Home": ("",),
    "PageDown": ("",),
    "Space": (" ",),
    "Tab": ("",),
    "c": ("c",),
    "ctrl+v": ("", "v"),
    "r": ("r",),
    "s": ("s",),
    "shift+Tab": ("", ""),
}
# Holds whether each key moving the focus moves it backward, past the page.
CLICK_FOCUS_MOVES_BACKWARD: dict[str, bool] = {
    "Tab": False,
    "shift+Tab": True,
}
CLICK_HASH_STATE = "location.hash"
# Holds each key a step presses, as the DevTools key input takes it.
CLICK_KEY_PRESSES: dict[str, dict[str, Any]] = {
    "+": {
        "key": "+",
        "code": "Equal",
        "windowsVirtualKeyCode": 187,
        "modifiers": 8,
    },
    "-": {"key": "-", "code": "Minus", "windowsVirtualKeyCode": 189},
    "1": {"key": "1", "code": "Digit1", "windowsVirtualKeyCode": 49},
    "2": {"key": "2", "code": "Digit2", "windowsVirtualKeyCode": 50},
    "5": {"key": "5", "code": "Digit5", "windowsVirtualKeyCode": 53},
    "=": {"key": "=", "code": "Equal", "windowsVirtualKeyCode": 187},
    "ArrowDown": {
        "key": "ArrowDown",
        "code": "ArrowDown",
        "windowsVirtualKeyCode": 40,
    },
    "ArrowLeft": {
        "key": "ArrowLeft",
        "code": "ArrowLeft",
        "windowsVirtualKeyCode": 37,
    },
    "ArrowRight": {
        "key": "ArrowRight",
        "code": "ArrowRight",
        "windowsVirtualKeyCode": 39,
    },
    "ArrowUp": {
        "key": "ArrowUp",
        "code": "ArrowUp",
        "windowsVirtualKeyCode": 38,
    },
    "Backspace": {
        "key": "Backspace",
        "code": "Backspace",
        "windowsVirtualKeyCode": 8,
    },
    "End": {"key": "End", "code": "End", "windowsVirtualKeyCode": 35},
    "Enter": {
        "key": "Enter",
        "code": "Enter",
        "windowsVirtualKeyCode": 13,
        "text": "\r",
    },
    "Escape": {"key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
    "Home": {"key": "Home", "code": "Home", "windowsVirtualKeyCode": 36},
    "PageDown": {
        "key": "PageDown",
        "code": "PageDown",
        "windowsVirtualKeyCode": 34,
    },
    "Space": {"key": " ", "code": "Space", "windowsVirtualKeyCode": 32},
    "Tab": {"key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9},
    "c": {"key": "c", "code": "KeyC", "windowsVirtualKeyCode": 67},
    "ctrl+v": {
        "key": "v",
        "code": "KeyV",
        "windowsVirtualKeyCode": 86,
        "modifiers": 2,
        "commands": ["paste"],
    },
    "r": {"key": "r", "code": "KeyR", "windowsVirtualKeyCode": 82},
    "s": {"key": "s", "code": "KeyS", "windowsVirtualKeyCode": 83},
    "shift+Tab": {
        "key": "Tab",
        "code": "Tab",
        "windowsVirtualKeyCode": 9,
        "modifiers": 8,
    },
}
CLICK_MENU_FRAME_NAME = "menu"
# Holds each key a step presses as the key events SeaMonkey's input takes.
CLICK_SEAMONKEY_KEY_EVENTS: dict[str, tuple[dict[str, Any], ...]] = {
    "+": (
        {"key": "Shift", "code": "ShiftLeft", "keyCode": 16},
        {"key": "+", "code": "Equal", "keyCode": 61},
    ),
    "-": ({"key": "-", "code": "Minus", "keyCode": 173},),
    "1": ({"key": "1", "code": "Digit1", "keyCode": 49},),
    "2": ({"key": "2", "code": "Digit2", "keyCode": 50},),
    "5": ({"key": "5", "code": "Digit5", "keyCode": 53},),
    "=": ({"key": "=", "code": "Equal", "keyCode": 61},),
    "ArrowDown": ({"key": "ArrowDown", "code": "ArrowDown", "keyCode": 40},),
    "ArrowLeft": ({"key": "ArrowLeft", "code": "ArrowLeft", "keyCode": 37},),
    "ArrowRight": (
        {"key": "ArrowRight", "code": "ArrowRight", "keyCode": 39},
    ),
    "ArrowUp": ({"key": "ArrowUp", "code": "ArrowUp", "keyCode": 38},),
    "Backspace": ({"key": "Backspace", "code": "Backspace", "keyCode": 8},),
    "End": ({"key": "End", "code": "End", "keyCode": 35},),
    "Enter": ({"key": "Enter", "code": "Enter", "keyCode": 13},),
    "Escape": ({"key": "Escape", "code": "Escape", "keyCode": 27},),
    "Home": ({"key": "Home", "code": "Home", "keyCode": 36},),
    "PageDown": ({"key": "PageDown", "code": "PageDown", "keyCode": 34},),
    "Space": ({"key": " ", "code": "Space", "keyCode": 32},),
    "Tab": ({"key": "Tab", "code": "Tab", "keyCode": 9},),
    "c": ({"key": "c", "code": "KeyC", "keyCode": 67},),
    "ctrl+v": (
        {"key": "Control", "code": "ControlLeft", "keyCode": 17},
        {"key": "v", "code": "KeyV", "keyCode": 86},
    ),
    "r": ({"key": "r", "code": "KeyR", "keyCode": 82},),
    "s": ({"key": "s", "code": "KeyS", "keyCode": 83},),
    "shift+Tab": (
        {"key": "Shift", "code": "ShiftLeft", "keyCode": 16},
        {"key": "Tab", "code": "Tab", "keyCode": 9},
    ),
}
CLICK_VIEW_FRAME_NAME = "view"
# Holds WebKit's bit of each DevTools modifier bit: Alt, Control, Meta, Shift.
CLICK_WEBKIT_MODIFIER_BITS: dict[int, int] = {1: 4, 2: 2, 4: 8, 8: 1}
# Bounds the presses of one walk, so a walk reaching nothing fails.
CLICK_WALK_PRESS_LIMIT = 60
# Returns whether the focus, or an open pulldown's light, is on a match.
CLICK_WALK_REACHED_FUNCTION = (
    "(element_selector) => document.hasFocus() && [...document"
    ".querySelectorAll(element_selector)].some((element) =>"
    " element === document.activeElement"
    ' || element.matches(\'[role="option"][aria-selected="true"]\'))'
)

COMMENT_BLOCK_MAX_LINES = 1
COMMENT_FIRST_WORD_REPLACEMENTS = {"Answers": "Returns"}

# Compares a shot with its own browser's gold twin pixel by pixel.
COMPARE_EXACT_CHANNEL_CHANGE = 0
COMPARE_EXACT_SQUARE_PX = 1
# Compares with another browser's gold, or WebKit's own, smoothing passing.
COMPARE_VAGUE_CHANNEL_CHANGE = 48
COMPARE_VAGUE_SQUARE_PX = 16

# Holds an error report a page writes to its console, its first line a group.
CONSOLE_ERROR_REPORT_PATTERN = re.compile(ERROR_REPORT_PATTERN_TEXT)

DEBUG_SCRIPT_ASSET: tuple[str, ...] = ("scripts/debug.js",)

DRAW_LIMIT_ERROR_TEXT = "draws more than 1 nodes"
DRAW_LIMIT_SETTING_LOWERED = '"CALL_GRAPH_MOST_DRAWN_NODES": 1,'
DRAW_LIMIT_SETTING_PATTERN = re.compile(r'"CALL_GRAPH_MOST_DRAWN_NODES": \d+,')
DRAW_LIMIT_SETTINGS_FILE_PATH = "scripts/settings.js"

ENGLISH_PUNCT = """.,"'?:!()/"""

ENTRY_PAGE = "index.html"

ESCAPE_NAMED_ENTITY_PATTERN = "|".join(
    re.escape(name)
    for name, glyph in sorted(html.entities.html5.items())
    if name.endswith(";") and not glyph.isascii()
)
ESCAPE_PREFIX_PATTERN = r"(?<!\\)(?:\\\\)*"

# Moves the focus through a window's controls until one move hands it on.
FIREFOX_FOCUS_RETURN_FUNCTION = (
    "(is_backward, move_limit) => {"
    " const focus_service = Services.focus;"
    " const browser_window = focus_service.activeWindow;"
    " for (let move_count = 0; move_count < move_limit; move_count++) {"
    " const focused_before = focus_service.focusedElement;"
    " focus_service.moveFocus(browser_window, null, is_backward"
    " ? focus_service.MOVEFOCUS_BACKWARD"
    " : focus_service.MOVEFOCUS_FORWARD, 0);"
    " if (focus_service.focusedElement === focused_before) return; }"
    " throw new Error(`${move_limit} moves reach no page`); }"
)
# Resolves once the page holds the focus, a hand off reaching it in a while.
FIREFOX_PAGE_FOCUS_WAIT_FUNCTION = (
    "async function (after_paint) {"
    " while (!document.hasFocus()) await after_paint(); }"
)

# Returns whether a frame's element has a layout box, which a hidden one lacks.
FRAME_LAID_OUT_FUNCTION = (
    "function () { return this.getClientRects().length > 0; }"
)
# Returns each frame element's window and whether it shows in the tab.
FRAME_WINDOWS_SHOWN_FUNCTION = (
    "() => new Promise((resolve) => {"
    " const frame_elements = [...document.querySelectorAll('iframe')];"
    " if (!frame_elements.length) { resolve([]); return; }"
    " const observer = new IntersectionObserver((entries) => {"
    " observer.disconnect();"
    " resolve(entries.map((entry) => [entry.target.contentWindow,"
    " entry.intersectionRect.width > 0"
    " && entry.intersectionRect.height > 0])); });"
    " for (const element of frame_elements) observer.observe(element); })"
)

HEAT_MAP_PAGE_TITLE = ""

IMAGE_SUFFIX = ".png"

INDEX_DATA_PATTERN = re.compile(
    r'<script id="shot-list-" type="application/json">(.*?)</script>',
    re.DOTALL,
)
INDEX_MARKER = "__SHOT_LIST__"
INDEX_PAGE_NAME = "test_index.html"
INDEX_REPORT_NAMES: tuple[str, ...] = (
    "perf2html_baseline_report",
    "perf2html_modified_report",
    "perf2html_diff_report",
)
INDEX_TEMPLATE_NAME = "test_template.html"

MARKDOWN_FENCE_INFO = "txt"
MARKDOWN_FENCE_MARK = "`"
MARKDOWN_FENCE_MIN_MARKS = 3

MENU_LOGO_LINK_PATTERN = re.compile(
    r'<nav id="menu-"[^>]*>.*?<a ([^>]*)>', re.DOTALL
)
MENU_LOGO_REPOSITORY_LINK = (
    'href="https://github.com/whatchamacallem/perf2html" target="_blank"'
    ' tabindex="-1"'
)

# Pages checked for an error report load in this many tabs at once.
PAGE_CHECK_TABS_AT_ONCE = 16
# The binding a page calls once drawn, which DevTools reports.
PAGE_DRAWN_BINDING_NAME = "screenshot_page_drawn"
# Hands the channel Firefox reports through to the binding a page calls.
PAGE_DRAWN_CHANNEL_FUNCTION = (
    f"(drawn_channel) => {{ window['{PAGE_DRAWN_BINDING_NAME}']"
    " = drawn_channel; }"
)
# Calls the binding after the load, the page's own drawn mark, a paint.
PAGE_DRAWN_FUNCTION = (
    "async function (after_paint, binding_name, binding_payload) {"
    " while (document.readyState !== 'complete'"
    " || document.title === 'speedscope'"
    " || window.page_is_drawn_ === false)"
    " await after_paint();"
    " await document.fonts.ready;"
    " await after_paint();"
    " window[binding_name](binding_payload); }"
)
# Resolves in a task after the paint of the next animation frame.
PAINT_WAIT_FUNCTION = (
    "() => new Promise((resolve) =>"
    " requestAnimationFrame(() => setTimeout(resolve)))"
)

REPORT_CHECKSUM_COMMAND = (
    "find . -type f ! -name MANIFEST.txt -print"
    " | LC_ALL=C sort | LC_ALL=C tr '\\n' '\\0'"
    " | xargs -0 -r cksum --"
    " | LC_ALL=C sort | cksum"
)
REPORT_THEME_STYLESHEET_ASSET: tuple[str, ...] = ("scripts/theme.css",)

# Chrome for Testing where packages.md installs it in the home dir.
SCREENSHOT_BROWSER_PATH = os.path.expanduser(
    "~/.local/share/chrome-for-testing/chrome/linux-157.0.8103.78"
    "/chrome-linux64/chrome"
)
SCREENSHOT_CHROME_DIR_NAME = "chrome"
# Holds each browser's shot dir and its gold, named from the project root.
SCREENSHOT_DIR_NAME = "screenshots"
# Starts the X server Firefox and SeaMonkey draw through, WebGL with it.
SCREENSHOT_DISPLAY_SERVER_ARGUMENTS: tuple[str, ...] = (
    "-screen",
    "0",
    "1600x1200x24",
    "-nolisten",
    "tcp",
)
SCREENSHOT_DISPLAY_SERVER_NAME = "Xvfb"
SCREENSHOT_FIREFOX_DIR_NAME = "firefox"
# Holds the address Firefox writes to stderr once it listens.
SCREENSHOT_FIREFOX_LISTENING_PATTERN = re.compile(
    r"WebDriver BiDi listening on (ws://\S+)"
)
# Firefox where packages.md installs it in the home dir.
SCREENSHOT_FIREFOX_PATH = os.path.expanduser(
    "~/.local/share/firefox-for-testing/firefox/linux-stable_160.0.1"
    "/firefox/firefox"
)
SCREENSHOT_FIREFOX_PROFILE_DIR_PATH = "build/screenshots_firefox_profile"
SCREENSHOT_FIREFOX_SESSION_PATH = "/session"
# Names a browser's gold dir from its shot dir's name.
SCREENSHOT_GOLD_DIR_FORMAT = "{}-gold"
SCREENSHOT_LABEL_URL_PARAM = "screenshot"
SCREENSHOT_LABEL_URL_VALUE = "1"
SCREENSHOT_MENU_URL_PARAM = "screenshot-menu"
SCREENSHOT_SCRATCH_DIR_PATH = "build/screenshots_scratch"
SCREENSHOT_SEAMONKEY_DIR_NAME = "seamonkey"
# Installs the browser window script that drives each SeaMonkey tab.
SCREENSHOT_SEAMONKEY_DRIVER_FUNCTION = """\
(event_marker, binding_name, chunk_length) => {
  const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
  const {Services} = Cu.import("resource://gre/modules/Services.jsm", {});
  const {AppConstants} =
    Cu.import("resource://gre/modules/AppConstants.jsm", {});
  const progress_flags = Ci.nsIWebProgressListener;
  const driver = {context_tabs: new Map(), frame_tabs: new Map(),
    tabs: new Map()};
  window.screenshot_driver = driver;
  driver.emit = (event) => {
    const code_points = Array.from(JSON.stringify(event));
    const chunks = [];
    for (let chunk_start = 0; chunk_start < code_points.length;
      chunk_start += chunk_length) {
      chunks.push(code_points.slice(chunk_start,
        chunk_start + chunk_length).join(""));
    }
    console.log(event_marker, ...chunks);
  };
  driver.window_utils = (frame_window) => frame_window
    .QueryInterface(Ci.nsIInterfaceRequestor)
    .getInterface(Ci.nsIDOMWindowUtils);
  driver.window_id = (frame_window) =>
    String(driver.window_utils(frame_window).outerWindowID);
  driver.observe = (subject, topic) => {
    if (topic === "content-document-global-created") {
      const tab_key = driver.window_id(subject.top);
      if (!driver.tabs.has(tab_key)) return;
      const frame = driver.window_id(subject);
      const context = driver.window_utils(subject).currentInnerWindowID;
      driver.context_tabs.set(context, tab_key);
      driver.frame_tabs.set(frame, tab_key);
      Cu.exportFunction((payload) => driver.emit({event: "drawn",
        tab: tab_key, context, payload: String(payload)}), subject,
        {defineAs: binding_name});
      driver.emit({event: "context_created", tab: tab_key, frame, context});
      return;
    }
    const window_id = subject.QueryInterface(Ci.nsISupportsPRUint64).data;
    if (topic === "inner-window-destroyed") {
      const tab_key = driver.context_tabs.get(window_id);
      if (tab_key === undefined) return;
      driver.context_tabs.delete(window_id);
      driver.emit({event: "context_destroyed", tab: tab_key,
        context: window_id});
      return;
    }
    const frame = String(window_id);
    const tab_key = driver.frame_tabs.get(frame);
    if (tab_key === undefined) return;
    driver.frame_tabs.delete(frame);
    driver.emit({event: "frame_removed", tab: tab_key, frame});
  };
  driver.console_observer = {observe: (subject) => {
    const console_message = subject.wrappedJSObject;
    const context = Number(console_message.innerID);
    const tab_key = driver.context_tabs.get(context);
    if (tab_key === undefined) return;
    driver.emit({event: "console", tab: tab_key, context,
      text: console_message.arguments.map((console_argument) =>
        ["boolean", "number", "string"].includes(typeof console_argument)
          ? String(console_argument) : "").join(" ")});
  }};
  Services.obs.addObserver(driver.console_observer,
    "console-api-log-event", false);
  driver.error_listener = {observe: (message) => {
    if (!(message instanceof Ci.nsIScriptError)
      || !(message.flags & Ci.nsIScriptError.exceptionFlag)) return;
    const tab_key = driver.context_tabs.get(message.innerWindowID);
    if (tab_key === undefined) return;
    driver.emit({event: "thrown", tab: tab_key,
      text: message.errorMessage});
  }};
  Services.console.registerListener(driver.error_listener);
  for (const topic of ["content-document-global-created",
    "inner-window-destroyed", "outer-window-destroyed"]) {
    Services.obs.addObserver(driver, topic, false);
  }
  driver.tab_open = (open_number, width, height) => {
    const tab_window = Services.ww.openWindow(null,
      AppConstants.BROWSER_CHROME_URL, "_blank",
      "chrome,all,dialog=no", null);
    const startup_observer = {observe: (subject) => {
      if (subject !== tab_window) return;
      Services.obs.removeObserver(startup_observer,
        "browser-delayed-startup-finished");
      try {
        driver.tab_ready(open_number, tab_window, width, height);
      } catch (error) {
        driver.emit({event: "tab_opened", open_number,
          error: String(error)});
      }
    }};
    Services.obs.addObserver(startup_observer,
      "browser-delayed-startup-finished", false);
  };
  driver.tab_ready = (open_number, tab_window, width, height) => {
    const browser = tab_window.gBrowser.selectedBrowser;
    browser.docShell.setOriginAttributes({userContextId: open_number});
    const content_window = browser.contentWindow;
    tab_window.resizeBy(width - content_window.innerWidth,
      height - content_window.innerHeight);
    if (content_window.innerWidth !== width
      || content_window.innerHeight !== height) {
      throw new Error(`the page is ${content_window.innerWidth}x`
        + `${content_window.innerHeight}, not ${width}x${height}`);
    }
    const tab_key = driver.window_id(content_window);
    const progress_listener = {
      QueryInterface: (interface_id) => {
        if (interface_id.equals(Ci.nsIWebProgressListener)
          || interface_id.equals(Ci.nsISupportsWeakReference)
          || interface_id.equals(Ci.nsISupports)) return progress_listener;
        throw Components.Exception("",
          Components.results.NS_ERROR_NO_INTERFACE);
      },
      onLocationChange: () => {},
      onProgressChange: () => {},
      onSecurityChange: () => {},
      onStateChange: (web_progress, request, state_flags) => {
        if (!(state_flags & progress_flags.STATE_IS_WINDOW)) return;
        const frame = String(web_progress.DOMWindowID);
        if (state_flags & progress_flags.STATE_START) {
          driver.emit({event: "load_begin", tab: tab_key, frame});
        } else if (state_flags & progress_flags.STATE_STOP) {
          driver.emit({event: "load_end", tab: tab_key, frame});
        }
      },
      onStatusChange: () => {},
    };
    browser.webProgress.addProgressListener(progress_listener,
      Ci.nsIWebProgress.NOTIFY_STATE_WINDOW);
    driver.tabs.set(tab_key, {browser, progress_listener,
      window: tab_window});
    tab_window.focus();
    driver.emit({event: "tab_opened", open_number, tab: tab_key});
  };
  driver.tab_close = (tab_key) => {
    const tab = driver.tabs.get(tab_key);
    tab.browser.webProgress.removeProgressListener(tab.progress_listener);
    driver.tabs.delete(tab_key);
    for (const tab_map of [driver.context_tabs, driver.frame_tabs]) {
      for (const [map_key, map_tab] of [...tab_map]) {
        if (map_tab === tab_key) tab_map.delete(map_key);
      }
    }
    tab.window.close();
  };
  driver.navigate = (tab_key, page_url) => {
    driver.tabs.get(tab_key).browser.loadURI(page_url);
  };
  driver.frame_tree = (tab_key) => {
    const frame_node = (frame_window) => {
      const child_nodes = [];
      for (let frame_index = 0; frame_index < frame_window.frames.length;
        frame_index++) {
        child_nodes.push(frame_node(frame_window.frames[frame_index]));
      }
      return [driver.window_id(frame_window), child_nodes];
    };
    return JSON.stringify(
      frame_node(driver.tabs.get(tab_key).browser.contentWindow));
  };
  driver.frame_shown = (parent_frame, frame) => {
    const parent_window =
      Services.wm.getOuterWindowWithId(Number(parent_frame));
    if (!parent_window) return JSON.stringify("absent");
    for (const frame_element of
      parent_window.document.querySelectorAll("iframe")) {
      const frame_window = frame_element.contentWindow;
      if (!frame_window || driver.window_id(frame_window) !== frame) {
        continue;
      }
      if (!frame_element.getClientRects().length) {
        return JSON.stringify(false);
      }
      const frame_box = frame_element.getBoundingClientRect();
      return JSON.stringify(frame_box.right > 0 && frame_box.bottom > 0
        && frame_box.left < parent_window.innerWidth
        && frame_box.top < parent_window.innerHeight);
    }
    return JSON.stringify("absent");
  };
  driver.image_data = (tab_key, width, height) => {
    const content_window = driver.tabs.get(tab_key).browser.contentWindow;
    if (content_window.innerWidth !== width
      || content_window.innerHeight !== height) {
      throw new Error(`the page is ${content_window.innerWidth}x`
        + `${content_window.innerHeight}, not ${width}x${height}`);
    }
    const canvas = document.createElementNS(
      "http://www.w3.org/1999/xhtml", "canvas");
    canvas.width = content_window.innerWidth;
    canvas.height = content_window.innerHeight;
    const drawing = canvas.getContext("2d");
    drawing.drawWindow(content_window, content_window.scrollX,
      content_window.scrollY, canvas.width, canvas.height,
      "rgb(255,255,255)", drawing.DRAWWINDOW_DRAW_VIEW);
    return JSON.stringify(canvas.toDataURL("image/png"));
  };
  driver.keys_send = (tab_key, key_actions) => {
    const tab_window = driver.tabs.get(tab_key).window;
    const input_processor = Cc["@mozilla.org/text-input-processor;1"]
      .createInstance(Ci.nsITextInputProcessor);
    if (!input_processor.beginInputTransactionForTests(tab_window)) {
      throw new Error("the window began no input transaction");
    }
    for (const [action_name, key_init] of key_actions) {
      input_processor[action_name](
        new tab_window.KeyboardEvent("", key_init));
    }
  };
  driver.focus_return = (tab_key, is_backward, move_limit) => {
    const tab = driver.tabs.get(tab_key);
    const focus_service = Services.focus;
    for (let move_count = 0; move_count <= move_limit; move_count++) {
      const focused_window = focus_service.focusedWindow;
      if (focused_window && driver.window_id(focused_window.top)
        === tab_key) return;
      focus_service.moveFocus(tab.window, null, is_backward
        ? focus_service.MOVEFOCUS_BACKWARD
        : focus_service.MOVEFOCUS_FORWARD, 0);
    }
    throw new Error(`${move_limit} moves reach no page`);
  };
  driver.clipboard_write = (pasted_text) => {
    Cc["@mozilla.org/widget/clipboardhelper;1"]
      .getService(Ci.nsIClipboardHelper).copyString(pasted_text);
  };
  driver.quit = () => {
    Services.startup.quit(Ci.nsIAppStartup.eForceQuit);
  };
  driver.script_run = (tab_key, context, expression, call_number) => {
    const frame_window = Services.wm.getCurrentInnerWindowWithId(context);
    if (!frame_window) return JSON.stringify({gone: true});
    let value;
    try {
      value = frame_window.wrappedJSObject.eval(expression);
    } catch (error) {
      return JSON.stringify({exception: String(error)});
    }
    if (call_number === null) return JSON.stringify({value});
    const settle = (result) => driver.emit(
      {event: "result", tab: tab_key, call_number, ...result});
    frame_window.wrappedJSObject.Promise.resolve(value).then(
      Cu.exportFunction((settled) => settle(
        {value: Cu.waiveXrays(settled)}), frame_window),
      Cu.exportFunction((error) => settle({exception: String(error)}),
        frame_window));
    return JSON.stringify({});
  };
}
"""
# Splits an event into console arguments, each one short enough to send.
SCREENSHOT_SEAMONKEY_EVENT_CHUNK_LENGTH = 4096
# Marks the console lines the driver writes, each one an event.
SCREENSHOT_SEAMONKEY_EVENT_MARKER = "screenshot_driver_event"
# Holds the line SeaMonkey writes to stdout when its DevTools server fails.
SCREENSHOT_SEAMONKEY_LISTEN_FAILED_PATTERN = re.compile(
    r"^Unable to start debugger server on "
)
# The console messages the driver writes its events as.
SCREENSHOT_SEAMONKEY_LISTENERS: tuple[str, ...] = ("ConsoleAPI",)
# Holds the line SeaMonkey writes to stdout once its DevTools server opened.
SCREENSHOT_SEAMONKEY_LISTENING_PATTERN = re.compile(
    r"^Started debugger server on "
)
SCREENSHOT_SEAMONKEY_PACKET_LENGTH_END = b":"
# SeaMonkey where packages.md installs it in the home dir.
SCREENSHOT_SEAMONKEY_PATH = os.path.expanduser(
    "~/.local/share/seamonkey-for-testing/2.53.24/seamonkey/seamonkey"
)
# Holds the preferences a fresh profile starts with, the DevTools server's.
SCREENSHOT_SEAMONKEY_PREFERENCES: dict[str, bool | int | str] = {
    "app.update.auto": False,
    "app.update.enabled": False,
    "app.updatecheck.override": True,
    "browser.dom.window.dump.enabled": True,
    "browser.rights.override": True,
    "browser.sessionhistory.max_total_viewers": 0,
    "browser.sessionstore.resume_from_crash": False,
    "browser.startup.homepage": BLANK_PAGE_URL,
    "browser.startup.homepage_override.mstone": "ignore",
    "browser.startup.page": 0,
    "browser.tabs.warnOnClose": False,
    "datareporting.policy.dataSubmissionEnabled": False,
    "devtools.chrome.enabled": True,
    "devtools.debugger.prompt-connection": False,
    "devtools.debugger.remote-enabled": True,
    "dom.max_chrome_script_run_time": 0,
    "dom.max_script_run_time": 0,
    "extensions.update.enabled": False,
    "shell.checkDefaultApps": 0,
    "shell.checkDefaultClient": False,
    "startup.homepage_welcome_url": "",
    "toolkit.telemetry.reportingpolicy.firstRun": False,
}
SCREENSHOT_SEAMONKEY_PREFERENCES_FILE_NAME = "user.js"
# The parent process, whose console runs the browser window's scripts.
SCREENSHOT_SEAMONKEY_PROCESS_ID = 0
SCREENSHOT_SEAMONKEY_PROFILE_DIR_PATH = "build/screenshots_seamonkey_profile"
SCREENSHOT_SEAMONKEY_READ_BYTES = 1 << 20
# Names the socket in the profile, a short name as a socket path is short.
SCREENSHOT_SEAMONKEY_SOCKET_NAME = "devtools"
# The views README.md names unsupported in SeaMonkey, its runs leaving them.
SCREENSHOT_SEAMONKEY_UNSUPPORTED_VIEWS: tuple[str, ...] = ("flame-graph",)
SCREENSHOT_TOGGLE_DARK_URL_PARAM = "toggle-dark"
# The modes the views take in turn, the default dark mode first.
SCREENSHOT_TOGGLE_DARK_VALUES: tuple[str, ...] = ("0", "1")
SCREENSHOT_VIEWPORTS: tuple[tuple[str, int, int], ...] = (("720p", 1280, 720),)
# Starts WebKit headless, speaking over the pipe descriptors 3 and 4.
SCREENSHOT_WEBKIT_ARGUMENTS: tuple[str, ...] = (
    "--inspector-pipe",
    "--headless",
    "--no-startup-window",
)
SCREENSHOT_WEBKIT_DIR_NAME = "webkit"
# WebKit's launcher where packages.md installs it in the home dir.
SCREENSHOT_WEBKIT_PATH = os.path.expanduser(
    "~/.local/share/webkit-for-testing/webkit-2388/pw_run.sh"
)

SHOOT_DIFF_REPORT = 1 << 0
# Shoots the index page of the finished run at the last resolution, once.
SHOOT_INDEX_PAGE = 1 << 3
# Shoots 720p alone, not 4k too.
SHOOT_ONE_VARIANT = 1 << 1
SHOOT_REGULAR_REPORT = 1 << 2
# Lists the reports a run shoots in turn: dir, shot name part, report flag.
SHOOT_REPORTS: tuple[tuple[str, str, int], ...] = (
    ("perf2html_modified_report", "modified", SHOOT_REGULAR_REPORT),
    ("perf2html_diff_report", "diff", SHOOT_DIFF_REPORT),
)
# Times a page drawn in two frames by its draws, its first frame bound alone.
SHOOT_TWO_FRAMES = 1 << 5
# Leaves untimed the flame graph and a large test's heat map.
SHOOT_UNTIMED = 1 << 4
# Lists the address parts of each view a test opens, by the report offering it.
SHOOT_TEST_VIEW_PARTS: dict[int, tuple[str, ...]] = {
    SHOOT_DIFF_REPORT: (
        "view=database",
        "view=heat-map&file={first_file}&functions=0",
    ),
    SHOOT_REGULAR_REPORT: (
        "view=call-graph",
        "view=database",
        "view=flame-graph&localProfilePath=profile",
        "view=heat-map&file={first_file}&functions=0",
    ),
}

SHOT_MODE_NAME_PARTS: dict[str, str] = {"0": "dark", "1": "light"}
SHOT_NAME_SEPARATOR = "-"
SHOT_NUMBER_DIGITS = 2

SOURCE_DATABASE_FILE_PATH = "scripts/source_database.js"
SOURCE_DATABASE_PATTERN = re.compile(r"= (\{.*\});", re.DOTALL)

SOURCE_SCAN_ALLOWED_NON_ASCII_CHARS = (
    "©",
    "≈",
    "∞",
    "▲",
    "◄",
    "►",
    "▼",
    "…",
    " ",
    "░",
    "▒",
    "▓",
    "█",
    "◼",
    "━",
    "┃",
    "┗",
    "┣",
    "┳",
    "⊞",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
)
SOURCE_SCAN_BANNED_TAG_NAMES = (
    "abbr",
    "address",
    "b",
    "big",
    "blockquote",
    "center",
    "cite",
    "code",
    "del",
    "dfn",
    "em",
    "font",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "ins",
    "kbd",
    "mark",
    "p",
    "q",
    "s",
    "samp",
    "small",
    "strike",
    "strong",
    "sub",
    "sup",
    "tt",
    "u",
    "var",
)
SOURCE_SCAN_COMMENT_MARKUP = (
    "<!--",
    "-->",
    "/*",
    "*/",
    "///",
    "//",
    "#",
    "*",
)

# Names the oldest browser the page scripts and stylesheets support.
SOURCE_SCAN_SUPPORT_FLOOR_BROWSER = "SeaMonkey 2.53.24"
# Each page file kind the support floor check reads.
SOURCE_SCAN_SUPPORT_FLOOR_EXTENSIONS = (".css", ".js")
# Each script or stylesheet feature pattern the support floor lacks.
SOURCE_SCAN_SUPPORT_FLOOR_MISSING_PATTERNS = (
    r"\.replaceChildren\(",
    r"\.at\(",
    r"\?\?=|\|\|=|&&=",
    r"\.to(?:Reversed|Sorted|Spliced)\(",
    r"\.checkVisibility\(",
    r"\bcurrentCSSZoom\b",
    r"\b(?:actual|font)BoundingBox",
    r"\.findLast(?:Index)?\(",
    r"\bstructuredClone\(",
    r"\bnavigator\.clipboard\b",
    r"\bnew Error\([^()]*,\s*\{",
    r"\bUint8Array\.fromBase64\(|\.toBase64\(",
    r":has\(",
    r":is\(",
    r":where\(",
    r":focus-visible",
    r":not\([^()]*,",
    r"\banchor\(|anchor-(?:name|scope)|position-(?:anchor|try)",
    r"container-type|@container|\b[0-9.]+cq(?:[bhiw]|max|min)\b",
    r"(?<![\w-])zoom\s*:",
    r"(?<![\w-])inset\s*:",
    r"(?<![\w-])(?:border|inset|margin|padding)-(?:block|inline)\s*:"
    r"|\b(?:border|inset|margin|padding)(?:Block|Inline)\b",
    r"(?<![\w-])gap\s*:",
    r"\b[0-9.]+lh\b",
    r"(?<![\w-])translate\s*:",
    r"animation-(?:range|timeline)",
    r"content-visibility\s*:\s*hidden",
)
# Each lacked feature's pattern, then its older form's or presence test's.
SOURCE_SCAN_SUPPORT_FLOOR_PAIRED_PATTERNS = {
    r"\.style\.zoom\b": r"\"zoom\" in \w+\.style\b",
    r"(?<![\w-])(?:min-)?width\s*:\s*max-content": r"-moz-max-content",
    r"(?<![\w-])width\s*:\s*fit-content": r"-moz-fit-content",
    r"(?<![\w-])width\s*:\s*min-content": r"-moz-min-content",
    r"(?<![\w-])user-select\s*:": r"-moz-user-select\s*:",
    r"(?<![\w-])overflow\s*:\s*clip\b": r"(?<![\w-])overflow\s*:\s*hidden\b",
}

# Resolves after a paint once the state read differs, its handlers then run.
STATE_CHANGE_FUNCTION = (
    "async function (after_paint, state_read, state_before) {"
    " while (JSON.stringify(state_read()) === state_before)"
    " await after_paint();"
    " await after_paint(); }"
)

TEST_BELOW_MAIN_FUNCTION_NAME = "(below main)"

TEST_CALL_GRAPH_BRANCH_FIELDS = 2
TEST_CALL_GRAPH_BRANCH_FUNCTION_FIELD = 1
TEST_CALL_GRAPH_BRANCH_PARENT_FIELD = 0
TEST_CALL_GRAPH_EDGE_CALLEE_FIELD = 1
TEST_CALL_GRAPH_EDGE_CALLER_FIELD = 0
TEST_CALL_GRAPH_EDGE_FIELDS = 5
TEST_CALL_GRAPH_EDGE_FUNCTION_FIELDS = (0, 1)
TEST_CALL_GRAPH_EDGE_INCLUSIVE_FIELD = 4
TEST_CALL_GRAPH_FUNCTION_FIELDS = 3
TEST_CALL_GRAPH_FUNCTION_LINKED_FIELD = 2
TEST_CALL_GRAPH_FUNCTION_NAME_FIELD = 0
TEST_CALL_GRAPH_FUNCTION_SELF_FIELD = 1
TEST_CALL_GRAPH_MODEL_KEYS = (
    "branches",
    "edges",
    "functions",
    "roots",
    "test_total",
)
TEST_CALL_GRAPH_PAGE_DIR_NAME = "call-graph"
TEST_CALL_GRAPH_PAGE_LEAST_BYTES = 2000
TEST_CALL_GRAPH_ROOT_CALLS_FIELD = 1
TEST_CALL_GRAPH_ROOT_FIELDS = 2
TEST_CALL_GRAPH_ROOT_FUNCTION_FIELD = 0
TEST_CALL_GRAPH_START_FUNCTION_CALLS = 1
TEST_CALL_GRAPH_START_FUNCTION_NAME = "main"
TEST_CALL_GRAPH_STOP_FUNCTION_NAME = "exit"
TEST_CALL_GRAPH_TABLE_ID = "call-graph-table-"

TEST_CALLGRIND_CALLS_PREFIX = "calls="
TEST_CALLGRIND_COST_LINE_PATTERN = r"[\d+*-]"
TEST_CALLGRIND_NAME_LINE_PATTERN = r"(c?)(?:(ob)|(fn))=(?:\((\d+)\))? ?(.*)"

TEST_DATABASE_CALL_COUNTS_START_FIELD = 1
TEST_DATABASE_CALLEE_ROWS_FIELD = 6
TEST_DATABASE_CALLER_ROWS_FIELD = 5
TEST_DATABASE_FUNCTION_HREF_FIELD = 1
TEST_DATABASE_FUNCTION_NAME_FIELD = 0
TEST_DATABASE_MODEL_ID = "database-model-"
TEST_DATABASE_PAGE_DIR_NAME = "database"
TEST_DATABASE_ROW_BASELINE_CALLS_FIELD = 7
TEST_DATABASE_ROW_CALLS_FIELD = 3
TEST_DATABASE_ROW_FILE_FIELD = 1
TEST_DATABASE_ROW_FUNCTION_FIELD = 0
TEST_DATABASE_ROW_LINE_FIELD = 2
TEST_DATABASE_VIEW_KEY = "database"

TEST_DELTA_HOME_FILE = "lib/home.c"
TEST_DELTA_HOME_FUNCTION_NAME = "inlined_only"
TEST_DELTA_HOME_INLINED_LINE = ("lib/inlined.h", 7)
TEST_DELTA_HOME_IMAGE = "/opt/line/libline.so"
TEST_DELTA_HOME_RECORDING_HEADER = "events: Ir\nsummary: 1\n"
TEST_DELTA_HOME_RECORDING_NAME = "delta_home.callgrind_diff.out"

TEST_DERIVED_COUNTER_NAMES = ("D1m", "DLm", "L1m", "LLm", "Bm", "CEst")

TEST_DIFF_UNKNOWN_FILE = "(unknown)"
TEST_DIFF_UNKNOWN_PLACES = (
    ("first_unknown", "/opt/line/libfirst.so", "libfirst.so/(unknown)"),
    ("second_unknown", "/opt/line/libsecond.so", "libsecond.so/(unknown)"),
)

TEST_FLAME_GRAPH_PAGE_LEAST_BYTES = 300
TEST_FLAME_GRAPH_SCRIPT_LEAST_BYTES = 200

TEST_FUNCTION_COUNTED_LINE = ("lib/counted.c", 7)
TEST_FUNCTION_COUNTED_NAME = "counted_function"

TEST_FUNCTION_DATA_CALL_COUNT_FIELD = 1
TEST_FUNCTION_DATA_CALL_PAIR_FIELDS = 2
TEST_FUNCTION_DATA_DOCUMENT = {
    "counters": ["Ir", "Dr"],
    "functions": [
        [0, [3, 0], [1, 2], []],
        [1, [2, 1], [], [0, 2, 2, 1]],
        [2, [2, 2], [1, 1], []],
    ],
}
TEST_FUNCTION_DATA_DOCUMENT_KEYS = ("counters", "functions")
TEST_FUNCTION_DATA_FILE_PATHS = (
    "test_fixture/data.c",
    "test_fixture/other.c",
)
TEST_FUNCTION_DATA_FILE_SUFFIX = "_function_data.json"
TEST_FUNCTION_DATA_RECORDING = (
    "events: Ir Dr\n"
    "summary: 7 3\n"
    "ob=/opt/data/libdata.so\n"
    "fl=test_fixture/data.c\n"
    "fn=outer_start\n"
    "cfn=data_start\n"
    "calls=0 10\n"
    "1 7 3\n"
    "fn=data_start\n"
    "11 2 1\n"
    "cfn=data_leaf\n"
    "calls=2 20\n"
    "12 3 0\n"
    "cob=/opt/other/libother.so\n"
    "cfi=test_fixture/other.c\n"
    "cfn=other_leaf\n"
    "calls=1 5\n"
    "13 2 2\n"
    "fn=data_leaf\n"
    "20 1 0\n"
    "21 2 0\n"
    "ob=/opt/other/libother.so\n"
    "fl=test_fixture/other.c\n"
    "fn=other_leaf\n"
    "5 1 0\n"
    "6 1 2\n"
)
TEST_FUNCTION_DATA_RECORDING_NAME = "function_data.callgrind.out"
TEST_FUNCTION_DATA_ROW_CALLEES_FIELD = 6
TEST_FUNCTION_DATA_ROW_CALLERS_FIELD = 5
TEST_FUNCTION_DATA_ROW_FIELDS = 7
TEST_FUNCTION_DATA_ROW_FILE_FIELD = 2
TEST_FUNCTION_DATA_ROW_IMAGE_FIELD = 1
TEST_FUNCTION_DATA_ROW_LINE_FIELD = 3
TEST_FUNCTION_DATA_ROW_NAME_FIELD = 0
TEST_FUNCTION_DATA_ROW_SELF_FIELD = 4
TEST_FUNCTION_DATA_STORED_CALLEES_FIELD = 3
TEST_FUNCTION_DATA_STORED_CALLERS_FIELD = 2
TEST_FUNCTION_DATA_STORED_INDEX_FIELD = 0
TEST_FUNCTION_DATA_STORED_ROW_FIELDS = 4
TEST_FUNCTION_DATA_STORED_SELF_FIELD = 1
TEST_FUNCTION_DATA_TABLE = {
    "images": ["/opt/data/libdata.so", "/opt/other/libother.so"],
    "functions": [
        ["data_leaf", 0, 0, 20],
        ["data_start", 0, 0, 10],
        ["other_leaf", 1, 1, 5],
    ],
}
TEST_FUNCTION_DECLARATION_CASES = (
    (("lib/lines.c", 31), None, ("lib/lines.c", 31)),
    (("lib/lines.c", 31), ("lib/./lines.c", 29), ("lib/lines.c", 29)),
    (("lib/lines.c", 31), ("include/lines.h", 3), ("lib/lines.c", 31)),
)
TEST_FUNCTION_DECLARATIONS = {
    "inline_function": ("/src/fixture/lib/fixture.c", 30),
    "plain_function": ("/src/fixture/lib/fixture.c", 12),
    "split_function": ("/src/fixture/include/split.h", 7),
}
TEST_FUNCTION_DECLARATIONS_DEBUG_FILE = (
    "/usr/lib/debug/.build-id/ab/cdef0123456789.debug"
)
TEST_FUNCTION_DECLARATIONS_EMBEDDED_RECORDS = (
    "Contents of the .debug_info section:\n"
)
TEST_FUNCTION_DECLARATIONS_IMAGE = "/opt/fixture/lib/libfixture.so.1"
TEST_FUNCTION_DECLARATIONS_LINE_TABLES = (
    "Raw dump of debug contents of section .debug_line:\n"
    "\n"
    "  Offset:                      0\n"
    "  Length:                      100\n"
    "  DWARF Version:               5\n"
    "\n"
    " The Directory Table (offset 0x22, lines 3, columns 1):\n"
    "  Entry\tName\n"
    "  0\t(indirect line string, offset: 0x10): /src/fixture\n"
    "  1\t(indirect line string, offset: 0x20): lib\n"
    "  2\t/src/fixture/include\n"
    "\n"
    " The File Name Table (offset 0x30, lines 3, columns 2):\n"
    "  Entry\tDir\tName\n"
    "  0\t1\t(indirect line string, offset: 0x30): fixture.c\n"
    "  1\t1\tfixture.c\n"
    "  2\t2\tsplit.h\n"
    "\n"
    " Line Number Statements:\n"
    "  [0x00000050]  Set column to 1\n"
    "  [0x00000052]  Advance Line by 11 to 12\n"
    "\n"
    "  Offset:                      0x40\n"
    "  Length:                      40\n"
    "  DWARF Version:               5\n"
    "\n"
    " The Directory Table (offset 0x62, lines 1, columns 1):\n"
    "  Entry\tName\n"
    "  0\t./string\n"
    "\n"
    " The File Name Table (offset 0x70, lines 1, columns 2):\n"
    "  Entry\tDir\tName\n"
    "  0\t0\tstrlen.S\n"
    "\n"
    " No Line Number Statements.\n"
)
TEST_FUNCTION_DECLARATIONS_NAMES = (
    "assembly_function",
    "free",
    "inline_function",
    "missing_function",
    "plain_function",
    "split_function",
    "twin_function",
)
TEST_FUNCTION_DECLARATIONS_RANGES = (
    "Contents of the .debug_rnglists section:\n"
    "\n"
    " Table at Offset: 0:\n"
    "  Length:          0x20\n"
    "  DWARF version:   5\n"
    "  Address size:    8\n"
    "  Segment size:    0\n"
    "  Offset entries:  0\n"
    "    Offset   Begin    End\n"
    "    0000000c 0000000000002800 (base address)\n"
    "    00000015 0000000000003000 0000000000003010 \n"
    "    0000001a 0000000000003100 0000000000003100  (start == end)\n"
    "    0000001f 0000000000009000 0000000000009020 \n"
    "    00000024 <End of list>\n"
)
TEST_FUNCTION_DECLARATIONS_RECORDS = (
    "Contents of the .debug_info section (loaded from"
    " /usr/lib/debug/.build-id/ab/cdef0123456789.debug):\n"
    "\n"
    "  Compilation Unit @ offset 0:\n"
    "   Length:        0x100 (32-bit)\n"
    "   Version:       5\n"
    " <0><c>: Abbrev Number: 1 (DW_TAG_compile_unit)\n"
    "    <d>   DW_AT_producer    : (indirect string, offset: 0x0): GNU C17\n"
    "    <11>   DW_AT_name        : (indirect line string, offset: 0x0):"
    " lib/fixture.c\n"
    "    <15>   DW_AT_comp_dir    : (indirect line string, offset: 0x10):"
    " /src/fixture\n"
    "    <19>   DW_AT_stmt_list   : 0\n"
    " <1><20>: Abbrev Number: 2 (DW_TAG_subprogram)\n"
    "    <21>   DW_AT_name        : (indirect string, offset: 0x20):"
    " plain_function\n"
    "    <25>   DW_AT_decl_file   : 1\n"
    "    <26>   DW_AT_decl_line   : 12\n"
    "    <27>   DW_AT_low_pc      : 0x1000\n"
    "    <2f>   DW_AT_high_pc     : 0x40\n"
    " <1><40>: Abbrev Number: 3 (DW_TAG_subprogram)\n"
    "    <41>   DW_AT_name        : inline_function\n"
    "    <45>   DW_AT_decl_file   : 1\n"
    "    <46>   DW_AT_decl_line   : 30\n"
    "    <47>   DW_AT_inline      : 3\t(declared as inline and inlined)\n"
    " <1><50>: Abbrev Number: 4 (DW_TAG_subprogram)\n"
    "    <51>   DW_AT_abstract_origin: <0x40>\n"
    "    <55>   DW_AT_low_pc      : 0x2000\n"
    " <1><60>: Abbrev Number: 5 (DW_TAG_subprogram)\n"
    "    <61>   DW_AT_name        : split_function\n"
    "    <65>   DW_AT_decl_file   : 2\n"
    "    <66>   DW_AT_decl_line   : 7\n"
    "    <67>   DW_AT_ranges      : 0xc\n"
    " <1><70>: Abbrev Number: 6 (DW_TAG_subprogram)\n"
    "    <71>   DW_AT_name        : twin_function\n"
    "    <75>   DW_AT_decl_file   : 1\n"
    "    <76>   DW_AT_decl_line   : 50\n"
    "    <77>   DW_AT_low_pc      : 0x4000\n"
    " <1><7f>: Abbrev Number: 0\n"
    "  Compilation Unit @ offset 0x80:\n"
    " <0><8c>: Abbrev Number: 7 (DW_TAG_compile_unit)\n"
    "    <8d>   DW_AT_stmt_list   : 0x40\n"
    "    <91>   DW_AT_comp_dir    : ./string\n"
    "    <99>   DW_AT_language    : 32769\t(MIPS assembler)\n"
    " <1><a0>: Abbrev Number: 8 (DW_TAG_subprogram)\n"
    "    <a1>   DW_AT_name        : assembly_function\n"
    "    <a5>   DW_AT_low_pc      : 0x5000\n"
)
TEST_FUNCTION_DECLARATIONS_SYMBOLS = (
    "\n"
    "/usr/lib/debug/.build-id/ab/cdef0123456789.debug:     file format"
    " elf64-x86-64\n"
    "\n"
    "SYMBOL TABLE:\n"
    "0000000000000000 l    df *ABS*\t0000000000000000 fixture.c\n"
    "0000000000001000 g     F .text\t0000000000000040"
    "              plain_function\n"
    "0000000000002000 l     F .text\t0000000000000010 inline_function\n"
    "0000000000003000 g     F .text\t00000000000186a0"
    " split_function@@FIXTURE_1\n"
    "0000000000004000 l     F .text\t0000000000000010 twin_function\n"
    "0000000000004100 l     F .text\t0000000000000010 twin_function\n"
    "0000000000005000 g   i   .text\t0000000000000020 assembly_function\n"
    "0000000000006000 l     O .data\t0000000000000008 plain_function\n"
    "0000000000000000       F *UND*\t0000000000000000 free@GLIBC_2.2.5\n"
)
TEST_FUNCTION_DIFF = {
    "counters": ["Ir", "Dr"],
    "images": [
        "/opt/b/libB.so",
        "build-x/tree-a/lib/libkept.so",
        "build-x/tree-b/bin/tool",
        "build-x/tree-b/lib/libkept.so",
    ],
    "files": [
        "lib/added.c",
        "lib/gone.c",
        "lib/kept.c",
        "lib/moved.c",
        "lib/twice.c",
    ],
    "functions": [
        ["gone", 1, 1, 5, [-2, 0], [2, 0], [[1, -1, 1]], []],
        [
            "kept_caller",
            3,
            2,
            9,
            [1, 0],
            [5, 1],
            [],
            [
                [0, -1, 1],
                [2, 0, 2],
                [3, 1, 0],
                [4, 1, 1],
                [5, 0, 1],
                [6, 0, 1],
            ],
        ],
        ["kept_steady", 3, 2, 19, [0, 0], [4, 0], [[1, 0, 2]], []],
        ["libkept.so/added", 3, 0, 49, [1, 0], [0, 0], [[1, 1, 0]], []],
        ["libkept.so/spread", 3, 4, 7, [0, 0], [1, 1], [[1, 1, 1]], []],
        ["libkept.so/twice", 3, 4, 3, [0, -1], [2, 2], [[1, 0, 1]], []],
        ["moved", 0, 3, 31, [0, 1], [3, 3], [[1, 0, 1]], []],
        ["tool/added", 2, 0, 49, [2, 0], [0, 0], [], []],
        ["tool/spread", 2, 4, 7, [3, 0], [0, 0], [], []],
        ["tool/twice", 2, 4, 3, [0, 0], [6, 0], [], []],
    ],
}
TEST_FUNCTION_DIFF_AMBIGUOUS_CASES = (
    (
        ("/opt/a/libA.so", "/opt/a/libC.so"),
        ("/opt/b/libB.so", "/opt/b/libD.so"),
    ),
    (("/opt/a/libA.so", "/opt/a/libC.so"), ("/opt/b/libB.so",)),
    (("/opt/a/libA.so",), ("/opt/b/libB.so", "/opt/b/libD.so")),
    (
        ("build-x/tree-a/lib/libX.so", "lib/libX.so"),
        ("build-x/tree-b/lib/libX.so",),
    ),
)
TEST_FUNCTION_DIFF_AMBIGUOUS_ERROR = (
    "error: ambiguous resolution of overloads of overload:"
)
TEST_FUNCTION_DIFF_AMBIGUOUS_NAME = "overload"
TEST_FUNCTION_DIFF_AMBIGUOUS_PATHS = ("lib/overload.c",)
TEST_FUNCTION_DIFF_BASELINE_DOCUMENT = {
    "counters": ["Ir", "Dr"],
    "functions": [
        [1, [2, 0], [2, 1], []],
        [2, [5, 1], [], [1, 1, 3, 2, 4, 1, 5, 1, 6, 1]],
        [3, [4, 0], [2, 2], []],
        [4, [3, 3], [2, 1], []],
        [5, [1, 1], [2, 1], []],
        [6, [2, 2], [2, 1], []],
        [7, [6, 0], [], []],
    ],
}
TEST_FUNCTION_DIFF_BASELINE_NAME = "baseline_function_data.json"
TEST_FUNCTION_DIFF_BASELINE_PATHS = (
    "lib/gone.c",
    "lib/kept.c",
    "lib/moved.c",
    "lib/twice.c",
)
TEST_FUNCTION_DIFF_BASELINE_TABLE = {
    "images": [
        "/opt/a/libA.so",
        "build-x/tree-a/bin/tool",
        "build-x/tree-a/lib/libkept.so",
    ],
    "functions": [
        ["other_test_function", 0, 0, 1],
        ["gone", 2, 0, 5],
        ["kept_caller", 2, 1, 9],
        ["kept_steady", 2, 1, 19],
        ["moved", 0, 2, 29],
        ["spread", 2, 3, 7],
        ["twice", 2, 3, 3],
        ["twice", 1, 3, 3],
    ],
}
TEST_FUNCTION_DIFF_BUILD_TREES = ("build-x/tree-a", "build-x/tree-b")
TEST_FUNCTION_DIFF_MODIFIED_DOCUMENT = {
    "counters": ["Ir", "Dr"],
    "functions": [
        [1, [1, 0], [3, 1], []],
        [2, [2, 0], [], []],
        [3, [6, 1], [], [1, 1, 4, 2, 5, 1, 6, 2, 8, 1]],
        [4, [4, 0], [3, 2], []],
        [5, [3, 4], [3, 1], []],
        [6, [1, 1], [3, 2], []],
        [7, [3, 0], [], []],
        [8, [2, 1], [3, 1], []],
        [9, [6, 0], [], []],
    ],
}
TEST_FUNCTION_DIFF_MODIFIED_NAME = "modified_function_data.json"
TEST_FUNCTION_DIFF_MODIFIED_PATHS = (
    "lib/added.c",
    "lib/kept.c",
    "lib/moved.c",
    "lib/twice.c",
)
TEST_FUNCTION_DIFF_MODIFIED_TABLE = {
    "images": [
        "/opt/b/libB.so",
        "build-x/tree-b/bin/tool",
        "build-x/tree-b/lib/libkept.so",
    ],
    "functions": [
        ["other_test_function", 0, 0, 1],
        ["added", 2, 0, 49],
        ["added", 1, 0, 49],
        ["kept_caller", 2, 1, 9],
        ["kept_steady", 2, 1, 19],
        ["moved", 0, 2, 31],
        ["spread", 2, 3, 7],
        ["spread", 1, 3, 7],
        ["twice", 2, 3, 3],
        ["twice", 1, 3, 3],
    ],
}
TEST_FUNCTION_ENTRY_CONFLICT = (
    "cfi=lib/lines.c\ncfn=two_line_function\ncalls=1 31\n3 1\n"
)
TEST_FUNCTION_LINE_RECORDING = (
    "events: Ir\n"
    "summary: 10\n"
    "ob=/opt/line/libline.so\n"
    "fl=lib/lines.c\n"
    "fn=start_caller\n"
    "cfn=start_function\n"
    "calls=0 20\n"
    "5 10\n"
    "fn=start_function\n"
    "22 1\n"
    "cfn=two_line_function\n"
    "calls=1 30\n"
    "23 2\n"
    "cfn=one_line_function\n"
    "calls=1 39\n"
    "24 1\n"
    "cfn=blocked_function\n"
    "calls=1 40\n"
    "25 2\n"
    "cfn=inlined_function\n"
    "calls=1 50\n"
    "26 2\n"
    "cfi=lib/first.c\n"
    "cfn=line_one_function\n"
    "calls=1 1\n"
    "27 2\n"
    "fn=two_line_function\n"
    "30 1\n"
    "31 1\n"
    "fn=one_line_function\n"
    "39 1\n"
    "fn=blocked_function\n"
    "40 1\n"
    "41 1\n"
    "fn=inlined_function\n"
    "50 1\n"
    "fi=lib/inlined.h\n"
    "7 1\n"
    "fl=lib/first.c\n"
    "fn=line_one_function\n"
    "1 1\n"
    "2 1\n"
)
TEST_FUNCTION_LINE_RECORDING_NAME = "function_line.callgrind.out"
TEST_FUNCTION_LINES = {
    "blocked_function": ("lib/lines.c", 40),
    "inlined_function": ("lib/lines.c", 50),
    "line_one_function": ("lib/first.c", 1),
    "one_line_function": ("lib/lines.c", 39),
    "start_function": ("lib/lines.c", 20),
    "two_line_function": ("lib/lines.c", 30),
}

TEST_FUNCTION_TABLE_KEYS = ("functions", "images")
TEST_FUNCTION_TABLE_NAME = "0_function_data.json"
TEST_FUNCTION_TABLE_ROW_FIELDS = 4

TEST_HEAT_MAP_CALL_ROW_COUNT_FIELD = 4
TEST_HEAT_MAP_CALL_ROW_FUNCTION_FIELD = 0
TEST_HEAT_MAP_MODEL_LEAST_BYTES = 5000
TEST_HEAT_MAP_PAGE_LEAST_BYTES = 1000

TEST_LIST_FILE_NAME = "test_list.txt"

TEST_MANIFEST_EXECUTABLE_LABEL = "executable"
TEST_MANIFEST_LEAST_BYTES = 40

TEST_OVERVIEW_CHANGE_CELL_TEXT = (
    " in a cell whose heat_percent agrees with it, else an empty text"
)
TEST_OVERVIEW_CHANGE_LARGEST_ERROR = 0.0050001
TEST_OVERVIEW_CHANGE_PATTERN = (
    r"(?:0\.00%|[▲▼] *(?:≈0\.00%|-?\d+\.\d{2}%|∞%|≈∞%|\d+\.\d{2}x))?"
)
TEST_OVERVIEW_DUTY_CYCLE_FIELD = 1
TEST_OVERVIEW_DUTY_CYCLE_PATTERN = r"\d+\.\d{2}(?:s|ms|us|ns|ps)"
TEST_OVERVIEW_PAGE_LEAST_BYTES = 2000
TEST_OVERVIEW_PAGE_TITLE = ""
TEST_OVERVIEW_RATIO_FIELDS = (2, 3, 4, 5)
TEST_OVERVIEW_RATIO_LARGEST_ERROR = 0.00000050001
TEST_OVERVIEW_RATIO_PATTERN = r"(?:\d+\.\d{6})?"
TEST_OVERVIEW_RAW_DATA_MARKUP = '<div id="overview-raw-data-">'
TEST_OVERVIEW_ROW_FIELD_COUNT = 6
TEST_OVERVIEW_HEADING_MARKUP = (
    '<div id="overview-tests-heading-" class="page-heading-"'
    ' data-download-file-name-="overview.svg"></div>'
)
TEST_OVERVIEW_TABLE_DATA_ID = "overview-tests-table-"
TEST_OVERVIEW_TIME_LARGEST_ERROR = 0.0050001
TEST_OVERVIEW_TIME_UNIT_SECONDS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
    "ps": 1e-12,
}
TEST_OVERVIEW_VALUE_FIELDS = (1, 2, 3, 4, 5)

TEST_PAGE_PREAMBLE_SCRIPT_NAMES = (
    "error_overlay.js",
    "settings.js",
    "utility.js",
    "ui_strings.js",
)

TEST_PATHS_DOCUMENT_CODES = ("err", "git", "repo", "sys")
TEST_PATHS_DOCUMENT_ERROR_CODE = "err"
TEST_PATHS_DOCUMENT_KEYS = ("p", "t")
TEST_PATHS_DOCUMENT_NAME = "0_file_data.json"

TEST_PERF_TOOL_TREE_PATH = "tests/perf/perf"

TEST_PROFILE_FILE_SUFFIX = ".callgrind.out"

TEST_RAW_ARCHIVE_LEAST_BYTES = 100

TEST_README_HTML_NAME = "README.html"
TEST_README_MARKDOWN_NAME = "README.md"

TEST_SHARED_IMAGES_FUNCTION_NAMES = (
    "/opt/one/libsame.so/shared_name",
    "/opt/two/libsame.so/shared_name",
    "libother.so/shared_name",
    "lone_name",
    "other_name",
)
TEST_SHARED_IMAGES_RECORDING = (
    "events: Ir\n"
    "summary: 5\n"
    "ob=/opt/one/libsame.so\n"
    "fl=one.c\n"
    "fn=shared_name\n"
    "1 1\n"
    "fn=lone_name\n"
    "2 1\n"
    "ob=/opt/two/libsame.so\n"
    "fl=two.c\n"
    "fn=shared_name\n"
    "3 1\n"
    "ob=/opt/other/libother.so\n"
    "fl=other.c\n"
    "fn=shared_name\n"
    "4 1\n"
    "fn=other_name\n"
    "5 1\n"
)
TEST_SHARED_IMAGES_RECORDING_NAME = "shared_images.callgrind.out"

TEST_SOURCE_DATABASE_GLOBAL_NAME = "report_source_database_"
TEST_SOURCE_DATABASE_KEYS = ("files", "functions")
TEST_SOURCE_DATABASE_LEAST_BYTES = 1000
TEST_SOURCE_DATABASE_SCRIPT_PATH = "scripts/source_database.js"
TEST_SOURCE_DATABASE_TEST_KEYS = {
    "filesWithCounters": "files",
    "functionsWithCounters": "functions",
}

TEST_TIMER_ARTIFACTS_PREFIX = "timer-artifacts-"

TEST_TIMING_DOCUMENT_NAME = "0_test_data.json"
TEST_TIMING_VALUE_NAMES = (
    "duty_cycle",
    "instructions_per_cycle",
    "loads_per_instruction",
    "branch_miss_ratio",
    "l1d_miss_ratio",
)

TEST_UNKNOWN_IMAGE_NAMES = ("???", "(unknown image)")

TIMING_CLICK_LIMIT_MS = 300
TIMING_CLICK_PHASE_NAME = "click"
TIMING_FILE_LINES_MAX = 3
TIMING_FILE_NAME = "timing.txt"
# Names a page's frames in the order drawn, the first bound as a page load.
TIMING_FRAME_PHASE_NAMES: tuple[str, ...] = ("first frame", "second frame")
# A load counts from a commit to its load event or its last phase, the later.
TIMING_LOAD_PHASE_NAME = "load"
TIMING_MICROSECONDS_PER_MILLISECOND = 1000
# Bounds a golden page load and its phases, clicks being bound apart.
TIMING_PAGE_LOAD_LIMIT_MS = 300
TIMING_SCRIPT_PHASE_NAME = "script"

# Marks the compositor taking a main thread frame, by that frame's number.
TRACE_ACTIVATE_NAME = "ActivateLayerTree"
TRACE_BEGIN_TYPE = "B"
TRACE_CATEGORIES: tuple[str, ...] = (
    "devtools.timeline",
    "disabled-by-default-devtools.timeline.frame",
)
# Marks a page's commit, where its load is counted from.
TRACE_COMMIT_NAME = "CommitLoad"
TRACE_COMPLETE_TYPE = "X"
TRACE_DISPATCH_NAME = "EventDispatch"
# Marks the compositor drawing its frame on the screen.
TRACE_DRAW_NAME = "DrawFrame"
TRACE_END_TYPE = "E"
# Marks a main thread frame's start, numbering it for its activation.
TRACE_FRAME_BEGIN_NAME = "BeginMainThreadFrame"
TRACE_FUNCTION_CALL_NAME = "FunctionCall"
TRACE_INSTANT_TYPE = "I"
TRACE_LOAD_NAME = "MarkLoad"
TRACE_MARK_NAMES: tuple[str, ...] = (TRACE_COMMIT_NAME, TRACE_LOAD_NAME)
# A function call of this script id runs no page script, so no file owns it.
TRACE_NO_SCRIPT_ID = "0"
TRACE_PAINT_NAME = "Paint"
# The phase each traced slice counts to and the argument naming its frame.
TRACE_PHASES: dict[str, tuple[str, str]] = {
    "EvaluateScript": (TIMING_SCRIPT_PHASE_NAME, "data"),
    TRACE_FUNCTION_CALL_NAME: (TIMING_SCRIPT_PHASE_NAME, "data"),
    "Layout": ("layout", "beginData"),
    TRACE_PAINT_NAME: ("paint", "data"),
    "UpdateLayoutTree": ("style", "beginData"),
}
# The dispatches a press starts with, its click timed from the first.
TRACE_PRESS_EVENT_TYPES: tuple[str, ...] = ("keydown",)
TRACE_READ_BYTES = 1 << 22
TRACE_SLICE_TYPES: tuple[str, ...] = (
    TRACE_BEGIN_TYPE,
    TRACE_COMPLETE_TYPE,
    TRACE_END_TYPE,
)

VERBOSE_RAW_LEVEL = 2

VIEW_CHECK_ERROR_HASH = "#view=database"

# Names the tool's waiting scripts in a trace, which times no page by them.
WAIT_SCRIPT_URL = "screenshot_wait.js"

# Joins a handshake's key in the accept key a WebSocket server answers with.
WEB_SOCKET_ACCEPT_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
WEB_SOCKET_CLOSE_OPCODE = 0x8
WEB_SOCKET_FINAL_BIT = 0x80
WEB_SOCKET_FRAME_HEAD_BYTES = 2
WEB_SOCKET_HEADER_END = b"\r\n\r\n"
WEB_SOCKET_KEY_BYTES = 16
WEB_SOCKET_LENGTH_MASK = 0x7F
WEB_SOCKET_LONG_LENGTH_BYTES = 8
WEB_SOCKET_LONG_LENGTH_MARK = 127
WEB_SOCKET_MASK_BIT = 0x80
WEB_SOCKET_MASK_BYTES = 4
WEB_SOCKET_OPCODE_MASK = 0x0F
WEB_SOCKET_PING_OPCODE = 0x9
WEB_SOCKET_PONG_OPCODE = 0xA
WEB_SOCKET_READ_BYTES = 1 << 20
WEB_SOCKET_SHORT_LENGTH_BYTES = 2
WEB_SOCKET_SHORT_LENGTH_LIMIT = 1 << 16
WEB_SOCKET_SHORT_LENGTH_MARK = 126
WEB_SOCKET_SWITCH_STATUS = "101"
WEB_SOCKET_TEXT_OPCODE = 0x1
WEB_SOCKET_VERSION = "13"

# The binding a page's console error text reaches, naming its context.
WEBKIT_CONSOLE_BINDING_NAME = "screenshot_console_error"
# Hands each console error's text to the binding, then writes it as before.
WEBKIT_CONSOLE_FORWARD_FUNCTION = (
    "(binding_name) => { const console_error = console.error;"
    " console.error = (...console_parts) => {"
    " window[binding_name](console_parts.map(String).join(' '));"
    " console_error.apply(console, console_parts); }; }"
)
WEBKIT_FRAME_ELEMENTS_EXPRESSION = "document.querySelectorAll('iframe')"
# Groups the objects a WebKit command keeps, released once read.
WEBKIT_OBJECT_GROUP_NAME = "screenshot_driver"
# Reads a property of the object it is called on, a list's item or length.
WEBKIT_PROPERTY_READ_FUNCTION = (
    "function (property_key) { return this[property_key]; }"
)
