/**
 * HANNA·HRV — Validador de resultados fisiológicos
 * Umbrales sin cambios respecto de la versión original. Basados en:
 *  - Task Force ESC/NASPE (1996)
 *  - Shaffer & Ginsberg (2017), Frontiers in Public Health
 *  - Laborde et al. (2017), rangos de referencia de RMSSD
 *
 * Es una función pura: recibe la respuesta de /api/compute y devuelve
 * { severity: "ok"|"warn"|"invalid", issues: [{field, value, msg, verdict}] }.
 * La interfaz (banner) se dibuja en results.js.
 */
(function () {
  "use strict";

  const THRESHOLDS = {
    rmssd: { floor_hard: 2, floor_warn: 4, floor_ok: 8, ceil_ok: 200, ceil_warn: 300, ceil_hard: 500 },
    hr: { floor_hard: 25, floor_warn: 35, floor_ok: 40, ceil_ok: 180, ceil_warn: 200, ceil_hard: 250 },
    sdnn: { floor_hard: 1, ceil_hard: 500 },
    artifacts: { warn: 15, bad: 30, hard: 60 },
    quality: { warn: 45, bad: 25 },
  };

  const VERDICT = {
    VALID: "valid", WARN_LOW: "warn_low", WARN_HIGH: "warn_high", WARN_QUALITY: "warn_quality",
    INVALID_LOW: "invalid_low", INVALID_HIGH: "invalid_high", ARTIFACT: "artifact",
  };

  const isNum = (v) => v != null && isFinite(+v);

  function validateHRV(data) {
    const rmssd = data.rmssd_corr ?? data.rmssd;
    const hr = data.hr_mean, art = data.artifact_percent, qual = data.quality_score;
    const issues = [];
    let severity = "ok";
    const bump = (lvl) => { if (lvl === "invalid") severity = "invalid"; else if (severity === "ok") severity = "warn"; };

    if (isNum(rmssd)) {
      const T = THRESHOLDS.rmssd, v = (+rmssd).toFixed(1) + " ms";
      if (rmssd < T.floor_hard) {
        issues.push({ field: "RMSSD", value: v, msg: "Señal plana detectada. Sin contacto con el sensor o artefacto total.", verdict: VERDICT.INVALID_LOW }); bump("invalid");
      } else if (rmssd < T.floor_warn) {
        issues.push({ field: "RMSSD", value: v, msg: "Señal extremadamente débil. Verificá el contacto con el sensor.", verdict: VERDICT.WARN_LOW }); bump("warn");
      } else if (rmssd > T.ceil_hard) {
        issues.push({ field: "RMSSD", value: v, msg: "Valor fisiológicamente imposible (máximo humano: ~300 ms). Artefacto severo de movimiento o señal corrupta.", verdict: VERDICT.INVALID_HIGH }); bump("invalid");
      } else if (rmssd > T.ceil_warn) {
        issues.push({ field: "RMSSD", value: v, msg: "Valor extremadamente alto. Solo posible en atletas de élite con Polar H10. Verificar si es correcto.", verdict: VERDICT.WARN_HIGH }); bump("warn");
      }
    }

    if (isNum(hr)) {
      const T = THRESHOLDS.hr, v = (+hr).toFixed(0) + " bpm";
      if (hr < T.floor_hard || hr > T.ceil_hard) {
        issues.push({ field: "FC media", value: v, msg: hr < T.floor_hard ? "Frecuencia cardíaca imposible en estado despierto." : "Frecuencia cardíaca imposible. Artefacto de señal.", verdict: hr < T.floor_hard ? VERDICT.INVALID_LOW : VERDICT.INVALID_HIGH }); bump("invalid");
      } else if (hr < T.floor_warn || hr > T.ceil_warn) {
        issues.push({ field: "FC media", value: v, msg: hr < T.floor_warn ? "FC muy baja. Solo atletas de resistencia extrema en reposo." : "FC muy alta. Verificar contacto del sensor.", verdict: hr < T.floor_warn ? VERDICT.WARN_LOW : VERDICT.WARN_HIGH }); bump("warn");
      }
    }

    if (isNum(art)) {
      const T = THRESHOLDS.artifacts, v = (+art).toFixed(1) + "%";
      if (art > T.hard) { issues.push({ field: "Artefactos", value: v, msg: "Señal con artefactos excesivos. Los resultados no son confiables.", verdict: VERDICT.ARTIFACT }); bump("invalid"); }
      else if (art > T.bad) { issues.push({ field: "Artefactos", value: v, msg: "Alta proporción de artefactos. Interpretá los resultados con precaución.", verdict: VERDICT.ARTIFACT }); bump("warn"); }
      else if (art > T.warn) { issues.push({ field: "Artefactos", value: v, msg: "Señal con algunos artefactos. Procurá más estabilidad en la próxima medición.", verdict: VERDICT.WARN_QUALITY }); bump("warn"); }
    }

    if (isNum(qual) && qual < THRESHOLDS.quality.bad) {
      issues.push({ field: "Calidad de señal", value: (+qual).toFixed(0) + "%", msg: "Calidad de señal insuficiente. Repetí la medición con mejor contacto.", verdict: VERDICT.WARN_QUALITY }); bump("warn");
    }

    return { severity, issues };
  }

  window.HBAValidator = { THRESHOLDS, VERDICT, validate: validateHRV };
})();
