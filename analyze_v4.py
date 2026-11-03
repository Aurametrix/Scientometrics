from pathlib import Path
import pandas as pd,numpy as np,json,re,hashlib,shutil
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
R=Path(__file__).resolve().parent
src=R/'papersAIevals4.csv';book=R/'prior_analysis.xlsx'
d=pd.read_csv(src,dtype=str).fillna('');d['excluded_dupe']=d.ID.str.strip().str.upper().str.startswith('DUPE');d['release']=pd.to_datetime(d.iloc[:,2],format='mixed',errors='coerce');d['online']=pd.to_datetime(d['First online date'],format='mixed',errors='coerce');d['age_days']=(d.online-d.release).dt.days;d['type']=d['Publication Type'].str.strip().str.lower();d['doi_key']=d.DOI.str.lower().str.strip();d['repeated_doi']=d.doi_key.ne('')&d.doi_key.duplicated(False)
d['age_eligible']=~d.excluded_dupe&d.age_days.ge(0)&d.online.le('2026-10-24')
old=pd.read_excel(book,sheet_name='Papers').set_index('Record ID');orig=pd.read_excel(book,sheet_name='Original data').set_index('ID');reg=pd.read_excel(book,sheet_name='Model register');reg.to_csv(R/'model_register_inherited.csv',index=False)
norm=lambda v:re.sub(r'\s+',' ',str(v)).strip().lower()
for c in ['mapped_family','successor','mapping_status']:d[c]=''
for c in ['mapped_release','successor_release','alternative_release']:d[c]=pd.NaT
d['successor_eligible']=False
for i,r in d.iterrows():
 if r.excluded_dupe: d.at[i,'mapping_status']='DUPE excluded';continue
 if r.ID not in old.index or r.ID not in orig.index:d.at[i,'mapping_status']='No prior mapping';continue
 o=old.loc[r.ID];raw=orig.loc[r.ID]
 if isinstance(o,pd.DataFrame):d.at[i,'mapping_status']='Ambiguous prior ID';continue
 for dest,source in [('mapped_family','Latest recognized family'),('successor','Selected successor'),('mapped_release','Mapped release'),('successor_release','Successor release'),('alternative_release','Alternate successor release')]:d.at[i,dest]=o[source]
 if norm(r.MODEL)!=norm(raw.MODEL):status='Model description changed; needs remapping'
 elif o['Mapping assessment']!='Family/date matched':status=str(o['Mapping assessment'])
 elif pd.isna(o['Mapped release']) or pd.isna(r.release) or abs((r.release-o['Mapped release']).days)>31:status='Updated release disagrees with mapping'
 elif pd.isna(o['Successor release']):status='No successor date established'
 elif not r.age_eligible:status='Invalid age/date'
 elif o['Successor release']<=o['Mapped release']:status='Invalid successor chronology'
 else:status='Eligible inherited mapping';d.at[i,'successor_eligible']=True
 d.at[i,'mapping_status']=status
d['superseded']=np.where(d.successor_eligible,(d.online>=d.successor_release).astype(float),np.nan)
d['days_since_successor']=np.where(d.successor_eligible,(d.online-d.successor_release).dt.days,np.nan)
d['cycle_days']=(d.successor_release-d.mapped_release).dt.days
d['cycle_fraction']=np.where(d.successor_eligible,(d.online-d.mapped_release).dt.days/d.cycle_days,np.nan)
def field(r):
 f=r.Field.lower()
 if f in ['', 'zzz']:return 'Unclassified'
 if 'programming education' in f:return 'Programming education'
 for pat,label in [('dermat','Dermatology'),('radiolog','Radiology'),('informat','Informatics'),('medical education|licensing','Medical education'),(r'surgery|surgical|orthop|ophthalm|\burolog|otolaryng','Surgical specialties'),('neurolog','Neurology'),('oncolog|cancer','Oncology')]:
  if re.search(pat,f):return label
 if r.ID.startswith(('HC','CM','D')):return 'Other health / biomedical'
 return 'Other fields'
d['field_group']=d.apply(field,axis=1);d.to_csv(R/'records_audit.csv',index=False)
a=d[d.age_eligible];s=d[d.successor_eligible];rng=np.random.default_rng(20261024)
def summary(g,label):
 x=g.age_days.to_numpy();ci=np.quantile(rng.choice(x,(5000,len(x)),replace=True).mean(1),[.025,.975]);return [label,len(x),x.mean(),np.std(x,ddof=1),np.median(x),np.quantile(x,.25),np.quantile(x,.75),*ci,100*np.mean(x>=365)]
