# HANNA·HRV

Plataforma web para medir y analizar variabilidad del ritmo cardíaco (HRV).
Backend Flask + NeuroKit2, frontend JS plano (sin build), despliegue en Vercel, historial en Supabase.

## Flujo de uso
1. **Paciente** → ID (obligatorio), edad y sexo (ajustan el rango de referencia del RMSSD).
2. **Método** → Cámara PPG · Face rPPG · Vibración SCG · Polar H10 · Importar RR (CSV/JSON).
3. **Preparación** → indicaciones concretas del método y duración.
4. **Medición** → temporizador, estado de conexión, señal en vivo, detener/repetir.
5. **Resultados** → indicadores, interpretación y recomendaciones (separados).
6. **Historial** → evolución, filtro por período y comparación de dos sesiones.

## Informe PDF (acceso protegido)
Desde **Resultados** (botón *Generar informe PDF*) o desde cada sesión del **Historial** se genera un informe HANNA de
7 páginas A4, cada una con una pregunta: ¿Cómo estoy hoy? · ¿Qué mide cada cosa y dónde estoy? · Mapa RMSSD × FC ·
¿De dónde salió el número? · Estrés y cargas · ¿Qué hago? · ¿Cómo vengo?

Los gráficos (mapa 3×3, latidos con zonas de FC, señal con picos o tren de latidos, histograma, Poincaré, mapa de cargas,
evolución) salen solo de datos reales. Si un dato falta, la sección lo declara. El backend devuelve ahora dos campos
adicionales en `/api/compute` (`nn_ms` y `ppg_view`); no cambian ningún cálculo. Los informes de sesiones guardadas no
incluyen los gráficos de latidos (el historial no guarda la serie).

**Acceso:** solo con contraseña, validada **en el servidor** (`POST /api/report`, cabecera `X-Report-Key`).
1. En Vercel → *Settings → Environment Variables* creá **`REPORT_PASSWORD`** con la clave que quieras.
2. Redeploy. Sin esa variable el informe queda **deshabilitado** (seguro por defecto).
3. La app pide la clave al generar; se conserva solo en memoria hasta recargar la página.

Privacidad: el PDF se genera en memoria y se entrega al navegador; no se guarda en disco ni en servicios externos.
Los informes anteriores no se almacenan: se regeneran desde la sesión guardada en el historial.

Para cobrar un arancel en lugar de (o además de) la contraseña, basta reemplazar la función `authorize()` de
`hba_report/routes.py` (por ejemplo, verificando un pago o un token). El resto del módulo no cambia.

Límites conocidos: el bloqueo por intentos fallidos es de mejor esfuerzo (en Vercel cada instancia tiene su propia
memoria); usá una contraseña larga. Las demás rutas (`/api/compute`, `/api/save`, `/api/history`) mantienen su
comportamiento original y no están protegidas.

## Ejecutar en local
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                                          # http://127.0.0.1:5000
```
La cámara, el Bluetooth y el acelerómetro del navegador solo funcionan en **https** o en `localhost`.

## Desplegar en Vercel
1. Subí esta carpeta a un repositorio (o usá `vercel` desde la carpeta).
2. En *Project → Settings → Environment Variables* definí (solo si querés guardar/consultar historial):
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
3. Deploy. `vercel.json` y `requirements.txt` no cambiaron.

Sin esas variables la app mide y calcula con normalidad; guardar e historial muestran un aviso claro.

## Estructura
```
app.py                  rutas Flask: /, /api/compute, /api/save, /api/history
api/hrv_core.py         algoritmos HRV (sin cambios de fórmulas)
api/report.py           función Vercel del informe (delgada)
hba_report/             módulo del informe: references.py (referencias), engine.py (interpretación),
                        story.py (textos y datos de cada gráfico), draw.py (gráficos vectoriales),
                        pdf.py (maquetación de las 7 páginas), routes.py (acceso)
tests/test_report.py    pruebas: python -m unittest discover -s tests -v
index.html              marcado de la app
static/css/style.css    sistema de diseño responsive (tokens, componentes, breakpoints)
static/js/core.js       estado, utilidades, diálogos, contenido de cada método
static/js/sensors.js    cámara, vibración, Polar H10, importación RR, señal en vivo
static/js/results.js    resultados / interpretación / recomendaciones
static/js/history.js    historial, gráficos, comparación
static/js/main.js       navegación, flujo guiado, sesión de medición, API
static/js/hrv_validator.js  validación fisiológica (umbrales originales)
static/vendor|fonts|icons   Chart.js, tipografías e íconos locales (sin CDNs)
```

## Licencias
Tipografías Sora y Figtree (SIL Open Font License) incrustadas en el PDF. Chart.js (MIT). Íconos Lucide (ISC).

## Aviso
La medición HRV es una herramienta de monitoreo y no constituye un diagnóstico médico.
