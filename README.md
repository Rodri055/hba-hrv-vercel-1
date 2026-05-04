# HBA v2.0 — Deploy en Vercel (gratis, sin cortes)


## Estructura del proyecto

```
hba-vercel/
├── api/
│   ├── hrv_core.py      ← lógica HRV compartida
│   ├── compute.py       ← POST /api/compute
│   ├── save.py          ← POST /api/save
│   └── history.py       ← GET  /api/history
├── public/
│   ├── index.html
│   ├── css/style.css
│   └── js/main.js
├── requirements.txt
└── vercel.json
```

---

## Deploy paso a paso (5 minutos)

### 1. Subir a GitHub

```bash
cd hba-vercel
git init
git add .
git commit -m "HBA v2.0 — Vercel serverless"
git remote add origin https://github.com/TU_USUARIO/hba.git
git push -u origin main
```

### 2. Importar en Vercel

1. Entrá a **vercel.com** → Log in con GitHub
2. Click **"Add New Project"**
3. Elegí tu repo `hba`
4. Vercel detecta el `vercel.json` automáticamente
5. Click **Deploy**

### 3. Variables de entorno (Supabase)

En Vercel → tu proyecto → **Settings → Environment Variables**:

```
SUPABASE_URL       = https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY  = eyJxxxx...
```

Después de agregar las variables → **Redeploy** (un click).

### 4. Listo

- URL gratuita: `https://hba-xxxx.vercel.app`
- HTTPS incluido ✓ (necesario para Polar H10 BLE y cámara)
- Sin sleep, sin cortes, sin límite de tiempo ✓
- Funciones serverless: se despiertan en < 1 seg ✓

---

## Supabase — crear tabla

1. Crear cuenta en supabase.com
2. Nuevo proyecto → anotar URL y anon key
3. SQL Editor → pegar y ejecutar:

```sql
create table if not exists hba_sessions (
  id                bigserial primary key,
  timestamp_utc     timestamptz default now(),
  patient_id        text,
  age               numeric,
  sex               char(1),
  comorbidities     text,
  notes             text,
  sensor_type       text,
  duration_minutes  numeric,
  rmssd             numeric,
  rmssd_corr        numeric,
  sdnn              numeric,
  lnrmssd           numeric,
  pnn50             numeric,
  mean_rr           numeric,
  lf_power          numeric,
  hf_power          numeric,
  lf_hf             numeric,
  total_power       numeric,
  sd1               numeric,
  sd2               numeric,
  sd1_sd2_ratio     numeric,
  dfa_alpha1        numeric,
  artifact_percent  numeric,
  quality_score     numeric,
  hr_mean           numeric,
  hr_max            numeric,
  hr_min            numeric,
  resp_rate_rpm     numeric,
  carga_autonomica  numeric,
  carga_emocional   numeric,
  carga_fisica      numeric,
  estres            numeric,
  semaphore_key     text,
  semaphore_label   text,
  freq_warning      text
);

create index if not exists idx_hba_patient on hba_sessions(patient_id);
create index if not exists idx_hba_ts      on hba_sessions(timestamp_utc desc);
alter table hba_sessions enable row level security;
create policy "public_access" on hba_sessions for all using (true) with check (true);
```

---

## Límites del free tier de Vercel

| Recurso | Límite free | HBA necesita |
|---------|-------------|--------------|
| Funciones serverless | 100 GB-hours/mes | ~0.5 GB-hours/mes ✓ |
| Tiempo por función | 10 seg (hobby) | ~3–5 seg ✓ |
| Ancho de banda | 100 GB/mes | < 1 GB/mes ✓ |
| Proyectos | Ilimitados | 1 ✓ |
| Dominios HTTPS | Ilimitados | 1 ✓ |

**Importante:** Las funciones en Vercel tienen un tiempo máximo de ejecución de 10 segundos
en el plan gratuito. El cálculo HRV con NeuroKit2 puede tardar 3–6 segundos en señales largas.
Si ves timeout, reducí la señal o migrá a Railway Hobby ($5/mes, sin límite de tiempo).

---

## Desarrollo local

```bash
npm install -g vercel    # instalar CLI de Vercel (una sola vez)
pip install -r requirements.txt
vercel dev               # corre el proyecto localmente en http://localhost:3000
```

Con `vercel dev` tenés hot-reload y las funciones serverless funcionan igual que en producción.