cols=['group','n','mean_days','sd_days','median_days','q1','q3','mean_ci_low','mean_ci_high','pct_at_least_365']
tables={'overall':pd.DataFrame([summary(a,'All age-eligible records')],columns=cols)}
for name,col in [('publication_type','type'),('fields','field_group')]:tables[name]=pd.DataFrame([summary(g,k) for k,g in a.groupby(col)],columns=cols)
def wilson(k,n):
 z=1.96;p=k/n;mid=(p+z*z/(2*n))/(1+z*z/n);half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n);return 100*(mid-half),100*(mid+half)
rows=[]
for label,g in [('All mapped records',s)]+list(s.groupby('type')):
 n=len(g);k=int(g.superseded.sum());lo,hi=wilson(k,n);rows.append([label,n,k,100*k/n,lo,hi,g.loc[g.superseded.eq(1),'days_since_successor'].median(),g.cycle_fraction.median()])
tables['successor']=pd.DataFrame(rows,columns=['group','n','successor_already_available','percent','ci_low','ci_high','median_days_past_successor_among_superseded','median_cycle_fraction'])
# Explicit sensitivity analyses preserve the requested ID rule in the primary cohort.
collision=d.doi_key.isin(['10.20944/preprints202411.2377.v1','10.1016/j.jpurol.2023.08.003'])
tables['sensitivity']=pd.DataFrame([summary(a,'Requested DUPE rule; valid dates'),summary(d[d.age_eligible&~collision],'Exclude known DOI/date collision clusters'),summary(d[d.age_eligible&~d.repeated_doi],'Exclude every repeated-DOI record')],columns=cols)
alt=s.alternative_release.fillna(s.successor_release);altpct=100*(s.online>=alt).mean();strict=s[s.release.eq(s.mapped_release)]
x=a[a.type=='article'].age_days.to_numpy();y=a[a.type=='preprint'].age_days.to_numpy();diff=rng.choice(x,(5000,len(x)),True).mean(1)-rng.choice(y,(5000,len(y)),True).mean(1)
meta=dict(raw=len(d),dupe_excluded=int(d.excluded_dupe.sum()),retained=int((~d.excluded_dupe).sum()),age_n=len(a),invalid_or_missing_age=int((~d.excluded_dupe&~d.age_eligible).sum()),successor_n=len(s),successor_percent=100*s.superseded.mean(),alternative_successor_percent=altpct,exact_release_match_n=len(strict),exact_release_match_percent=100*strict.superseded.mean(),unknown_successor_n=int((~d.excluded_dupe&~d.successor_eligible).sum()),article_minus_preprint_days=x.mean()-y.mean(),difference_ci=np.quantile(diff,[.025,.975]).tolist(),welch_p=stats.ttest_ind(x,y,equal_var=False).pvalue,seed=20261024,input_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
(R/'results.json').write_text(json.dumps(meta,indent=2));d[~d.excluded_dupe&d.repeated_doi].to_csv(R/'remaining_doi_collisions.csv',index=False);d[~d.excluded_dupe].mapping_status.value_counts().to_csv(R/'mapping_coverage.csv')
for n,t in tables.items():t.to_csv(R/f'table_{n}.csv',index=False)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
fig,ax=plt.subplots(1,2,figsize=(10,4));ax[0].hist(a.age_days/30.4375,bins=35,color='#176B87');ax[0].set(xlabel='Recorded model age (months)',ylabel='Records',title='Model age distribution')
for typ,c in [('article','#176B87'),('preprint','#D77732')]:
 v=np.sort(a.loc[a.type==typ,'age_days']/30.4375);ax[1].step(v,np.arange(1,len(v)+1)/len(v),label=f'{typ} (n={len(v)})',color=c)
ax[1].set(xlabel='Model age (months)',ylabel='Cumulative proportion');ax[1].legend();fig.tight_layout()
def save(fig,name):
 for ext in ['png','pdf','svg']:fig.savefig(R/f'{name}.{ext}',bbox_inches='tight')
 plt.close(fig)
save(fig,'figure1_age')
t=tables['fields'].query('n>=20').sort_values('mean_days');fig,ax=plt.subplots(figsize=(9,4));ax.errorbar(t.mean_days/30.4375,np.arange(len(t)),xerr=np.vstack([t.mean_days-t.mean_ci_low,t.mean_ci_high-t.mean_days])/30.4375,fmt='o',capsize=3,color='#176B87');ax.set_yticks(np.arange(len(t)),[f'{r.group} (n={r.n})' for r in t.itertuples()]);ax.set_xlabel('Mean model age in months (95% bootstrap CI)');fig.tight_layout();save(fig,'figure2_fields')
fig,ax=plt.subplots(1,2,figsize=(10,4));t=tables['successor'];ax[0].bar(t.group,t.percent,color=['#718096','#176B87','#D77732'][:len(t)]);ax[0].errorbar(t.group,t.percent,yerr=np.vstack([t.percent-t.ci_low,t.ci_high-t.percent]),fmt='none',color='black',capsize=4);ax[0].set(ylim=(0,105),ylabel='Successor available at online date (%)',title=f'Eligible inherited mappings (n={len(s)})');ax[0].tick_params(axis='x',labelsize=8);ax[1].hist(s.days_since_successor,bins=30,color='#176B87');ax[1].axvline(0,color='#D77732');ax[1].set(xlabel='Days after successor release (negative = before)',ylabel='Records',title='Timing relative to selected successor');fig.tight_layout();save(fig,'figure3_successors')
styles=getSampleStyleSheet();styles['BodyText'].leading=14;styles['BodyText'].spaceAfter=9;story=[];text=[]
def para(v,style='BodyText'):story.append(Paragraph(v,styles[style]));text.append(v)
def table(headers,rows):
 z=Table([[Paragraph(str(v),styles['BodyText']) for v in row] for row in [headers]+rows],colWidths=[210]+[92]*(len(headers)-1),repeatRows=1);z.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEAF0')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F3F6F8')])]));story.append(z);story.append(Spacer(1,12))
