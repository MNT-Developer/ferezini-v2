"use strict";
(() => {
  document.querySelectorAll("[data-project-row]").forEach(row => {
    row.addEventListener("click", event => {
      if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      if (event.target.closest("a, button, input, select, textarea, label, summary, [contenteditable]")) return;
      if (!window.getSelection().isCollapsed) return;
      window.location.assign(row.querySelector("a.table-title").href);
    });
  });

  const trigger = document.getElementById("import-project");
  const dialog = document.getElementById("import-project-dialog");
  if (trigger && dialog) {
    trigger.addEventListener("click", () => dialog.showModal());
    dialog.addEventListener("close", () => dialog.querySelector("form").reset());
  }
})();
