"use strict";
/* HANNA·HRV — history.js
   Consulta /api/history, filtra por rango, grafica la evolución y compara dos sesiones. */
(function () {
  const { G, $, $$, esc, num, fmt, ic, fmtDate, SENSORS, toast } = window.HBA;

  const H = { pid: "", rows: [], range: 30, picked: [], charts: {} };
  const SEM_LBL = { optimo: "Óptimo", funcional: "Funcional", comprometido: "Comprometido", critico: "Crítico" };
  const rm = (r) => num(r.rmssd_corr ?? r.rmssd);

  function kill() { Object.values(H.charts).forEach((c) => c.destroy()); H.charts = {}; }
  const note = (kind, title, msg, extra) => `<div class="empty-state is-${kind}">${ic(kind === "err" ? "triangle-alert" : kind === "cfg" ? "database" : "clock", "ic-xl")}<h3>${esc(title)}</h3><p>${esc(msg)}</p>${extra || ""}</div>`;

  async function load(pid) {
    pid = (pid || "").trim();
    if (!pid) { toast("Ingresá un ID de paciente para buscar.", "err"); $("histId").focus(); return; }
    H.pid = pid; H.picked = []; $("histId").value = pid;
    $("histState").innerHTML = `<div class="empty-state"><div class="spin" aria-hidden="true"></div><p>Cargando historial…</p></div>`;
    $("histBody").hidden = true;
    try {
      const res = await fetch(`/api/history?patient_id=${encodeURIComponent(pid)}`);
      const j = await res.json().catch(() => ({}));
      if (j.backend === "none_configured" || j.warning) {
        G.backend = "none";
        $("histState").innerHTML = note("cfg", "Historial no disponible", "Supabase no está configurado en este despliegue. Definí SUPABASE_URL y SUPABASE_ANON_KEY en las variables de entorno de Vercel.");
        return;
      }
      if (!res.ok || j.error || (j.backend && j.backend !== "supabase")) {
        G.backend = "error";
        $("histState").innerHTML = note("err", "No se pudo consultar el historial", String(j.error || j.backend || "Error del servidor.").slice(0, 200), `<button class="btn btn-soft" type="button" data-act="hist-retry">${ic("refresh-cw")}Reintentar</button>`);
        return;
      }
      G.backend = "ok";
      H.rows = (j.data || []).slice().sort((a, b) => new Date(b.timestamp_utc) - new Date(a.timestamp_utc));
      if (!H.rows.length) { $("histState").innerHTML = note("empty", "Sin mediciones guardadas", `No hay sesiones guardadas para el ID «${pid}». Realizá una medición y guardala para verla acá.`); return; }
      $("histState").innerHTML = ""; $("histBody").hidden = false;
      render();
    } catch (_) {
      G.backend = "error";
      $("histState").innerHTML = note("err", "Sin conexión con el servidor", "Revisá tu conexión e intentá de nuevo.", `<button class="btn btn-soft" type="button" data-act="hist-retry">${ic("refresh-cw")}Reintentar</button>`);
    }
    window.HBA.refreshHome && window.HBA.refreshHome();
  }

  function filtered() {
    if (!H.range) return H.rows;
    const lim = Date.now() - H.range * 864e5;
    return H.rows.filter((r) => new Date(r.timestamp_utc).getTime() >= lim);
  }

  function render() {
    $$("[data-range]").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.range === H.range)));
    const rows = filtered();
    $("histCount").textContent = `${rows.length} ${rows.length === 1 ? "sesión" : "sesiones"} en el período · ${H.rows.length} en total`;
    drawCharts(rows);
    $("histList").innerHTML = rows.length ? listHTML(rows) : note("empty", "Sin sesiones en este período", "Elegí un rango más amplio para ver otras mediciones.");
    drawCompare();
  }

  function drawCharts(rows) {
    kill();
    const box = $("histCharts");
    if (rows.length < 2) { box.innerHTML = `<p class="note">${ic("info")}Para ver la evolución hacen falta al menos 2 mediciones en el período elegido.</p>`; return; }
    box.innerHTML = `<figure class="chart-card"><figcaption>RMSSD corregido <span class="muted">· ms</span></figcaption><div class="chart-box"><canvas id="chRm" role="img" aria-label="Evolución del RMSSD"></canvas></div></figure>
      <figure class="chart-card"><figcaption>Cargas autonómicas <span class="muted">· 0–100</span></figcaption><div class="chart-box"><canvas id="chCg" role="img" aria-label="Evolución de las cargas"></canvas></div></figure>
      <figure class="chart-card"><figcaption>Potencia HF sobre HF+LF <span class="muted">· %</span></figcaption><div class="chart-box"><canvas id="chBal" role="img" aria-label="Evolución del balance HF/LF"></canvas></div></figure>`;
    if (!window.Chart) return;
    Chart.defaults.font.family = "'Figtree', system-ui, sans-serif"; Chart.defaults.color = "#3F5C94";
    const asc = rows.slice().reverse();
    const labels = asc.map((r) => { const d = new Date(r.timestamp_utc); return `${d.getDate()}/${d.getMonth() + 1}`; });
    const base = { responsive: true, maintainAspectRatio: false, spanGaps: true, interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } }, y: { grid: { color: "rgba(10,92,255,.10)" } } } };
    const ln = (label, data, color, dash) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: 2.2, pointRadius: 3, pointBackgroundColor: "#fff", pointBorderColor: color, pointBorderWidth: 2, tension: 0.3, borderDash: dash || [] });
    H.charts.rm = new Chart($("chRm"), { type: "line", data: { labels, datasets: [{ ...ln("RMSSD", asc.map(rm), "#0A5CFF"), fill: true, backgroundColor: "rgba(10,92,255,.09)" }] }, options: base });
    const legend = { ...base, plugins: { legend: { display: true, labels: { boxWidth: 12, usePointStyle: true } } } };
    H.charts.cg = new Chart($("chCg"), { type: "line", data: { labels, datasets: [
      ln("Autonómica", asc.map((r) => num(r.carga_autonomica)), "#0A2A6B"), ln("Emocional", asc.map((r) => num(r.carga_emocional)), "#1F8BFF", [6, 4]),
      ln("Física", asc.map((r) => num(r.carga_fisica)), "#5AA9FF", [2, 3]), ln("Estrés", asc.map((r) => num(r.estres)), "#0A5CFF", [10, 3, 2, 3])] }, options: legend });
    const share = (r) => { const lf = num(r.lf_power), hf = num(r.hf_power); return lf != null && hf != null && lf + hf > 0 ? Math.round(hf / (lf + hf) * 100) : null; };
    H.charts.bal = new Chart($("chBal"), { type: "line", data: { labels, datasets: [ln("HF %", asc.map(share), "#1F8BFF")] }, options: { ...base, scales: { ...base.scales, y: { ...base.scales.y, min: 0, max: 100 } } } });
  }

  function listHTML(rows) {
    return `<div class="tbl-wrap"><table class="tbl tbl-hist"><thead><tr><th scope="col">Comparar</th><th scope="col">Fecha</th><th scope="col">Estado</th><th scope="col">RMSSD</th><th scope="col">FC media</th><th scope="col">Método</th><th scope="col">Informe</th></tr></thead><tbody>
      ${rows.map((r) => { const id = String(r.id ?? r.timestamp_utc), on = H.picked.includes(id);
        return `<tr class="${on ? "is-picked" : ""}"><td data-label="Comparar"><label class="check"><input type="checkbox" data-pick="${esc(id)}" ${on ? "checked" : ""}><span>Elegir</span></label></td>
        <th scope="row" data-label="Fecha">${esc(fmtDate(r.timestamp_utc))}</th>
        <td data-label="Estado">${r.semaphore_label ? `<span class="chip chip-st">${esc(r.semaphore_label)}</span>` : '<span class="muted">—</span>'}</td>
        <td data-label="RMSSD"><span class="cell"><strong>${fmt(rm(r), 1)}</strong> <span class="u">ms</span></span></td>
        <td data-label="FC media"><span class="cell">${num(r.hr_mean) != null ? `<strong>${fmt(r.hr_mean, 0)}</strong> <span class="u">bpm</span>` : "—"}</span></td>
        <td data-label="Método">${esc((SENSORS[r.sensor_type] || {}).label || r.sensor_type || "—")}${r.duration_minutes ? ` · ${esc(r.duration_minutes)} min` : ""}</td>
        <td data-label="Informe"><button type="button" class="btn btn-soft btn-sm" data-report="${esc(id)}" aria-label="Informe PDF de la sesión del ${esc(fmtDate(r.timestamp_utc))}">${ic("file-text")}PDF</button></td></tr>`; }).join("")}
      </tbody></table></div>`;
  }

  const CMP = [["RMSSD corregido", rm, 1, "ms"], ["SDNN", (r) => num(r.sdnn), 1, "ms"], ["lnRMSSD", (r) => num(r.lnrmssd), 2, ""], ["pNN50", (r) => num(r.pnn50), 1, "%"],
    ["FC media", (r) => num(r.hr_mean), 0, "bpm"], ["LF/HF", (r) => num(r.lf_hf), 2, ""], ["DFA α1", (r) => num(r.dfa_alpha1), 2, ""],
    ["Carga autonómica", (r) => num(r.carga_autonomica), 0, ""], ["Carga emocional", (r) => num(r.carga_emocional), 0, ""], ["Carga física", (r) => num(r.carga_fisica), 0, ""], ["Estrés", (r) => num(r.estres), 0, ""],
    ["Calidad de señal", (r) => num(r.quality_score), 0, "%"]];
  function drawCompare() {
    const box = $("histCompare");
    if (H.picked.length !== 2) {
      box.innerHTML = `<p class="note">${ic("git-compare")}${H.picked.length === 1 ? "Elegí una segunda sesión para compararlas." : "Elegí dos sesiones de la lista para compararlas."}</p>`; return;
    }
    const pair = H.picked.map((id) => H.rows.find((r) => String(r.id ?? r.timestamp_utc) === id)).filter(Boolean)
      .sort((a, b) => new Date(a.timestamp_utc) - new Date(b.timestamp_utc));
    if (pair.length !== 2) { box.innerHTML = ""; return; }
    const [a, b] = pair;
    const rows = CMP.map(([l, f, d, u]) => { const x = f(a), y = f(b); if (x == null && y == null) return "";
      const dl = x != null && y != null ? y - x : null; const sign = dl == null ? "" : dl > 0 ? "+" : dl < 0 ? "−" : "";
      return `<tr><th scope="row" data-label="Indicador">${l}</th><td data-label="Anterior">${x != null ? x.toFixed(d) + " " + u : "—"}</td><td data-label="Reciente">${y != null ? y.toFixed(d) + " " + u : "—"}</td>
        <td data-label="Cambio"><strong>${dl == null ? "—" : sign + Math.abs(dl).toFixed(d) + " " + u}</strong></td></tr>`; }).join("");
    box.innerHTML = `<div class="tbl-wrap"><table class="tbl"><caption class="muted">Anterior: ${esc(fmtDate(a.timestamp_utc))} · Reciente: ${esc(fmtDate(b.timestamp_utc))}</caption>
      <thead><tr><th scope="col">Indicador</th><th scope="col">Anterior</th><th scope="col">Reciente</th><th scope="col">Cambio</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="note">${ic("info")}El cambio es la diferencia numérica entre ambas sesiones; no implica mejora ni empeoramiento por sí solo.</p>`;
  }

  function init() {
    $("histForm").addEventListener("submit", (e) => { e.preventDefault(); load($("histId").value); });
    $$("[data-range]").forEach((b) => b.addEventListener("click", () => { H.range = +b.dataset.range; if (H.rows.length) render(); }));
    $("histList").addEventListener("change", (e) => {
      const id = e.target.dataset && e.target.dataset.pick; if (id == null) return;
      if (e.target.checked) { if (H.picked.length >= 2) { e.target.checked = false; toast("Solo se pueden comparar dos sesiones. Quitá una para elegir otra.", "err"); return; } H.picked.push(id); }
      else H.picked = H.picked.filter((x) => x !== id);
      e.target.closest("tr").classList.toggle("is-picked", e.target.checked); drawCompare();
    });
    $("histState").addEventListener("click", (e) => { if (e.target.closest("[data-act=hist-retry]")) load(H.pid); });
  }

  function onShow() { Object.values(H.charts).forEach((c) => c.resize()); }

  window.HBA.history = { init, load, onShow, count: () => H.rows.length, pid: () => H.pid, rows: () => H.rows.slice(), get: (id) => H.rows.find((r) => String(r.id ?? r.timestamp_utc) === String(id)) };
})();
