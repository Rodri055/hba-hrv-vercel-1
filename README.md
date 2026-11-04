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

## Aviso
La medición HRV es una herramienta de monitoreo y no constituye un diagnóstico médico.
