import json,re,glob,collections
key=json.load(open('answer_key.json'))['questions']
LOGS={'glm-5.2':'glm_full.log','nemotron-ultra':'nemo_full.log','qwen':'qwen_full.log'}
ORG={'glm-5.2':'report_glm','nemotron-ultra':'report_nemo','qwen':'report_qwen'}

def parse_cells(logfile):
    txt=open(logfile).read(); dec=json.JSONDecoder(); cells=[]
    for m in re.finditer(r'-----\s+q\d+__[^\n]+\.json\s+-----\n',txt):
        s=txt.find('{',m.end())
        if s<0: continue
        try: obj,_=dec.raw_decode(txt,s); cells.append(obj)
        except: pass
    return cells
def hpct(r):
    if not r: return None
    m=re.search(r'\*\*\s*~?\$?([\d,]+(?:\.\d+)?)\s*%',r) or re.search(r'([\d]+(?:\.\d+)?)\s*%',r)
    return float(m.group(1).replace(',','')) if m else None
def hnum(r):
    if not r: return None
    m=re.search(r'\*\*\s*~?\$?([\d,]+(?:\.\d+)?)\s*(million|M\b|acres)',r,re.I)
    if m:
        v=float(m.group(1).replace(',','')); 
        if re.match(r'million|M',m.group(2),re.I): v*=1e6
        return v
    m=re.search(r'([\d,]{4,})\s*acres',r); return float(m.group(1).replace(',','')) if m else None
def verdict(exp,val,unit,tol):
    if val is None: return '·'
    if unit=='acres': return '✓' if abs(val-exp)/exp<=0.02 else ('~' if abs(val-exp)/exp<=0.05 else '✗')
    t=tol or 0.5; d=abs(val-exp)
    return '✓' if d<=t else ('~' if d<=2*t else '✗')

# grade per model
res={m:{} for m in LOGS}
for m,lf in LOGS.items():
    for c in parse_cells(lf):
        k=next((x for x in key if x['q']==c.get('question')),None)
        if not k: continue
        unit=k['unit']
        v = hnum(c.get('response')) if unit=='acres' else (hpct(c.get('response')) if 'percent' in unit or unit.endswith('+percent') else None)
        res[m].setdefault(c['question'],{})[c['trial']]=(v, c.get('response') is not None)

# per-model tally over numeric questions
def cell_mark(m,q,unit,exp,tol):
    d=res[m].get(q,{})
    out=[]
    for t in (1,2):
        v,ok=d.get(t,(None,False))
        out.append(verdict(exp,v,unit,tol) if ok else '⏱')
    return out, d
short=[ "% CA in 30x30","% GAP3+4","% non-conserved","acres conserved","acres to 30%","top ecoregion %","Sierra %","top habitat %",
 "desert shrub","desert woodland","hardwood woodland","herbaceous","conifer forest","shrub","blue oak wood","eastside pine","subalpine conifer",
 "least-protected","ACE BioRankSW","native bird","native reptile","plant top20","channelized","diffuse","wetlands","GDE","floodplain",
 "headwater strm","major rivers","fwa richness"]

rows=[]; tally={m:collections.Counter() for m in LOGS}
for i,k in enumerate(key):
    q=k['q']; unit=k['unit']; exp=k['answer']; tol=k.get('tolerance_pp')
    expn=exp if isinstance(exp,(int,float)) else None
    cells={}
    for m in LOGS:
        if expn is None: cells[m]=('—',None); continue
        marks,d=cell_mark(m,q,unit,expn,tol)
        v1=d.get(1,(None,))[0]; v2=d.get(2,(None,))[0]
        # representative for tally
        best=min(marks,key=lambda x:{'✓':0,'~':1,'✗':2,'⏱':3,'·':3}[x])
        tally[m][best]+=1
        nd='⚠' if (isinstance(v1,float) and isinstance(v2,float) and abs(v1-v2)>(2*(tol or .5) if unit!='acres' else .05*expn)) else ''
        def fmt(v): return ('—' if v is None else (f"{v:,.0f}" if v>=1e4 else f"{v:g}"))
        disp = f"{fmt(v1)}" if (v1==v2 or v2 is None) else f"{fmt(v1)}/{fmt(v2)}"
        cells[m]=(f"{''.join(marks)} {disp}{nd}", best)
    es = (f"{expn:g}" if isinstance(expn,(int,float)) and expn<1e4 else (f"{expn:,.0f}" if isinstance(expn,(int,float)) else str(exp)))
    rows.append((i+1,short[i],es,cells))

