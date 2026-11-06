"""
HBA-HRV · report/references.py
Catálogo de indicadores y referencias del informe.

PRINCIPIOS
- Aquí NO se calcula nada: solo se describe cómo presentar e interpretar valores que ya calculó hrv_core.
- Las bandas (band) replican exactamente las que usa hrv_core.enrich_dashboard (_hml). Son UMBRALES OPERATIVOS
  DEL PROTOCOLO HBA, no normas poblacionales publicadas. El informe los rotula así.
- El RMSSD usa la tabla edad/sexo de hrv_core.rmssd_reference (misma fuente que la app).
- No hay un rango universal: la literatura muestra amplia variabilidad interindividual y dependencia de la
  duración, la postura, el momento del día y el método de medición.
- Indicadores sin banda definida en el protocolo (pNN50, potencias, lnRMSSD, SD1/SD2, Mean RR) se muestran
  SIN clasificación por color.

COLOR (criterio del informe)
- verde  : valor dentro de la banda de referencia del indicador.
- ámbar  : valor fuera de la banda hacia el lado que, según el protocolo, requiere atención contextual.
- celeste: valor fuera de la banda hacia el lado opuesto (informativo; no se califica como bueno ni malo).
- rojo   : SOLO alertas técnicas de validez de la señal (mismos umbrales que hrv_validator.js).
- azul   : valores sin referencia (se muestran sin clasificar).
"""

# ── Métodos de medición ─────────────────────────────────────────────────────────────────────────────────────
SENSOR_LABEL = {
    "camera_ppg": "Cámara PPG (dedo)",
    "face_rppg": "Face rPPG (rostro)",
    "vibration_scg": "Vibración SCG",
    "polar_h10": "Polar H10 (banda de pecho)",
    "rr_upload": "Importación de archivo RR",
}

# confianza metodológica general del método (no del valor puntual)
SENSOR_CONFIDENCE = {
    "polar_h10": ("alta", "Registra intervalos RR directamente con una banda de pecho."),
    "rr_upload": ("alta", "Analiza intervalos RR importados; la calidad depende del equipo que los originó."),
    "camera_ppg": ("moderada", "Estima el pulso con la cámara; es sensible al movimiento y a la presión del dedo."),
    "face_rppg": ("exploratoria", "Método experimental sin contacto; es muy sensible a la luz y al movimiento."),
    "vibration_scg": ("exploratoria", "Método experimental con acelerómetro; es sensible al movimiento y a la postura."),
}

# ── Umbrales técnicos de validez (espejo de static/js/hrv_validator.js) ────────────────────────────────────
VALIDITY = {
    "rmssd": {"floor_hard": 2, "floor_warn": 4, "ceil_warn": 300, "ceil_hard": 500},
    "hr": {"floor_hard": 25, "floor_warn": 35, "ceil_warn": 200, "ceil_hard": 250},
    "artifacts": {"warn": 15, "bad": 30, "hard": 60},
    "quality": {"warn": 45, "bad": 25},
}

