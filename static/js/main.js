"use strict";
const PPG_SR=30,SCG_SR=50,WIN=300,FPS=10;
const G={sensor:"camera_ppg",durationMin:3,totalSec:180,running:false,ppgBuf:[],rrBuf:[],sigBuf:[],elapsed:0,lastMetrics:null,timerH:null,rafH:null,chartLast:0,bleDevice:null,stream:null,frameCtx:null,motionH:null};
const $=id=>document.getElementById(id);

function showScreen(id){document.querySelectorAll(".screen").forEach(s=>s.classList.remove("active"));$(id).classList.add("active");window.scrollTo(0,0);}
$("btnBack").addEventListener("click",()=>showScreen("screenSensor"));

// Chart
let chart=null;
function buildChart(){
  chart=new Chart($("signalChart").getContext("2d"),{type:"line",data:{labels:Array(WIN).fill(""),datasets:[{data:Array(WIN).fill(null),borderColor:"#00d4aa",borderWidth:1.5,pointRadius:0,fill:true,backgroundColor:"rgba(0,212,170,0.05)",tension:0.3}]},options:{animation:false,responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{display:false},y:{display:false,grace:"20%"}}}});
}
function pushSig(v){G.sigBuf.push(v);if(G.sigBuf.length>WIN*3)G.sigBuf.shift();}
function renderChart(now){G.rafH=requestAnimationFrame(renderChart);if(!G.running||now-G.chartLast<1000/FPS)return;G.chartLast=now;const buf=G.sigBuf;const data=buf.length>=WIN?buf.slice(-WIN):[...Array(WIN-buf.length).fill(null),...buf];chart.data.datasets[0].data=data;chart.update("none");}

// Timer
function startTimer(){G.elapsed=0;G.timerH=setInterval(()=>{G.elapsed++;const m=String(Math.floor(G.elapsed/60)).padStart(2,"0"),s=String(G.elapsed%60).padStart(2,"0");$("chipTimer").textContent=`${m}:${s}`;if(G.elapsed>=G.totalSec)stopSession(true);},1000);}
function stopTimer(){if(G.timerH){clearInterval(G.timerH);G.timerH=null;}}

// Countdown
function countdown(title,text,hint,secs){return new Promise(resolve=>{const o=$("countdownOverlay");$("cdTitle").textContent=title;$("cdText").textContent=text;$("cdHint").textContent=hint;o.style.display="flex";let n=secs;$("cdN").textContent=n;const iv=setInterval(()=>{n--;if(n<=0){clearInterval(iv);o.style.display="none";resolve();}else $("cdN").textContent=n;},1000);});}

// Status
function setStatus(text,cls=""){$("statusText").textContent=text;const d=$("statusDot");d.className="pill-dot"+(cls?" "+cls:"");}
function setQuality(q){const fill=$("qualityFill"),txt=$("qualityText");if(q==null){fill.style.width="0%";txt.textContent="—";return;}fill.style.width=`${q}%`;txt.textContent=`${Math.round(q)}%`;fill.style.background=q>=70?"var(--s-opt)":q>=40?"var(--s-com)":"var(--s-cri)";}
function setBtns(running){$("btnStart").disabled=running;$("btnStop").disabled=!running;$("btnSave").disabled=running||!G.lastMetrics;$("btnSave2").disabled=!G.lastMetrics;}

// Sensor meta
const SENSOR_META={
  camera_ppg:{label:"Cámara PPG",dur1:false,torch:true,camera:true,guide:"Apoyá el codo en la mesa. Cubrí completamente el lente y el flash con el dedo índice. Respirá con normalidad."},
  face_rppg:{label:"rPPG Facial",dur1:true,torch:false,camera:true,guide:"Sentate frente a la cámara con luz uniforme y estable. No te muevas durante el test."},
  vibration_scg:{label:"SCG Vibración",dur1:true,torch:false,camera:false,guide:"Acostáte boca arriba. Colocá el celular centrado sobre el esternón. Otorgá permiso de movimiento."},
  polar_h10:{label:"Polar H10",dur1:true,torch:false,camera:false,guide:"Ajustá la cinta Polar H10 y aceptá el permiso Bluetooth cuando aparezca."},
  rr_upload:{label:"RR Import",dur1:true,torch:false,camera:false,guide:"Cargá el archivo exportado desde Polar App, Kubios, Garmin u otro sistema HRV."},
};

