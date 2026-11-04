"use strict";
/* HANNA·HRV — results.js
   Dibuja SOLO datos devueltos por /api/compute. Si una métrica no existe, no se muestra. */
(function () {
  const { G, $, $$, esc, num, fmt, ic, SENSORS } = window.HBA;

  const C = { hanna: "#0A5CFF", electric: "#1F8BFF", mid: "#5AA9FF", celeste: "#A9D4FF", deep: "#0A2A6B", ink: "#0A1F4D", grid: "rgba(10,92,255,.10)" };
  const charts = {};
  function killChart(k) { if (charts[k]) { charts[k].destroy(); delete charts[k]; } }
  function chartDefaults() {
    if (!window.Chart) return;
    Chart.defaults.font.family = "'Figtree', system-ui, sans-serif";
    Chart.defaults.color = "#3F5C94";
  }

  const STAGES = [
    { key: "critico", label: "Crítico", icon: "triangle-alert" },
    { key: "comprometido", label: "Comprometido", icon: "circle-alert" },
    { key: "funcional", label: "Funcional", icon: "circle-check" },
    { key: "optimo", label: "Óptimo", icon: "sparkles" },
  ];
  const STATE_LBL = { alto: "Alto", medio: "En rango", bajo: "Bajo", informativo: "Informativo", insuficiente: "No disponible" };
  const LEVEL_LBL = { bajo: "Bajo", moderado: "Moderado", alto: "Alto", "muy alto": "Muy alto", insuficiente: "Insuficiente" };

  const hasVal = (b) => num(b.value) != null;

  /* ── Banner de validación ── */
  function validationBanner(v) {
    if (!v || v.severity === "ok") return "";
    const bad = v.severity === "invalid";
    const rows = v.issues.map((i) => `<div class="val-row"><strong>${esc(i.field)}</strong><span class="val-v">${esc(i.value)}</span><span class="val-m">${esc(i.msg)}</span></div>`).join("");
    const causes = bad ? `<div class="val-causes"><p class="h-sm">Causas frecuentes</p><ul class="bullets">
      <li>Movimiento excesivo durante la medición.</li><li>Dedo mal posicionado sobre el lente.</li><li>Luz ambiental directa sobre el sensor.</li>
      <li>Flash apagado.</li><li>Señal muy corta o interrumpida.</li></ul></div>` : "";
    return `<section class="val ${bad ? "is-bad" : "is-warn"}" role="alert">
      <div class="val-head">${ic(bad ? "triangle-alert" : "circle-alert", "ic-lg")}<div>
        <h3>${bad ? "Resultado no válido: repetí la medición" : "Resultado con advertencias"}</h3>
        <p>${bad ? "Los valores registrados están fuera del rango fisiológico humano." : "Los valores están en el límite del rango fisiológico normal."}</p></div></div>
      <div class="val-list">${rows}</div>${causes}
      <div class="val-actions">${bad
        ? `<button class="btn btn-primary" type="button" data-act="retry">${ic("rotate-ccw")}Repetir medición</button>`
        : `<button class="btn btn-soft" type="button" data-act="dismiss-val">Entendido, ver resultados</button>`}</div>
    </section>`;
  }

  /* ── Hero ── */
  function refBar(norms, r) {
    if (!norms || num(norms.rmssd_low) == null || r == null) return "";
    const lo = +norms.rmssd_low, hi = +norms.rmssd_high; let pct;
    if (r <= lo) pct = Math.max(2, (r / lo) * 35);
    else if (r <= hi) pct = 35 + ((r - lo) / (hi - lo)) * 30;
    else pct = Math.min(98, 65 + ((r - hi) / (hi * 0.5)) * 33);
    const hasAge = norms.age != null && norms.age !== "";
    return `<div class="ref">
      <p class="h-sm">${hasAge ? "Referencia para su edad y sexo" : "Referencia general (sin edad cargada)"}</p>
      <div class="ref-bar" role="img" aria-label="RMSSD ${fmt(r, 1)} ms; rango de referencia ${lo.toFixed(0)} a ${hi.toFixed(0)} ms"><i style="left:${pct}%"></i></div>
      <div class="ref-scale"><span>${lo.toFixed(0)} ms</span><span>${hi.toFixed(0)} ms</span></div></div>`;
  }

  function hero(data, v) {
    const dash = data.hba_dashboard || {}, sem = dash.semaphore || {};
    const r = num(data.rmssd_corr ?? data.rmssd), bad = v && v.severity === "invalid";
    const idx = STAGES.findIndex((s) => s.key === sem.key);
    const stage = STAGES[idx] || null;
    const ramp = bad || !stage ? "" : `<ol class="ramp" aria-label="Estado autonómico">${STAGES.map((s, i) =>
      `<li class="${i === idx ? "is-on" : i < idx ? "is-pass" : ""}" ${i === idx ? 'aria-current="true"' : ""}><i></i><span>${s.label}</span></li>`).join("")}</ol>`;
    const meta = [
      ["Método", (SENSORS[data.sensor_type] || {}).label || data.sensor_type],
      ["Duración", data.duration_minutes ? `${data.duration_minutes} min` : null],
      ["Calidad de señal", num(data.quality_score) != null ? `${fmt(data.quality_score, 0)} %` : null],
      ["Artefactos", num(data.artifact_percent) != null ? `${fmt(data.artifact_percent, 1)} %` : null],
      ["Factor por duración", num(data.duration_correction) != null ? `×${fmt(data.duration_correction, 2)}` : null],
      ["Latidos analizados", num(data.n_nn) != null ? String(data.n_nn) : null],
    ].filter((m) => m[1] != null).map((m) => `<div><dt>${m[0]}</dt><dd>${esc(m[1])}</dd></div>`).join("");
    return `<section class="hero-res ${bad ? "is-invalid" : "sem-" + esc(sem.key || "funcional")}" aria-labelledby="hrTitle">
      <div class="hr-main">
        <h3 id="hrTitle" class="hr-label">RMSSD corregido</h3>
        <p class="hr-value"><span>${fmt(r, 1)}</span><small>ms</small></p>
        ${bad ? `<span class="badge badge-bad">${ic("triangle-alert")}Resultado no válido</span>`
          : stage ? `<span class="badge badge-state">${ic(stage.icon)}${esc(sem.label || stage.label)}</span>` : ""}
        <p class="hr-desc">${bad ? "El valor está fuera del rango fisiológico y no debe interpretarse." : esc(sem.description || "")}</p>
      </div>
      <div class="hr-side">${ramp}${bad ? "" : refBar(dash.norms, r)}</div>
      <dl class="hr-meta">${meta}</dl>
    </section>`;
  }

  /* ── Resultados ── */
  function tiles(data) {
    const items = [
      ["FC media", data.hr_mean, 0, "bpm"], ["SDNN", data.sdnn, 1, "ms"],
      ["lnRMSSD", data.lnrmssd, 2, ""], ["LF/HF", data.lf_hf, 2, ""],
    ].filter((i) => num(i[1]) != null);
    if (!items.length) return "";
    return `<div class="tiles">${items.map((i) => `<div class="tile"><p class="tile-k">${i[0]}</p><p class="tile-v">${fmt(i[1], i[2])}${i[3] ? `<small>${i[3]}</small>` : ""}</p></div>`).join("")}</div>`;
  }

  function cargas(c) {
    if (!c) return "";
    const items = [["carga_autonomica", "Carga autonómica"], ["carga_emocional", "Carga emocional"], ["carga_fisica", "Carga física"], ["estres", "Estrés"]]
      .map(([k, l]) => ({ l, v: num((c[k] || {}).value), lv: (c[k] || {}).level })).filter((i) => i.v != null);
    if (!items.length) return "";
    return `<section class="block"><div class="block-head"><h3>Cargas autonómicas</h3><p class="muted">Escala 0–100. Un valor mayor indica mayor carga.</p></div>
      <ul class="bars">${items.map((i) => `<li><div class="bar-top"><span>${i.l}</span><strong>${Math.round(i.v)}<small> · ${esc(LEVEL_LBL[i.lv] || i.lv || "")}</small></strong></div>
      <div class="bar" role="img" aria-label="${i.l}: ${Math.round(i.v)} de 100"><i style="width:${Math.max(2, Math.min(100, i.v))}%"></i></div></li>`).join("")}</ul></section>`;
  }

  function balance(data) {
    const lf = num(data.lf_power), hf = num(data.hf_power);
    if (lf == null || hf == null || lf + hf <= 0) return "";
    const p = Math.round(hf / (lf + hf) * 100), s = 100 - p;
    return `<section class="block"><div class="block-head"><h3>Balance espectral HF / LF</h3>
      <p class="muted">Reparto de la potencia entre las bandas HF (vagal) y LF. LF no equivale estrictamente a actividad simpática.</p></div>
      <div class="split" role="img" aria-label="HF ${p} por ciento, LF ${s} por ciento"><i class="sp-hf" style="width:${p}%"><b>${p > 12 ? "HF " + p + "%" : ""}</b></i><i class="sp-lf" style="width:${s}%"><b>${s > 12 ? "LF " + s + "%" : ""}</b></i></div>
      <div class="split-key"><span><i class="k-hf"></i>HF · parasimpático ${p}%</span><span><i class="k-lf"></i>LF ${s}%</span></div>
      ${data.freq_warning ? `<p class="note">${ic("info")}${esc(data.freq_warning)}</p>` : ""}</section>`;
  }

  function rrCharts(rr) {
    if (!rr || rr.length < 12) return "";
    return `<section class="block"><div class="block-head"><h3>Intervalos RR capturados</h3>
      <p class="muted">Señal original, sin depurar. Los indicadores se calculan después de eliminar artefactos.</p></div>
      <div class="chart-grid"><figure><figcaption>Tacograma · RR (ms) por latido</figcaption><div class="chart-box"><canvas id="cvTacho" aria-label="Tacograma de intervalos RR" role="img"></canvas></div></figure>
      <figure><figcaption>Poincaré · RR(n) frente a RR(n+1)</figcaption><div class="chart-box chart-sq"><canvas id="cvPoin" aria-label="Diagrama de Poincaré" role="img"></canvas></div></figure></div></section>`;
  }
  function drawRR(rr) {
    killChart("tacho"); killChart("poin");
    if (!window.Chart || !rr || rr.length < 12 || !$("cvTacho")) return;
    chartDefaults();
    const step = Math.ceil(rr.length / 1500), d = rr.filter((_, i) => i % step === 0);
    charts.tacho = new Chart($("cvTacho"), { type: "line", data: { labels: d.map((_, i) => i + 1), datasets: [{ data: d, borderColor: C.hanna, borderWidth: 1.6, pointRadius: 0, tension: 0.25, fill: true, backgroundColor: "rgba(10,92,255,.08)" }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 6 }, grid: { display: false } }, y: { grid: { color: C.grid }, title: { display: true, text: "ms" } } } } });
    const pts = []; for (let i = 0; i < d.length - 1; i++) pts.push({ x: d[i], y: d[i + 1] });
    charts.poin = new Chart($("cvPoin"), { type: "scatter", data: { datasets: [{ data: pts, backgroundColor: "rgba(10,92,255,.45)", pointRadius: 2.5 }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: C.grid }, title: { display: true, text: "RR(n) ms" } }, y: { grid: { color: C.grid }, title: { display: true, text: "RR(n+1) ms" } } } } });
  }

  function indicatorTable(data, bios) {
    const rows = bios.filter(hasVal).map((b) => ({ n: b.name, v: fmt(b.value, b.unit === "bpm" ? 0 : 2), u: b.unit, s: b.state }));
    const extras = [["pNN50", data.pnn50, 1, "%"], ["FC máxima", data.hr_max, 0, "bpm"], ["FC mínima", data.hr_min, 0, "bpm"], ["RMSSD sin corregir", data.rmssd, 1, "ms"], ["Frecuencia respiratoria estimada", data.resp_rate_rpm, 1, "rpm"]]
      .filter((e) => num(e[1]) != null).map((e) => ({ n: e[0], v: fmt(e[1], e[2]), u: e[3], s: null }));
    const all = rows.concat(extras);
    if (!all.length) return "";
    const miss = bios.filter((b) => !hasVal(b)).map((b) => b.name);
    return `<section class="block"><div class="block-head"><h3>Todos los indicadores</h3></div>
      <div class="tbl-wrap"><table class="tbl tbl-ind"><thead><tr><th scope="col">Indicador</th><th scope="col">Valor</th><th scope="col">Lectura</th></tr></thead><tbody>
      ${all.map((r) => `<tr><th scope="row" data-label="Indicador">${esc(r.n)}</th><td data-label="Valor"><span class="cell"><strong>${r.v}</strong> <span class="u">${esc(r.u)}</span></span></td>
      <td data-label="Lectura">${r.s ? `<span class="chip chip-${esc(r.s)}">${esc(STATE_LBL[r.s] || r.s)}</span>` : '<span class="muted">—</span>'}</td></tr>`).join("")}
      </tbody></table></div>
      ${miss.length ? `<p class="note">${ic("info")}No se pudieron calcular en esta medición: ${esc(miss.join(", "))}.</p>` : ""}</section>`;
  }

  /* ── Interpretación ── */
  function interpretation(data, v) {
    const dash = data.hba_dashboard || {}, sem = dash.semaphore || {};
    if (v && v.severity === "invalid") return `<div class="empty-state">${ic("triangle-alert", "ic-xl")}<h3>No hay interpretación disponible</h3>
      <p>El resultado no es válido, por eso no se interpreta. Repetí la medición siguiendo las indicaciones de preparación.</p>
      <button class="btn btn-primary" type="button" data-act="retry">${ic("rotate-ccw")}Repetir medición</button></div>`;
    const st = dash.stress_type, nota = (dash.recomendaciones || {}).nota_stress;
    const stress = st && st !== "indeterminado" ? `<section class="block"><div class="block-head"><h3>Tipo de carga predominante</h3></div>
      <p class="lead">${esc(dash.stress_label || "")}</p>${nota ? `<p class="note">${ic("info")}${esc(nota)}</p>` : ""}</section>` : "";
    const bios = (dash.biomarkers || []).filter(hasVal).map((b) => {
      const inf = b.info || {}, lect = inf[b.state];
      return `<details class="acc"><summary><span class="acc-t">${esc(b.name)}</span><span class="acc-v">${fmt(b.value, b.unit === "bpm" ? 0 : 2)} ${esc(b.unit)}</span><span class="chip chip-${esc(b.state)}">${esc(STATE_LBL[b.state] || b.state)}</span>${ic("chevron-right", "acc-i")}</summary>
        <div class="acc-b">${inf.que_mide ? `<p><strong>Qué mide.</strong> ${esc(inf.que_mide)}</p>` : ""}
        ${lect && b.state !== "informativo" ? `<p><strong>En esta medición.</strong> ${esc(lect)}</p>` : ""}
        ${b.detail ? `<p class="muted">${esc(b.detail)}</p>` : ""}
        ${inf.alto || inf.medio || inf.bajo ? `<ul class="bullets"><li><b>Alto:</b> ${esc(inf.alto || "")}</li><li><b>Normal:</b> ${esc(inf.medio || "")}</li><li><b>Bajo:</b> ${esc(inf.bajo || "")}</li></ul>` : ""}
        ${inf.protocolo ? `<p class="muted">${esc(inf.protocolo)}</p>` : ""}</div></details>`;
    }).join("");
    return `<section class="block"><div class="block-head"><h3>Estado autonómico: ${esc(sem.label || "")}</h3></div><p class="lead">${esc(sem.description || "")}</p></section>${stress}
      <section class="block"><div class="block-head"><h3>Qué significa cada indicador</h3><p class="muted">Tocá un indicador para ver su explicación y sus rangos.</p></div><div class="acc-list">${bios}</div></section>
      ${disclaimer()}`;
  }

  /* ── Recomendaciones ── */
  const REC_SECTIONS = [["descanso", "moon", "Descanso"], ["nutricion", "salad", "Nutrición"], ["meditacion", "flower-2", "Meditación y respiración"], ["actividad", "footprints", "Actividad física"], ["stretching", "person-standing", "Stretching miofascial"], ["musica", "music", "Musicoterapia"]];
  const ul = (a) => (a && a.length ? `<ul class="bullets">${a.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "");
  function recBody(k, r) {
    let b = "";
    if (k === "descanso") { if (r.horas) b += `<p><strong>Objetivo: ${esc(r.horas)}</strong></p>`; b += ul(r.tips); }
    else if (k === "nutricion") { if (r.descripcion) b += `<p>${esc(r.descripcion)}</p>`; if (r.suplementos && r.suplementos.length) b += `<p class="h-sm">Suplementos</p>${ul(r.suplementos)}`; if (r.alimentos && r.alimentos.length) b += `<p class="h-sm">Alimentos</p>${ul(r.alimentos)}`; }
    else if (k === "meditacion") { if (r.descripcion) b += `<p>${esc(r.descripcion)}</p>`; b += ul(r.tecnicas); if (r.duracion_min) b += `<span class="chip chip-medio">${r.duracion_min} min/día</span>`; if (r.nota) b += `<p class="note">${esc(r.nota)}</p>`; }
    else if (k === "actividad") { if (r.tipo) b += `<p><strong>${esc(r.tipo)}</strong></p>`; b += ul(r.ejemplos); if (r.frecuencia) b += `<span class="chip chip-medio">${esc(r.frecuencia)}</span>`; }
    else if (k === "stretching") { if (r.descripcion) b += `<p>${esc(r.descripcion)}</p>`; b += ul(r.tecnicas); if (r.duracion_min) b += `<span class="chip chip-medio">${r.duracion_min} min</span>`; }
    else if (k === "musica") { if (r.recomendacion) b += `<p>${esc(r.recomendacion)}</p>`; b += ul(r.frecuencias); if (r.nota) b += `<p class="note">${esc(r.nota)}</p>`; if (r.nota_extra) b += `<p class="note">${esc(r.nota_extra)}</p>`; }
    return b;
  }
  function recommendations(data, v) {
    const dash = data.hba_dashboard || {};
    if (v && v.severity === "invalid") return interpretation(data, v);
    const plan = (dash.plan || []).length ? `<section class="block"><div class="block-head"><h3>Plan de intervención sugerido</h3><p class="muted">Porcentaje sugerido por el protocolo HBA para cada área.</p></div>
      <ul class="bars">${dash.plan.map((p) => `<li><div class="bar-top"><span>${esc(p.item)}</span><strong>${esc(p.pct)}%</strong></div><div class="bar" role="img" aria-label="${esc(p.item)}: ${esc(p.pct)} por ciento"><i style="width:${Math.max(1, Math.min(100, +p.pct || 0))}%"></i></div></li>`).join("")}</ul></section>` : "";
    const recs = dash.recomendaciones || {};
    const secs = REC_SECTIONS.filter(([k]) => recs[k]).map(([k, i, l]) => `<details class="acc"><summary>${ic(i, "acc-ic")}<span class="acc-t">${l}</span>${ic("chevron-right", "acc-i")}</summary><div class="acc-b">${recBody(k, recs[k])}</div></details>`).join("");
    return `${plan}${secs ? `<section class="block"><div class="block-head"><h3>Recomendaciones integrales</h3></div><div class="acc-list">${secs}</div></section>` : ""}
      <p class="note">${ic("info")}Las sugerencias de suplementos, actividad y descanso son orientativas. Consultá con un profesional de la salud antes de aplicarlas.</p>${disclaimer()}`;
  }

  function disclaimer() {
    return `<p class="disclaimer">${ic("shield-check")}<span>La medición HRV es una herramienta de monitoreo. No es un diagnóstico médico ni reemplaza la evaluación de un profesional de la salud.</span></p>`;
  }

  /* ── Render principal ── */
  function render(data, rr) {
    const v = window.HBAValidator.validate(data); G.validation = v;
    const dash = data.hba_dashboard;
    $("resEmpty").hidden = true; $("resContent").hidden = false;
    $("valBanner").innerHTML = validationBanner(v);
    $("resHero").innerHTML = hero(data, v);
    const isRR = ["polar_h10", "rr_upload"].includes(data.sensor_type);
    $("rtab-results").innerHTML = tiles(data) + (dash ? cargas(dash.cargas) : "") + balance(data) + (isRR ? rrCharts(rr) : "") + (dash ? indicatorTable(data, dash.biomarkers || []) : "");
    $("rtab-interp").innerHTML = dash ? interpretation(data, v) : "";
    $("rtab-recs").innerHTML = dash ? recommendations(data, v) : "";
    $("resMeta").textContent = `${window.HBA.fmtDate(G.lastAt || Date.now())}${G.lastMetrics && G.lastMetrics.patient_id ? " · Paciente " + G.lastMetrics.patient_id : ""}`;
    setRTab("results");
    drawRR(isRR ? rr : null);
  }

  function setRTab(name) {
    $$("[data-rtab]").forEach((b) => { const on = b.dataset.rtab === name; b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; });
    $$(".rpanel").forEach((p) => { p.hidden = p.id !== "rtab-" + name; });
    if (name === "results") Object.values(charts).forEach((c) => c.resize());
  }

  function clear() {
    killChart("tacho"); killChart("poin");
    $("resEmpty").hidden = false; $("resContent").hidden = true;
    ["valBanner", "resHero", "rtab-results", "rtab-interp", "rtab-recs"].forEach((id) => { $(id).innerHTML = ""; });
  }

  window.HBA.results = { render, clear, setRTab, validationBanner };
})();
