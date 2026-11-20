// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE-MIT.md file.

window.try_catch_handler_(function () {
  "use strict";

  const RESOURCE_FAILURE_TEXT = window.settings_opening_(
    "RESOURCE_FAILURE_TEXT",
  );
  const RESOURCE_TAG_NAMES = window.settings_opening_("RESOURCE_TAG_NAMES");
  const expected_failure_sources = new Set();

  function resource_failure_expect_(source) {
    expected_failure_sources.add(source);
  }

  function resource_failure_handler_(browser_event) {
    const target = browser_event.target;
    if (
      target &&
      target !== window &&
      RESOURCE_TAG_NAMES.includes(target.tagName) &&
      !expected_failure_sources.has(target.href || target.src)
    )
      throw new Error(RESOURCE_FAILURE_TEXT + (target.href || target.src));
  }

  // Marks the page drawn in a task after the paint that shows its first draw.
  function page_drawn_mark_() {
    if (window.page_is_drawn_) window.throw_exception_("str_error_internal");
    requestAnimationFrame(
      window.try_catch_handler_(() =>
        setTimeout(
          window.try_catch_handler_(() => {
            window.page_is_drawn_ = true;
          }),
        ),
      ),
    );
  }

  window.page_drawn_mark_ = page_drawn_mark_;
  window.page_is_drawn_ = false;
  window.resource_failure_expect_ = resource_failure_expect_;
  window.addEventListener(
    "error",
    window.try_catch_handler_(resource_failure_handler_),
    true,
  );
})();
