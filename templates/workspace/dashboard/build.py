#!/usr/bin/env python3
"""Build dashboard/index.html from ledger.csv, history/events.jsonl and the latest digest.

Usage: python3 dashboard/build.py   (run from anywhere; paths are relative to the repo root)
The page is a pure function of those files. Days-waiting figures are computed in the
browser when the page is opened, so they stay current between rebuilds.
"""
import csv
import json
import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import response_model

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard" / "index.html"


def load():
    ledger = list(csv.DictReader(open(ROOT / "ledger.csv", newline="")))
    events = [json.loads(l) for l in open(ROOT / "history" / "events.jsonl") if l.strip()]
    digests = sorted((ROOT / "digests").glob("*.md"))
    digest = {"name": digests[-1].stem, "text": digests[-1].read_text()} if digests else None
    resp, meta = response_model.score(ledger, events, response_model.load_feedback(ROOT))
    for r in ledger:
        r["resp"] = resp[r["job_id"]]
    return {
        "ledger": ledger,
        "model": meta,
        "events": [{k: e.get(k) for k in ("ts", "job_id", "type", "source", "summary", "status_after")} for e in events],
        "digest": digest,
        "generated": datetime.now().astimezone().isoformat(timespec="minutes"),
    }


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Search Dashboard</title>
<style>
:root{color-scheme:light;
  --bg:#f4f4f2;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--ink3:#74736e;--line:#dddcd7;--grid:#e8e7e3;
  --bar:#2a78d6;--bar-hover:#184f95;--accent:#184f95;--warn:#8a5a00;
  --c-submitted:#2a78d6;--c-new:#1b8a4a;--c-prep:#e0a100}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
  --bg:#121211;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--ink3:#9a998f;--line:#33322f;--grid:#2a2926;
  --bar:#3987e5;--bar-hover:#86b6ef;--accent:#86b6ef;--warn:#e0a94a;
  --c-submitted:#3987e5;--c-new:#2fa862;--c-prep:#c98500}}
:root[data-theme="dark"]{color-scheme:dark;
  --bg:#121211;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--ink3:#9a998f;--line:#33322f;--grid:#2a2926;
  --bar:#3987e5;--bar-hover:#86b6ef;--accent:#86b6ef;--warn:#e0a94a;
  --c-submitted:#3987e5;--c-new:#2fa862;--c-prep:#c98500}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;
  padding:24px max(16px,env(safe-area-inset-right)) 48px max(16px,env(safe-area-inset-left))}
main{max-width:1100px;margin:0 auto}
h1{font-size:20px;margin:0}
h2{font-size:13px;font-weight:600;color:var(--ink2);margin:0 0 12px;text-transform:uppercase;letter-spacing:.04em}
.sub{color:var(--ink3);font-size:12px;margin:2px 0 20px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.tile,.card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.tile .v{font-size:30px;font-weight:600;line-height:1.1}
.tile .l{color:var(--ink2);font-size:12px;margin-top:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin-bottom:12px}
.card{min-width:0}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--ink2);font-size:11px}
.bar{fill:var(--bar);cursor:default}
.bar:hover,.bar:focus{fill:var(--bar-hover);outline:none}
.bar.click{cursor:pointer}
.axis{stroke:var(--grid)}
.val{fill:var(--ink)!important;font-weight:600}
ul.plain{list-style:none;margin:0;padding:0}
ul.plain li{padding:7px 0;border-top:1px solid var(--grid);display:flex;gap:10px;justify-content:space-between;align-items:baseline}
ul.plain li:first-child{border-top:0}
.muted{color:var(--ink3)}.nw{white-space:nowrap}.chk{display:flex;align-items:center;gap:6px;color:var(--ink2);cursor:pointer}tr.struck td{color:var(--ink3)}
tr.tint td{background:color-mix(in srgb,var(--c) calc(var(--a)*100%),transparent)}
tr.tint td:first-child{box-shadow:inset 3px 0 0 var(--c)}
tr.st-submitted{--c:var(--c-submitted)}tr.st-new{--c:var(--c-new)}tr.st-preparing,tr.st-shortlisted{--c:var(--c-prep)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin:0 0 10px}.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:5px;background:var(--c)}tr.struck td:not(:last-child){text-decoration:line-through}.tag{font-size:11px;color:var(--warn);border:1px solid var(--warn);border-radius:4px;padding:0 5px;margin-left:6px}
.empty{color:var(--ink3);padding:8px 0}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
select,input[type=search],button{font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:5px 9px}
button{cursor:pointer}
.rc{white-space:nowrap}.rc small{color:var(--ink3);font-size:11px;margin-left:4px}.rc.dim{color:var(--ink3);font-style:italic}
.method{margin-top:12px;font-size:12px;color:var(--ink2)}.method summary{cursor:pointer;font-weight:600;color:var(--ink)}.method td,.method th{padding:3px 10px 3px 0;text-align:left;font-size:12px;border:0}
.tablewrap{overflow-x:auto}
.rc{white-space:nowrap}.rc small{color:var(--ink3);font-size:11px;margin-left:4px}.rc.dim{color:var(--ink3);font-style:italic}
.method{margin-top:12px;font-size:12px;color:var(--ink2)}.method summary{cursor:pointer;font-weight:600;color:var(--ink)}.method td,.method th{padding:3px 14px 3px 0;text-align:left;font-size:12px;border:0;vertical-align:top}
table{border-collapse:collapse;width:100%;min-width:640px}
th,td{text-align:left;padding:6px 8px;border-top:1px solid var(--grid);vertical-align:top}
th{color:var(--ink2);font-weight:600;font-size:12px;cursor:pointer;white-space:nowrap;border-top:0}
td.n{font-variant-numeric:tabular-nums;text-align:right}
a{color:var(--accent)}
pre{white-space:pre-wrap;margin:0;font:12px/1.5 ui-monospace,Menlo,monospace;color:var(--ink2);max-height:260px;overflow:auto}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);padding:5px 9px;border-radius:5px;font-size:12px;display:none;z-index:10;max-width:260px}
#tip b{font-size:14px}
button.theme{float:right}
</style></head>
<body><main>
<button class="theme" id="theme" type="button">Theme</button>
<h1>Job Search Dashboard</h1>
<p class="sub" id="gen"></p>
<section class="tiles" id="tiles"></section>
<section class="grid">
  <div class="card"><h2>Pipeline by status <span class="muted" style="text-transform:none;font-weight:400">(click a bar to filter the table)</span></h2><div id="status"></div></div>
  <div class="card"><h2>Awaiting reply</h2><div id="waiting"></div></div>
