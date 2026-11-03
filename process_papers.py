"""Rebuild the analysis CSV and companion tables from the preserved 31-column input.
Requires python-dateutil for strict, day-resolution parsing of mixed source dates.
Run: python process_papers.py
"""
import csv,json,re,collections,datetime,pathlib,html,shutil,zipfile
from dateutil import parser
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'analysis'; OUT.mkdir(exist_ok=True)
DATA=ROOT/'current/Papers7.csv'
CUTOFF=datetime.date(2026,11,2)
with DATA.open(encoding='utf-8-sig',newline='') as f: source=list(csv.reader(f))
history=json.loads((ROOT/'history.json').read_text())
def dt(v):
    v=str(v).strip()
    if not v or re.search(r'unverified|unspecified|not specified|n/a|not yet|no successor',v,re.I):return None
    if re.fullmatch(r'\d{4}(-\d{2})?',v):return None
    if re.fullmatch(r'[A-Za-z]+\s+\d{4}',v):return None
    try:return parser.parse(v,dayfirst=False,fuzzy=False,default=datetime.datetime(1900,1,1)).date()
    except (ValueError,OverflowError):return None
def iso(v):return v.isoformat() if v else ''
def diff(a,b):return (a-b).days if a and b else ''
def write(name,data,headers=None):
    if not data and not headers:return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=headers or list(data[0]));w.writeheader();w.writerows(data)
def canonical(s):
    s=re.sub(r'(?i)chatgpt','GPT',s).strip()
    s=re.sub(r'(?i)^openai\s+','',s)
    t=re.sub(r'[ _-]','',s).lower().replace('gpt4.o','gpt4o')
    aliases={'gpt4.0':'GPT-4','gpt5.0':'GPT-5','basebert':'BERT','sentencebert':'Sentence-BERT','sbert':'Sentence-BERT'}
    for v in ['3.5','4','4o','4.1','4.5','5','5.1','5.2','5.3','5.4','5.5','5.6']:
        aliases['gpt'+v]='GPT-'+v
    for v in ['2','3','3.1','3.2','4']:aliases['llama'+v]='Llama '+v
    aliases.update({'deepseekr1':'DeepSeek R1','gpt4omini':'GPT-4o mini','gpt4.1mini':'GPT-4.1 mini'})
    return aliases.get(t,s)
def vendor(s):
    s=s.lower()
    for label,pat in [('OpenAI',r'gpt|^o[134]'),('Google',r'gemini|bard|palm|gemma'),('Anthropic',r'claude'),('Meta',r'llama'),('DeepSeek',r'deepseek'),('Mistral',r'mistral|mixtral'),('xAI',r'grok'),('Alibaba',r'qwen'),('Microsoft product',r'copilot')]:
        if re.search(pat,s):return label
    return ''
def relationship(family,succ):
    a,b=family.lower(),succ.lower()
    if re.search('no documented|no verified|no successor|not yet',b):return 'No successor documented in input'
    if not b or 'unverified' in b:return 'Unresolved'
    if 'bert' in a or a in ['sbert','xlm-r']:
        if (a=='colbert' and 'colbertv2' in b) or (a=='deberta' and 'debertav2' in b) or (a=='arabert' and 'arabertv2' in b):return 'Same-line version candidate'
        if 'huatuogpt' in b or b=='t5':return 'Different task or architecture; unsupported replacement'
        return 'Related encoder alternative; not direct replacement'
    va,vb=vendor(a),vendor(b)
    if va and vb and va!=vb:return 'Cross-provider alternative; not direct successor'
    if 'different sizes' in b:return 'Different size; comparability review'
    if 'api' in b:return 'API-lineage replacement; product access review'
    if va and va==vb:return 'Same-provider succession candidate'
    return 'Lineage unverified'

