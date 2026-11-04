"use strict";
/* HANNA·HRV — main.js
   Navegación, flujo guiado, sesión de medición y comunicación con la API.
   Contratos de API sin cambios: /api/compute, /api/save, /api/history. */
(function () {
  const H = window.HBA;
  const { G, $, $$, esc, num, fmt, ic, mmss, fmtDate, store, toast, confirmDialog, CAPS, SENSORS, STEPS, WIN, FPS } = H;
  const S = H.sensors;
  let signalChart = null, wakeLock = null;

  /* ═════ Estado de la barra superior ═════ */
  function setStatus(text, cls) {
    $("statusText").textContent = text;
    $("statusDot").className = "pill-dot" + (cls ? " " + cls : "");
  }

  /* ═════ Vistas y pasos ═════ */
  function showView(name) {
    if (G.running || G.phase === "computing") { toast("Detené la medición antes de salir de esta pantalla.", "err"); return false; }
    $$(".view").forEach((v) => v.classList.toggle("is-active", v.id === "view-" + name));
    $$(".nav-btn").forEach((b) => { const on = b.dataset.view === name; b.classList.toggle("is-active", on); if (on) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
    window.scrollTo(0, 0);
    if (name === "history") { H.history.onShow(); const pid = readProfile().patient_id; if (pid && !$("histId").value) $("histId").value = pid; }
    if (name === "home") refreshHome();
    return true;
  }

  function renderStepper() {
    $("stepper").innerHTML = STEPS.map((s) => {
      const st = s.n === G.step ? "is-current" : s.n < G.step ? "is-done" : "";
      return `<li class="${st}"><button type="button" class="step-btn" data-step="${s.n}" ${s.n === G.step ? 'aria-current="step"' : ""}>
        <span class="step-n">${s.n < G.step ? ic("check") : s.n}</span><span class="step-l">${s.label}</span></button></li>`;
    }).join("");
    $("stepCompact").textContent = `Paso ${G.step} de ${STEPS.length} · ${STEPS[G.step - 1].label}`;
    $("stepProgress").style.width = `${((G.step - 1) / (STEPS.length - 1)) * 100}%`;
  }

  function goStep(n, focus) {
    if (G.running) return;
    if (n === 6) { gotoHistory(); return; }
    if (n >= 2 && !profileOk(false)) n = 1;
    if (n === 5 && !G.lastMetrics) n = G.step >= 4 ? 4 : G.step;
    G.step = n;
    $$(".step-panel").forEach((p) => { p.hidden = p.id !== "step-" + n; });
    renderStepper();
    if (n === 3) renderPrep();
    if (n === 4) enterMeasure();
    if (n === 5) { H.results.setRTab("results"); }
    if (focus !== false) { const h = $("step-" + n).querySelector("h2"); if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); } }
    const top = $("view-measure").getBoundingClientRect().top + window.scrollY - (window.innerWidth < 1024 ? 80 : 16);
    window.scrollTo({ top: Math.max(0, top), behavior: "auto" });
  }

  /* ═════ Paso 1: paciente ═════ */
  function readProfile() {
    return { patient_id: $("patientId").value.trim(), age: $("age").value.trim(), sex: $("sex").value, comorbidities: $("comorbidities").value.trim(), notes: $("notes").value.trim() };
  }
  function profileOk(show) {
    const p = readProfile(); let ok = true;
    const setErr = (id, inputId, msg) => { $(id).textContent = msg || ""; $(inputId).setAttribute("aria-invalid", msg ? "true" : "false"); };
    if (!p.patient_id) { ok = false; if (show) setErr("errPatient", "patientId", "Ingresá el ID, DNI o código del paciente."); } else setErr("errPatient", "patientId", "");
    const a = p.age === "" ? null : Number(p.age);
    if (a != null && (!isFinite(a) || a < 0 || a > 120)) { ok = false; if (show) setErr("errAge", "age", "La edad debe estar entre 0 y 120."); } else setErr("errAge", "age", "");
    return ok;
  }
  function saveProfile() { store.set("hba.profile", readProfile()); refreshHome(); }

  async function submitProfile(e) {
    e.preventDefault();
    if (!profileOk(true)) { const bad = $("patientId").getAttribute("aria-invalid") === "true" ? $("patientId") : $("age"); bad.focus(); return; }
    if (!readProfile().age) {
      const ok = await confirmDialog("Continuar sin edad", "La edad se usa para comparar el RMSSD con valores de referencia. Sin ella se usa un rango general.", "Continuar sin edad", "Agregar edad");
      if (!ok) { $("age").focus(); return; }
    }
    saveProfile(); goStep(2);
  }

  /* ═════ Paso 2: método ═════ */
  function renderMethods() {
    $("methodGrid").innerHTML = Object.entries(SENSORS).map(([k, m]) => `
      <button type="button" class="method" role="radio" aria-checked="${k === G.sensor}" data-sensor="${k}">
        <span class="m-ic">${ic(m.icon)}</span>
        <span class="m-head"><strong>${m.label}</strong><span class="tag tag-${m.tagKind}">${m.tag}</span></span>
        <span class="m-line"><b>Qué es</b>${esc(m.what)}</span>
        <span class="m-line"><b>Necesita</b>${esc(m.needs)}</span>
        <span class="m-line"><b>Cómo se usa</b>${esc(m.how)}</span>
        ${CAPS[m.cap] ? "" : `<span class="m-warn">${ic("triangle-alert")}No disponible en este dispositivo o navegador</span>`}
      </button>`).join("");
  }
  function selectSensor(k) {
    G.sensor = k; const m = SENSORS[k];
    if (!m.durs.includes(G.durationMin)) G.durationMin = 3;
    G.totalSec = G.durationMin * 60;
    $$(".method").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.sensor === k)));
  }

  /* ═════ Paso 3: preparación ═════ */
  function capReason(m) {
    if (CAPS[m.cap]) return "";
    if (window.isSecureContext === false) return "Este método requiere una conexión segura (https).";
    return { camera: "Este dispositivo o navegador no permite usar la cámara.", bluetooth: "Este navegador no admite Web Bluetooth. Usá Chrome o Edge en PC o Android.", motion: "Este dispositivo no expone el acelerómetro al navegador." }[m.cap] || "No disponible.";
  }
  function block(icon, title, items) {
    if (!items || !items.length) return "";
    return `<section class="prep-block"><h3>${ic(icon)}${title}</h3><ul class="bullets">${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul></section>`;
  }
  function renderPrep() {
    const m = SENSORS[G.sensor];
    $("prepTitle").textContent = `Preparación · ${m.label}`;
    const time = G.sensor === "rr_upload" ? "El análisis tarda menos de un minuto."
      : `${G.durationMin} min de medición${G.sensor === "polar_h10" ? " más unos segundos de conexión." : " más 5 segundos de cuenta regresiva."}`;
    const reason = capReason(m);
    $("prepBody").innerHTML = (reason ? `<div class="alert is-warn" role="alert">${ic("triangle-alert")}<div><strong>Método no disponible aquí.</strong><p>${esc(reason)} Elegí otro método para continuar.</p></div></div>` : "") +
      `<div class="prep-grid">${block("user", "Posición", m.position)}${block("heart-pulse", "Colocación del sensor", m.placement)}${block("sun", "Condiciones recomendadas", m.conditions)}
      ${block("signal", G.sensor === "rr_upload" ? "Formato del archivo" : "Conexión y requisitos", m.connection)}${block("timer", "Tiempo estimado", [time])}${block("triangle-alert", "Importante", m.warnings)}</div>`;
    $("durLabel").textContent = G.sensor === "rr_upload" ? "Duración de la grabación importada" : "Duración de la medición";
    $("durRow").innerHTML = m.durs.map((d) => `<button type="button" class="seg-btn" data-dur="${d}" aria-pressed="${d === G.durationMin}">${d} min</button>`).join("");
    $("rrWrap").hidden = G.sensor !== "rr_upload";
    $("rrFileLabel").textContent = G.rrFileName ? `${G.rrFileName} · ${G.rrImport.length} intervalos RR` : "Tocá para elegir un archivo .csv o .json";
    $("btnToMeasure").disabled = !CAPS[m.cap] || (G.sensor === "rr_upload" && !(G.rrImport && G.rrImport.length));
    $("prepHint").textContent = G.sensor === "rr_upload" && !(G.rrImport && G.rrImport.length) ? "Cargá un archivo para continuar." : "";
  }

  async function onRRFile() {
    const f = $("rrFile").files[0]; if (!f) return;
    $("rrError").textContent = "";
    try {
      G.rrImport = await S.parseRRFile(f); G.rrFileName = f.name;
      toast(`Archivo cargado: ${G.rrImport.length} intervalos RR.`, "ok");
    } catch (err) {
      G.rrImport = []; G.rrFileName = ""; $("rrError").textContent = err.message; $("rrFile").value = "";
    }
    renderPrep();
  }

  /* ═════ Paso 4: medición ═════ */
  function buildChart() {
    if (signalChart || !window.Chart) return;
    Chart.defaults.font.family = "'Figtree', system-ui, sans-serif";
    signalChart = new Chart($("signalChart").getContext("2d"), { type: "line",
      data: { labels: Array(WIN).fill(""), datasets: [{ data: Array(WIN).fill(null), borderColor: "#0A5CFF", borderWidth: 1.8, pointRadius: 0, fill: true, backgroundColor: "rgba(10,92,255,.08)", tension: 0.3 }] },
      options: { animation: false, responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false, grace: "20%" } } } });
  }
  function drawChart() {
    if (!signalChart) return;
    const b = G.sigBuf;
    signalChart.data.datasets[0].data = b.length >= WIN ? b.slice(-WIN) : [...Array(WIN - b.length).fill(null), ...b];
    signalChart.update("none");
  }
  function chartLoop(now) {
    if (!G.running) { G.rafH = null; return; }
    G.rafH = requestAnimationFrame(chartLoop);
    if (now - G.chartLast < 1000 / FPS) return;
    G.chartLast = now; drawChart();
  }

  function enterMeasure() {
    const m = SENSORS[G.sensor];
    $("mMethod").textContent = m.label;
    $("cameraBox").hidden = !m.camera; $("torchWrap").hidden = !m.torch;
    const imp = G.sensor === "rr_upload";
    $("timerCard").hidden = imp; $("mImport").hidden = !imp;
    $("mSub").textContent = imp ? "Revisá que el archivo sea el correcto y tocá «Analizar archivo» para calcular los indicadores." : "Seguí el temporizador y no muevas el sensor ni el dispositivo hasta que termine.";
    $("mImportInfo").textContent = imp ? `${G.rrFileName} · ${G.rrImport.length} intervalos RR · ${G.durationMin} min` : "";
    $("btnStartTxt").textContent = imp ? "Analizar archivo" : "Iniciar medición";
    G.phase === "idle" && resetMeasureUI();
    buildChart();
    if (imp && signalChart) { G.sigBuf = []; G.rrImport.forEach((r) => S.pushSig(r)); drawChart(); }
    setTimeout(() => signalChart && signalChart.resize(), 30);
  }

  function resetMeasureUI() {
    $("mTimer").textContent = "00:00"; $("mRemain").textContent = `de ${mmss(G.durationMin * 60)}`;
    $("mProgress").style.width = "0%"; $("mProgressWrap").setAttribute("aria-valuenow", "0");
    setSignalUI({ lvl: 0, txt: "Sin iniciar", hint: "" });
    $("mConn").textContent = connLabel("idle");
    $("mMsg").textContent = G.sensor === "rr_upload" ? "Todo listo. Tocá «Analizar archivo» para calcular los indicadores." : "Todo listo. Tocá «Iniciar medición» cuando estés en posición.";
    $("mError").hidden = true; setPhase("idle");
  }
  function connLabel(state) {
    const s = G.sensor;
    if (state === "idle") return s === "polar_h10" ? "Sin conectar" : s === "rr_upload" ? "Archivo cargado" : CAPS[SENSORS[s].cap] ? "Sensor listo" : "No disponible";
    if (state === "connecting") return s === "polar_h10" ? "Conectando con el Polar…" : "Solicitando permisos…";
    if (state === "live") return s === "polar_h10" ? "Polar conectado" : s === "vibration_scg" ? "Acelerómetro activo" : "Cámara activa";
    return state;
  }
  function setSignalUI(sig) {
    const el = $("mSignal"); el.dataset.lvl = sig.lvl;
    $("mSignalTxt").textContent = sig.txt; $("mHint").textContent = sig.hint || "";
  }
  function setPhase(p) {
    G.phase = p;
    const busy = p === "countdown" || p === "connecting" || p === "computing";
    $("btnStart").hidden = G.running || busy; $("btnStop").hidden = !G.running;
    $("btnStart").disabled = !CAPS[SENSORS[G.sensor].cap];
    $("btnBackPrep").disabled = G.running || busy; $("btnSkipRes").hidden = !G.lastMetrics || G.running || busy;
    $("mProgressWrap").classList.toggle("is-busy", p === "computing");
    $("view-measure").dataset.phase = p;
  }
  function showMError(title, msg, actions) {
    const box = $("mError");
    box.innerHTML = `<div class="alert is-bad" role="alert">${ic("circle-alert")}<div><strong>${esc(title)}</strong><p>${esc(msg)}</p>
      <div class="alert-actions">${(actions || []).map((a) => `<button type="button" class="btn ${a.primary ? "btn-primary" : "btn-soft"}" data-act="${a.act}">${a.label}</button>`).join("")}</div></div></div>`;
    box.hidden = false; box.scrollIntoView({ block: "nearest" });
  }
  const RETRY = [{ label: "Reintentar", act: "retry-measure", primary: true }, { label: "Elegir otro método", act: "other-method" }];

  function countdown(title, text, hint, secs) {
    return new Promise((resolve, reject) => {
      const o = $("countdown"); $("cdTitle").textContent = title; $("cdText").textContent = text; $("cdHint").textContent = hint;
      o.hidden = false; let n = secs; $("cdN").textContent = n; $("cdCancel").focus();
      const close = () => { clearInterval(iv); o.hidden = true; $("cdCancel").onclick = null; };
      const iv = setInterval(() => { n--; if (n <= 0) { close(); resolve(); } else $("cdN").textContent = n; }, 1000);
      $("cdCancel").onclick = () => { close(); const e = new Error("cancel"); e.cancelled = true; reject(e); };
    });
  }

  function startTimer() {
    G.elapsed = 0; G.timerH = setInterval(() => {
      G.elapsed++;
      $("mTimer").textContent = mmss(G.elapsed);
      const pct = Math.min(100, G.elapsed / G.totalSec * 100);
      $("mProgress").style.width = pct + "%"; $("mProgressWrap").setAttribute("aria-valuenow", String(Math.round(pct)));
      $("mRemain").textContent = `faltan ${mmss(Math.max(0, G.totalSec - G.elapsed))}`;
      setSignalUI(S.liveSignal());
      if (G.elapsed >= G.totalSec) stopSession(true);
    }, 1000);
  }
  function stopTimer() { if (G.timerH) { clearInterval(G.timerH); G.timerH = null; } }
  async function lockScreen() { try { if (navigator.wakeLock) wakeLock = await navigator.wakeLock.request("screen"); } catch (_) {} }
  function unlockScreen() { try { if (wakeLock) wakeLock.release(); } catch (_) {} wakeLock = null; }

  function cleanup() {
    stopTimer(); unlockScreen();
    if (G.sensor === "camera_ppg" || G.sensor === "face_rppg") S.stopCamera();
    if (G.sensor === "polar_h10") S.stopPolar();
    if (G.sensor === "vibration_scg") S.stopVibration();
  }
  function beginLive() {
    G.phase = "measuring"; setPhase("measuring"); setStatus("Midiendo…", "live");
    $("mConn").textContent = connLabel("live"); $("mMsg").textContent = "Medición en curso. Mantené la posición y respirá con normalidad.";
    $("mProgress").style.width = "0%"; $("mRemain").textContent = `faltan ${mmss(G.totalSec)}`;
    G.rafH = requestAnimationFrame(chartLoop); startTimer(); lockScreen();
  }

  function resetBuffers() { G.ppgBuf = []; G.ppgTs = []; G.rrBuf = []; G.sigBuf = []; G.rrLastAt = 0; G.lastHr = null; }

  async function startSession() {
    if (G.running || ["countdown", "connecting", "computing"].includes(G.phase)) return;
    if (!profileOk(true)) { toast("Completá los datos del paciente antes de medir.", "err"); goStep(1); return; }
    const m = SENSORS[G.sensor];
    if (!CAPS[m.cap]) { showMError("Método no disponible", capReason(m), [{ label: "Elegir otro método", act: "other-method", primary: true }]); return; }
    resetBuffers(); $("mError").hidden = true;
    try {
      if (G.sensor === "rr_upload") {
        if (!(G.rrImport && G.rrImport.length)) { toast("Cargá un archivo RR primero.", "err"); goStep(3); return; }
        setPhase("countdown"); G.phase = "countdown";
        await countdown("Analizando", "Procesando los intervalos RR importados.", "", 3);
        G.rrBuf = G.rrImport.slice(); setPhase("computing"); setStatus("Analizando…", "live");
        await computeAndDisplay(); return;
      }
      // Los permisos de Bluetooth y movimiento DEBEN pedirse en el mismo toque del usuario,
      // antes de cualquier otra espera asíncrona.
      if (G.sensor === "polar_h10") {
        G.phase = "connecting"; setPhase("connecting"); setStatus("Esperando Bluetooth…", "warn"); $("mConn").textContent = connLabel("connecting");
        G.bleDevice = await S.requestPolar();
        await countdown("Polar conectando", "Ajustá la cinta y mantené el Polar H10 cerca.", "No bloquees la pantalla.", 3);
        G.running = true; setStatus("Conectando…", "warn");
        await S.connectPolar(G.bleDevice, onBleLost);
        setStatus("Polar conectado", "live"); beginLive(); return;
      }
      if (G.sensor === "vibration_scg") { G.phase = "connecting"; setPhase("connecting"); $("mConn").textContent = connLabel("connecting"); await S.requestMotionPermission(); }
      G.phase = "countdown"; setPhase("countdown");
      await countdown("Preparación", m.how, "No bloquees la pantalla.", 5);
      G.running = true; setStatus("Iniciando…", "warn"); $("mConn").textContent = connLabel("connecting");
      if (G.sensor === "camera_ppg" || G.sensor === "face_rppg") await S.startCamera();
      if (G.sensor === "vibration_scg") S.startVibration();
      beginLive();
    } catch (err) {
      const wasRunning = G.running; G.running = false; cleanup(); setPhase("idle");
      $("mConn").textContent = connLabel("idle"); $("mProgress").style.width = "0%";
      if (err.cancelled) { setStatus("Cancelado", "warn"); $("mMsg").textContent = "Cancelaste el inicio. Podés volver a intentarlo cuando quieras."; return; }
      if (err.name === "NotFoundError" && G.sensor === "polar_h10" && !wasRunning) { setStatus("Cancelado", "warn"); $("mMsg").textContent = "No se eligió ningún dispositivo. Tocá «Iniciar medición» para buscar el Polar de nuevo."; return; }
      setStatus("Error", "err");
      showMError("No se pudo iniciar la medición", friendlyError(err), RETRY);
    }
  }

  function friendlyError(err) {
    const n = err && err.name, msg = (err && err.message) || "Error desconocido.";
    if (n === "NotAllowedError" || n === "PermissionDeniedError") return G.sensor === "vibration_scg" ? msg : "El permiso fue denegado. Habilitá el acceso en los ajustes del navegador y reintentá.";
    if (n === "NotFoundError" || n === "OverconstrainedError") return G.sensor === "polar_h10" ? "No se encontró el Polar H10. Verificá que esté encendido, con la cinta puesta y cerca." : "No se encontró una cámara compatible en este dispositivo.";
    if (n === "NotReadableError") return "La cámara está en uso por otra aplicación. Cerrala y reintentá.";
    if (n === "NetworkError" || /GATT|Bluetooth/i.test(msg)) return `No se pudo conectar por Bluetooth: ${msg}. Verificá que el Polar esté encendido, el Bluetooth activado y que uses Chrome o Edge.`;
    return msg;
  }

  function onBleLost() {
    if (!G.running || G.phase !== "measuring") return;
    G.running = false; cleanup(); setPhase("idle"); setStatus("Conexión perdida", "err"); $("mConn").textContent = "Conexión perdida";
    const n = G.rrBuf.length, acts = n >= 12 ? [{ label: `Analizar lo registrado (${n} latidos)`, act: "analyze-partial", primary: true }] : [];
    showMError("Se perdió la conexión con el Polar", `Se recibieron ${n} latidos en ${mmss(G.elapsed)}. ${n >= 12 ? "Podés analizar lo registrado o repetir la medición completa." : "No alcanzan para calcular. Repetí la medición."}`, acts.concat([{ label: "Repetir medición", act: "retry-measure", primary: n < 12 }]));
  }

  async function stopSession(auto) {
    if (!G.running) return;
    G.running = false; cleanup(); setPhase("idle");
    $("mConn").textContent = connLabel("idle");
    if (auto || G.ppgBuf.length >= 30 || G.rrBuf.length >= 12) { await computeAndDisplay(); return; }
    setStatus("Detenido", "warn");
    showMError("Medición detenida", "Se detuvo antes de registrar datos suficientes para calcular.", RETRY.slice(0, 1));
  }

  /* ═════ Cálculo ═════ */
  function meta() {
    const p = readProfile();
    return { sensor_type: G.sensor, duration_minutes: G.durationMin, age: p.age === "" ? null : Number(p.age), sex: p.sex || null, patient_id: p.patient_id, comorbidities: p.comorbidities, notes: p.notes };
  }
  function computeErr(msg) {
    if (/Señal insuficiente|ppg insuficiente/i.test(msg)) return "La señal fue demasiado corta: se necesitan al menos 45 segundos de medición continua.";
    if (/picos/i.test(msg)) return "No se detectó un pulso confiable. Revisá la posición del sensor y repetí la medición.";
    return msg;
  }
  async function computeAndDisplay() {
    setPhase("computing"); setStatus("Calculando HRV…", "warn"); $("mMsg").textContent = "Calculando indicadores…";
    const isRR = ["polar_h10", "rr_upload"].includes(G.sensor), mt = meta();
    const payload = { ...mt };
    if (isRR) payload.rri_ms = G.rrBuf; else { payload.ppg = G.ppgBuf; payload.sampling_rate = S.samplingRate(); }
    try {
      const res = await fetch("/api/compute", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await res.json().catch(() => ({ error: `Respuesta inválida del servidor (HTTP ${res.status}).` }));
      if (data.error) { setPhase("idle"); setStatus("Error de cálculo", "err"); showMError("No se pudieron calcular los indicadores", computeErr(data.error), RETRY); return; }
      G.lastMetrics = { ...data, ...mt }; G.lastAt = Date.now(); G.lastSaved = false; G.lastRR = isRR ? G.rrBuf.slice() : null;
      store.set("hba.last", { metrics: G.lastMetrics, at: G.lastAt, saved: false });
      setPhase("idle"); setStatus("Completado", "live");
      H.results.render(G.lastMetrics, G.lastRR); updateSaveBtn(); refreshHome(); goStep(5);
    } catch (_) {
      setPhase("idle"); setStatus("Sin conexión", "err");
      showMError("No se pudo conectar con el servidor", "Los datos de la medición siguen en pantalla. Revisá tu conexión y reintentá el cálculo.", [{ label: "Reintentar cálculo", act: "analyze-partial", primary: true }, { label: "Repetir medición", act: "retry-measure" }]);
    }
  }

  /* ═════ Guardado ═════ */
  function updateSaveBtn() {
    const b = $("btnSave"); b.disabled = !G.lastMetrics || G.lastSaved;
    b.innerHTML = G.lastSaved ? `${ic("circle-check")}Sesión guardada` : `${ic("save")}Guardar sesión`;
  }
  async function saveSession() {
    if (!G.lastMetrics || G.lastSaved) return;
    const p = readProfile();
    if (!p.patient_id) { toast("Ingresá el ID del paciente antes de guardar.", "err"); goStep(1); return; }
    if (G.validation && G.validation.severity === "invalid") {
      if (!(await confirmDialog("Guardar un resultado no válido", "Esta medición está fuera del rango fisiológico. Guardarla puede distorsionar el historial.", "Guardar igual", "No guardar"))) return;
    }
    const b = $("btnSave"); b.disabled = true; setStatus("Guardando…", "warn");
    try {
      const res = await fetch("/api/save", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: p.patient_id, age: p.age || null, sex: p.sex || null, comorbidities: p.comorbidities, notes: p.notes, metrics: G.lastMetrics }) });
      const d = await res.json().catch(() => ({}));
      if (d.ok && d.backend === "supabase") {
        G.lastSaved = true; G.backend = "ok"; store.set("hba.last", { metrics: G.lastMetrics, at: G.lastAt, saved: true });
        setStatus("Guardado", "live"); toast(`Sesión guardada para el paciente ${p.patient_id}.`, "ok");
      } else if (d.backend === "none_configured") {
        G.backend = "none"; setStatus("Sin base de datos", "err");
        toast("No se pudo guardar: falta configurar SUPABASE_URL y SUPABASE_ANON_KEY en Vercel → Environment Variables.", "err");
      } else {
        G.backend = "error"; setStatus("Error al guardar", "err"); toast("No se pudo guardar: " + String(d.error || d.backend || "error desconocido").slice(0, 160), "err");
      }
    } catch (_) { setStatus("Sin conexión", "err"); toast("No se pudo guardar: sin conexión con el servidor.", "err"); }
    updateSaveBtn(); refreshHome();
  }

  /* ═════ Inicio ═════ */
  function stateChip(label, kind) { return `<span class="chip chip-${kind}">${label}</span>`; }
  function refreshHome() {
    const p = readProfile(), m = G.lastMetrics;
    $("patientChipTxt").textContent = p.patient_id ? `Paciente ${p.patient_id}` : "Sin paciente";
    $("homePatient").textContent = p.patient_id ? `Paciente ${p.patient_id}${p.age ? " · " + p.age + " años" : ""}` : "Todavía no cargaste un paciente";
    if (m) {
      const sem = (m.hba_dashboard || {}).semaphore || {}, bad = G.validation && G.validation.severity === "invalid";
      const t = [["FC media", m.hr_mean, 0, "bpm"], ["SDNN", m.sdnn, 1, "ms"], ["lnRMSSD", m.lnrmssd, 2, ""], ["Calidad", m.quality_score, 0, "%"]].filter((x) => num(x[1]) != null);
      $("homeLast").innerHTML = `<div class="last-top"><div><p class="muted">${esc(fmtDate(G.lastAt))}</p>
        <p class="last-v">${fmt(m.rmssd_corr ?? m.rmssd, 1)}<small>ms RMSSD corregido</small></p></div>
        ${bad ? '<span class="badge badge-bad">Resultado no válido</span>' : sem.label ? `<span class="badge badge-state">${esc(sem.label)}</span>` : ""}</div>
        ${t.length ? `<div class="tiles tiles-sm">${t.map((x) => `<div class="tile"><p class="tile-k">${x[0]}</p><p class="tile-v">${fmt(x[1], x[2])}${x[3] ? `<small>${x[3]}</small>` : ""}</p></div>`).join("")}</div>` : ""}
        <button class="btn btn-soft btn-block" type="button" data-act="goto-results">${ic("chart-no-axes-column")}Ver resultados completos</button>`;
    } else {
      $("homeLast").innerHTML = `<div class="empty-state is-flat">${ic("heart-pulse", "ic-xl")}<h3>Todavía no hay mediciones</h3><p>Cuando completes una medición, acá vas a ver el resumen y los indicadores principales.</p></div>`;
    }
    const bk = { ok: stateChip("Conectado", "ok"), none: stateChip("No configurado", "warn"), error: stateChip("Con errores", "warn"), unknown: stateChip("Sin verificar", "muted") }[G.backend];
    const cap = (k, l) => `<span class="chip chip-${CAPS[k] ? "ok" : "muted"}">${l}</span>`;
    $("homeData").innerHTML = `<ul class="kv">
      <li><span>Datos del paciente</span>${!p.patient_id ? stateChip("Falta el ID", "warn") : !p.age ? stateChip("Falta la edad", "warn") : stateChip("Completos", "ok")}</li>
      <li><span>Última medición</span>${m ? stateChip(esc(fmtDate(G.lastAt)), "ok") : stateChip("Ninguna", "muted")}</li>
      <li><span>Guardado en historial</span>${!m ? stateChip("—", "muted") : G.lastSaved ? stateChip("Guardada", "ok") : stateChip("Sin guardar", "warn")}</li>
      <li><span>Base de datos</span>${bk}</li>
      <li><span>Métodos en este equipo</span><span class="chips">${cap("camera", "Cámara")}${cap("bluetooth", "Bluetooth")}${cap("motion", "Movimiento")}</span></li></ul>`;
    $("homeHistInfo").textContent = H.history.count() ? `${H.history.count()} sesiones cargadas de ${H.history.pid()}.` : "Buscá por ID de paciente para ver la evolución y comparar mediciones.";
  }
  H.refreshHome = refreshHome;

  function gotoHistory() {
    if (!showView("history")) return;
    const pid = readProfile().patient_id;
    if (pid) { $("histId").value = pid; if (!H.history.count() || H.history.pid() !== pid) H.history.load(pid); }
    else $("histId").focus();
  }

  /* ═════ Eventos ═════ */
  function wire() {
    $$(".nav-btn").forEach((b) => b.addEventListener("click", () => { if (b.dataset.view === "history") gotoHistory(); else showView(b.dataset.view); }));
    $("profileForm").addEventListener("submit", submitProfile);
    ["patientId", "age", "sex", "comorbidities", "notes"].forEach((id) => $(id).addEventListener("change", saveProfile));
    $("patientId").addEventListener("input", () => profileOk(false)); $("age").addEventListener("input", () => profileOk(false));
    $("methodGrid").addEventListener("click", (e) => { const b = e.target.closest(".method"); if (b) selectSensor(b.dataset.sensor); });
    $("durRow").addEventListener("click", (e) => { const b = e.target.closest("[data-dur]"); if (!b) return; G.durationMin = +b.dataset.dur; G.totalSec = G.durationMin * 60; renderPrep(); });
    $("rrFile").addEventListener("change", onRRFile);
    $("stepper").addEventListener("click", (e) => { const b = e.target.closest("[data-step]"); if (b && (+b.dataset.step <= G.step || +b.dataset.step === 6)) goStep(+b.dataset.step); });
    $("btnStart").addEventListener("click", startSession);
    $("btnStop").addEventListener("click", () => stopSession(false));
    $("btnSave").addEventListener("click", saveSession);
    $$("[data-rtab]").forEach((b) => {
      b.addEventListener("click", () => H.results.setRTab(b.dataset.rtab));
      b.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const tabs = $$("[data-rtab]"), i = tabs.indexOf(b), n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        n.focus(); H.results.setRTab(n.dataset.rtab);
      });
    });
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[data-act]"); if (!el) return;
      switch (el.dataset.act) {
        case "start": if (showView("measure")) goStep(1); break;
        case "back": goStep(+el.dataset.to); break;
        case "next": goStep(+el.dataset.to); break;
        case "retry": { const v = $("valBanner"); v.innerHTML = ""; if (showView("measure")) { resetMeasureUI(); goStep(3); } break; }
        case "retry-measure": startSession(); break;
        case "other-method": $("mError").hidden = true; goStep(2); break;
        case "analyze-partial": computeAndDisplay(); break;
        case "dismiss-val": $("valBanner").innerHTML = ""; break;
        case "goto-results": if (showView("measure")) goStep(5); break;
        case "goto-history": gotoHistory(); break;
        case "repeat": if (showView("measure")) { resetMeasureUI(); goStep(3); } break;
      }
    });
    window.addEventListener("beforeunload", (e) => { if (G.running) { e.preventDefault(); e.returnValue = ""; } });
  }

  /* ═════ Inicio de la app ═════ */
  function init() {
    const p = store.get("hba.profile");
    if (p) { $("patientId").value = p.patient_id || ""; $("age").value = p.age || ""; $("sex").value = p.sex || ""; $("comorbidities").value = p.comorbidities || ""; $("notes").value = p.notes || ""; }
    const last = store.get("hba.last");
    G.rrImport = [];
    if (last && last.metrics) { G.lastMetrics = last.metrics; G.lastAt = last.at; G.lastSaved = !!last.saved; G.validation = window.HBAValidator.validate(last.metrics); }
    renderMethods(); H.history.init(); wire();
    if (G.lastMetrics) { H.results.render(G.lastMetrics, null); updateSaveBtn(); } else H.results.clear();
    G.step = 1; $$(".step-panel").forEach((p2) => { p2.hidden = p2.id !== "step-1"; }); renderStepper();
    setStatus("Listo"); refreshHome();
  }
  init();
})();
