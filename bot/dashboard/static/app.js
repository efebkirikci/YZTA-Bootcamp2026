/* CopyTrader dashboard client — WebSocket canli akis + ayar yonetimi. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 2) => (v === null || v === undefined || isNaN(v)) ? "—" : Number(v).toFixed(d);
  const fmtUsd = (v) => { const n = Number(v); if (isNaN(n)) return "—"; return (n < 0 ? "-$" : "$") + Math.abs(n).toFixed(2); };
  const cls = (v) => (Number(v) > 0 ? "pos" : Number(v) < 0 ? "neg" : "");

  let equityChart = null;

  function render(s) {
    $("badge-mode").textContent = s.meta.mode;
    $("badge-mode").className = "badge " + (s.meta.mode === "live" ? "badge-live" : "badge-paper");
    $("badge-api").textContent = s.meta.api_ok ? "API canli" : "API baglanti hatasi";
    $("badge-api").className = "badge " + (s.meta.api_ok ? "badge-ok" : "badge-warn");
    $("badge-ai").textContent = s.meta.ai_enabled ? "AI aktif" : "AI kapali";
    $("badge-ai").className = "badge " + (s.meta.ai_enabled ? "badge-on" : "badge-off");

    $("stat-equity").textContent = fmtUsd(s.portfolio.equity);
    const ed = $("stat-equity-delta");
    const total = s.portfolio.realized_pnl + s.portfolio.unrealized_pnl;
    ed.textContent = (total >= 0 ? "+" : "") + fmtUsd(total);
    ed.className = "delta " + cls(total);
    $("stat-realized").textContent = fmtUsd(s.portfolio.realized_pnl);
    $("stat-realized").className = "val " + cls(s.portfolio.realized_pnl);
    $("stat-unrealized").textContent = fmtUsd(s.portfolio.unrealized_pnl);
    $("stat-unrealized").className = "val " + cls(s.portfolio.unrealized_pnl);
    $("stat-open").textContent = s.portfolio.open_positions;
    $("stat-funding").textContent = fmtUsd(s.portfolio.total_funding_collected);
    $("stat-scans").textContent = s.meta.scan_count;

    const mb = $("market-body");
    if (s.market.rows && s.market.rows.length) {
      mb.innerHTML = s.market.rows.map(r => {
        const chg = r.change_pct === null || r.change_pct === undefined ? null : Number(r.change_pct);
        const fr = r.funding_rate === null || r.funding_rate === undefined ? null : Number(r.funding_rate) * 100;
        const vol = r.volume ? (Number(r.volume) / 1e6).toFixed(1) + "M" : "—";
        return `<tr><td><b>${r.symbol}</b></td><td>${fmt(r.price, 4)}</td>` +
          `<td class="${cls(chg)}">${chg === null ? "—" : (chg >= 0 ? "+" : "") + chg.toFixed(2) + "%"}</td>` +
          `<td class="${cls(fr)}">${fr === null ? "—" : fr.toFixed(4) + "%"}</td><td>${vol}</td></tr>`;
      }).join("");
      $("market-updated").textContent = "· " + (s.market.last_update || "").replace("T", " ").slice(0, 19) + " UTC";
    } else {
      mb.innerHTML = '<tr><td colspan="5" class="muted">Veri bekleniyor…</td></tr>';
    }

    const pb = $("positions-body");
    if (s.positions.length) {
      pb.innerHTML = s.positions.map(p => {
        const pnl = Number(p.unrealized_pnl || 0);
        return `<tr><td><b>${p.symbol}</b></td><td class="side-${p.side.toLowerCase()}">${p.side}</td>` +
          `<td>${p.strategy}</td><td>$${fmt(p.size_usd)}</td><td>${fmt(p.entry_price, 4)}</td>` +
          `<td class="${cls(pnl)}">${fmtUsd(pnl)}</td><td>${fmtUsd(p.funding_collected || 0)}</td>` +
          `<td><button class="btn btn-ghost" onclick="window.closePos(${p.id})">Kapat</button></td></tr>`;
      }).join("");
    } else {
      pb.innerHTML = '<tr><td colspan="8" class="muted">Pozisyon yok</td></tr>';
    }

    const sl = $("signals-list");
    if (s.latest_signals && s.latest_signals.length) {
      sl.innerHTML = s.latest_signals.slice().reverse().map(sg =>
        `<div class="signal"><span class="sym">${sg.symbol}</span>` +
        `<span class="side-${sg.side.toLowerCase()}">${sg.side}</span>` +
        `<span class="rsn">${sg.reason}</span>` +
        `<span class="muted">${(sg.confidence * 100).toFixed(0)}%</span></div>`).join("");
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
      funding_rate_threshold: $("set-funding_rate_threshold"),
      scan_interval_sec: $("set-scan_interval_sec"),
      max_position_size_usd: $("set-max_position_size_usd"),
      max_open_positions: $("set-max_open_positions"),
      stop_loss_pct: $("set-stop_loss_pct"),
      take_profit_pct: $("set-take_profit_pct"),
      max_portfolio_risk_pct: $("set-max_portfolio_risk_pct"),
      max_daily_loss_usd: $("set-max_daily_loss_usd"),
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
      funding_rate_threshold: $("set-funding_rate_threshold").value,
      scan_interval_sec: $("set-scan_interval_sec").value,
      max_position_size_usd: $("set-max_position_size_usd").value,
      max_open_positions: $("set-max_open_positions").value,
      stop_loss_pct: $("set-stop_loss_pct").value,
      take_profit_pct: $("set-take_profit_pct").value,
      max_portfolio_risk_pct: $("set-max_portfolio_risk_pct").value,
      max_daily_loss_usd: $("set-max_daily_loss_usd").value,
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

  window.closePos = async (id) => {
    const r = await fetch(`/api/trade/close/${id}`, { method: "POST" });
    const res = await r.json();
    if (res.ok) alert("Pozisyon kapatildi — PnL: $" + res.pnl.toFixed(2));
    else alert("Kapatilamadi: " + (res.error || "bilinmeyen hata"));
  };

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
