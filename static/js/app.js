(function () {
  // Theme toggle
  var root = document.documentElement;
  var btn = document.getElementById("themeToggle");
  function syncIcon() {
    if (!btn) return;
    btn.querySelector("i").className = root.getAttribute("data-bs-theme") === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
  }
  syncIcon();
  if (btn) {
    btn.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      try { localStorage.setItem("cc-theme", next); } catch (e) {}
      syncIcon();
      document.dispatchEvent(new CustomEvent("cc:theme", { detail: next }));
    });
  }

  // Tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el, { trigger: "hover" });
  });

  // Auto-dismiss toasts
  document.querySelectorAll(".cc-toast").forEach(function (t, i) {
    setTimeout(function () {
      t.style.transition = "opacity .3s, transform .3s";
      t.style.opacity = "0";
      t.style.transform = "translateX(20px)";
      setTimeout(function () { t.remove(); }, 300);
    }, 4500 + i * 400);
  });

  // Auto-submit filter forms on change
  document.querySelectorAll("form[data-autosubmit]").forEach(function (form) {
    form.addEventListener("change", function (e) {
      if (e.target.matches("[data-no-autosubmit]")) return;
      form.requestSubmit();
    });
  });

  // Clickable table rows
  document.querySelectorAll("tr[data-href]").forEach(function (row) {
    row.classList.add("row-link");
    row.addEventListener("click", function (e) {
      if (e.target.closest("a, button, form, input, select")) return;
      window.location = row.dataset.href;
    });
  });

  // Confirm prompts
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.dataset.confirm)) e.preventDefault();
    });
  });
})();