# ── Indicadores ─────────────────────────────────────────────────────────────────────────────────────────────
# band: (bajo, alto) del protocolo HBA | attn: lado que requiere atención contextual ("low"/"high"/None)
# min_min: duración mínima preferible (min) para interpretar con solidez
INDICATORS = {
    "hr_mean": dict(
        name="Frecuencia cardíaca media", short="FC media", unit="bpm", dec=0, band=(60, 85), attn="high", min_min=1,
        measures="Número promedio de latidos por minuto durante el registro.",
        meaning={
            "in": "Se ubica dentro de la banda de referencia del protocolo ({band}).",
            "low": "Es inferior a 60 bpm. Puede ser habitual en personas con buen acondicionamiento físico; se interpreta junto con el contexto y los síntomas.",
            "high": "Supera 85 bpm. Puede asociarse a activación, estrés, cafeína, movimiento previo, calor o fatiga; conviene repetir en reposo.",
        },
        follow="Medir siempre en reposo y a la misma hora para que los valores sean comparables.",
    ),
    "rmssd": dict(
        name="RMSSD", short="RMSSD", unit="ms", dec=1, band="age_sex", attn="low", min_min=1,
        measures="Variabilidad entre latidos consecutivos; refleja principalmente la actividad vagal (parasimpática).",
        meaning={
            "in": "Se ubica dentro de la referencia del protocolo para su edad y sexo ({band}).",
            "low": "Se ubica por debajo de la referencia para su edad y sexo ({band}). Puede relacionarse con estrés, fatiga, sueño insuficiente o descondicionamiento, entre otros factores; no constituye un diagnóstico.",
            "high": "Se ubica por encima de la referencia para su edad y sexo ({band}). Valores muy altos conviene confirmarlos, porque los artefactos de señal pueden elevar el RMSSD.",
        },
        follow="Es el indicador principal para el seguimiento: interesa su tendencia en varias mediciones más que un valor aislado.",
    ),
    "lnrmssd": dict(
        name="lnRMSSD", short="lnRMSSD", unit="", dec=2, band=None, attn=None, min_min=1,
        measures="Logaritmo natural del RMSSD; es una versión estadísticamente más estable para comparar mediciones.",
        meaning={"none": "El protocolo no lo clasifica por rangos; es útil para comparar mediciones entre sí a lo largo del tiempo."},
        follow="Útil para graficar la evolución, porque amortigua los valores extremos.",
    ),
    "sdnn": dict(
        name="SDNN", short="SDNN", unit="ms", dec=1, band=(30, 60), attn="low", min_min=3,
        measures="Variabilidad global del ritmo cardíaco; integra la acción de ambas ramas del sistema nervioso autónomo.",
        meaning={
            "in": "Se ubica dentro de la banda de referencia del protocolo ({band}).",
            "low": "Es inferior a 30 ms: variabilidad global reducida para un registro corto. Se interpreta junto con el RMSSD y el contexto.",
            "high": "Supera 60 ms: variabilidad global amplia para un registro corto. Es informativo; conviene confirmar que no haya artefactos.",
        },
        follow="En registros cortos depende de la duración: comparar solo mediciones de igual duración.",
    ),
    "mean_rr": dict(
        name="Intervalo RR medio", short="RR medio", unit="ms", dec=0, band=None, attn=None, min_min=1,
        measures="Duración promedio del intervalo entre latidos; es el inverso de la frecuencia cardíaca.",
        meaning={"none": "No tiene banda propia: se lee junto con la frecuencia cardíaca."},
        follow="Se interpreta a través de la frecuencia cardíaca.",
    ),
    "pnn50": dict(
        name="pNN50", short="pNN50", unit="%", dec=1, band=None, attn=None, min_min=1,
        measures="Porcentaje de pares de latidos consecutivos que difieren en más de 50 ms; refleja actividad vagal.",
        meaning={"none": "El protocolo HBA no define una banda para este indicador; se muestra sin clasificar y es útil para seguir su tendencia."},
        follow="Acompaña al RMSSD: ambos reflejan modulación vagal.",
    ),
    "hf_share": dict(
        name="Reparto de potencia HF / LF", short="HF relativo", unit="%", dec=0, band=None, attn=None, min_min=5,
        measures="Porcentaje de la potencia espectral (HF + LF) que corresponde a la banda HF, asociada a la actividad vagal y a la respiración.",
        meaning={"none": "No tiene banda en el protocolo. Es un reparto relativo: se muestra así porque no se publican potencias absolutas. Su lectura aislada es limitada."},
        follow="Requiere registros de unos 5 minutos para análisis espectral confiable.",
    ),
    "lf_hf": dict(
        name="Relación LF/HF", short="LF/HF", unit="", dec=2, band=(1.5, 3.0), attn="high", min_min=5,
        measures="Cociente entre las potencias LF y HF; se usa como indicador orientativo del balance autonómico.",
        meaning={
            "in": "Se ubica dentro de la banda de referencia del protocolo ({band}).",
            "low": "Es inferior a 1,5. Suele asociarse a mayor peso relativo de HF (relajación o respiración lenta). Es informativo.",
            "high": "Supera 3,0. Puede reflejar mayor activación o estrés, pero también influye la respiración y la postura; su valor aislado es limitado.",
        },
        follow="Solo es confiable con registros de 5 minutos o más; en registros más cortos es orientativo.",
    ),
    "sd1": dict(
        name="SD1 (Poincaré)", short="SD1", unit="ms", dec=1, band=(15, 40), attn="low", min_min=1,
        measures="Variabilidad de corto plazo en el diagrama de Poincaré; equivale matemáticamente a RMSSD dividido por la raíz de 2.",
        meaning={
            "in": "Se ubica dentro de la banda de referencia del protocolo ({band}).",
            "low": "Es inferior a 15 ms, en línea con una variabilidad latido a latido reducida (guarda relación directa con el RMSSD).",
            "high": "Supera 40 ms; guarda relación directa con el RMSSD y se interpreta con él.",
        },
        follow="Se interpreta junto con el RMSSD, del cual deriva.",
    ),
    "sd2": dict(
        name="SD2 (Poincaré)", short="SD2", unit="ms", dec=1, band=(30, 70), attn="low", min_min=3,
        measures="Variabilidad de largo plazo en el diagrama de Poincaré.",
        meaning={
            "in": "Se ubica dentro de la banda de referencia del protocolo ({band}).",
            "low": "Es inferior a 30 ms: variabilidad de largo plazo reducida para un registro corto.",
            "high": "Supera 70 ms: variabilidad de largo plazo amplia para un registro corto.",
        },
        follow="En registros cortos depende de la duración.",
    ),
    "sd1_sd2_ratio": dict(
        name="Relación SD1/SD2", short="SD1/SD2", unit="", dec=2, band=None, attn=None, min_min=3,
        measures="Proporción entre la variabilidad de corto y de largo plazo.",
        meaning={"none": "El protocolo la usa como contexto: valores menores a 0,5 se asocian a predominio de la variabilidad de largo plazo. No se clasifica por color."},
        follow="Se interpreta junto con SD1 y SD2.",
    ),
    "dfa_alpha1": dict(
        name="DFA alfa-1", short="DFA alfa-1", unit="", dec=2, band=(0.75, 1.5), attn="low", min_min=3,
        measures="Correlaciones fractales de corto plazo del ritmo cardíaco; describe la complejidad de la regulación autonómica.",
        meaning={
            "in": "Se ubica dentro de la banda de referencia del protocolo ({band}).",
            "low": "Es inferior a 0,75. El protocolo lo asocia a menor complejidad de la regulación y a fatiga acumulada; es una pista y requiere contexto.",
            "high": "Supera 1,5. Es informativo; conviene confirmar que no haya artefactos ni errores de detección de latidos.",
        },
        follow="Es sensible a la calidad de la señal: interpretar solo con registros limpios.",
    ),
    "baevsky": dict(
        name="Índice de tensión (Baevsky)", short="Baevsky", unit="", dec=0, band=(50, 150), attn="high", min_min=3,
        measures="Índice de tensión del sistema regulatorio autonómico: valores mayores indican mayor esfuerzo regulatorio.",
        meaning={
            "in": "Se ubica dentro de la banda de referencia del protocolo ({band}).",
            "low": "Es inferior a 50, en línea con una regulación poco exigida. Es informativo.",
            "high": "Supera 150: indica mayor tensión regulatoria en esta medición. Se interpreta con el contexto (estrés, sueño, esfuerzo previo).",
        },
        follow="Disponible solo con métodos que entregan intervalos RR (Polar H10, archivo RR).",
    ),
    "resp_rate_rpm": dict(
        name="Frecuencia respiratoria estimada", short="Resp.", unit="rpm", dec=1, band=None, attn=None, min_min=1,
        measures="Respiraciones por minuto estimadas a partir de la señal.",
        meaning={"none": "Es una estimación derivada de la señal; no reemplaza una medición directa."},
        follow="Útil para interpretar la potencia HF.",
    ),
}

