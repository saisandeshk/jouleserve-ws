"""Approximate local renderer for the P5 reference deck's slide files (a Slides artifact), for
visual QA only: Sandesh approved checking rendered slides before he sees them (2026-10-04).

It applies the slide format's documented defaults, draws <x-connector> arrows, screenshots each
slide with the Playwright-cached headless Chromium, and reports text that overflows its box, flow
content past the bottom margin, overlapping pinned elements and fonts under 24px. It is not the
deck's own runtime, so treat small differences in line breaks as approximate.

Usage: python3 env/render_slides.py <deck root holding project/> <out dir> [slide ids...]
Uploaded images (/_blob/<id>) are mapped to local files in BLOBS below; add new ones there.
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT, OUT = sys.argv[1], sys.argv[2]
IDS = sys.argv[3:]
CHROME = next((c for c in (os.environ.get("SLIDE_CHROME"),
                           os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell"),
                           "/opt/brave.com/brave/brave", "/usr/bin/brave-browser") if c and os.path.exists(c)), None)
BLOBS = {
         "/_blob/9b83a2f30d74e4643cf604a6c3e5c385": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/energy_map.png",
         "/_blob/0725e2d95ddb66817859bc91d90a1c4c": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/opportunity.png",
         "/_blob/e13847c3ea658fccc4e758076f83b0c4": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/caps.png",
         "/_blob/69c5f109f1ab9aed0331081ab4d51247": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/traffic_sim.png",
         "/_blob/6f92e179632458f8a738d7f68d97e449": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/context_growth.png",
         "/_blob/3b9e1ffc315a4523ab7b4ff3d5029a10": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/vlm_burst.png",
         "/_blob/06cfad8f6b15ab92d06afa38aa1e8bfc": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/cap_chains.png",
         "/_blob/14cc5c90983217638598d85dfce0bc06": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/energy_map.png",
         "/_blob/3eafc85b5bcd7f79f7cde7e6ddeaf587": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/figures/summary.png",
         "/_blob/d4e3799f63749666a2dcda2e17c36477": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_turn_vs_task_s391.png",
         "/_blob/b750cc64cfb12ebad9ad2aedc42c9b98": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_token_price_by_workload_s394.png",
         "/_blob/2ad18d5eab60a3fb93354b0321096f33": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_capped_calls_s396.png",
         "/_blob/0fb0c0326bc6ef0e4e73498090e5028e": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_failure_energy_s397.png",
         "/_blob/1d95df64268861ec0c334456fa096206": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_prefill_cache_s398.png",
         "/_blob/d57dcc2895ae68cd798b2c610b54efe1": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_context_window_s400.png",
         "/_blob/e4c6c0e80f499fbf9e71bbfcad3ca8c7": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_vision_tool_energy_s401.png",
         "/_blob/657bd5bbc32db6c1ccbe344a923d94f4": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_path_agreement_s403.png",
         "/_blob/44c129d837b1bec66c3fc4aef31f9528": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_thermal_s405.png",
         "/_blob/637dfc9509cc9fed33f53dc1b40998a8": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_window_budget_repo.png",
         "/_blob/4a86d261662a78f48508481a8bfd905e": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-05-p1-repo/p1_figures/p1_token_price_s393.png",
         "/_blob/4b538ccc9cf4f178e3608db80da82808": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-01-workload-opportunity/figures/time_split.png",
         "/_blob/e0c130ece5d8cd561bf6484b8f214df1": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-02-stepwise-d1/figures/output_per_step_cdf.png",
         "/_blob/eeecb9f7c5e2e427d730760b9746fd80": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-03-admission-sim/figures/retention_value.png",
         "/_blob/d2ef785321065d758b947aa06dc0c5ea": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-03-admission-sim/figures/scaling.png",
         "/_blob/254540e25cc5f82652dfd8de6fd9a2c2": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-03-admission-sim/figures/headroom.png",
         "/_blob/020a92f9717905d39c7bee8cd3deb7e0": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-04-drone-runaways/figures/loops.png",
         "/_blob/c1499efb008a4a95584f38761fc1d89d": "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-01-workload-opportunity/figures/ws_costs.png","/_blob/5782cc27b5482310b0b1af225e4362a7":
         "file:///home/saisandeshk/Study/ISP/jouleserve-ws/reports/2026-10-01-workload-opportunity/figures/timelines.png"}
os.makedirs(OUT, exist_ok=True)
deck = json.load(open(os.path.join(ROOT, "project/deck.json")))
ids = IDS or deck["order"]

CSS = """
html,body{margin:0;padding:0;background:#777}
section{width:1920px;height:1080px;box-sizing:border-box;position:relative;overflow:hidden}
section *{box-sizing:border-box;margin:0}
h1{font-size:96px;font-weight:600;line-height:1.1} h2{font-size:64px;font-weight:600;line-height:1.15}
h3{font-size:44px;font-weight:600;line-height:1.2} p{font-size:32px;line-height:1.4}
ul,ol{padding-left:1.25em} li{padding-left:0.2em}
table{border-collapse:collapse} th,td{padding:0.35em 0.6em;border-bottom:1px solid rgba(0,0,0,.18);text-align:left;vertical-align:top}
th{font-weight:600} aside{display:none} x-connector{display:none} img{display:block}
"""

JS = r"""
(function(){
const sec = document.querySelector('section');
if (!sec.style.display) { sec.style.display='flex'; sec.style.flexDirection='column'; }
sec.querySelectorAll('div').forEach(d => { if (!d.style.display) { d.style.display='flex'; d.style.flexDirection='column'; } });
// connectors
const NS='http://www.w3.org/2000/svg';
sec.querySelectorAll('x-connector').forEach(c => {
  let host = c.parentElement;
  while (host !== sec && getComputedStyle(host).position !== 'relative') host = host.parentElement;
  let svg = host.querySelector(':scope > svg.xc');
  if (!svg) { svg = document.createElementNS(NS,'svg'); svg.setAttribute('class','xc');
    svg.style.cssText='position:absolute;left:0;top:0;overflow:visible;pointer-events:none';
    svg.setAttribute('width', host.offsetWidth); svg.setAttribute('height', host.offsetHeight); host.appendChild(svg); }
  const n = a => parseFloat(c.getAttribute(a));
  const [x1,y1,x2,y2] = ['x1','y1','x2','y2'].map(n);
  const route = c.getAttribute('route') || 'straight', head = c.getAttribute('head') || 'end';
  const col = c.style.color || '#000', w = parseFloat(c.style.borderWidth) || 2;
  let pts = [[x1,y1],[x2,y2]];
  if (route==='hv') pts=[[x1,y1],[x2,y1],[x2,y2]];
  if (route==='vh') pts=[[x1,y1],[x1,y2],[x2,y2]];
  if (route==='elbow') { const mx=(x1+x2)/2; pts=[[x1,y1],[mx,y1],[mx,y2],[x2,y2]]; }
  const pl = document.createElementNS(NS,'polyline');
  pl.setAttribute('points', pts.map(p=>p.join(',')).join(' '));
  pl.setAttribute('fill','none'); pl.setAttribute('stroke',col); pl.setAttribute('stroke-width',w);
  pl.setAttribute('stroke-linecap','round'); pl.setAttribute('stroke-linejoin','round');
  if (c.style.borderStyle==='dashed') pl.setAttribute('stroke-dasharray', `${3*w} ${2*w}`);
  svg.appendChild(pl);
  const arrow = (a,b) => { const [ax,ay]=a,[bx,by]=b; const ang=Math.atan2(by-ay,bx-ax), L=4*w;
    const p = document.createElementNS(NS,'path');
    p.setAttribute('d',`M ${bx-L*Math.cos(ang-0.45)} ${by-L*Math.sin(ang-0.45)} L ${bx} ${by} L ${bx-L*Math.cos(ang+0.45)} ${by-L*Math.sin(ang+0.45)}`);
    p.setAttribute('fill','none'); p.setAttribute('stroke',col); p.setAttribute('stroke-width',w); p.setAttribute('stroke-linecap','round'); p.setAttribute('stroke-linejoin','round'); svg.appendChild(p); };
  if (head==='end'||head==='both') arrow(pts[pts.length-2], pts[pts.length-1]);
  if (head==='both') arrow(pts[1], pts[0]);
});
})();
"""

CHECK = r"""
(function(){
const sec=document.querySelector('section'); const S=sec.getBoundingClientRect(); const out=[];
const pb=parseFloat(getComputedStyle(sec).paddingBottom);
const limit = 1080 - pb;
const name = e => (e.tagName.toLowerCase()) + ' "' + (e.textContent||'').trim().slice(0,48) + '"';
// 1. text/box overflow (fixed-size boxes and text elements)
sec.querySelectorAll('p,h1,h2,h3,li,td,th,div').forEach(e => {
  if (e.scrollHeight > e.clientHeight + 3 && getComputedStyle(e).overflow!=='visible' ) out.push('clip: '+name(e));
  if (e.tagName==='DIV' && e.style.height && e.scrollHeight > e.clientHeight + 3) out.push('overflow fixed-height box ('+e.scrollHeight+'>'+e.clientHeight+'): '+name(e));
  if (e.scrollWidth > e.clientWidth + 3 && /^(P|H1|H2|H3|TD|TH|LI)$/.test(e.tagName)) out.push('too wide (word breaks?): '+name(e));
});
// 2. flow content past the bottom margin
[...sec.children].forEach(c => { if (getComputedStyle(c).position!=='absolute' && c.tagName!=='ASIDE') {
  const r=c.getBoundingClientRect(); if (r.bottom - S.top > limit + 1) out.push(`flow past margin: bottom ${Math.round(r.bottom-S.top)} > ${limit}: `+name(c)); }});
// 3. anything outside the slide
sec.querySelectorAll('*').forEach(e => { const r=e.getBoundingClientRect(); if (r.width && (r.right-S.left>1921 || r.bottom-S.top>1081)) out.push('outside slide: '+name(e)); });
// 4. overlapping pinned siblings (boxes and labels)
const hosts=new Set(); sec.querySelectorAll('*').forEach(e=>{ if(getComputedStyle(e).position==='absolute') hosts.add(e.parentElement); });
hosts.forEach(h => { const kids=[...h.children].filter(e=>getComputedStyle(e).position==='absolute' && e.tagName!=='svg' && e.tagName!=='X-CONNECTOR');
  for (let i=0;i<kids.length;i++) for (let j=i+1;j<kids.length;j++) { const a=kids[i].getBoundingClientRect(), b=kids[j].getBoundingClientRect();
    if (a.left<b.right-1 && b.left<a.right-1 && a.top<b.bottom-1 && b.top<a.bottom-1) out.push('overlap: '+name(kids[i])+' x '+name(kids[j])); } });
// 5. min font size
sec.querySelectorAll('p,li,td,th,h1,h2,h3').forEach(e=>{ if(parseFloat(getComputedStyle(e).fontSize)<24) out.push('font<24: '+name(e)); });
if(!document.fonts.check('24px "IBM Plex Sans"')) out.push('FONT NOT LOADED');
const pre=document.createElement('pre'); pre.id='report'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
"""

for sid in ids:
    src = open(os.path.join(ROOT, f"project/slides/{sid}.html")).read()
    for k, v in BLOBS.items():
        src = src.replace(k, v)
    page = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<link rel='stylesheet' href='{deck['faces']['ibm-plex-sans']['href']}'><style>{CSS}</style></head>"
            f"<body>{src}<script>{JS}</script><script>Promise.race([document.fonts.ready, new Promise(r=>setTimeout(r,4000))]).then(()=>{{{CHECK}}});</script></body></html>")
    pf = os.path.abspath(os.path.join(OUT, f"{sid}.html"))
    open(pf, "w").write(page)
    common = [CHROME] + ([] if CHROME.endswith("chrome-headless-shell") else ["--headless=new", "--disable-gpu"]) + ["--no-sandbox", "--hide-scrollbars", "--allow-file-access-from-files",
              "--window-size=1920,1080", "--virtual-time-budget=8000"]
    with tempfile.TemporaryDirectory() as ud:
        subprocess.run(common + [*([f"--user-data-dir={ud}"] if CHROME.endswith("chrome-headless-shell") else []), f"--screenshot={os.path.join(OUT, sid + '.png')}", "file://" + pf],
                       capture_output=True, timeout=120)
    with tempfile.TemporaryDirectory() as ud:
        res = subprocess.run(common + [*([f"--user-data-dir={ud}"] if CHROME.endswith("chrome-headless-shell") else []), "--dump-dom", "file://" + pf], capture_output=True, text=True, timeout=120)
    dom = res.stdout
    if '<pre id="report">' not in dom:
        print("   dump failed:", len(dom), res.stderr[-300:])
    m = re.search(r'<pre id="report">(.*?)</pre>', dom, re.S)
    rep = json.loads(html.unescape(m.group(1))) if m else ["(no report)"]
    print(f"{sid}: {'OK' if not rep else ''}")
    for r in rep:
        print("   ", r)
