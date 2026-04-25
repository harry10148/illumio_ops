// Integrations tab: switcher + shared helpers + per-pane renderers.
(function () {
  'use strict';

  // Escape user-provided text before inserting into markup.
  // Used throughout this module — NEVER inline user data without this.
  function escapeAttr(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }
  window.escapeAttr = escapeAttr;

  function integrationsSwitch(name) {
    ['overview', 'cache', 'siem', 'dlq'].forEach(function (n) {
      var pane = document.getElementById('it-pane-' + n);
      if (pane) pane.style.display = (n === name) ? '' : 'none';
    });
    document.querySelectorAll('#p-integrations .sub-tab').forEach(function (btn) {
      btn.classList.toggle('active',
        btn.getAttribute('onclick') && btn.getAttribute('onclick').indexOf("'" + name + "'") >= 0);
    });
    if (name === 'overview') renderOverview();
    else if (name === 'cache') renderCache();
    else if (name === 'siem') renderSiem();
    else if (name === 'dlq') renderDlq();
  }
  window.integrationsSwitch = integrationsSwitch;

  // Hook into the project's existing switchTab to auto-render Overview on first visit.
  var originalSwitchTab = window.switchTab;
  if (typeof originalSwitchTab === 'function') {
    window.switchTab = function (name) {
      var r = originalSwitchTab.apply(this, arguments);
      if (name === 'integrations') integrationsSwitch('overview');
      return r;
    };
  }

  // Placeholder renderers — later tasks replace each body.
  async function renderOverview() {}
  async function renderCache() {}
  async function renderSiem() {}
  async function renderDlq() {}

  // Expose for later tasks.
  window._integrations = {
    renderOverview: function () { return renderOverview(); },
    renderCache: function () { return renderCache(); },
    renderSiem: function () { return renderSiem(); },
    renderDlq: function () { return renderDlq(); },
    setRender: function (name, fn) {
      if (name === 'overview') renderOverview = fn;
      else if (name === 'cache') renderCache = fn;
      else if (name === 'siem') renderSiem = fn;
      else if (name === 'dlq') renderDlq = fn;
    },
  };
})();