def page():story.append(PageBreak())
def image(n,h=220):story.append(Image(str(R/f'{n}.png'),width=490,height=h))
o=tables['overall'].iloc[0]
para('AI model age and successor availability','Title');para('Updated exploratory analysis | papersAIevals4.csv | 24 October 2026')
para(f'The updated dataset contains {len(d):,} records. Excluding IDs beginning with DUPE (case-insensitive, ignoring leading spaces) removes {meta["dupe_excluded"]}, leaving {meta["retained"]}. All other records remain in the requested cohort; age calculations require nonnegative, available dates no later than the analysis date. This gives {len(a)} age-eligible records.')
para(f'Mean recorded model age is {o.mean_days:.1f} days ({o.mean_days/30.4375:.1f} months; 95% bootstrap CI {o.mean_ci_low:.1f}-{o.mean_ci_high:.1f} days). Median age is {o.median_days:.0f} days (IQR {o.q1:.0f}-{o.q3:.0f}); {o.pct_at_least_365:.1f}% are at least one year old.')
table(['Publication type','n','Mean months','Median months'],[[r.group,r.n,f'{r.mean_days/30.4375:.1f}',f'{r.median_days/30.4375:.1f}'] for r in tables['publication_type'].itertuples()])
para(f'Articles average {meta["article_minus_preprint_days"]:.1f} days older than preprints (95% bootstrap CI {meta["difference_ci"][0]:.1f}-{meta["difference_ci"][1]:.1f}; Welch p={meta["welch_p"]:.3g}). These are unadjusted associations within a selected bibliography, not estimates of peer-review delay.')
para(f'Among {len(s)} records with eligible inherited model-successor mappings, {meta["successor_percent"]:.1f}% were online after the selected successor became available. The remaining {meta["unknown_successor_n"]} retained records have unresolved or unavailable successor classifications. They are not counted as current models.')
para('Model age and successor availability are distinct outcomes. A successor being available does not prove that an older model is unsuitable, inferior for the task, or irrelevant to deployed systems. The successor results below are conditional on the supplied workbook definitions and have not been independently source-verified in this revision.')
page();para('Model age: distribution and fields','Title');image('figure1_age',205);image('figure2_fields',225)
para('Figure 1: age distribution and empirical cumulative distributions. Figure 2: field means with 95% percentile bootstrap intervals; only groups with at least 20 records are plotted. Complete field tables include smaller groups. One month equals 30.4375 days. Fields are harmonized using explicit keyword rules in the code.')
page();para('Successor availability at publication','Title');image('figure3_successors',205)
table(['Mapped group','n','Successor available','Percent'],[[r.group,r.n,r.successor_already_available,f'{r.percent:.1f}%'] for r in tables['successor'].itertuples()])
para(f'Among superseded mapped records, median time since successor release is {s.loc[s.superseded.eq(1),"days_since_successor"].median():.0f} days. Median model age divided by the selected release-to-successor interval is {s.cycle_fraction.median():.2f}. A ratio above 1 means the paper appeared after the chosen successor date; it does not count how many actual generations had elapsed.')
para(f'Using the workbook alternative successor dates where available changes the superseded proportion to {altpct:.1f}%. Restricting to exact agreement between the updated release date and inherited mapped release gives {len(strict)} records and {meta["exact_release_match_percent"]:.1f}% superseded. This sensitivity matters because successor definitions mix previews, major releases, and product-line migrations.')
para('The chosen successor is the one associated with the workbook\'s latest recognized model family. Multi-model papers can contain additional families whose successors are not represented. No-successor-date records are unresolved, not automatically current. The fraction superseded must always be reported with the eligible-mapping denominator.')
page();para('Methods, exclusions, and reproducibility','Title')
para('The CSV supplies IDs, model descriptions, dates, fields, and Publication Type. Its article/preprint/chapter categories are used directly. No old duplicate decisions, DOI-based deletion, or earlier classification is silently carried forward. Missing or negative ages affect eligibility for that metric only. All original rows and flags are retained in records_audit.csv.')
para('Model mapping transfer: join to the prior workbook by exact ID; require identical model description after case/whitespace normalization; require prior Mapping assessment = Family/date matched; require updated release within 31 days of mapped release; and require a valid later successor date and valid paper age. The 31-day allowance accommodates month-level dating and is tested by exact-date sensitivity. Changed models and conflicting or uncertain mappings are explicitly unresolved. Prior duplicate-based eligibility flags are not reused. All successor indicators are recalculated with updated online dates.')
para('Statistics: 5,000 record bootstrap resamples, seed 20261024, for mean confidence intervals and the article-preprint mean difference; Wilson 95% intervals for successor proportions; Welch test for the unadjusted age difference. These exploratory intervals assume independent records and omit uncertainty in extraction, model mapping, and source selection. Remaining duplicates can exaggerate precision. No population-wide or causal inference is justified.')
para('The older workbook is supplementary mapping evidence, not an authoritative current dataset. Its release dates, successors, alternative dates, definitions, and source links are exported in model_register_inherited.csv. No external URLs were used to overwrite the updated CSV. A full source audit is still needed before publication-grade obsolescence claims.')
para('Reproduce: place the supplied CSV and workbook alongside analyze_v4.py as papersAIevals4.csv and prior_analysis.xlsx; run python analyze_v4.py. Dependencies: pandas, numpy, scipy, matplotlib, openpyxl, reportlab. The archive includes inputs, code, full numerical tables, all record decisions, and PNG/PDF/SVG figures. results.json records seed and input hash.')
page();para('Remaining data issues and sensitivity','Title')
para(f'{int((~d.excluded_dupe&d.repeated_doi).sum())} retained rows share nonempty DOI values with another source row. This flag includes pairs where the other row was already marked DUPE. The audit file lists them; these are candidates for review, not automatic duplicate findings. Some DOI clusters represent different titles incorrectly assigned the same identifier.')
table(['Age sensitivity cohort','n','Mean days','Median days'],[[r.group,r.n,f'{r.mean_days:.1f}',f'{r.median_days:.1f}'] for r in tables['sensitivity'].itertuples()])
para('Known collisions include the repeated theoretical-physics preprint DOI assigned to distinct arXiv papers and the shared pediatric/female-urology DOI. The first sensitivity excludes these two clusters. The second removes every repeated-DOI record, including retained records whose only partner is already DUPE-marked; it is deliberately conservative, not a preferred deduplication procedure.')
para('Recorded First online date is not necessarily the earliest public preprint date. Unspecified snapshots, inferred model identity, month-start release placeholders, month-end online dates, and mixed model lists limit precision. Negative ages can signal mismatched paper versions and model versions. Publication year is not substituted for missing full online dates.')
para('Interpretation: the revised data can describe the age of evaluated technology and, for a clearly stated mapped subset, whether a selected successor existed at the recorded online date. It cannot establish that the same fraction of all academic research was technologically obsolete on first public release. Future refinement should link study versions and model snapshots and verify successor availability under a consistent rule.')
SimpleDocTemplate(str(R/'AI_Model_Currency_v4_Report.pdf'),pagesize=(612,792),leftMargin=45,rightMargin=45,topMargin=40,bottomMargin=40).build(story)
(R/'Report_text.txt').write_text('\n\n'.join(text));print(json.dumps(meta,indent=2))