document.querySelectorAll(".sensor-card").forEach(card=>{
  card.addEventListener("click",()=>{
    document.querySelectorAll(".sensor-card").forEach(c=>c.classList.remove("active"));
    card.classList.add("active"); G.sensor=card.dataset.sensor;
    const m=SENSOR_META[G.sensor];
    $("mediaTitle").textContent=m.label;
    $("guideBox").textContent=m.guide;
    $("cameraCard").style.display=m.camera?"":"none";
    $("torchWrap").style.display=m.torch?"":"none";
    $("rrUploadWrap").style.display=G.sensor==="rr_upload"?"":"none";
    $("dur1").style.display=m.dur1?"":"none";
    if(!m.dur1&&G.durationMin===1)$("dur3").click();
  });
});

document.querySelectorAll(".dur-btn").forEach(btn=>{
  btn.addEventListener("click",()=>{
    document.querySelectorAll(".dur-btn").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active"); G.durationMin=parseInt(btn.dataset.min); G.totalSec=G.durationMin*60;
  });
});

// Cámara
async function startCamera(){
  const isFace=G.sensor==="face_rppg";
  G.stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:isFace?"user":"environment",width:{ideal:160},height:{ideal:120},frameRate:{ideal:PPG_SR}}});
  const vid=$("video"); vid.srcObject=G.stream; await vid.play();
  if(!isFace&&$("torchToggle").checked){try{await G.stream.getVideoTracks()[0].applyConstraints({advanced:[{torch:true}]});}catch(_){}}
  const canvas=$("frameCanvas"); canvas.width=4; canvas.height=4;
  G.frameCtx=canvas.getContext("2d",{willReadFrequently:true});
  let last=0; const interval=1000/PPG_SR;
  function capture(ts){if(!G.running)return;if(ts-last>=interval){last=ts;G.frameCtx.drawImage(vid,0,0,4,4);const px=G.frameCtx.getImageData(0,0,4,4).data;let val=0;if(isFace){for(let i=1;i<px.length;i+=4)val+=px[i];}else{for(let i=0;i<px.length;i+=4)val+=px[i];}val/=(px.length/4);G.ppgBuf.push(val);pushSig(val);}requestAnimationFrame(capture);}
  requestAnimationFrame(capture);
}
function stopCamera(){if(G.stream){G.stream.getTracks().forEach(t=>{try{t.applyConstraints({advanced:[{torch:false}]});}catch(_){}t.stop();});G.stream=null;}const vid=$("video");if(vid)vid.srcObject=null;}

// Vibración
function startVibration(){
  if(!window.DeviceMotionEvent)throw new Error("No DeviceMotionEvent");
  const bind=()=>{G.motionH=e=>{if(!G.running)return;const a=e.accelerationIncludingGravity;if(!a)return;const mag=Math.sqrt((a.x||0)**2+(a.y||0)**2+(a.z||0)**2);G.ppgBuf.push(mag);pushSig(mag);};window.addEventListener("devicemotion",G.motionH,{passive:true});};
  if(typeof DeviceMotionEvent.requestPermission==="function"){DeviceMotionEvent.requestPermission().then(s=>{if(s==="granted")bind();});}else bind();
}
function stopVibration(){if(G.motionH){window.removeEventListener("devicemotion",G.motionH);G.motionH=null;}}

