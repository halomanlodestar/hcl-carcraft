/* Theme-aware Chart.js helpers. Each chart is (re)built from a factory so it can be redrawn when the theme flips. */
window.CC = window.CC || {};
(function (CC) {
  var registry = [];
  var inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

  CC.palette = { red: "#e0313b", blue: "#2e90fa", green: "#12b76a", amber: "#f79009", violet: "#7a5af8", pink: "#ee46bc", cyan: "#0ba5ec", slate: "#667085" };
  CC.series = ["#e0313b", "#2e90fa", "#12b76a", "#f79009", "#7a5af8", "#0ba5ec", "#ee46bc", "#667085"];

  CC.compactINR = function (v) {
    if (Math.abs(v) >= 1e7) return "₹" + (v / 1e7).toFixed(1) + " Cr";
    if (Math.abs(v) >= 1e5) return "₹" + (v / 1e5).toFixed(1) + " L";
    if (Math.abs(v) >= 1e3) return "₹" + (v / 1e3).toFixed(0) + "k";
    return "₹" + v;
  };
  CC.inr = function (v) { return inr.format(v); };

  function theme() {
    var s = getComputedStyle(document.documentElement);
    return { text: s.getPropertyValue("--cc-muted").trim(), grid: s.getPropertyValue("--cc-border").trim(), surface: s.getPropertyValue("--cc-surface").trim(), ink: s.getPropertyValue("--cc-ink").trim() };
  }

  function applyDefaults() {
    var t = theme();
    Chart.defaults.font.family = '"Plus Jakarta Sans", system-ui, sans-serif';
    Chart.defaults.font.size = 12;
    Chart.defaults.color = t.text;
    Chart.defaults.borderColor = t.grid;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.pointStyle = "circle";
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Chart.defaults.plugins.legend.labels.padding = 16;
    Chart.defaults.plugins.tooltip.backgroundColor = t.ink;
    Chart.defaults.plugins.tooltip.titleColor = t.surface;
    Chart.defaults.plugins.tooltip.bodyColor = t.surface;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.boxPadding = 4;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.layout.padding = { left: 8 };
    return t;
  }

  CC.chart = function (id, factory) {
    var el = document.getElementById(id);
    if (!el) return;
    var entry = { el: el, factory: factory, chart: null };
    entry.render = function () {
      if (entry.chart) entry.chart.destroy();
      entry.chart = new Chart(el, factory(theme()));
    };
    registry.push(entry);
    applyDefaults();
    entry.render();
  };

  CC.moneyAxis = function (t, stacked) {
    return {
      x: { stacked: !!stacked, grid: { display: false }, border: { display: false } },
      y: { stacked: !!stacked, border: { display: false }, grid: { color: t.grid }, ticks: { callback: function (v) { return CC.compactINR(v); }, maxTicksLimit: 6 } }
    };
  };

  document.addEventListener("cc:theme", function () {
    applyDefaults();
    registry.forEach(function (e) { e.render(); });
  });
})(window.CC);
