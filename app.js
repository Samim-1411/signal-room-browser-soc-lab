(function () {
  "use strict";
  let alerts = [], accounts = [], events = [], activeAlert = null, toastTimer = null;
  const state = loadState();
  const $ = function (s, root) { return (root || document).querySelector(s); };
  const $$ = function (s, root) { return Array.from((root || document).querySelectorAll(s)); };
  function loadState() { try { return {lessons:(JSON.parse(localStorage.getItem("signal-room-state") || "{}").lessons || [])}; } catch (_) { return {lessons:[]}; } }
  function persist() { localStorage.setItem("signal-room-state", JSON.stringify({lessons:state.lessons})); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c]; }); }
  async function api(path, options) {
    const response = await fetch(path, Object.assign({headers:{"Content-Type":"application/json"}}, options || {}));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Local API request failed");
    return data;
  }
  function statusOf(a) { return a.status || "open"; }
  function openCount() { return alerts.filter(function (a) { return statusOf(a) === "open"; }).length; }
  async function refreshData() {
    try {
      const result = await Promise.all([api("/api/alerts"),api("/api/accounts"),api("/api/events")]);
      alerts=result[0]; accounts=result[1]; events=result[2]; drawOverview(); drawAlerts(); drawAccounts(); drawEvents(events);
    } catch (error) { showToast("Could not reach local SQLite API: " + error.message); }
  }
  function priorityTemplate(a) {
    const status=statusOf(a);
    return '<div class="alert-row" data-alert="'+esc(a.id)+'"><i class="severity-bar '+esc(a.severity)+'"></i><div><div class="alert-title">'+esc(a.title)+'</div><div class="alert-meta">'+esc(a.id)+' · '+esc(a.source)+'</div></div><div class="alert-right"><div class="severity-text '+esc(a.severity)+'">'+esc(a.severity.toUpperCase())+'</div><div class="time-text">'+(status === "open" ? esc(a.time) : esc(status.toUpperCase()))+'</div></div></div>';
  }
  function drawOverview() {
    $("#priority-alerts").innerHTML=alerts.slice(0,3).map(priorityTemplate).join("");
    $("#stat-open").textContent=String(openCount()).padStart(2,"0");
    $("#nav-count").textContent=String(openCount()).padStart(2,"0");
  }
  function drawAlerts() {
    const q=$("#alert-search").value.toLowerCase().trim(), sev=$("#severity-filter").value;
    const filtered=alerts.filter(function(a){return(sev==="all"||a.severity===sev)&&(!q||[a.id,a.title,a.source,a.kind,a.ip,a.user].join(" ").toLowerCase().includes(q));});
    $("#alert-rows").innerHTML=filtered.map(function(a){const status=statusOf(a),label=status==="open"?"OPEN":status.toUpperCase();return '<tr><td><div class="td-title" data-alert="'+esc(a.id)+'">'+esc(a.title)+'</div><div class="td-sub">'+esc(a.id)+' · '+esc(a.kind)+'</div></td><td><span class="severity-chip '+esc(a.severity)+'">'+esc(a.severity.toUpperCase())+'</span></td><td><span class="source-cell">'+esc(a.user)+'</span></td><td><span class="source-cell">'+esc(a.time)+'</span></td><td><span class="status-chip '+(status==="investigating"?"investigating":"")+'">'+esc(label)+'</span></td><td><button class="row-arrow" data-alert="'+esc(a.id)+'" aria-label="Open '+esc(a.title)+'">→</button></td></tr>';}).join("");
    $("#queue-total").textContent=filtered.length; $("#no-results").hidden=filtered.length!==0; drawOverview();
  }
  function drawAccounts() {
    const q=$("#account-search").value.toLowerCase().trim();
    const found=accounts.filter(function(a){return !q||[a.id,a.name,a.role,a.type,a.device,a.signal].join(" ").toLowerCase().includes(q);});
    $("#account-rows").innerHTML=found.map(function(a){const signal=a.alert?'<span class="severity-chip '+esc(a.severity)+'">'+esc(a.signal)+'</span>':'<span class="status-chip">No alert</span>';const link=a.alert?'<button class="account-link" data-alert="'+esc(a.alert)+'">'+esc(a.alert)+' · '+esc(a.alertTitle)+'</button>':'<span class="source-cell">—</span>';return '<tr><td><div class="account-primary">'+esc(a.id)+'</div><div class="td-sub">'+esc(a.name)+'</div></td><td><div class="account-type">'+esc(a.type)+'</div><div class="td-sub">'+esc(a.role)+'</div></td><td><span class="source-cell">'+esc(a.device)+'</span></td><td>'+signal+'</td><td>'+link+'</td><td><button class="account-action" data-account-query="'+esc(a.id)+'">View events →</button></td></tr>';}).join("");
    $("#account-no-results").hidden=found.length!==0;
  }
  function drawEvents(rows) {
    events=rows;
    $("#event-count").textContent=rows.length+(rows.length===1?" event":" events");
    $("#event-list").innerHTML=rows.length?rows.map(function(e){const cls=e.type==="AUTH"||e.type==="IDENTITY"?"auth":e.type==="NETWORK"?"network":"process";return '<div class="event-entry"><div class="event-time">'+esc(e.time)+'</div><div class="event-kind '+cls+'">'+esc(e.type)+'</div><div class="event-copy"><b>'+esc((e.details.split(" ")[0]||e.type))+'</b> '+esc(e.details.split(" ").slice(1).join(" "))+'</div></div>';}).join(""):'<div class="event-empty">No sample events match that search.</div>';
  }
  function showToast(message) { const t=$("#toast");t.textContent=message;t.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(function(){t.classList.remove("show");},2500); }
  function openAlert(id) {
    const a=alerts.find(function(x){return x.id===id;});if(!a)return;activeAlert=id;const status=statusOf(a);
    const buttons=[["open","Keep open"],["investigating","Investigating"],["escalated","Escalate"]].map(function(p){return '<button data-status="'+p[0]+'" class="'+(status===p[0]?"selected":"")+'">'+p[1]+'</button>';}).join("");
    $("#dialog-content").innerHTML='<div class="detail-kicker">'+esc(a.id)+' · '+esc(a.kind.toUpperCase())+' ALERT</div><h2>'+esc(a.title)+'</h2><p>'+esc(a.summary)+'</p><div class="detail-meta"><div class="meta-box"><small>SEVERITY</small><b>'+esc(a.severity.toUpperCase())+'</b></div><div class="meta-box"><small>USER / ACCOUNT</small><b>'+esc(a.user)+'</b></div><div class="meta-box"><small>HOST</small><b>'+esc(a.host)+'</b></div><div class="meta-box"><small>SOURCE IP</small><b>'+esc(a.ip)+'</b></div><div class="meta-box"><small>DETECTED</small><b>'+esc(a.time)+'</b></div><div class="meta-box"><small>STATUS</small><b>'+esc(status.toUpperCase())+'</b></div></div><div class="evidence-box"><div class="eyebrow">SIMULATED EVIDENCE</div><code>'+esc(a.evidence)+'</code></div><p><b>Analyst lead:</b> '+esc(a.recommendation)+'</p><label class="analyst-label" for="analyst-notes">INVESTIGATION NOTES · SAVED TO LOCAL SQLITE</label><textarea id="analyst-notes" class="notes-input" maxlength="4000" placeholder="Record evidence, unknowns, and your reasoning...">'+esc(a.notes||"")+'</textarea><div class="triage-actions">'+buttons+'</div>';
    $("#alert-dialog").showModal();
  }
  async function setStatus(id,status){try{await api("/api/alerts/"+encodeURIComponent(id),{method:"PATCH",body:JSON.stringify({status:status})});await refreshData();openAlert(id);showToast("Disposition saved to local SQLite.");}catch(error){showToast("Save failed: "+error.message);}}
  async function saveNotes(){if(!activeAlert)return;const id=activeAlert,notes=$("#analyst-notes").value;try{await api("/api/alerts/"+encodeURIComponent(id),{method:"PATCH",body:JSON.stringify({notes:notes})});const a=alerts.find(function(x){return x.id===id;});if(a)a.notes=notes;showToast("Notes saved to local SQLite.");}catch(error){showToast("Notes were not saved: "+error.message);}}
  async function runEventSearch(q){try{const rows=await api("/api/events?q="+encodeURIComponent(q||""));drawEvents(rows);}catch(error){showToast("Event search failed: "+error.message);}}
  function switchView(name){$$(".view").forEach(function(v){v.classList.toggle("active",v.id==="view-"+name);});$$(".nav-item").forEach(function(b){b.classList.toggle("active",b.dataset.view===name);});const labels={overview:"Overview",alerts:"Alert queue",events:"Event explorer",accounts:"Example accounts",playbook:"Learning path"};$("#crumb-current").textContent=labels[name]||"Overview";if(name==="alerts")drawAlerts();if(name==="accounts")drawAccounts();}
  function lesson(which){const lessons={alert:{kicker:"FOUNDATIONS · 5 MIN",title:"Read an alert without jumping to conclusions",text:"An alert is a lead generated from observed activity. First capture the facts. Then test possible explanations against additional evidence.",steps:["Identify the account and device. Check whether both are known to the person.","Write down the exact event times and source addresses. Build a short sequence.","Separate what the telemetry proves from what it merely suggests.","Record what evidence is missing before making a disposition."],callout:"A location mismatch can result from a VPN, mobile carrier routing, or travel. Treat it as a signal to investigate, not proof of account compromise."},timeline:{kicker:"INVESTIGATION · 8 MIN",title:"Build a timeline from related signals",text:"Use the Event explorer to join events by user, device, and time. The goal is to establish sequence and context from the available evidence.",steps:["Search for j.chen in Event explorer.","Compare the two sign-in timestamps and note the device change.","Check the MFA event after the second sign-in.","List two benign explanations and one additional data source that would help distinguish them."],callout:"The sample is intentionally incomplete. Good analysts label uncertainty instead of filling gaps with assumptions."},disposition:{kicker:"DECISION MAKING · 6 MIN",title:"Choose a disposition and explain why",text:"A useful disposition is supported by evidence and describes the next safe step. Practice recording a clear reason others can review.",steps:["Open an alert and inspect the simulated evidence.","Choose Keep open, Investigating, or Escalate.","Write a short note: facts, unknowns, and why your choice fits the evidence.","Reopen the alert to confirm your note and status were saved locally."],callout:"This training control changes only the local SQLite database. It does not alter an account, device, or security system."}};const l=lessons[which];if(!l)return;if(state.lessons.indexOf(which)<0)state.lessons.push(which);persist();$("#progress-caption").textContent=state.lessons.length+" of 3 exercises started";$("#lesson-content").innerHTML='<div class="detail-kicker">'+l.kicker+'</div><h2>'+l.title+'</h2><p>'+l.text+'</p><ol class="lesson-step">'+l.steps.map(function(s){return '<li>'+s+'</li>';}).join("")+'</ol><div class="lesson-callout">'+l.callout+'</div><button class="btn btn-primary" id="lesson-done">Got it — return to lab</button>';$("#lesson-dialog").showModal();}
  document.addEventListener("click",function(e){
    const nav=e.target.closest(".nav-item");if(nav){switchView(nav.dataset.view);return;}
    const go=e.target.closest("[data-go]");if(go){switchView(go.dataset.go);return;}
    const alertButton=e.target.closest("[data-alert]");if(alertButton){openAlert(alertButton.dataset.alert);return;}
    const query=e.target.closest("[data-query]");if(query){switchView("events");$("#event-search").value=query.dataset.query;runEventSearch(query.dataset.query);return;}
    const accountQuery=e.target.closest("[data-account-query]");if(accountQuery){switchView("events");$("#event-search").value=accountQuery.dataset.accountQuery;runEventSearch(accountQuery.dataset.accountQuery);return;}
    const lessonButton=e.target.closest("[data-lesson]");if(lessonButton){lesson(lessonButton.dataset.lesson);return;}
    const statusButton=e.target.closest("[data-status]");if(statusButton&&activeAlert){setStatus(activeAlert,statusButton.dataset.status);return;}
    if(e.target.id==="start-investigation"){switchView("alerts");openAlert("SOC-1042");return;}
    if(e.target.id==="scenario-start"){lesson("timeline");return;}
    if(e.target.id==="lesson-done"){$("#lesson-dialog").close();showToast("Progress saved on this device.");return;}
    if(e.target.id==="reset-lab"){if(confirm("Reset SQLite training dispositions and notes to the original sample state?")){api("/api/reset",{method:"POST",body:"{}"}).then(function(){return refreshData();}).then(function(){showToast("SQLite training data reset.");}).catch(function(error){showToast("Reset failed: "+error.message);});}}
  });
  $("#alert-search").addEventListener("input",drawAlerts);$("#severity-filter").addEventListener("change",drawAlerts);
  let searchTimer;$("#event-search").addEventListener("input",function(e){clearTimeout(searchTimer);const q=e.target.value;searchTimer=setTimeout(function(){runEventSearch(q);},120);});
  $("#account-search").addEventListener("input",drawAccounts);
  $("#dialog-content").addEventListener("change",function(e){if(e.target.id==="analyst-notes")saveNotes();});
  $("#progress-caption").textContent=state.lessons.length?state.lessons.length+" of 3 exercises started":"One exercise started";
  refreshData();
}());