# orden de presentación en la página de resultados
ORDER = ["hr_mean", "rmssd", "lnrmssd", "sdnn", "mean_rr", "pnn50", "hf_share", "lf_hf",
         "sd1", "sd2", "sd1_sd2_ratio", "dfa_alpha1", "baevsky", "resp_rate_rpm"]

# indicadores para el resumen visual de portada (en orden de prioridad)
COVER_KPI = ["rmssd", "hr_mean", "sdnn", "lf_hf", "pnn50", "lnrmssd", "sd1"]

# cargas compuestas del protocolo HBA (no son una norma publicada)
CARGAS = [("carga_autonomica", "Carga autonómica"), ("carga_emocional", "Carga emocional"),
          ("carga_fisica", "Carga física"), ("estres", "Estrés")]

# ── Lecturas de referencia (generales; el informe no cita cifras de ellas) ─────────────────────────────────
SOURCES = [
    "Task Force of the ESC and NASPE (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use. Circulation, 93(5), 1043-1065.",
    "Shaffer, F. & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. Frontiers in Public Health, 5, 258.",
    "Laborde, S., Mosley, E. & Thayer, J. F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research. Frontiers in Psychology, 8, 213.",
]

DISCLAIMER = ("Este informe presenta resultados de mediciones fisiológicas y orientación general de seguimiento. "
              "No constituye un diagnóstico médico ni reemplaza una evaluación profesional. Los indicadores HRV deben "
              "interpretarse considerando el contexto individual, las condiciones de medición y las limitaciones del método utilizado.")
