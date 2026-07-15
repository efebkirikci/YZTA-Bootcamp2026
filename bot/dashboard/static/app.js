/* CopyTrader dashboard client — WebSocket + ayar yonetimi. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 2) => (v === null || v === undefined || isNaN(v)) ? "—" : Number(v).toFixed(d);
  const fmtUsd = (v) => { const n = Number(v); if (isNaN(n)) return "—"; return (n < 0 ? "-$" : "$") + Math.abs(n).toFixed(2); };
  const cls = (v) => (Number(v) > 0 ? "pos" : Number(v) < 0 ? "neg" : "");

  let equityChart = null;

  function render(s) {
    $("badge-mode").textContent = s.meta.mode;
    $("badge-mode").className = "badge badge-" + s.meta.mode;
    $("badge-api").textContent = s.meta.api_ok ? "API canli" : "API baglanti hatasi";
    $("badge-api").className = "badge " + (s.meta.api_ok ? "badge-ok" : "badge-warn");

    $("stat-equity").textContent = fmtUsd(s.portfolio.equity);
    $("stat-realized").textContent = fmtUsd(s.portfolio.realized_pnl);
    $("stat-realized").className = "val " + cls(s.portfolio.realized_pnl);
    $("stat-unrealized").textContent = fmtUsd(s.portfolio.unrealized_pnl);
    $("stat-unrealized").className = "val " + cls(s.portfolio.unrealized_pnl);
    $("stat-open").textContent = s.portfolio.open_positions;
    $("stat-funding").textContent = fmtUsd(s.portfolio.total_funding_collected);
    $("stat-scans").textContent = s.meta.scan_count;

    const mb = $("market-body");
    if (s.market.rows.length) {
      mb.innerHTML = s.market.rows.map(r =>
        `<tr><td><b>${r.symbol}</b></td><td>${fmt(r.price, 4)}</td>` +
        `<td>${r.funding_rate === null ? "—" : (r.funding_rate * 100).toFixed(4) + "%"}</td></tr>`
      ).join("");
      $("market-updated").textContent = "· " + (s.market.last_update || "").replace("T", " ").slice(0, 19) + " UTC";
    }

    const pb = $("positions-body");
    if (s.positions.length) {
      pb.innerHTML = s.positions.map(p =>
        `<tr><td><b>${p.symbol}</b></td><td class="side-${p.side.toLowerCase()}">${p.side}</td>` +
        `<td>${p.strategy}</td><td>$${fmt(p.size_usd)}</td><td>${fmt(p.entry_price, 4)}</td>` +
        `<td class="${cls(p.unrealized_pnl)}">${fmtUsd(p.unrealized_pnl)}</td>` +
        `<td>${fmtUsd(p.funding_collected || 0)}</td></tr>`).join("");
    } else {
      pb.innerHTML = '<tr><td colspan="7" class="muted">Pozisyon yok</td></tr>';
    }

    const sl = $("signals-list");
    if (s.latest_signals && s.latest_signals.length) {
      sl.innerHTML = s.latest_signals.slice().reverse().map(sg =>
        `<div class="signal"><span class="sym">${sg.symbol}</span>` +
        `<span class="side-${sg.side.toLowerCase()}">${sg.side}</span>` +
        `<span class="rsn">${sg.reason}</span></div>`).join("");
    } else {
      sl.innerHTML = '<div class="muted">Sinyal bekleniyor…</div>';
    }

    if (s.events.length) {
      $("events").innerHTML = s.events.slice().reverse().map(e =>
        `<div class="event ${e.kind}"><span class="ts">${(e.ts || "").replace("T", " ").slice(11, 19)}</span>${e.text}</div>`
      ).join("");
    }

    drawEquity(s.equity_curve || []);
  }

  function drawEquity(curve) {
    if (!window.Chart) return;
    const labels = curve.map(p => (p.ts || "").replace("T", " ").slice(11, 19));
    const data = curve.map(p => p.equity);
    if (!equityChart) {
      equityChart = new Chart($("equity-chart"), {
        type: "line",
        data: { labels, datasets: [{ label: "Ozsermaye", data, borderColor: "#8b5cf6",
          backgroundColor: "rgba(139,92,246,0.12)", fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 }] },
        options: { responsive: true, plugins: { legend: { display: false } },
          scales: { x: { ticks: { color: "#8b8b9e", maxTicksLimit: 8 }, grid: { color: "#1a1a24" } },
                     y: { ticks: { color: "#8b8b9e" }, grid: { color: "#1a1a24" } } } },
      });
    } else {
      equityChart.data.labels = labels;
      equityChart.data.datasets[0].data = data;
      equityChart.update("none");
    }
  }

  function fillSettings(settings) {
    const map = {
      active_strategy: $("set-active_strategy"),
      symbols: $("set-symbols"),
      max_position_size_usd: $("set-max_position_size_usd"),
      max_open_positions: $("set-max_open_positions"),
    };
    for (const [key, el] of Object.entries(map)) {
      if (settings[key]) el.value = settings[key].value;
    }
  }

  $("settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const map = {
      active_strategy: $("set-active_strategy").value,
      symbols: $("set-symbols").value,
      max_position_size_usd: $("set-max_position_size_usd").value,
      max_open_positions: $("set-max_open_positions").value,
    };
    let ok = 0;
    for (const [key, value] of Object.entries(map)) {
      const r = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
      });
      if (r.ok) ok++;
    }
    const el = $("settings-saved");
    el.textContent = ok + " ayar kaydedildi ✓";
    setTimeout(() => (el.textContent = ""), 2500);
  });

  function connectWS() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onmessage = (e) => { try { render(JSON.parse(e.data)); } catch (_) {} };
    ws.onclose = () => setTimeout(connectWS, 3000);
    ws.onerror = () => ws.close();
  }

  async function poll() {
    try {
      const r = await fetch("/api/state");
      const s = await r.json();
      render(s);
      fillSettings(s.settings);
    } catch (_) {}
    setTimeout(poll, 3000);
  }

  fetch("/api/state").then(r => r.json()).then(s => {
    fillSettings(s.settings);
    render(s);
  }).catch(() => {});
  if (window.WebSocket) connectWS();
  poll();
})();