code_groups={'30':'Agriculture / veterinary','31':'Biological sciences','32':'Health / clinical','33':'Built environment','34':'Chemical sciences','35':'Business / economics','36':'Arts / humanities','37':'Earth sciences','38':'Business / economics','39':'Education','40':'Engineering','41':'Environment','42':'Health / clinical','43':'History / archaeology','44':'Social sciences','45':'Indigenous studies','46':'Computing','47':'Language / communication','48':'Law','49':'Mathematics','50':'Philosophy / religion','51':'Physical sciences','52':'Psychology'}
keywords=[('Health / clinical',r'clinical|medicine|medical|health|patient care|dentistry|biomedical'),('Education',r'education|pedagogy'),('Computing',r'computing|computer science|informatics'),('Engineering',r'engineering'),('Biological sciences',r'biological|biology'),('Language / communication',r'language|linguistic|communication'),('Business / economics',r'commerce|management|economics|tourism'),('Psychology',r'psychology'),('Social sciences',r'human society|social'),('Law',r'law|legal'),('Environment',r'environment'),('Agriculture / veterinary',r'agricultur|veterinary'),('Mathematics',r'mathematic'),('Physical sciences',r'physical|physics'),('Chemical sciences',r'chemical'),('Arts / humanities',r'arts|writing'),('Built environment',r'built environment'),('Earth sciences',r'earth sciences'),('History / archaeology',r'history|archaeology'),('Philosophy / religion',r'philosophy|religion')]
def field_tags(x):
    text=x[25]; codes=re.findall(r'(?:^|;)\s*(\d{2})\s+[A-Z]',text)
    if codes:return sorted({code_groups[c] for c in codes if c in code_groups}),'Broad source classification codes'
    tags=[label for label,pat in keywords if re.search(pat,text,re.I)]
    # Informatics classified within clinical medicine is not independently computing here.
    if 'Health / clinical' in tags and 'Computing' in tags:tags.remove('Computing')
    if tags:return sorted(set(tags)),'Source Field keyword mapping'
    if x[23] and x[23] not in ('Unspecified','Other fields'):return [x[23]],'Existing provisional field'
    return ['Other / unspecified'],'Insufficient source classification'
def origin(x):
    if 'Dimensions' in x[24]:return 'Dimensions general search'
    if x[27]:return x[27]
    return 'Other searches'
def title_text(c):
    match=re.search(r'\(20\d{2}\)\.\s*(.*)',c)
    return match.group(1).split('. ')[0] if match else c
def bert_role(x,bert):
    if not bert:return 'Not BERT-screened','No BERT-family cue in model list or selected family'
    title=title_text(x[20]);lo=title.lower()
    patterns=[('Method / custom-model candidate',r'quantiz|distill|pre.?train|architecture|hybrid|layer.?wise|adapter|federated|prompt.?tun|fine.?tun|finetun|compression|pruning|improving bert|enhanc.*bert|bert.*enhanc|bert.*bilstm|bert.*cnn|bert.*crf'),('Benchmark / comparison candidate',r'benchmark|comparative|comparison|comparing|comparisons|evaluation of|evaluating|versus'),('Application candidate',r'classification|prediction|predicting|detection|detecting|recognition|sentiment|diagnos|extraction|grading|assessment|identif')]
    for label,pat in patterns:
        m=re.search(pat,lo)
        if m:return label,'Citation-text cue: '+m.group(0)+'; full-text role not verified'
    return 'Role unclear','Model-family cue only; full-text review required'

