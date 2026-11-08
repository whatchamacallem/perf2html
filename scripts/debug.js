// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE-MIT.md file.

window.report_manifest_table_ = "manifest    curl/perf2html.sh v0\nrevision    3163ec0656\ncpu         AMD Ryzen AI 9 HX 370 w/ Radeon 890M\nmemory      15.18 GiB (45% use)\nos          Ubuntu 26.04.1 LTS\ncompiler    gcc 16.0.1\nbuild       -DCMAKE_C_FLAGS=-O2 -g\nexecutable  build-relwithdebinfo/gcc-16-0-1-22_DCMAKECFLAGSO2g/tests/perf/perf\nrecorded    1794150322 2026-11-08 08:05:22 AM MST";

window.try_catch_handler_(function () {
  "use strict";

  const SCREENSHOT_LABEL_QUERY_KEY_NAME = settings_(
    "SCREENSHOT_LABEL_QUERY_KEY_NAME",
  );
  const SCREENSHOT_LABEL_QUERY_VALUE = settings_(
    "SCREENSHOT_LABEL_QUERY_VALUE",
  );
  const SCREENSHOT_MENU_KEY_NUMBER = settings_("SCREENSHOT_MENU_KEY_NUMBER");

  // Shows the report page address in a screenshot corner, a click copies it.
  function screenshot_label_show() {
    const query_values = new URLSearchParams(location.search);
    const label_value = query_values.get(SCREENSHOT_LABEL_QUERY_KEY_NAME);
    if (label_value === null) return;
    if (label_value !== SCREENSHOT_LABEL_QUERY_VALUE)
      window.throw_exception_(
        "str_error_screenshot_label_query_unusable",
        SCREENSHOT_LABEL_QUERY_KEY_NAME,
        label_value,
        SCREENSHOT_LABEL_QUERY_VALUE,
      );
    // The address shown opens the page with no screenshot code running.
    query_values.delete(SCREENSHOT_LABEL_QUERY_KEY_NAME);
    query_values.delete(SCREENSHOT_MENU_KEY_NUMBER);
    const query_text = query_values.size ? "?" + query_values : "";
    const path_names = location.pathname.split("/");
    const page_name = path_names.pop();
    const report_name = path_names.pop();
    const page_path = `${report_name}/${page_name}`;
    const label = document.createElement("div");
    label.className = "screenshot-";
    label.textContent = page_path + query_text + location.hash;
    label.addEventListener(
      "click",
      window.try_catch_handler_(() =>
        navigator.clipboard.writeText(label.textContent),
      ),
    );
    document.body.appendChild(label);
  }

  screenshot_label_show();
})();
