"use strict";
(() => {
  const toggle = document.getElementById("toggle-sidebar");
  if (toggle) {
    toggle.addEventListener("click", () => {
      document.body.classList.toggle("sidebar-collapsed");
      toggle.setAttribute("aria-expanded", String(!document.body.classList.contains("sidebar-collapsed")));
    });
  }
  window.fereziniToast = (message, error = false) => {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.toggle("error", error);
    toast.hidden = false;
    clearTimeout(window.fereziniToastTimeout);
    window.fereziniToastTimeout = setTimeout(() => { toast.hidden = true; }, 6000);
  };
})();
