"use strict";
/* HANNA·HRV — report.js
   Generación del informe PDF. El acceso se valida EN EL SERVIDOR (cabecera X-Report-Key vs REPORT_PASSWORD);
   acá solo se pide la contraseña y se muestra el resultado. La contraseña se guarda únicamente en memoria
   (variable `pwd`): al recargar la página se vuelve a pedir. No se escribe en localStorage ni en la URL. */
(function () {
  const H = window.HBA;
  const { G, $, toast } = H;
  let pwd = null, blobUrl = null, blobName = "informe-hrv.pdf", build = null, busy = false;

  /* ── datos que se envían ── */
  async function fetchHistory(pid) {
    if (!pid) return [];
    const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 8000);
    try {
      const res = await fetch(`/api/history?patient_id=${encodeURIComponent(pid)}`, { signal: ctl.signal });
      const j = await res.json();
      return j && j.backend === "supabase" && Array.isArray(j.data) ? j.data.slice(0, 100) : [];
    } catch (_) { return []; } finally { clearTimeout(t); }
  }
  const tz = () => -new Date().getTimezoneOffset();

  async function payloadFromResult() {
    const m = G.lastMetrics;
    return {
      patient_id: m.patient_id, age: m.age, sex: m.sex, comorbidities: m.comorbidities, notes: m.notes, metrics: m,
      measured_at: new Date(G.lastAt || Date.now()).toISOString(), tz_offset_min: tz(),
      rr_ms: G.lastRR || null, history: await fetchHistory(m.patient_id),
    };
  }
  async function payloadFromRow(row) {
    const known = H.history.rows();
    return {
      patient_id: row.patient_id, age: row.age, sex: row.sex, comorbidities: row.comorbidities, notes: row.notes, metrics: row,
      measured_at: row.timestamp_utc, tz_offset_min: tz(), history: known.length ? known : await fetchHistory(row.patient_id),
    };
  }

  /* ── diálogo de contraseña ── */
  const dlg = () => $("rptDlg");
  function openPwd(msg) {
    $("rptErr").textContent = msg || ""; $("rptPwd").value = ""; $("rptPwd").setAttribute("aria-invalid", msg ? "true" : "false");
    setBusy(false);
    if (!dlg().open) (dlg().showModal ? dlg().showModal() : dlg().setAttribute("open", ""));
    setTimeout(() => $("rptPwd").focus(), 30);
  }
  function setBusy(on) {
    busy = on;
    $("rptGo").disabled = on; $("rptGo").textContent = on ? "Generando informe…" : "Generar informe";
    const b = $("btnReport"); if (b) b.disabled = on;
    $("rvRegen").disabled = on;
  }

  /* ── generación ── */
  async function generate() {
    if (busy || !build) return false;
    setBusy(true);
    let res;
    try {
      const payload = await build();
      res = await fetch("/api/report", {
        method: "POST", cache: "no-store",
        headers: { "Content-Type": "application/json", "X-Report-Key": encodeURIComponent(pwd || "") },
        body: JSON.stringify(payload),
      });
    } catch (_) {
      setBusy(false); toast("No se pudo conectar con el servidor para generar el informe.", "err"); return false;
    }
    if (res.status === 200) {
      const blob = await res.blob();
      const cd = res.headers.get("Content-Disposition") || "", mt = /filename="([^"]+)"/.exec(cd);
      blobName = mt ? mt[1] : "informe-hrv.pdf";
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      blobUrl = URL.createObjectURL(blob);
      setBusy(false); if (dlg().open) dlg().close();
      showViewer(blob.size);
      return true;
    }
    const j = await res.json().catch(() => ({}));
    setBusy(false);
    if (res.status === 401) { pwd = null; openPwd(j.error || "Contraseña incorrecta."); return false; }
    if (res.status === 429) { pwd = null; openPwd(j.error || "Demasiados intentos. Esperá unos minutos."); return false; }
    if (dlg().open) dlg().close();
    toast(j.error || `No se pudo generar el informe (error ${res.status}).`, "err");
    return false;
  }

  async function start(builder) {
    if (busy) return;
    build = builder;
    try {
      const st = await (await fetch("/api/report/status", { cache: "no-store" })).json();
      if (!st.enabled) { toast("El informe PDF no está habilitado: falta configurar REPORT_PASSWORD en el servidor.", "err"); return; }
    } catch (_) { toast("No se pudo consultar el servidor.", "err"); return; }
    if (pwd) await generate(); else openPwd("");
  }

  /* ── visor ── */
  function showViewer(size) {
    const v = $("rptView");
    $("rvInfo").textContent = `${blobName} · ${Math.max(1, Math.round(size / 1024))} KB`;
    const canPreview = !!navigator.pdfViewerEnabled && window.innerWidth >= 900;
    $("rvFrameWrap").hidden = !canPreview; $("rvNoPrev").hidden = canPreview;
    $("rvFrame").src = canPreview ? blobUrl + "#toolbar=1&navpanes=0" : "about:blank";
    if (!v.open) (v.showModal ? v.showModal() : v.setAttribute("open", ""));
  }
  function closeViewer() {
    const v = $("rptView"); if (v.open) v.close();
    $("rvFrame").src = "about:blank";
    if (blobUrl) { URL.revokeObjectURL(blobUrl); blobUrl = null; }
  }
  function download() {
    if (!blobUrl) return;
    const a = document.createElement("a"); a.href = blobUrl; a.download = blobName; document.body.appendChild(a); a.click(); a.remove();
    toast("Descargando el informe…", "ok");
  }
  function openTab() { if (blobUrl) window.open(blobUrl, "_blank", "noopener"); }
  function print() {
    if (!blobUrl) return;
    const f = document.createElement("iframe");
    f.setAttribute("aria-hidden", "true"); f.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
    f.onload = () => {
      try { f.contentWindow.focus(); f.contentWindow.print(); }
      catch (_) { window.open(blobUrl, "_blank", "noopener"); toast("Abrí el PDF y usá Imprimir desde el visor del navegador.", "info"); }
    };
    f.src = blobUrl; document.body.appendChild(f);
    setTimeout(() => f.remove(), 120000);
  }

  /* ── eventos ── */
  function init() {
    $("btnReport").addEventListener("click", () => { if (!G.lastMetrics) { toast("Primero completá una medición.", "err"); return; } start(payloadFromResult); });
    $("histList").addEventListener("click", (e) => {
      const b = e.target.closest("[data-report]"); if (!b) return;
      const row = H.history.get(b.dataset.report); if (row) start(() => payloadFromRow(row));
    });
    $("rptForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const v = $("rptPwd").value;
      if (!v) { $("rptErr").textContent = "Ingresá la contraseña."; $("rptPwd").focus(); return; }
      pwd = v; generate();
    });
    $("rptCancel").addEventListener("click", () => { pwd = null; if (dlg().open) dlg().close(); });
    $("rvClose").addEventListener("click", closeViewer);
    $("rptView").addEventListener("close", () => { $("rvFrame").src = "about:blank"; });
    $("rvDownload").addEventListener("click", download);
    $("rvOpen").addEventListener("click", openTab);
    $("rvPrint").addEventListener("click", print);
    $("rvRegen").addEventListener("click", async () => { const ok = await generate(); if (ok) toast("Informe generado de nuevo.", "ok"); });
    window.addEventListener("pagehide", () => { pwd = null; });
  }
  init();
})();