// Polar H10
const HR_SVC="0000180d-0000-1000-8000-00805f9b34fb",HR_CHAR="00002a37-0000-1000-8000-00805f9b34fb";
async function startPolarH10(){
  if(!navigator.bluetooth)throw new Error("Web Bluetooth no disponible. Usá Chrome/Edge.");
  setStatus("Buscando Polar…","warn");
  G.bleDevice=await navigator.bluetooth.requestDevice({filters:[{namePrefix:"Polar"}],optionalServices:[HR_SVC]});
  const server=await G.bleDevice.gatt.connect();
  const svc=await server.getPrimaryService(HR_SVC);
  const ch=await svc.getCharacteristic(HR_CHAR);
  ch.addEventListener("characteristicvaluechanged",e=>{
    if(!G.running)return;
    const dv=e.target.value,flags=dv.getUint8(0),hasRR=(flags>>4)&0x01;
    let offset=(flags&0x01)?3:2;
    const hr=(flags&0x01)?dv.getUint16(1,true):dv.getUint8(1);
    pushSig(hr);
    if(hasRR){while(offset+1<dv.byteLength){const rr=dv.getUint16(offset,true)/1024.0*1000.0;offset+=2;if(rr>300&&rr<2200){G.rrBuf.push(rr);pushSig(rr);}}}
  });
  await ch.startNotifications(); setStatus("Polar conectado","live");
}
function stopPolarH10(){try{if(G.bleDevice?.gatt?.connected)G.bleDevice.gatt.disconnect();}catch(_){}G.bleDevice=null;}

// RR upload
async function loadRRFile(){
  const file=$("rrFile").files[0]; if(!file)throw new Error("Sin archivo");
  const text=await file.text(); let rrs=[];
  if(file.name.toLowerCase().endsWith(".json")){const obj=JSON.parse(text);rrs=Array.isArray(obj)?obj:(obj.rri_ms||obj.rr||Object.values(obj).flat());rrs=rrs.map(Number);}
  else{const lines=text.trim().split(/\r?\n/);const header=lines[0].toLowerCase().split(/[,;\t]/);let col=["rr","rri","rri_ms","nn","ibi"].reduce((a,k)=>a>=0?a:header.indexOf(k),-1);if(col<0)col=0;for(let i=1;i<lines.length;i++){const v=parseFloat(lines[i].split(/[,;\t]/)[col]);if(!isNaN(v))rrs.push(v);}}
  const mean=rrs.reduce((a,b)=>a+b,0)/rrs.length;
  if(mean<5)rrs=rrs.map(r=>r*1000);
  rrs=rrs.filter(r=>r>200&&r<2500);
  if(rrs.length<12)throw new Error(`Solo ${rrs.length} RR válidos.`);
  G.rrBuf=rrs; rrs.forEach(r=>pushSig(r));
  $("rrFileLabel").textContent=`✓ ${file.name} (${rrs.length} RR)`;
}

// Sesión
$("btnStart").addEventListener("click",startSession);
$("btnStop").addEventListener("click",()=>stopSession(false));
$("btnSave").addEventListener("click",saveSession);
$("btnSave2").addEventListener("click",saveSession);
$("rrFile").addEventListener("change",async()=>{try{await loadRRFile();setStatus(`RR cargado (${G.rrBuf.length})`,"live");}catch(e){alert(e.message);}});

async function startSession(){
  G.ppgBuf=[];G.rrBuf=[];G.sigBuf=[];G.lastMetrics=null;G.totalSec=G.durationMin*60;
  setQuality(null);$("freqWarning").classList.remove("visible");
  try{
    if(G.sensor==="rr_upload"){if(!G.rrBuf.length){alert("Cargá un archivo RR primero.");return;}await countdown("Analizando…","Procesando intervalos RR importados.","",3);G.running=true;setBtns(true);setStatus("Analizando…","live");await computeAndDisplay();G.running=false;setBtns(false);return;}
    const meta=SENSOR_META[G.sensor];
    await countdown("Preparación",meta.guide,G.sensor==="polar_h10"?"Aceptá el permiso Bluetooth.":"No bloquees la pantalla.",5);
    G.running=true;setBtns(true);setStatus("Midiendo…","live");
    if(G.sensor==="polar_h10")await startPolarH10();
    if(G.sensor==="camera_ppg"||G.sensor==="face_rppg")await startCamera();
    if(G.sensor==="vibration_scg")startVibration();
    G.rafH=requestAnimationFrame(renderChart);startTimer();
  }catch(err){G.running=false;setBtns(false);setStatus("Error","err");alert(`Error: ${err.message}`);}
}