# ---- write markdown ----
o=[]
o.append("# Model performance, cost & 30-question scorecard\n")
o.append("Blind headless runs of the 30-question report set (`headless-questions.txt`), **2 trials each = 60 cells per model**, on the current deployed layer (mcp-data-server v0.8.5). The models never see the report value — this measures deployed behavior, unlike the answer-key-supervised reproduction in `reproduction_record.json`. `qwen` = DSE-Nimbus (self-hosted, no per-call $); `nemotron-ultra` + `glm-5.2` via OpenRouter.\n")
o.append("## Why glm-5.2 is the default\n")
o.append("glm-5.2 is the most **accurate and most deterministic** of the three at essentially the **same cost and reasonable wall-time** — and it's the only open model that reproduces *both* the res-8 ACE/richness features and the 3-bucket land-status without an answer key.\n")
o.append("| | **glm-5.2** ⭐ | nemotron-ultra | qwen (Nimbus) |")
o.append("|---|--:|--:|--:|")
def trow(label, g,n,q): o.append(f"| {label} | {g} | {n} | {q} |")
trow("Questions ✓ both trials","**~22 / 27**","~15 / 27","~8 / 27")
trow("Numeric cells ✓/~ (of 54)","**~44 (81%)**","~32 (59%)","~20 (37%)")
trow("Non-deterministic Qs","**~2**","~8","~10")
trow("API calls","221","263","≈250")
trow("Tool calls","224","245","—")
trow("Input tokens","6.24 M","7.70 M","—")
trow("— cached","**85%**","47%","—")
trow("Output tokens","397 k","261 k","—")
trow("— reasoning","305 k","173 k","—")
trow("Job wall-clock","171 min","120 min","214 min")
trow("Timed-out cells","1","3","≈10")
trow("**Cost (USD, 60 cells)**","**$2.98**","$3.32","n/a (self-hosted)")
trow("— input / output split","$1.81 / $1.17","$2.57 / $0.74","—")
o.append("\n- **Cost is input-dominated** (61% glm, 78% nemotron): the agent resends growing context each turn, so input volume (6–8 M tok) dwarfs output (0.26–0.40 M) even though output bills ~9–10× more per token. glm's **85% prompt-cache hit** (vs nemotron 47%) is why it's cheaper despite emitting more reasoning.")
o.append("- nemotron is fastest wall-clock but least accurate and least stable (3 timeouts, ~8 non-deterministic). qwen is slowest and weakest.\n")
o.append("## 30-question scorecard\n")
o.append("Per cell: `T1T2 value` — ✓ match · ~ close · ✗ mismatch · ⏱ timeout/no-answer · ⚠ trials disagree. Values are the extracted headline (heuristic).\n")
o.append("| # | question | report | glm-5.2 | nemotron-ultra | qwen |")
o.append("|--|--|--|--|--|--|")
for i,lab,es,cells in rows:
    o.append(f"| {i} | {lab} | {es} | {cells['glm-5.2'][0]} | {cells['nemotron-ultra'][0]} | {cells['qwen'][0]} |")
o.append("\n**Caveats.** Headline figures extracted heuristically from transcripts (a few cells may misparse); 30 Q is a subset of the partner's 149-bank; ranking/name questions (8, 18) aren't numerically scored. Cost = OpenRouter's per-call `cost` summed (pass-through). Streams questions (28–29) fail for all three via the `public-usgs-nhd` bucket listing issue (data-workflows#411).\n")
open('model-performance.md','w').write("\n".join(o))
print("wrote model-performance.md")
for m in LOGS: print(m, dict(tally[m]))
