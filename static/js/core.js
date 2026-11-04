"use strict";
/* HANNA·HRV — core.js
   Estado global, utilidades de UI y descripción de cada método de medición. */
(function () {
  const PPG_SR = 30, SCG_SR = 50, WIN = 300, FPS = 10;

  const G = {
    sensor: "camera_ppg", durationMin: 3, totalSec: 180,
    running: false, phase: "idle",           // idle | countdown | connecting | measuring | computing
    ppgBuf: [], ppgTs: [], rrBuf: [], sigBuf: [],
    elapsed: 0, lastMetrics: null, lastSaved: false, lastAt: null, validation: null,
    timerH: null, rafH: null, chartLast: 0,
    bleDevice: null, stream: null, frameCtx: null, motionH: null, vfcH: null,
    rrLastAt: 0, rrFileName: "", backend: "unknown", step: 1,
  };

  const $ = (id) => document.getElementById(id);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v) => (v != null && v !== "" && isFinite(+v) ? +v : null);
  const fmt = (v, d = 1) => (num(v) == null ? "—" : (+v).toFixed(d));
  const ic = (name, cls) => `<svg class="ic ${cls || ""}" aria-hidden="true"><use href="/static/icons/sprite.svg#i-${name}"/></svg>`;
  const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  const fmtDate = (ts) => {
    const d = new Date(ts); if (isNaN(d)) return "—";
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" }) + " " +
      d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
  };

  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (_) { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} },
  };

  /* ── Avisos y diálogos (reemplazan alert/confirm) ── */
  function toast(msg, kind) {
    const box = $("toasts"); if (!box) return;
    const el = document.createElement("div");
    el.className = "toast " + (kind || "");
    el.setAttribute("role", kind === "err" ? "alert" : "status");
    el.innerHTML = `${ic(kind === "err" ? "circle-alert" : kind === "ok" ? "circle-check" : "info")}<span>${esc(msg)}</span>`;
    box.appendChild(el);
    setTimeout(() => el.remove(), kind === "err" ? 7000 : 4000);
  }

  function confirmDialog(title, body, okLabel, cancelLabel) {
    return new Promise((resolve) => {
      const d = $("dlg");
      $("dlgTitle").textContent = title; $("dlgBody").textContent = body;
      $("dlgOk").textContent = okLabel || "Continuar"; $("dlgCancel").textContent = cancelLabel || "Cancelar";
      const done = (v) => { d.removeEventListener("close", onClose); $("dlgOk").onclick = $("dlgCancel").onclick = null; if (d.open) d.close(); resolve(v); };
      const onClose = () => done(false);
      d.addEventListener("close", onClose);
      $("dlgOk").onclick = () => done(true);
      $("dlgCancel").onclick = () => done(false);
      if (typeof d.showModal === "function") d.showModal(); else d.setAttribute("open", "");
    });
  }

  /* ── Capacidades reales del dispositivo/navegador ── */
  const secure = window.isSecureContext !== false;
  const CAPS = {
    camera: secure && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
    bluetooth: secure && !!navigator.bluetooth,
    motion: secure && !!window.DeviceMotionEvent,
    file: true,
  };

  /* ── Métodos de medición ── */
  const SENSORS = {
    camera_ppg: {
      label: "Cámara PPG", icon: "camera", tag: "Recomendado", tagKind: "good", cap: "camera", durs: [3, 5], torch: true, camera: true,
      what: "Detecta el pulso con la cámara trasera y el flash, apoyando la yema del dedo sobre el lente.",
      needs: "Celular con cámara trasera y flash. Permiso de cámara.",
      how: "Cubrí lente y flash con el dedo índice y mantené la mano quieta.",
      position: ["Sentate con la espalda apoyada y los pies en el piso.", "Apoyá el codo sobre una mesa para que la mano no se mueva.", "Cubrí por completo el lente y el flash con la yema del dedo índice, sin apretar fuerte."],
      conditions: ["Ambiente tranquilo: sin hablar ni moverte.", "Manos tibias; las manos frías dan una señal más débil.", "Respirá con normalidad."],
      placement: [],
      connection: ["El navegador pedirá permiso de cámara al iniciar.", "El flash se enciende solo si el dispositivo lo permite."],
      warnings: ["Si el flash no se enciende, medí con luz ambiente intensa: la señal puede ser más débil.", "No bloquees la pantalla durante la medición."],
    },
    face_rppg: {
      label: "Face rPPG", icon: "scan-face", tag: "Experimental", tagKind: "exp", cap: "camera", durs: [1, 3, 5], torch: false, camera: true,
      what: "Estima el pulso a partir de los cambios de color del rostro con la cámara frontal, sin contacto.",
      needs: "Cámara frontal y luz uniforme. Permiso de cámara.",
      how: "Mirá a la cámara sin moverte durante toda la medición.",
      position: ["Sentate frente al dispositivo con el rostro completo y centrado en la imagen.", "Apoyá el dispositivo en una superficie fija."],
      conditions: ["Luz uniforme y estable, de frente; evitá contraluz y sombras que cambien.", "No hables, no sonrías ni muevas la cabeza."],
      placement: [],
      connection: ["El navegador pedirá permiso de cámara al iniciar."],
      warnings: ["Método experimental: la señal sin contacto es orientativa y más sensible al movimiento.", "No bloquees la pantalla durante la medición."],
    },
    vibration_scg: {
      label: "Vibración SCG", icon: "vibrate", tag: "Experimental", tagKind: "exp", cap: "motion", durs: [1, 3, 5], torch: false, camera: false,
      what: "Registra las microvibraciones del latido con el acelerómetro del celular apoyado sobre el pecho.",
      needs: "Celular con acelerómetro. En iPhone, permiso de movimiento.",
      how: "Acostate boca arriba con el celular centrado sobre el esternón.",
      position: ["Acostate boca arriba sobre una superficie firme.", "Apoyá el celular plano y centrado sobre el esternón, con la pantalla hacia arriba."],
      conditions: ["Ambiente en silencio, sin hablar ni moverte.", "Respirá con normalidad."],
      placement: ["Sostené el celular con el peso de la mano sin presionar."],
      connection: ["Aceptá el permiso de movimiento cuando el navegador lo pida (iPhone)."],
      warnings: ["Método experimental: la señal es orientativa.", "Funciona solo en dispositivos con acelerómetro (celulares y algunas tablets)."],
    },
    polar_h10: {
      label: "Polar H10", icon: "bluetooth", tag: "Más preciso", tagKind: "best", cap: "bluetooth", durs: [1, 3, 5], torch: false, camera: false,
      what: "Cinta de pecho que transmite cada intervalo entre latidos por Bluetooth. Es el método más preciso.",
      needs: "Polar H10 con batería y Chrome o Edge (Web Bluetooth) en Android o PC.",
      how: "Colocá la cinta, activá Bluetooth y elegí tu Polar en la ventana que aparece.",
      position: ["Sentate cómodo y relajado, con la espalda apoyada.", "Mantené el dispositivo cerca del sensor durante la medición."],
      conditions: ["Ambiente tranquilo, sin hablar ni moverte.", "Respirá con normalidad."],
      placement: ["Humedecé los electrodos de la cinta con agua.", "Ajustá la cinta justo debajo del pecho, con el logo Polar centrado.", "El sensor se activa al detectar contacto con la piel."],
      connection: ["Bluetooth activado en el dispositivo.", "Usá Chrome o Edge: Safari y iPhone no soportan Web Bluetooth.", "Si el Polar no aparece en la lista, cerrá otras apps que estén conectadas al sensor."],
      warnings: ["El navegador pide elegir el sensor al tocar «Iniciar medición».", "No bloquees la pantalla durante la medición."],
    },
    rr_upload: {
      label: "Importar RR", icon: "file-up", tag: "Sin sensor", tagKind: "good", cap: "file", durs: [1, 3, 5], torch: false, camera: false,
      what: "Analiza una grabación ya hecha: intervalos RR exportados desde Polar, Kubios, Garmin u otro sistema.",
      needs: "Archivo .csv o .json con intervalos RR, en milisegundos o segundos.",
      how: "Cargá el archivo y elegí la duración de la grabación.",
      position: [], conditions: [], placement: [],
      connection: ["CSV: una columna llamada rr, rri, rri_ms, nn o ibi (o la primera columna).", "JSON: una lista de valores, o un objeto con rri_ms o rr."],
      warnings: ["Se necesitan al menos 12 intervalos RR válidos.", "La duración que elijas se usa para corregir el RMSSD: debe coincidir con la grabación."],
    },
  };

  const STEPS = [
    { n: 1, label: "Paciente" }, { n: 2, label: "Método" }, { n: 3, label: "Preparación" },
    { n: 4, label: "Medición" }, { n: 5, label: "Resultados" }, { n: 6, label: "Historial" },
  ];

  window.HBA = { PPG_SR, SCG_SR, WIN, FPS, G, $, $$, esc, num, fmt, ic, mmss, fmtDate, store, toast, confirmDialog, CAPS, SENSORS, STEPS };
  window.G = G; // compatibilidad con código previo
})();