async function stopSession(auto=false){
  G.running=false;stopTimer();
  if(G.sensor==="camera_ppg"||G.sensor==="face_rppg")stopCamera();
  if(G.sensor==="polar_h10")stopPolarH10();
  if(G.sensor==="vibration_scg")stopVibration();
  setBtns(false);setStatus(auto?"Completado":"Detenido",auto?"live":"warn");
  if(auto||G.ppgBuf.length>=30||G.rrBuf.length>=12)await computeAndDisplay();
}

async function computeAndDisplay(){
  setStatus("Calculando HRV…","warn");
  const isRR=["polar_h10","rr_upload"].includes(G.sensor);
  const isSCG=G.sensor==="vibration_scg";
  const payload={sensor_type:G.sensor,duration_minutes:G.durationMin,age:$("age").value||null,sex:$("sex").value||null,patient_id:$("patientId").value||"",comorbidities:$("comorbidities").value||"",notes:$("notes").value||""};
  if(isRR){payload.rri_ms=G.rrBuf.length?G.rrBuf:G.ppgBuf;}
  else{payload.ppg=G.ppgBuf;payload.sampling_rate=isSCG?SCG_SR:PPG_SR;}
  try{
    const res=await fetch("/api/compute",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    const data=await res.json();
    if(data.error){setStatus("Error de cálculo","err");alert(`HRV Error: ${data.error}`);return;}
    G.lastMetrics={...data,...payload};setQuality(data.quality_score??null);setBtns(false);setStatus("Completado","live");
    if(data.freq_warning){$("freqWarning").textContent=`⚠ ${data.freq_warning}`;$("freqWarning").classList.add("visible");}
    renderDashboard(data);showScreen("screenResults");
  }catch(err){setStatus("Sin conexión","err");alert("No se pudo conectar con el servidor.");}
}

// Dashboard
function renderDashboard(data){
  const dash=data.hba_dashboard; if(!dash)return;
  renderSem(dash.semaphore,data);
  renderStressType(dash.stress_type,dash.stress_label,dash.recomendaciones?.nota_stress);
  renderCargas(dash.cargas);
  renderMetrics(data);
  renderBio(dash.biomarkers);
  renderPlan(dash.plan);
  renderRecs(dash.recomendaciones);
}

function renderSem(sem,data){
  const hero=$("semHero"); hero.className=`sem-hero ${sem.key}`;
  $("semIcon").textContent=sem.icon; $("semLabel").textContent=sem.label; $("semDesc").textContent=sem.description;
  const r=data.rmssd_corr??data.rmssd; $("semRmssdVal").textContent=r!=null?r.toFixed(1):"—";
  const norms=data.hba_dashboard?.norms;
  if(norms?.rmssd_low&&r!=null){
    const lo=norms.rmssd_low,hi=norms.rmssd_high;
    $("normLow").textContent=`${lo.toFixed(0)}ms`; $("normHigh").textContent=`${hi.toFixed(0)}ms`;
    let pct;
    if(r<=lo)pct=Math.max(2,(r/lo)*35);
    else if(r<=hi)pct=35+((r-lo)/(hi-lo))*30;
    else pct=Math.min(98,65+((r-hi)/(hi*0.5))*33);
    $("normMarker").style.left=`${pct}%`; $("normBarWrap").style.display="";
  }
}

function renderStressType(stress_type,stress_label,nota){
  const el=$("stressTypeWrap"); if(!el)return;
  if(!stress_type||stress_type==="indeterminado"){el.style.display="none";return;}
  el.style.display="";
  const colors={fisico:"var(--s-com)",fisico_leve:"var(--s-com)",emocional:"var(--s-fun)",emocional_leve:"var(--s-fun)",equilibrado:"var(--s-opt)",indeterminado:"var(--text-3)"};
  el.innerHTML=`
    <div class="stress-badge" style="border-color:${colors[stress_type]||"var(--text-3)"}">
      <div class="stress-label" style="color:${colors[stress_type]||"var(--text-3)"}">${stress_label||"—"}</div>
      ${nota?`<div class="stress-nota">${nota}</div>`:""}
    </div>`;
}

function renderCargas(cargas){
  if(!cargas)return;
  const items=[{key:"carga_autonomica",label:"Autonómica"},{key:"carga_emocional",label:"Emocional"},{key:"carga_fisica",label:"Física"},{key:"estres",label:"Estrés"}];
  const cls={bajo:"low",moderado:"mod",alto:"high","muy alto":"vhigh"};
  $("cargasGrid").innerHTML=items.map(it=>{const c=cargas[it.key]||{};const v=c.value!=null?Math.round(c.value):null;const lvl=c.level||"bajo";const cl=cls[lvl]||"low";return`<div class="carga-card ${cl}" style="--pct:${v??0}%"><div class="carga-name">${it.label}</div><div class="carga-val">${v??"—"}</div><div class="carga-level">${lvl}</div></div>`;}).join("");
}

function renderMetrics(data){
  const f=(v,d=1)=>(v!=null&&isFinite(v))?(+v).toFixed(d):"—";
  const art=data.artifact_percent;
  const artCls=art==null?"":art<10?"ok":art<25?"warn":"bad";
  const items=[
    {k:"FC media",v:f(data.hr_mean,0),u:"bpm",c:""},
    {k:"FC máx",v:f(data.hr_max,0),u:"bpm",c:""},
    {k:"RMSSD",v:f(data.rmssd,1),u:"ms",c:""},
    {k:"RMSSD*",v:f(data.rmssd_corr,1),u:"ms",c:""},
    {k:"SDNN",v:f(data.sdnn,1),u:"ms",c:""},
    {k:"lnRMSSD",v:f(data.lnrmssd,2),u:"",c:""},
    {k:"DFA α1",v:f(data.dfa_alpha1,2),u:"",c:""},
    {k:"Calidad",v:f(data.quality_score,0),u:"%",c:""},
    {k:"Artefactos",v:f(art,1),u:"%",c:artCls},
  ];
  $("metricsGrid").innerHTML=items.map(i=>`<div class="metric-card ${i.c}"><div class="metric-key">${i.k}</div><div class="metric-val">${i.v}</div><div class="metric-unit">${i.u}</div></div>`).join("");
}

function renderBio(biomarkers){
  if(!biomarkers?.length)return;
  const f=v=>(v!=null&&isFinite(v))?(+v).toFixed(2):"—";
  const stLbl={alto:"Alto",medio:"Normal",bajo:"Bajo",informativo:"—",insuficiente:"N/D"};
  $("bioTableWrap").innerHTML=`
    <table class="bio-table">
      <thead><tr><th>Biomarcador</th><th>Valor</th><th>Estado</th><th>Qué mide</th></tr></thead>
      <tbody>${biomarkers.map(b=>{
        const info=b.info||{};
        const tooltip=info.que_mide||b.detail||"";
        return`<tr>
          <td>
            <div class="bio-name">${b.name}</div>
            ${b.info?`<div class="bio-protocol">${info.protocolo||""}</div>`:""}
          </td>
          <td class="bio-val">${f(b.value)} <span class="bio-unit">${b.unit||""}</span></td>
          <td><span class="state-chip ${b.state||"informativo"}">${stLbl[b.state]||b.state}</span></td>
          <td class="bio-detail">${tooltip}</td>
        </tr>`;
      }).join("")}</tbody>
    </table>`;
}

function renderPlan(plan){
  if(!plan?.length)return;
  $("planList").innerHTML=`<div class="plan-list">${plan.map(p=>`<div class="plan-item"><span class="plan-text">${p.item}</span><div class="plan-bar-wrap"><div class="plan-bar"><div class="plan-fill" style="width:${p.pct}%"></div></div><span class="plan-pct">${p.pct}%</span></div></div>`).join("")}</div>`;
}

function renderRecs(recs){
  const el=$("recsWrap"); if(!el||!recs)return;
  const sections=[
    {key:"descanso",icon:"🌙",label:"Descanso"},
    {key:"nutricion",icon:"🥗",label:"Nutrición"},
    {key:"meditacion",icon:"🧘",label:"Meditación y respiración"},
    {key:"actividad",icon:"🏃",label:"Actividad física"},
    {key:"stretching",icon:"🤸",label:"Stretching miofascial"},
    {key:"musica",icon:"🎵",label:"Musicoterapia"},
  ];
  el.innerHTML=sections.map(sec=>{
    const r=recs[sec.key]; if(!r)return"";
    let body="";
    if(sec.key==="descanso"){
      body=`<div class="rec-detail">${r.horas?" <strong>Objetivo: "+r.horas+"</strong><br>":""}</div>`;
      if(r.tips?.length)body+=`<ul class="rec-list">${r.tips.map(t=>`<li>${t}</li>`).join("")}</ul>`;
    }else if(sec.key==="nutricion"){
      if(r.descripcion)body+=`<p class="rec-desc">${r.descripcion}</p>`;
      if(r.suplementos?.length)body+=`<div class="rec-subtitle">Suplementos</div><ul class="rec-list">${r.suplementos.map(s=>`<li>${s}</li>`).join("")}</ul>`;
      if(r.alimentos?.length)body+=`<div class="rec-subtitle">Alimentos</div><ul class="rec-list">${r.alimentos.map(s=>`<li>${s}</li>`).join("")}</ul>`;
    }else if(sec.key==="meditacion"){
      if(r.descripcion)body+=`<p class="rec-desc">${r.descripcion}</p>`;
      if(r.tecnicas?.length)body+=`<ul class="rec-list">${r.tecnicas.map(t=>`<li>${t}</li>`).join("")}</ul>`;
      if(r.duracion_min)body+=`<div class="rec-chip">⏱ ${r.duracion_min} min/día</div>`;
      if(r.nota)body+=`<div class="rec-nota">${r.nota}</div>`;
    }else if(sec.key==="actividad"){
      if(r.tipo)body+=`<div class="rec-detail"><strong>${r.tipo}</strong></div>`;
      if(r.ejemplos?.length)body+=`<ul class="rec-list">${r.ejemplos.map(e=>`<li>${e}</li>`).join("")}</ul>`;
      if(r.frecuencia)body+=`<div class="rec-chip">📅 ${r.frecuencia}</div>`;
    }else if(sec.key==="stretching"){
      if(r.descripcion)body+=`<p class="rec-desc">${r.descripcion}</p>`;
      if(r.tecnicas?.length)body+=`<ul class="rec-list">${r.tecnicas.map(t=>`<li>${t}</li>`).join("")}</ul>`;
      if(r.duracion_min)body+=`<div class="rec-chip">⏱ ${r.duracion_min} min</div>`;
    }else if(sec.key==="musica"){
      if(r.recomendacion)body+=`<p class="rec-desc">${r.recomendacion}</p>`;
      if(r.frecuencias?.length)body+=`<ul class="rec-list">${r.frecuencias.map(f=>`<li>${f}</li>`).join("")}</ul>`;
      if(r.nota)body+=`<div class="rec-nota">${r.nota}</div>`;
      if(r.nota_extra)body+=`<div class="rec-nota accent">${r.nota_extra}</div>`;
    }
    return`<div class="rec-card"><div class="rec-header"><span class="rec-icon">${sec.icon}</span><span class="rec-label">${sec.label}</span></div><div class="rec-body">${body}</div></div>`;
  }).join("");
}

async function saveSession(){
  if(!G.lastMetrics)return; setStatus("Guardando…","warn");
  try{
    const res=await fetch("/api/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({patient_id:$("patientId").value||"",age:$("age").value||null,sex:$("sex").value||null,comorbidities:$("comorbidities").value||"",notes:$("notes").value||"",metrics:G.lastMetrics})});
    const data=await res.json(); setStatus(data.ok?"Guardado ✓":"Error al guardar",data.ok?"live":"err");
  }catch{setStatus("Sin conexión","err");}
}

buildChart(); G.rafH=requestAnimationFrame(renderChart); setBtns(false); setStatus("Listo");