records=[]; alternatives=[]; fields=[]; audit=[]; bert_review=[]; histories=[]
counts=collections.Counter(x[13] for x in source[1:])
doi_counts=collections.Counter(x[21].strip().lower() for x in source[1:] if x[21].strip())
for rownum,x in enumerate(source[1:],2):
    key=f'P7-{rownum-1:05d}';doi=x[21].strip().lower(); h=history.get(doi,{'status':'missing_doi' if not doi else 'not_queried'})
    f=canonical(x[0]); release=dt(x[1]); successor=dt(x[3]); original_online=dt(x[19]); online=original_online
    received=dt(h.get('received',''));revised=dt(h.get('revised',''));accepted=dt(h.get('accepted',''))
    online_source='Input First online date; not independently verified';hist_source=h.get('source','');hstatus=h['status']
    if h.get('online') and hstatus in ['history_retrieved','xml_history_not_reported']:
        online=dt(h['online']);online_source='Europe PMC JATS electronic publication date'
    if doi=='10.1016/j.ipm.2026.105123':
        received=dt('2026-01-28');revised=dt('2026-07-24');accepted=dt('2026-08-25');online=dt('2026-09-08')
        online_source='User-supplied publisher history';hist_source='User supplied; publisher URL https://www.sciencedirect.com/science/article/pii/S0306457326005133 (automated fetch returned 403)';hstatus='user_supplied_history'
    flags=[]
    if counts[x[13]]>1:flags.append('Repeated source ID; use Record key')
    if not release:flags.append('Release date unresolved')
    if not online:flags.append('Online date unresolved')
    if online and original_online and online!=original_online:flags.append('Analysis online date differs from source')
    if online and online>CUTOFF:flags.append('Online date after analysis cutoff')
    if release and online and release>online:flags.append('Model release after publication')
    if release and successor and successor<release:flags.append('Successor predates model')
    if received and online and received>online:flags.append('Received date after publication')
    if accepted and received and accepted<received:flags.append('Accepted before received')
    if accepted and online and accepted>online:flags.append('Accepted after online; chronology review')
    bert=int(bool(re.search(r'bert|\bxlm-r\b',x[0]+' '+x[15],re.I)))
    selectedbert=bool(re.search(r'bert|\bxlm-r\b',x[0],re.I))
    role,evidence=bert_role(x,bert)
    modelclass='Encoder / BERT-related' if selectedbert else ('Generative language-model family' if vendor(x[0]) else 'Other / unresolved')
    if selectedbert:stratum={'Method / custom-model candidate':'Encoder methodological development','Benchmark / comparison candidate':'Encoder comparison / benchmark','Application candidate':'Encoder application; role review','Role unclear':'Encoder role unresolved'}[role]
    else:stratum='Generative / other; BERT also mentioned' if bert else 'Generative / other'
    tags,fieldbasis=field_tags(x);primary=tags[0] if len(tags)==1 else 'Multidisciplinary'
    pubtype=x[22].strip().lower();pubtype={'article':'Journal article','proceeding':'Conference proceeding','preprint':'Preprint','chapter':'Book chapter','retracted article':'Retracted article'}.get(pubtype,pubtype)
    age=diff(online,release);gap=diff(online,successor)
    # Preserve signed arithmetic for audit; eligibility removes impossible/undated observations.
    ageok=int(isinstance(age,int) and age>=0 and online<=CUTOFF and pubtype!='Retracted article')
    rel=relationship(x[0],x[2]);succok=int(ageok and successor is not None and successor>=release and rel in ['Same-line version candidate','Same-provider succession candidate','API-lineage replacement; product access review'])
    if bert:flags.append('BERT role provisional; no author-awareness inference')
    if rel in ['Cross-provider alternative; not direct successor','Different task or architecture; unsupported replacement','Related encoder alternative; not direct replacement']:flags.append('Selected successor not established as direct replacement')
    if x[0] in ['Gemini','Copilot']:flags.append('Product/version ambiguity despite inherited dates')
    if x[0] in ['Gemini','Copilot']:ageok=0;succok=0
    if ' / ' in x[2] or 'tier unspecified' in x[2].lower():
        flags.append('Successor branch or tier unresolved');succok=0
    agebin='' if not isinstance(age,int) or age<0 else ('<6 months' if age<183 else '6–<12 months' if age<365 else '1–<2 years' if age<730 else '2–<3 years' if age<1095 else '3+ years')
    r=dict(zip(source[0][:4],x[:4]))
    r.update({'ID-c':x[4],'Source sequence ID':x[11],'ID':x[13]})
    for j in range(19,29):r[source[0][j] if j!=28 else 'Field provisional (duplicate source)']=x[j]
    r.update({'Record key':key,'Models reported (source)':x[15],'Canonical selected family':f,'Analysis online date':iso(online),'Online date basis':online_source,'Model age (days)':age,'Successor gap (days)':gap,'After successor (1/0)':int(gap>=0) if isinstance(gap,int) else '', 'Publication year':online.year if online else '', 'Model age band':agebin,'Model class':modelclass,'BERT present (screen)':bert,'BERT use (provisional)':role,'Suggested analysis stratum':stratum,'Field analysis group':primary,'Field tags':'; '.join(tags),'Publication type analysis':pubtype,'Origin cohort':origin(x),'Selected successor relationship':rel,'Model age arithmetic eligible (1/0)':ageok,'Successor lineage screen eligible (1/0)':succok,'Release mapping verification':'Inherited input; external verification pending','Received date':iso(received),'Last reported revised date':iso(revised),'Accepted date':iso(accepted),'Release to received (days)':diff(received,release),'Received to accepted (days)':diff(accepted,received),'Accepted to online (days)':diff(online,accepted),'Received to online (days)':diff(online,received),'History status':hstatus,'History source':hist_source,'Review flags':'; '.join(flags)})
    records.append(r)
    for tag in tags:fields.append({'Record key':key,'DOI':doi,'Field tag':tag,'Field assignment basis':fieldbasis,'Number of field tags':len(tags),'Fractional weight':1/len(tags)})
    histories.append({'Record key':key,'DOI':doi,'History status':hstatus,'Received':iso(received),'Last reported revision':iso(revised),'Accepted':iso(accepted),'Analysis online':iso(online),'Source':hist_source,'Retrieved on':h.get('retrieved_on',str(CUTOFF)),'Raw history events':json.dumps(h.get('history_events',{})),'Metadata online candidate (not automatically applied)':h.get('metadata_online','')})
    if bert:bert_review.append({'Record key':key,'DOI':doi,'Citation':x[20],'Models reported':x[15],'Provisional role':role,'Evidence':evidence,'Annotation confidence':'Low; automated citation/model screening','Verified role':'','Model choice rationale':'Not assessed','Evidence of author awareness':'Not assessed; cannot infer from model age','Full-text evidence quote':'','Reviewer decision':'Pending','Backbone date':x[1] if selectedbert else '', 'Custom model release date':'','Recommended action':'Review full text before role-based exclusions; code each model separately if mixed'})
    candidates=[(x[2],x[3],'Selected mapping in B-D','Inherited mapping; not externally verified','')]
    if x[9] and (x[9],x[10])!=(x[2],x[3]):candidates.append((x[9],x[10],'Previous mapping in J-K','Inherited alternative; not externally verified',''))
    if f=='GPT-4':
        candidates.append(('GPT-4o','2024-05-13','Later flagship comparison scenario','Official announcement date verified; task and access comparability require review','https://openai.com/index/hello-gpt-4o/'))
    if f in ['GPT-3.5','GPT-3.5 Turbo']:
        candidates.append(('GPT-4','2023-03-14','Official GPT-4 announcement scenario','Official announcement date verified; original mapping retained in first four columns','https://openai.com/index/gpt-4-research/'))
    if selectedbert:
        for name,date,url in [('RoBERTa','2019-07-26','https://arxiv.org/abs/1907.11692'),('ModernBERT','2024-12-18','https://arxiv.org/abs/2412.13663')]:
            if name.lower() not in x[0].lower():candidates.append((name,date,'Encoder comparison scenario','Paper-first-public date verified; checkpoint availability and suitability unverified',url))
        if 'Health / clinical' in tags:candidates.append(('PubMedBERT','2020-07-31','Biomedical encoder comparison scenario','Paper-first-public date verified; checkpoint availability and suitability unverified','https://arxiv.org/abs/2007.15779'))
    names=[]
    for z,(name,date,scenario,status,url) in enumerate(candidates,1):
        when=dt(date);d=diff(online,when)
        relation=relationship(x[0],name) if 'scenario' not in scenario else 'Task-relevant alternative candidate; not direct successor'
        alternatives.append({'Record key':key,'DOI':doi,'Scenario':scenario,'Candidate':name,'Candidate date (source)':date,'Candidate date ISO':iso(when),'Date basis':('Official model announcement' if 'openai.com' in url else 'Paper first public appearance; NOT a verified checkpoint release') if url else 'Inherited release mapping','Relationship':relation,'Verification':status,'Source URL':url,'Publication minus candidate date (days)':d,'Published on or after candidate date (1/0)':int(d>=0) if isinstance(d,int) else '', 'Candidate existed by received date (date proxy)':int(when<=received) if when and received else '', 'Provisional lineage screen (not verification)':0 if 'scenario' in scenario or selectedbert else succok})
        if z>1:names.append(name)
    r['Alternative comparison candidates']='; '.join(dict.fromkeys(names))
    r['History chronology eligible (1/0)']=int(bool(received and accepted and online and received<=accepted<=online<=CUTOFF))
    audit.append({'Record key':key,'DOI':doi,'Source CSV row':rownum,'Original online':x[19],'Analysis online':iso(online),'Original model age':x[16],'Recomputed model age':age,'Original successor gap':x[17],'Recomputed successor gap':gap,'Original after successor':x[18],'Recomputed after successor':r['After successor (1/0)'],'Original review flags':x[6],'New review flags':r['Review flags']})