</section>
<section class="grid">
  <div class="card"><h2>Open roles by fit score</h2><div id="scores"></div></div>
  <div class="card"><h2>Roles found per day</h2><div id="found"></div></div>
</section>
<section class="grid">
  <div class="card"><h2>Recent activity</h2><div id="recent"></div></div>
  <div class="card"><h2 id="digesth">Latest digest</h2><pre id="digest"></pre></div>
</section>
<section class="card">
  <h2>All roles</h2>
  <div class="filters">
    <select id="fstatus" aria-label="Status"></select>
    <select id="ftier" aria-label="Tier"></select>
    <input id="fq" type="search" placeholder="Search title, employer, location" aria-label="Search">
    <label class="chk"><input type="checkbox" id="fhide"> Hide rejected, skipped, excluded &amp; expired</label>
    <button id="freset" type="button">Reset</button>
    <span class="muted" id="fcount" style="align-self:center"></span>
  </div>
  <div class="legend"><span><i style="--c:var(--c-submitted)"></i>Submitted</span><span><i style="--c:var(--c-new)"></i>New (greener = higher score)</span><span><i style="--c:var(--c-prep)"></i>Preparing / shortlisted</span><span><s>Rejected (by employer) / skipped (my decision)</s></span></div>
  <div class="tablewrap"><table><thead><tr id="thead"></tr></thead><tbody id="tbody"></tbody></table></div>
  <details class="method"><summary>How response chance is worked out</summary><div id="method"></div></details>
