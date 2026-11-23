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
    dialog.querySelector("[data-close-import]").addEventListener("click", () => dialog.close());
    dialog.querySelector("form").addEventListener("submit", () => {
      const button = dialog.querySelector('button[type="submit"]');
      button.disabled = true;
      button.textContent = "Importando…";
    });
    dialog.addEventListener("close", () => {
      dialog.querySelector("form").reset();
      const button = dialog.querySelector('button[type="submit"]');
      button.disabled = false;
      button.textContent = "Importar";
    });
  }
})();
