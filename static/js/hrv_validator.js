/**
 * HANNA·HRV — Validador de resultados fisiológicos
 * ═══════════════════════════════════════════════════
 * Se inyecta DESPUÉS de main.js. Intercepta renderDashboard()
 * y showScreen() sin modificar el código original.
 *
 * Umbrales clínicos basados en:
 *  - Task Force ESC/NASPE (1996)
 *  - Shaffer & Ginsberg (2017) — Frontiers in Public Health
 *  - Laborde et al. (2017) — RMSSD reference ranges
 */

;(function() {
  'use strict';

  // ── UMBRALES FISIOLÓGICOS ─────────────────────────────────
  const THRESHOLDS = {
    // RMSSD (ms)
    rmssd: {
      floor_hard:   2,    // < 2ms  → señal plana / sin contacto
      floor_warn:   4,    // 2–4ms  → señal muy débil / posible artefacto
      floor_ok:     8,    // 4–8ms  → fisiológicamente posible (muy bajo)
      ceil_ok:    200,    // 8–200ms → rango fisiológico normal
      ceil_warn:  300,    // 200–300ms → límite alto (atleta élite extremo)
      ceil_hard:  500,    // > 300ms → irreal / artefacto severo
    },
    // FC media (bpm)
    hr: {
      floor_hard:  25,   // < 25 → imposible despierto
      floor_warn:  35,   // 25–35 → solo atletas bradicárdicos extremos
      floor_ok:    40,
      ceil_ok:    180,
      ceil_warn:  200,
      ceil_hard:  250,   // > 200 → artefacto
    },
    // SDNN (ms)
    sdnn: {
      floor_hard:  1,
      ceil_hard: 500,
    },
    // Artefactos (%)
    artifacts: {
      warn:  15,   // > 15% → advertir
      bad:   30,   // > 30% → señal muy comprometida
      hard:  60,   // > 60% → irreal
    },
    // Quality score (0–100)
    quality: {
      warn:  45,
      bad:   25,
    }
  };

  // ── CLASIFICACIÓN ─────────────────────────────────────────
  const VERDICT = {
    VALID:        'valid',        // ✅ Datos fisiológicamente coherentes
    WARN_LOW:     'warn_low',     // ⚠️ Valores bajos, posiblemente correctos
    WARN_HIGH:    'warn_high',    // ⚠️ Valores altos, poco frecuentes
    WARN_QUALITY: 'warn_quality', // ⚠️ Señal de baja calidad
    INVALID_LOW:  'invalid_low',  // ❌ Por debajo del piso fisiológico
    INVALID_HIGH: 'invalid_high', // ❌ Por encima del techo fisiológico
    ARTIFACT:     'artifact',     // ❌ Señal con exceso de artefactos
  };

  /**
   * Evalúa los datos HRV y devuelve un objeto de validación.
   * @param {Object} data — respuesta del servidor /api/compute
   * @returns {Object} { verdict, severity, issues[], rmssd_display }
   */
  function validateHRV(data) {
    const rmssd  = data.rmssd_corr ?? data.rmssd;
    const hr     = data.hr_mean;
    const sdnn   = data.sdnn;
    const art    = data.artifact_percent;
    const qual   = data.quality_score;

    const issues = [];
    let severity = 'ok'; // ok | warn | invalid

    // ── Validar RMSSD ────────────────────────────────────────
    if (rmssd != null) {
      const T = THRESHOLDS.rmssd;

      if (rmssd < T.floor_hard) {
        issues.push({
          field: 'RMSSD',
          value: rmssd.toFixed(1) + ' ms',
          msg: 'Señal plana detectada. Sin contacto con el sensor o artefacto total.',
          verdict: VERDICT.INVALID_LOW,
        });
        severity = 'invalid';

      } else if (rmssd < T.floor_warn) {
        issues.push({
          field: 'RMSSD',
          value: rmssd.toFixed(1) + ' ms',
          msg: 'Señal extremadamente débil. Verificá el contacto con el sensor.',
          verdict: VERDICT.WARN_LOW,
        });
        if (severity === 'ok') severity = 'warn';

      } else if (rmssd > T.ceil_hard) {
        issues.push({
          field: 'RMSSD',
          value: rmssd.toFixed(1) + ' ms',
          msg: `Valor fisiológicamente imposible (máximo humano: ~300ms). Artefacto severo de movimiento o señal corrupta.`,
          verdict: VERDICT.INVALID_HIGH,
        });
        severity = 'invalid';

      } else if (rmssd > T.ceil_warn) {
        issues.push({
          field: 'RMSSD',
          value: rmssd.toFixed(1) + ' ms',
          msg: 'Valor extremadamente alto. Solo posible en atletas de élite con Polar H10. Verificar si es correcto.',
          verdict: VERDICT.WARN_HIGH,
        });
        if (severity === 'ok') severity = 'warn';
      }
    }

    // ── Validar FC ───────────────────────────────────────────
    if (hr != null) {
      const T = THRESHOLDS.hr;
      if (hr < T.floor_hard || hr > T.ceil_hard) {
        issues.push({
          field: 'FC Media',
          value: hr.toFixed(0) + ' bpm',
          msg: hr < T.floor_hard
            ? 'Frecuencia cardíaca imposible en estado despierto.'
            : 'Frecuencia cardíaca imposible. Artefacto de señal.',
          verdict: hr < T.floor_hard ? VERDICT.INVALID_LOW : VERDICT.INVALID_HIGH,
        });
        severity = 'invalid';
      } else if (hr < T.floor_warn || hr > T.ceil_warn) {
        issues.push({
          field: 'FC Media',
          value: hr.toFixed(0) + ' bpm',
          msg: hr < T.floor_warn
            ? 'FC muy baja. Solo atletas de resistencia extrema en reposo.'
            : 'FC muy alta. Verificar contacto del sensor.',
          verdict: hr < T.floor_warn ? VERDICT.WARN_LOW : VERDICT.WARN_HIGH,
        });
        if (severity === 'ok') severity = 'warn';
      }
    }

    // ── Validar artefactos ───────────────────────────────────
    if (art != null) {
      const T = THRESHOLDS.artifacts;
      if (art > T.hard) {
        issues.push({
          field: 'Artefactos',
          value: art.toFixed(1) + '%',
          msg: 'Señal con artefactos excesivos. Los resultados no son confiables.',
          verdict: VERDICT.ARTIFACT,
        });
        severity = 'invalid';
      } else if (art > T.bad) {
        issues.push({
          field: 'Artefactos',
          value: art.toFixed(1) + '%',
          msg: 'Alta proporción de artefactos. Interpretá los resultados con precaución.',
          verdict: VERDICT.ARTIFACT,
        });
        if (severity === 'ok') severity = 'warn';
      } else if (art > T.warn) {
        issues.push({
          field: 'Artefactos',
          value: art.toFixed(1) + '%',
          msg: 'Señal con algunos artefactos. Procurá más estabilidad en la próxima medición.',
          verdict: VERDICT.WARN_QUALITY,
        });
        if (severity === 'ok') severity = 'warn';
      }
    }

    // ── Validar calidad ──────────────────────────────────────
    if (qual != null && qual < THRESHOLDS.quality.bad) {
      issues.push({
        field: 'Calidad de señal',
        value: qual.toFixed(0) + '%',
        msg: 'Calidad de señal insuficiente. Repetí la medición con mejor contacto.',
        verdict: VERDICT.WARN_QUALITY,
      });
      if (severity === 'ok') severity = 'warn';
    }

    // ── RMSSD display: si es inválido mostramos "ERR" ────────
    const rmssd_display = severity === 'invalid'
      ? null   // null → mostrar banner de error, no el valor
      : rmssd;

    return { severity, issues, rmssd_display };
  }

  // ── UI: Construir banner de validación ────────────────────
  function buildValidationBanner(validation, data) {
    if (validation.severity === 'ok') return null;

    const isInvalid = validation.severity === 'invalid';
    const color = isInvalid ? 'var(--s-cri)' : 'var(--s-com)';
    const colorBg = isInvalid ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)';
    const colorBdr = isInvalid ? 'rgba(239,68,68,0.28)' : 'rgba(245,158,11,0.28)';
    const icon = isInvalid ? '🚫' : '⚠️';
    const title = isInvalid
      ? 'Resultado no válido — Repetir medición'
      : 'Resultado con advertencias';

    const issueRows = validation.issues.map(issue => `
      <div class="val-issue-row">
        <div class="val-issue-field">${issue.field}</div>
        <div class="val-issue-val">${issue.value}</div>
        <div class="val-issue-msg">${issue.msg}</div>
      </div>
    `).join('');

    const causeList = isInvalid ? `
      <div class="val-causes">
        <div class="val-causes-title">Causas frecuentes:</div>
        <ul class="val-causes-list">
          <li>Movimiento excesivo durante la medición</li>
          <li>Dedo no bien posicionado sobre el lente</li>
          <li>Luz ambiental directa sobre el sensor</li>
          <li>Flash apagado (activar en configuración)</li>
          <li>Señal muy corta o interrumpida</li>
        </ul>
      </div>
    ` : '';

    const actionBtn = isInvalid ? `
      <button class="val-btn-retry" onclick="window._hannaRetry()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/></svg>
        Repetir medición
      </button>
    ` : `
      <button class="val-btn-dismiss" onclick="this.closest('.val-banner').style.display='none'">
        Entendido, ver resultados
      </button>
    `;

    const el = document.createElement('div');
    el.className = 'val-banner' + (isInvalid ? ' val-invalid' : ' val-warn');
    el.innerHTML = `
      <div class="val-header">
        <span class="val-icon">${icon}</span>
        <div class="val-title-wrap">
          <div class="val-title">${title}</div>
          <div class="val-subtitle">
            ${isInvalid
              ? 'Los valores registrados están fuera del rango fisiológico humano.'
              : 'Los valores están en el límite del rango fisiológico normal.'}
          </div>
        </div>
      </div>
      <div class="val-issues">${issueRows}</div>
      ${causeList}
      <div class="val-actions">${actionBtn}</div>
    `;

    return el;
  }

  // ── UI: Marcar semáforo como inválido ─────────────────────
  function markSemInvalid(data) {
    const hero = document.getElementById('semHero');
    if (!hero) return;

    // Reemplazar valor RMSSD con indicador de error
    const rmssdEl = document.getElementById('semRmssdVal');
    if (rmssdEl) {
      const raw = data.rmssd_corr ?? data.rmssd;
      rmssdEl.innerHTML = `
        <span style="font-size:14px;color:var(--s-cri);font-family:var(--font-m);letter-spacing:-0.01em">
          ⚠ ${raw != null ? raw.toFixed(1) : '?'} ms
        </span>
        <span style="display:block;font-size:11px;color:var(--s-cri);opacity:0.8;margin-top:4px">IRREAL</span>
      `;
    }

    // Agregar badge de error encima del semáforo
    const existing = hero.querySelector('.sem-invalid-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'sem-invalid-overlay';
    overlay.innerHTML = `
      <div class="sem-invalid-badge">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        Resultado no válido — datos fuera de rango fisiológico
      </div>
    `;
    hero.insertBefore(overlay, hero.firstChild);
  }

  // ── RETRY: volver a medir ─────────────────────────────────
  window._hannaRetry = function() {
    // Limpiar estado anterior
    const banner = document.querySelector('.val-banner');
    if (banner) banner.remove();
    const overlay = document.querySelector('.sem-invalid-overlay');
    if (overlay) overlay.remove();

    // Navegar a tab Medir
    if (typeof switchTab === 'function') {
      switchTab('tabMedir');
    } else {
      // fallback original
      if (typeof showScreen === 'function') {
        showScreen('screenSensor');
      }
    }
  };

  // ── HOOK: interceptar renderDashboard ─────────────────────
  // Esperamos a que main.js haya definido la función
  function hookRenderDashboard() {
    const originalRender = window.renderDashboard;
    if (!originalRender) return false;

    window.renderDashboard = function(data) {
      // Ejecutar render original primero
      originalRender(data);

      // Validar datos
      const validation = validateHRV(data);

      // Si hay problemas, mostrar UI
      if (validation.severity !== 'ok') {
        // Marcar el semáforo
        if (validation.severity === 'invalid') {
          markSemInvalid(data);
        }

        // Insertar banner al tope del panel de resultados
        const panel = document.getElementById('tabResultados');
        const panelBody = panel?.querySelector('.panel-body');
        if (panelBody) {
          // Remover banner previo si existe
          const prev = panelBody.querySelector('.val-banner');
          if (prev) prev.remove();

          const banner = buildValidationBanner(validation, data);
          if (banner) {
            panelBody.insertBefore(banner, panelBody.firstChild);
            // Scroll al top para que se vea
            setTimeout(() => panel.scrollTo({ top: 0, behavior: 'smooth' }), 100);
          }
        }
      }

      // Guardar validación en G para acceso externo
      if (window.G) window.G.lastValidation = validation;
    };

    return true;
  }

  // Intentar hookear cuando el DOM esté listo
  // main.js corre sincrónicamente así que esperamos al siguiente tick
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(hookRenderDashboard, 50);
    });
  } else {
    setTimeout(hookRenderDashboard, 50);
  }

  // ── ESTILOS inline del validador ─────────────────────────
  const style = document.createElement('style');
  style.textContent = `

    /* ── Banner principal ── */
    .val-banner {
      border-radius: 16px;
      overflow: hidden;
      animation: valIn 0.35s cubic-bezier(0.34,1.3,0.64,1);
      margin-bottom: 4px;
    }
    @keyframes valIn {
      from { opacity:0; transform:translateY(-12px) scale(0.97); }
      to   { opacity:1; transform:none; }
    }
    .val-invalid {
      background: rgba(239,68,68,0.07);
      border: 1px solid rgba(239,68,68,0.30);
      box-shadow: 5px 5px 0 rgba(0,0,0,0.55),
                  0 0 32px rgba(239,68,68,0.08),
                  inset 0 1px 0 rgba(255,255,255,0.07);
    }
    .val-warn {
      background: rgba(245,158,11,0.07);
      border: 1px solid rgba(245,158,11,0.28);
      box-shadow: 5px 5px 0 rgba(0,0,0,0.50),
                  0 0 28px rgba(245,158,11,0.07),
                  inset 0 1px 0 rgba(255,255,255,0.06);
    }

    /* ── Header ── */
    .val-header {
      display: flex; align-items: flex-start; gap: 13px;
      padding: 16px 18px 13px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      background: rgba(255,255,255,0.02);
    }
    .val-icon { font-size: 26px; flex-shrink:0; line-height:1; margin-top:2px; }
    .val-title-wrap { flex:1; }
    .val-title {
      font-family: 'Montserrat', sans-serif;
      font-size: 16px; font-weight: 700;
      letter-spacing: -0.02em; color: #eef2ff;
      margin-bottom: 4px;
    }
    .val-invalid .val-title { color: var(--s-cri, #ef4444); }
    .val-warn    .val-title { color: var(--s-com, #f59e0b); }
    .val-subtitle {
      font-size: 13px; color: #8896b3; line-height: 1.5;
      font-family: 'Inter', sans-serif;
    }

    /* ── Issues ── */
    .val-issues { padding: 13px 18px 10px; display:flex; flex-direction:column; gap:10px; }
    .val-issue-row {
      display: grid;
      grid-template-columns: 110px 90px 1fr;
      gap: 8px; align-items: start;
    }
    @media (max-width: 400px) {
      .val-issue-row { grid-template-columns: 1fr; gap:3px; }
    }
    .val-issue-field {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.12em;
      color: #3d4d6a; padding-top:2px;
    }
    .val-issue-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 14px; font-weight: 600;
      color: #eef2ff; letter-spacing: -0.01em;
    }
    .val-invalid .val-issue-val { color: var(--s-cri, #ef4444); }
    .val-warn    .val-issue-val { color: var(--s-com, #f59e0b); }
    .val-issue-msg {
      font-size: 13px; color: #8896b3; line-height: 1.55;
      font-family: 'Inter', sans-serif;
    }

    /* ── Causas ── */
    .val-causes {
      margin: 0 18px 12px;
      background: rgba(0,0,0,0.20);
      border-radius: 10px; padding: 12px 15px;
      border: 1px solid rgba(255,255,255,0.05);
    }
    .val-causes-title {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.15em;
      color: #3d4d6a; margin-bottom: 8px;
    }
    .val-causes-list {
      list-style: none; padding:0; margin:0;
      display:flex; flex-direction:column; gap:5px;
    }
    .val-causes-list li {
      font-size: 13px; color: #8896b3; line-height:1.4;
      padding-left: 16px; position:relative;
      font-family: 'Inter', sans-serif;
    }
    .val-causes-list li::before {
      content:'→'; position:absolute; left:0;
      color: var(--s-cri, #ef4444);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .val-warn .val-causes-list li::before { color: var(--s-com, #f59e0b); }

    /* ── Acciones ── */
    .val-actions { padding: 0 18px 16px; display:flex; gap:10px; flex-wrap:wrap; }

    .val-btn-retry {
      display: flex; align-items: center; gap: 9px;
      padding: 14px 22px; border-radius: 11px; border: none;
      background: linear-gradient(145deg, #c9a227, #a07d10);
      color: #0B1320;
      font-family: 'Montserrat', sans-serif;
      font-size: 15px; font-weight: 700; letter-spacing:-0.02em;
      cursor: pointer; transition: all 0.2s;
      box-shadow: 5px 5px 0 rgba(0,0,0,0.60),
                  0 0 24px rgba(212,175,55,0.18),
                  inset 0 1px 0 rgba(255,255,255,0.20);
      -webkit-tap-highlight-color: transparent;
    }
    .val-btn-retry:active {
      transform: translate(3px,3px);
      box-shadow: 2px 2px 0 rgba(0,0,0,0.60);
    }
    .val-btn-retry:hover {
      background: linear-gradient(145deg, #d4af37, #b08d18);
    }

    .val-btn-dismiss {
      display: flex; align-items: center; gap: 8px;
      padding: 13px 20px; border-radius: 11px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.12);
      color: #8896b3;
      font-family: 'Montserrat', sans-serif;
      font-size: 14px; font-weight: 600;
      cursor: pointer; transition: all 0.2s;
      box-shadow: 4px 4px 0 rgba(0,0,0,0.45);
      -webkit-tap-highlight-color: transparent;
    }
    .val-btn-dismiss:active { transform: translate(2px,2px); box-shadow: 1px 1px 0 rgba(0,0,0,0.55); }
    .val-btn-dismiss:hover  { background: rgba(255,255,255,0.09); color: #eef2ff; }

    /* ── Overlay en sem-hero ── */
    .sem-invalid-overlay {
      position: absolute; top: 12px; left: 12px; right: 12px;
      z-index: 5; pointer-events: none;
    }
    .sem-invalid-badge {
      display: inline-flex; align-items: center; gap: 7px;
      background: rgba(239,68,68,0.15);
      border: 1px solid rgba(239,68,68,0.35);
      border-radius: 8px; padding: 6px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px; font-weight: 600;
      color: var(--s-cri, #ef4444);
      letter-spacing: 0.04em;
      box-shadow: 2px 2px 0 rgba(0,0,0,0.45);
    }

    /* ── sem-hero relative para el overlay ── */
    .sem-hero { position: relative !important; }
  `;
  document.head.appendChild(style);

})();
