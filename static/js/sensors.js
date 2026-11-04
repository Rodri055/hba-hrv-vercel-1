"use strict";
/* HANNA·HRV — sensors.js
   Captura de señal para cada método. No calcula HRV: eso lo hace /api/compute. */
(function () {
  const { G, $, WIN, PPG_SR, SCG_SR } = window.HBA;

  const HR_SVC = "0000180d-0000-1000-8000-00805f9b34fb";
  const HR_CHAR = "00002a37-0000-1000-8000-00805f9b34fb";

  function pushSig(v) { G.sigBuf.push(v); if (G.sigBuf.length > WIN * 3) G.sigBuf.shift(); }
  function pushSample(v) { G.ppgBuf.push(v); G.ppgTs.push(performance.now()); pushSig(v); }

  /* Frecuencia de muestreo REAL (muestras/seg). El backend la necesita para convertir
     muestras a milisegundos; asumir 30/50 Hz fijos distorsiona FC y HRV. */
  function effectiveRate() {
    const n = G.ppgTs.length; if (n < 10) return null;
    const span = (G.ppgTs[n - 1] - G.ppgTs[0]) / 1000; if (span <= 0) return null;
    const r = (n - 1) / span;
    return isFinite(r) && r >= 5 && r <= 400 ? r : null;
  }
  function samplingRate() {
    return effectiveRate() || (G.sensor === "vibration_scg" ? SCG_SR : PPG_SR);
  }

  /* ── Cámara (PPG de dedo = canal rojo · rPPG facial = canal verde) ── */
  async function startCamera() {
    const isFace = G.sensor === "face_rppg";
    G.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: isFace ? "user" : "environment", width: { ideal: 160 }, height: { ideal: 120 }, frameRate: { ideal: PPG_SR } },
    });
    const vid = $("video"); vid.srcObject = G.stream; await vid.play();
    if (!isFace && $("torchToggle").checked) {
      const tr = G.stream.getVideoTracks()[0], caps = tr.getCapabilities ? tr.getCapabilities() : {};
      if (caps && caps.torch) { try { await tr.applyConstraints({ advanced: [{ torch: true }] }); } catch (_) {} }
    }
    const canvas = $("frameCanvas"); canvas.width = 4; canvas.height = 4;
    G.frameCtx = canvas.getContext("2d", { willReadFrequently: true });
    const read = () => {
      G.frameCtx.drawImage(vid, 0, 0, 4, 4);
      const px = G.frameCtx.getImageData(0, 0, 4, 4).data; let val = 0;
      for (let i = isFace ? 1 : 0; i < px.length; i += 4) val += px[i];
      pushSample(val / (px.length / 4));
    };
    if ("requestVideoFrameCallback" in vid) {
      const cb = () => { if (!G.running) return; read(); vid.requestVideoFrameCallback(cb); };
      vid.requestVideoFrameCallback(cb);
    } else {
      let last = 0; const interval = 1000 / PPG_SR;
      const loop = (ts) => { if (!G.running) return; if (ts - last >= interval) { last = ts; read(); } requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
    }
  }
  function stopCamera() {
    if (G.stream) {
      G.stream.getTracks().forEach((t) => { try { const c = t.getCapabilities ? t.getCapabilities() : {}; if (c && c.torch) t.applyConstraints({ advanced: [{ torch: false }] }); } catch (_) {} t.stop(); });
      G.stream = null;
    }
    const vid = $("video"); if (vid) vid.srcObject = null;
  }

  /* ── Vibración (acelerómetro) ── */
  // Debe llamarse directo desde el toque del usuario (iOS exige el gesto).
  async function requestMotionPermission() {
    if (!window.DeviceMotionEvent) throw new Error("Este dispositivo no tiene acelerómetro disponible en el navegador.");
    if (typeof DeviceMotionEvent.requestPermission === "function") {
      const s = await DeviceMotionEvent.requestPermission();
      if (s !== "granted") throw new Error("Permiso de movimiento denegado. Habilitalo en los ajustes del navegador y repetí la medición.");
    }
  }
  function startVibration() {
    G.motionH = (e) => {
      if (!G.running) return;
      const a = e.accelerationIncludingGravity; if (!a) return;
      pushSample(Math.sqrt((a.x || 0) ** 2 + (a.y || 0) ** 2 + (a.z || 0) ** 2));
    };
    window.addEventListener("devicemotion", G.motionH, { passive: true });
  }
  function stopVibration() { if (G.motionH) { window.removeEventListener("devicemotion", G.motionH); G.motionH = null; } }

  /* ── Polar H10 (Web Bluetooth) ── */
  // requestDevice DEBE ser la primera llamada asíncrona dentro del toque del usuario.
  function requestPolar() {
    if (!navigator.bluetooth) return Promise.reject(new Error("Web Bluetooth no está disponible. Usá Chrome o Edge en PC o Android (iPhone no es compatible)."));
    return navigator.bluetooth.requestDevice({ filters: [{ namePrefix: "Polar" }, { namePrefix: "polar" }], optionalServices: [HR_SVC] });
  }
  async function connectPolar(device, onLost) {
    device.addEventListener("gattserverdisconnected", onLost);
    const server = await device.gatt.connect();
    const svc = await server.getPrimaryService(HR_SVC);
    const ch = await svc.getCharacteristic(HR_CHAR);
    ch.addEventListener("characteristicvaluechanged", (e) => {
      if (!G.running) return;
      const dv = e.target.value, flags = dv.getUint8(0), hasRR = (flags >> 4) & 1;
      let offset = (flags & 1) ? 3 : 2;
      G.lastHr = (flags & 1) ? dv.getUint16(1, true) : dv.getUint8(1);
      if (flags & 0x08) offset += 2; // energía gastada presente
      if (hasRR) {
        while (offset + 1 < dv.byteLength) {
          const rr = dv.getUint16(offset, true) / 1024.0 * 1000.0; offset += 2;
          if (rr > 300 && rr < 2200) { G.rrBuf.push(rr); pushSig(rr); G.rrLastAt = performance.now(); }
        }
      }
    });
    await ch.startNotifications();
    G.rrLastAt = performance.now();
  }
  function stopPolar() {
    try { if (G.bleDevice && G.bleDevice.gatt && G.bleDevice.gatt.connected) G.bleDevice.gatt.disconnect(); } catch (_) {}
    G.bleDevice = null;
  }

  /* ── Importación RR (CSV / JSON) ── */
  async function parseRRFile(file) {
    const text = await file.text(); let rrs = [];
    if (file.name.toLowerCase().endsWith(".json")) {
      let obj; try { obj = JSON.parse(text); } catch (_) { throw new Error("El archivo JSON no es válido."); }
      rrs = Array.isArray(obj) ? obj : (obj.rri_ms || obj.rr || Object.values(obj).flat());
      rrs = rrs.map(Number);
    } else {
      const lines = text.trim().split(/\r?\n/), sep = /[,;\t]/;
      const first = lines[0].split(sep).map((x) => x.trim().toLowerCase());
      const hasHeader = first.some((c) => c !== "" && isNaN(parseFloat(c)));
      let col = ["rr", "rri", "rri_ms", "nn", "ibi"].reduce((a, k) => (a >= 0 ? a : first.indexOf(k)), -1);
      if (col < 0) col = 0;
      for (let i = hasHeader ? 1 : 0; i < lines.length; i++) {
        const v = parseFloat(lines[i].split(sep)[col]); if (!isNaN(v)) rrs.push(v);
      }
    }
    rrs = rrs.filter((v) => isFinite(v));
    if (!rrs.length) throw new Error("No se encontraron valores RR en el archivo.");
    const mean = rrs.reduce((a, b) => a + b, 0) / rrs.length;
    if (mean < 5) rrs = rrs.map((r) => r * 1000); // segundos → ms
    rrs = rrs.filter((r) => r > 200 && r < 2500);
    if (rrs.length < 12) throw new Error(`Solo hay ${rrs.length} intervalos RR válidos; se necesitan al menos 12.`);
    return rrs;
  }

  /* ── Estado de señal en vivo (orientativo; la calidad final la calcula el servidor) ── */
  function liveSignal() {
    const s = G.sensor, now = performance.now();
    if (s === "polar_h10") {
      const gap = (now - G.rrLastAt) / 1000;
      if (!G.rrLastAt || gap > 5) return { lvl: 0, txt: "Sin latidos", hint: "Verificá que la cinta esté húmeda y bien ajustada." };
      return { lvl: 2, txt: "Recibiendo latidos", hint: G.lastHr ? `${G.lastHr} bpm` : "" };
    }
    const w = G.sigBuf.slice(-90);
    if (w.length < 30) return { lvl: 0, txt: "Iniciando", hint: "Esperando las primeras muestras." };
    let mn = Infinity, mx = -Infinity, sum = 0;
    for (const v of w) { if (v < mn) mn = v; if (v > mx) mx = v; sum += v; }
    const mean = sum / w.length, range = mx - mn;
    if (s === "camera_ppg" && mean < 30) return { lvl: 1, txt: "Débil", hint: "Imagen muy oscura: cubrí por completo lente y flash con el dedo." };
    if (s === "face_rppg" && mean < 20) return { lvl: 1, txt: "Débil", hint: "Poca luz: buscá un lugar mejor iluminado." };
    if (s === "camera_ppg" && mean > 250 && range < 0.5) return { lvl: 1, txt: "Débil", hint: "Imagen saturada: aflojá un poco la presión del dedo." };
    if (range < (s === "vibration_scg" ? 1e-4 : 0.3)) return { lvl: 1, txt: "Plana", hint: "No se ve variación: no muevas el dispositivo ni el dedo." };
    return { lvl: 2, txt: "Recibida", hint: "" };
  }

  window.HBA.sensors = {
    pushSig, effectiveRate, samplingRate,
    startCamera, stopCamera, requestMotionPermission, startVibration, stopVibration,
    requestPolar, connectPolar, stopPolar, parseRRFile, liveSignal,
  };
})();