</section>
<div id="tip"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById("data").textContent);
const L=D.ledger, E=D.events, byId=Object.fromEntries(L.map(r=>[r.job_id,r]));
const ORDER=["new","preparing","shortlisted","submitted","rejected","expired","excluded","skipped"];
const OPEN=["new","preparing","shortlisted"],DEAD=["rejected","skipped"],HIDE=["rejected","skipped","excluded","expired"];
const DAY=864e5, now=Date.now();
const $=s=>document.querySelector(s);
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
const NS="http://www.w3.org/2000/svg";
const sv=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e};
const fmtDate=ts=>new Date(ts).toISOString().slice(0,10);

$("#gen").textContent="Built "+D.generated.replace("T"," ").slice(0,16)+" from ledger.csv and history/events.jsonl. Days-waiting figures are live.";

// theme toggle (per-viewer convenience only)
$("#theme").onclick=()=>{const r=document.documentElement,cur=r.dataset.theme||(matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");r.dataset.theme=cur==="dark"?"light":"dark"};

// tooltip
const tip=$("#tip");
function showTip(e,value,label){tip.replaceChildren();const b=el("b",null,value);tip.append(b,el("div",null,label));tip.style.display="block";
  const r=e.target.getBoundingClientRect();const x=e.clientX||r.left+r.width/2,y=e.clientY||r.top;
  tip.style.left=Math.min(x+12,innerWidth-tip.offsetWidth-8)+"px";tip.style.top=Math.max(y-tip.offsetHeight-10,4)+"px"}
const hideTip=()=>tip.style.display="none";
function wire(node,value,label){node.addEventListener("pointermove",e=>showTip(e,value,label));node.addEventListener("pointerleave",hideTip);
  node.addEventListener("focus",e=>showTip(e,value,label));node.addEventListener("blur",hideTip);node.setAttribute("tabindex","0");
  node.setAttribute("role","img");node.setAttribute("aria-label",label+": "+value)}

// counts
const cnt={};ORDER.forEach(s=>cnt[s]=0);L.forEach(r=>cnt[r.status]=(cnt[r.status]||0)+1);
const open=OPEN.reduce((a,s)=>a+cnt[s],0);
const respondedIds=new Set(E.filter(e=>["response","rejected"].includes(e.type)).map(e=>e.job_id));
const confirmedIds=new Set(E.filter(e=>e.type==="user_confirmed").map(e=>e.job_id));
const subDates={},subSrc={};
E.filter(e=>e.type==="submitted").forEach(e=>{if(!subDates[e.job_id]||e.ts>subDates[e.job_id]){subDates[e.job_id]=e.ts;subSrc[e.job_id]=e.source}});
const waiting=L.filter(r=>r.status==="submitted"&&!respondedIds.has(r.job_id));

// response chance: eventual chance from the build (fit, posting age, applicants, route, sector, my confidence),
// then lowered live by days without a reply: P = p0(1-F)/(1-p0*F), F = share of replies normally in by day t
const M=D.model, Fd=t=>1-Math.pow(.5,Math.max(t,0)/M.half_life);
const daysSince=r=>subDates[r.job_id]?Math.max(0,(now-new Date(subDates[r.job_id]))/DAY):0;
function chance(r){const o=r.resp;if(!o||o.state!=="est")return null;const p0=o.p0,t=r.status==="submitted"?daysSince(r):0,f=Fd(t);
  const p=r.status==="submitted"?p0*(1-f)/(1-p0*f):p0;return{p,p0,t,why:o.why}}
const band=p=>p<.10?"very low":p<.25?"low":p<.45?"medium":p<.65?"high":"very high";
const pct=p=>p<.02?"<2%":Math.round(p*100)+"%";

// tiles
[["Tracked",L.length],["Open roles",open],["In progress",cnt.preparing+cnt.shortlisted],["Submitted",cnt.submitted],["Awaiting reply",waiting.length],["Replies expected",waiting.reduce((a,r)=>a+(chance(r)?chance(r).p:0),0).toFixed(1)],["Rejected by employer",cnt.rejected],["Skipped by me",cnt.skipped]]
 .forEach(([l,v])=>{const t=el("div","tile");t.append(el("div","v",v),el("div","l",l));$("#tiles").append(t)});

// horizontal bars
function hbars(host,items,onclick){
  const rowH=26,left=96,W=420,H=items.length*rowH+4,max=Math.max(1,...items.map(i=>i.value));
  const s=sv("svg",{viewBox:`0 0 ${W} ${H}`,role:"group","aria-label":"Bar chart"});
  items.forEach((it,i)=>{const y=i*rowH+2,w=Math.max(it.value?3:0,(W-left-36)*it.value/max);
    const t=sv("text",{x:left-8,y:y+14,"text-anchor":"end"});t.textContent=it.label;s.append(t);
    const r=sv("rect",{x:left,y:y+2,width:w,height:rowH-8,rx:4,class:"bar"+(onclick?" click":"")});
    wire(r,String(it.value),it.label);if(onclick)r.addEventListener("click",()=>onclick(it));s.append(r);
    const v=sv("text",{x:left+w+6,y:y+14,class:"val"});v.textContent=it.value;s.append(v)});
  host.replaceChildren(s)}
hbars($("#status"),ORDER.filter(s=>cnt[s]>0).map(s=>({label:s,value:cnt[s],key:s})),it=>{$("#fstatus").value=it.key;renderTable();$("#tbody").scrollIntoView({behavior:"smooth",block:"start"})});

// vertical bars
function vbars(host,items,fmt){
  const W=420,H=170,pb=22,pt=16,n=items.length||1,gap=2,bw=Math.max(3,(W-8)/n-gap),max=Math.max(1,...items.map(i=>i.value));
  const s=sv("svg",{viewBox:`0 0 ${W} ${H}`,role:"group","aria-label":"Column chart"});
  s.append(sv("line",{x1:0,x2:W,y1:H-pb,y2:H-pb,class:"axis"}));
  items.forEach((it,i)=>{const h=(H-pb-pt)*it.value/max,x=4+i*(bw+gap),y=H-pb-h;
    if(it.value){const r=sv("rect",{x,y,width:bw,height:h,rx:Math.min(4,bw/2),class:"bar"});wire(r,String(it.value),it.label);s.append(r);
      if(n<=14||i%Math.ceil(n/12)===0){const v=sv("text",{x:x+bw/2,y:y-4,"text-anchor":"middle",class:"val"});v.textContent=it.value;s.append(v)}}
    if(n<=14||i%Math.ceil(n/7)===0){const t=sv("text",{x:x+bw/2,y:H-6,"text-anchor":"middle"});t.textContent=it.short||it.label;s.append(t)}});
  host.replaceChildren(s)}
const scoreBins=[...Array(10)].map((_,i)=>({label:`${i*10}–${i*10+9}`,short:String(i*10),value:0}));
L.filter(r=>OPEN.includes(r.status)&&r.score!=="").forEach(r=>{scoreBins[Math.min(9,Math.floor(+r.score/10))].value++});
vbars($("#scores"),scoreBins.slice(3));
const days={};E.filter(e=>e.type==="found").forEach(e=>{const d=fmtDate(e.ts);days[d]=(days[d]||0)+1});
vbars($("#found"),Object.keys(days).sort().map(d=>({label:d,short:d.slice(5),value:days[d]})));

// awaiting reply
const wl=$("#waiting");
if(!waiting.length)wl.append(el("div","empty","Nothing awaiting a reply."));
else{const ul=el("ul","plain");waiting.sort((a,b)=>(subDates[a.job_id]||"").localeCompare(subDates[b.job_id]||"")).forEach(r=>{
  const li=el("li");const left=el("span");left.append(document.createTextNode(r.title+" "),el("span","muted","· "+r.employer));
  if(subSrc[r.job_id]==="inferred"&&!confirmedIds.has(r.job_id))left.append(el("span","tag","unconfirmed"));
  const d=subDates[r.job_id]?Math.max(0,Math.floor((now-new Date(subDates[r.job_id]))/DAY)):null;
  const c=chance(r);li.append(left,el("span","muted nw",(c?pct(c.p)+" · ":"")+(d==null?"date unknown":d+(d===1?" day":" days"))));ul.append(li)});wl.append(ul)}

// recent activity
const KEY=["submitted","response","rejected","shortlisted","docs_prepared","docs_approved"];
const rl=el("ul","plain");E.filter(e=>KEY.includes(e.type)).sort((a,b)=>b.ts.localeCompare(a.ts)).slice(0,12).forEach(e=>{
  const li=el("li");const j=byId[e.job_id];const left=el("span");left.append(document.createTextNode((j?j.employer+" – "+j.title:e.job_id)+" "),el("span","muted","· "+e.type.replace("_"," ")));
  li.append(left,el("span","muted nw",fmtDate(e.ts)));rl.append(li)});
$("#recent").append(rl);

// digest
if(D.digest){$("#digesth").textContent="Latest digest · "+D.digest.name;$("#digest").textContent=D.digest.text}else $("#digest").textContent="No digests yet.";

// table
const COLS=[["score","Score",true],["title","Title"],["employer","Employer"],["location","Location"],["tier","Tier"],["status","Status"],["url","Link"],["resp","Response chance"]];
let sortKey="score",sortDir=-1;
function fillSelect(sel,label,values){sel.append(new Option(label,""));values.forEach(v=>sel.append(new Option(v,v)))}
fillSelect($("#fstatus"),"All statuses",ORDER.filter(s=>cnt[s]>0));
fillSelect($("#ftier"),"All tiers",[...new Set(L.map(r=>r.tier).filter(Boolean))]);
COLS.forEach(([k,l])=>{const th=el("th",null,l);th.onclick=()=>{sortDir=sortKey===k?-sortDir:(k==="score"||k==="resp"?-1:1);sortKey=k;renderTable()};$("#thead").append(th)});
const newScores=L.filter(r=>r.status==="new"&&r.score!=="").map(r=>+r.score),nMin=Math.min(...newScores),nMax=Math.max(...newScores);
const newAlpha=r=>{const t=r.score===""||nMax===nMin?0:(+r.score-nMin)/(nMax-nMin);return (.07+.4*t).toFixed(3)};
const rowClass=r=>["submitted","new","preparing","shortlisted"].includes(r.status)?"tint st-"+r.status:null;
function renderTable(){
  const s=$("#fstatus").value,t=$("#ftier").value,q=$("#fq").value.toLowerCase();
  let rows=L.filter(r=>(!s||r.status===s)&&!($("#fhide").checked&&HIDE.includes(r.status))&&(!t||r.tier===t)&&(!q||(r.title+" "+r.employer+" "+r.location).toLowerCase().includes(q)));
  const rv=r=>{const c=chance(r);return r.resp&&r.resp.state==="replied"?2:c?c.p:-1};
  rows.sort((a,b)=>{const x=sortKey==="score"?+a.score||-1:sortKey==="resp"?rv(a):(a[sortKey]||"").toLowerCase(),y=sortKey==="score"?+b.score||-1:sortKey==="resp"?rv(b):(b[sortKey]||"").toLowerCase();return(x>y?1:x<y?-1:0)*sortDir});
  $("#fcount").textContent=rows.length+" of "+L.length;
  $("#tbody").replaceChildren(...rows.map(r=>{const tr=el("tr",DEAD.includes(r.status)?"struck":rowClass(r));
    if(r.status==="new"){const a=newAlpha(r);tr.style.setProperty("--a",a)}else if(r.status==="submitted")tr.style.setProperty("--a",.2);else if(r.status==="preparing"||r.status==="shortlisted")tr.style.setProperty("--a",.25);
    tr.append(el("td","n",r.score||"–"),el("td",null,r.title),el("td",null,r.employer),el("td",null,r.location),el("td",null,r.tier||"–"),el("td",null,r.status));
    const td=el("td");if(/^https?:\/\//.test(r.url||"")){const a=el("a",null,"open");a.href=r.url;a.target="_blank";a.rel="noopener noreferrer";td.append(a)}tr.append(td);
    const rc=el("td","rc"),c=chance(r);
    if(r.resp&&r.resp.state==="replied")rc.textContent="Replied";
    else if(c){rc.append(document.createTextNode(pct(c.p)),el("small",null,band(c.p)+(r.status==="submitted"?"":" if applied")));if(r.status!=="submitted")rc.classList.add("dim");
      rc.title=[(r.status==="submitted"?"Day "+Math.floor(c.t)+" without a reply. Start point "+pct(c.p0)+", now "+pct(c.p):"Chance if you applied: "+pct(c.p0)),"Base rate "+Math.round(M.base*100)+"%"].concat(c.why.map(w=>(w[1]>0?"+":"")+w[1]+"  "+w[0])).join("\n")}
    else rc.textContent="–";
    tr.append(rc);return tr}))}
["fstatus","ftier"].forEach(i=>$("#"+i).onchange=renderTable);$("#fq").oninput=renderTable;$("#fhide").onchange=renderTable;
$("#freset").onclick=()=>{$("#fstatus").value="";$("#ftier").value="";$("#fq").value="";$("#fhide").checked=false;renderTable()};
renderTable();

// method note
$("#method").innerHTML=`<p>Chance that the company replies at all (interview, call, request for information or a rejection; automated receipts do not count). Small history, so treat it as a ranking, not a forecast.</p>
<table><tr><th>Step</th><th>What it does</th></tr>
<tr><td>Base rate</td><td>${Math.round(M.base*100)}%. Starts from a ${Math.round(100*M.prior[0]/(M.prior[0]+M.prior[1]))}% prior (senior roles with 100+ applicants), updated with your own history: ${M.replies} replies from ${M.applications} applications (${M.n_eff} counting silent ones only by how long they have waited).</td></tr>
<tr><td>Fit score</td><td>+0.04 per point above 65, capped at ±0.8.</td></tr>
<tr><td>Posting age</td><td>≤14 days +0.2, ≤30 days 0, ≤45 days −0.3, ≤90 days −0.9, older −1.4. Old postings are often filled, stale or kept open for a pipeline.</td></tr>
<tr><td>Applicants</td><td>100+ −0.4, 50–99 −0.2, fewer 0.</td></tr>
<tr><td>Route</td><td>Message to a recruiter +0.4, agency with unnamed client −0.2.</td></tr>
<tr><td>Connections</td><td>A connection at the company +0.15, or +0.5 if you have contacted one.</td></tr>
<tr><td>Sector</td><td>Government or public-sector focus −0.6.</td></tr>
<tr><td>Your confidence</td><td>Low −0.9, medium 0, high +0.7. Set in response-feedback.json.</td></tr>
<tr><td>Waiting time</td><td>Each day without a reply lowers the chance. Half of replies normally arrive within ${M.half_life} days, so after two weeks of silence the chance is roughly a third of where it started.</td></tr></table>
<p>Adjustments are added as log-odds and clipped to ${M.clip[0]} to +${M.clip[1]}. Hover a percentage to see its factors. Sort the column to rank what to chase. Rows not yet applied show the chance if you applied.</p>`;
</script></body></html>
"""


def main():
    data = json.dumps(load(), ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.replace("__DATA__", data))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