write('Papers7.csv',records);write('successor_scenarios.csv',alternatives);write('field_memberships.csv',fields);write('bert_review_queue.csv',bert_review);write('publication_histories.csv',histories);write('recalculation_audit.csv',audit)
summary={'records':len(records),'unique_dois':len(doi_counts),'repeated_ID_extra_occurrences':sum(n-1 for n in counts.values() if n>1),'bert_screened':len(bert_review),'bert_roles':dict(collections.Counter(r['Provisional role'] for r in bert_review)),'field_groups':dict(collections.Counter(r['Field analysis group'] for r in records)),'history_status':dict(collections.Counter(r['History status'] for r in records)),'received_dates':sum(bool(r['Received date']) for r in records),'accepted_dates':sum(bool(r['Accepted date']) for r in records),'online_dates_changed':sum(bool(r['Original online']) and dt(r['Original online'])!=dt(r['Analysis online']) for r in audit),'model_age_eligible':sum(r['Model age arithmetic eligible (1/0)'] for r in records),'successor_lineage_screen_eligible':sum(r['Successor lineage screen eligible (1/0)'] for r in records),'successor_scenarios':len(alternatives),'case':[r for r in records if r['DOI'].lower()=='10.1016/j.ipm.2026.105123'][0]}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
# Invariants: raw requested columns are retained byte-for-byte as CSV field values.
assert len(records)==2611 and len({r['Record key'] for r in records})==2611
for x,r in zip(source[1:],records):
    assert list(r.values())[:4]==x[:4]
    for j in range(19,29):assert r[source[0][j] if j!=28 else 'Field provisional (duplicate source)']==x[j]
    if all(r[k] for k in ['Received date','Accepted date','Analysis online date']):
        assert r['Received to accepted (days)']+r['Accepted to online (days)']==r['Received to online (days)']
print(json.dumps({k:v for k,v in summary.items() if k!='case'},indent=2))
print('Case metrics:',{k:v for k,v in summary['case'].items() if '(days)' in k})
