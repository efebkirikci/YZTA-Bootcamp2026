/* CopyTrader dashboard client — /api/state polling (v1). */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const fmtUsd = (v) => (Number(v) < 0 ? "-$" : "$") + Math.abs(Number(v)).toFixed(2);

  function render(s) {
    $("badge-mode").textContent = s.meta.mode;
    $("badge-mode").className = "badge badge-" + s.meta.mode;
    $("badge-api").textContent = s.meta.api_ok ? "API canli" : "API baglanti hatasi";
    $("badge-api").className = "badge " + (s.meta.api_ok ? "badge-ok" : "badge-warn");
    $("stat-equity").textContent = fmtUsd(s.portfolio.equity);
    $("stat-realized").textContent = fmtUsd(s.portfolio.realized_pnl);
    $("stat-unrealized").textContent = fmtUsd(s.portfolio.unrealized_pnl);
    $("stat-open").textContent = s.portfolio.open_positions;

    const mb = $("market-body");
    if (s.market.rows.length) {
      mb.innerHTML = s.market.rows.map(r =>
        `<tr><td><b>${r.symbol}</b></td><td>${Number(r.price).toFixed(4)}</td>` +
        `<td>${r.funding_rate === null ? "—" : (r.funding_rate * 100).toFixed(4) + "%"}</td></tr>`
      ).join("");
    }
  }

  async function poll() {
    try {
      const r = await fetch("/api/state");
      render(await r.json());
    } catch (_) {}
    setTimeout(poll, 3000);
  }
  poll();
})();
