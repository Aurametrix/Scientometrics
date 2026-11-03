import csv,json,pathlib,html,shutil,zipfile,collections
R=pathlib.Path(__file__).resolve().parent;O=R/'analysis'
s=json.loads((O/'summary.json').read_text()); c=s['case']
readme='''# Papers7 analysis guide

## What was changed
The main CSV retains all 2,611 source records, the first four columns unchanged, ID-c,
ID and the former column L as Source sequence ID. The ten requested trailing source
columns are retained unchanged. The second identically named Field provisional is
renamed Field provisional (duplicate source). Source model descriptions are retained
because a selected family alone is insufficient evidence about model use.
The redundant H-K mapping and old numerical lag columns are removed from the main
table. Their alternatives and original values remain in the scenario and audit tables.
All dates used for arithmetic are parsed as month/day/year for numeric slash dates.
ISO and explicit named-month dates are also accepted. Unknown dates remain missing,
not zero. Source strings are preserved. The analysis cutoff is 2026-11-02.

## Join and count correctly
Record key is the unique within-snapshot join key. IDs are NOT unique: 816 extra
occurrences are present. Do not join on ID alone. No records were deduplicated or
removed. There are 2,610 nonempty unique DOI strings and one missing DOI; this does not rule out preprint/journal
versions of the same underlying study. Use DOI for cross-snapshot identity and check
version families before treating observations as independent studies.

## Measures
Model age (days) = Analysis online date - Mapped release.
Successor gap (days) = Analysis online date - Successor release. Positive means the
paper appeared after the selected successor date; negative means before.
After successor = 1 when gap >= 0, 0 when gap < 0, missing when date unavailable.
Same-day publication is included in 1; day precision cannot establish event order.
Release to received = Received - Mapped release. This is model age at journal receipt,
not the date of model choice, experiment completion, or evidence of lack of awareness.
Received to accepted includes author revision time as well as editorial/reviewer time.
Accepted to online is the post-acceptance interval.
Received to online is their sum when all three dates are known.
The most recent REPORTED revision is retained; it may not describe every revision round.

Signed arithmetic is retained for anomaly review. For descriptive model-age plots,
filter Model age arithmetic eligible = 1. This only screens chronology, missing dates,
cutoff, retraction label, and selected obvious product ambiguity. It does NOT validate
model identity or inherited release dates. For successor plots, additionally require
Successor lineage screen eligible = 1 and independently review mapping provenance.
That screen is provisional, not a claim of direct replacement, practical availability,
task superiority, or technological obsolescence. For full three-date editorial
decomposition, require History chronology eligible = 1.

## Publication dates and provenance
First online date remains the ORIGINAL source field. Analysis online date is the date
actually used. Explicit electronic-publication dates extracted from article XML take
precedence. Untyped publication dates, repository release dates, collection dates and
indexing dates do not replace it. The user's supplied history overrides the CulturalProbe
case and is labelled user-supplied, not independently page-verified (publisher fetch 403).
Source citation year is not rewritten even when it reflects a later print issue year.
Metadata online candidates from Europe PMC are retained in the history table for review,
but are not automatically used. History extraction is DOI matched and cached.

## BERT screening, not a full-text review
BERT present screens the selected family AND source model list for BERT / XLM-R cues.
It is broader than original BERT and includes encoder relatives. It is not exhaustive
for all encoder architectures and not an assertion of which model is primary.
Provisional roles are reproducible keyword screens of citation text/model names:
method/custom-model candidate, benchmark/comparison candidate, application candidate,
or unclear. Fine-tuning keywords can be routine adaptation; they do NOT establish
innovation. A named custom model may have been developed in an earlier paper.
No paper is labelled ignorant, unaware or obsolete. Model choice rationale and awareness
are Not assessed. No baseline-only classification is inferred without full-text evidence.

Use bert_review_queue.csv to record the verified role, exact full-text evidence, model
choice rationale and reviewer decision. Review methods, experimental settings, ablations
and baseline tables. Multi-model papers may need multiple role labels and model-specific
dates. Keep innovations/custom-model development and baseline-only uses in separate
strata; include clearly identified applied uses in an application analysis. Do not exclude
papers simply because the rationale for using BERT is not reported. Validate the automated
screen against independently double-coded examples before using its role labels as final.

## Successor scenarios
successor_scenarios.csv is LONG format: one row per paper and comparison scenario.
It includes selected B-D mappings, differing former J-K mappings, GPT-4o as a later
flagship scenario for GPT-4, and an official GPT-4 announcement date scenario for GPT-3.5.
For selected BERT-family papers, related encoder candidates include RoBERTa, ModernBERT,
and PubMedBERT for health-classified records. These are research comparison candidates,
not universal replacements. Language, domain, compute, license, task, tuning method and
checkpoint access must be checked. Sentence embeddings and molecular encoders cannot
automatically be substituted with general text encoders.
Verified arXiv dates are PAPER-FIRST-PUBLIC dates, not verified checkpoint release dates:
RoBERTa 2019-07-26; ModernBERT 2024-12-18; PubMedBERT 2020-07-31.
This also exposes why the inherited ModernBERT date 2024-12-19 must not be silently
interpreted as the same event. Candidate existence at receipt uses that explicit date
proxy, not verified practical access. Negative gaps are retained; do not treat a later
alternative as available to authors earlier. Compare ONE scenario per paper at a time.
Never stack scenario rows and count them as independent papers.

## Fields and sampling
Field analysis group uses broad classification codes in source Field where supplied;
otherwise it uses explicit discipline keywords and then the existing provisional field.
Multiple broad domains are labelled Multidisciplinary. field_memberships.csv keeps each
domain separately, with 1/n fractional weights for totals that should sum to paper count.
These are SOURCE DISCIPLINE tags, not a validated application-domain classification.
A computing-classified medical application can still need a separate application tag.
Origin cohort records the search/review source; it is not country or author affiliation.
Publication type analysis standardizes case and separates preprints, proceedings,
chapters, journal articles and explicitly labelled retractions.

For initial visualizations: facet model-age distributions by Model class / Canonical
selected family, Publication year, Field analysis group and Publication type analysis.
Show n and missingness. Compare medians and IQRs rather than means alone. Separate
source cohorts or use a common sampling frame; clinical-review and general-search
records are not automatically comparable. Avoid ranking fields without adjusting for
model family, year, publication type and sampling source. Use DOI/study clusters where
multiple versions are linked. Report 2023 as a launch-period cohort and repeat comparisons
with matched follow-up since release; adding BERT does not eliminate the launch-window
constraint. Do not assume administrative truncation disappears after stratification.

## Automated acquisition and next steps
harvest_history.py uses the public Europe PMC search API in DOI batches, then retrieves
available open-access full-text XML. It reads JATS article-meta/history and explicitly
tagged article-history notes in front matter. It never scans reference-list dates.
Missing history fields, no matching record, metadata-only, and failed requests are
different statuses. It caches responses, retries transient failures, uses eight workers
to tolerate latency, and globally limits new requests to two per second.
Run: python harvest_history.py current/Papers7.csv history.json --xml-limit 0
Run: python process_papers.py
Run: python package_analysis.py
Python 3 is required; process_papers.py additionally uses python-dateutil.
The cache is deliberately excluded from this package; it contains source article XML.
The extracted history.json is included, so the processed tables are reproducible offline.

For unresolved records, next use PubMed XML editorial history where available, then
publisher-specific APIs/XML/HTML, then permitted PDFs. Those fallback adapters are a
recommended next stage, NOT implemented by this script. For Elsevier, use its Article
Retrieval API with a user-obtained key and any required institutional entitlement rather
than scraping blocked ScienceDirect pages. For public HTML, save the labeled history
snippet and URL and use publisher-specific parsers. Avoid broad date regexes over full
papers, which can capture dates from references and funding statements. For PDF fallback,
extract the first-page history region and review OCR-derived dates. Do not bypass access
controls. Cache by DOI, log failures, and make reruns idempotent.

Crossref created/deposited/indexed dates are NOT submission, acceptance or study dates.
Europe PMC dateOfCreation/dateOfRevision/fullTextReceivedDate are also not editorial
history dates. Never use them as substitutes. Crossref published-online is a publication
candidate, not proof of study timing. Authors rarely report model-choice dates, so even
complete journal histories do not fully separate research execution from publication.

Missing histories are not a random subset. Compare retrieval rates by publisher prefix,
field, year, type and source cohort. Report full-cohort model-age descriptions separately
from the history-available subset. Do not impute missing submission dates with an overall
average. Sensitivity analyses can bound plausible pre-submission ages, but must label the
assumptions and avoid conclusions about author motives.

## Sources checked
https://jats.nlm.nih.gov/publishing/tag-library/1.3/element/history.html
https://dev.europepmc.org/RestfulWebService
https://dev.elsevier.com/documentation/ArticleRetrievalAPI.wadl
https://dev.elsevier.com/tecdoc_text_mining.html
https://github.com/CrossRef/rest-api-doc/blob/master/api_format.md
https://arxiv.org/abs/1907.11692
https://arxiv.org/abs/2412.13663
https://arxiv.org/abs/2007.15779
https://openai.com/index/gpt-4-research/
https://openai.com/index/hello-gpt-4o/
'''
(O/'README.md').write_text(readme,encoding='utf-8')
with (O/'Papers7.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f));headers=list(rows[0])
defs={
'Record key':'Unique within this snapshot. Join companion tables on this field; original IDs repeat.',
'Analysis online date':'ISO date actually used; explicit XML electronic date or user-provided history, else original source date.',
'Model age (days)':'Analysis online date minus Mapped release; signed whole days. Not editorial lag.',
'Successor gap (days)':'Analysis online date minus Successor release; signed whole days. Not time between model releases.',
'After successor (1/0)':'1 if successor gap >= 0; 0 if < 0; blank if dates missing.',
'Release to received (days)':'Received date minus Mapped release. Not model-choice age.',
'Received to accepted (days)':'Accepted minus Received; includes revisions and editorial processes.',
'Accepted to online (days)':'Analysis online minus Accepted.',
'Received to online (days)':'Analysis online minus Received.',
'Model age arithmetic eligible (1/0)':'Date and cutoff screen only; inherited release mapping remains unverified.',
'Successor lineage screen eligible (1/0)':'Provisional chronology and lineage screen. Not external validation, task equivalence or obsolescence.',
'History chronology eligible (1/0)':'Received <= Accepted <= Analysis online <= cutoff, with all three dates present.',
'BERT present (screen)':'BERT/XLM-R cue in selected family or source model list; 1/0.',
'BERT use (provisional)':'Automated citation/model cue; full-text role unverified. See BERT review queue.',
'Suggested analysis stratum':'Separates encoder methods, comparisons, applications and uncertain/mixed generative records.',
'Field analysis group':'Normalized source discipline; Multidisciplinary when multiple broad source domains.',
'Field tags':'Semicolon-separated source domains; use field_memberships.csv for long format.',
'Origin cohort':'Sampling/search source cohort, not geography.',
'Model age band':'Day-based bins: <183, 183–364, 365–729, 730–1094, >=1095.',
'Publication year':'Year of Analysis online date; can differ from citation print year.',
'Canonical selected family':'Conservative case/name aliases for grouping; not a verified checkpoint.',
'Models reported (source)':'Original MODEL cell; includes multiple models where supplied.',
'Selected successor relationship':'Rule-based lineage/task distinction; requires reviewer verification.',
'Release mapping verification':'Inherited dates have not been comprehensively independently checked.',
'Last reported revised date':'Latest reported revision-received date; not necessarily all revision rounds.',
'Received date':'Editorial received date from XML or supplied case; blank means not available from completed route.',
'Accepted date':'Editorial acceptance date from XML or supplied case.',
'History status':'Retrieved, user supplied, XML history not reported, metadata only, not found, or request failed.',
'History source':'Exact retrieval endpoint or explicit user-provided provenance.',
'Alternative comparison candidates':'Convenience summary; dates and scenario definitions are in successor_scenarios.csv.',
'Online date basis':'Provenance of Analysis online date.',
'Model class':'Selected-family architecture grouping; encoder-related vs generative vs unresolved.',
'Publication type analysis':'Normalized journal article, conference proceeding, preprint, book chapter or retracted article.',
'Review flags':'Semicolon-separated chronology, identity and interpretability issues; see audit table.',
'Source sequence ID':'Original column L, previously headed 0; retained without reinterpretation.',
'Field provisional (duplicate source)':'Original column AC retained under a unique header.'}
with (O/'data_dictionary.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['Column','Definition']);w.writerows((k,defs.get(k,'Original source value retained unchanged; not independently verified.')) for k in headers)
queue=[]
for r in rows:
 if not r['Received date'] or not r['Accepted date']:
  doi=r['DOI'].lower();route='PubMed editorial XML if indexed, then publisher history / permitted PDF'
  if doi.startswith('10.1016/'):route='Elsevier Article Retrieval API with key and required entitlement; publisher history / permitted PDF'
  queue.append({'Record key':r['Record key'],'DOI':r['DOI'],'History status':r['History status'],'Missing received':int(not r['Received date']),'Missing accepted':int(not r['Accepted date']),'Suggested next route':route})
with (O/'history_review_queue.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(queue[0]));w.writeheader();w.writerows(queue)
coverage=[]
for dimension in ['Field analysis group','Publication year','Publication type analysis','Origin cohort','DOI prefix']:
 groups=collections.defaultdict(list)
 for r in rows:groups[(r['DOI'].split('/')[0] if r['DOI'] else 'Missing DOI') if dimension=='DOI prefix' else r[dimension]].append(r)
 for value,group in sorted(groups.items()):
  n=len(group);nr=sum(bool(r['Received date']) for r in group);na=sum(bool(r['Accepted date']) for r in group)
  coverage.append({'Dimension':dimension,'Group':value,'Records':n,'Received dates':nr,'Accepted dates':na,'Received date coverage':nr/n,'Accepted date coverage':na/n})
with (O/'history_coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(coverage[0]));w.writeheader();w.writerows(coverage)

def table(mapping):return '<table><tbody>'+''.join('<tr><th>'+html.escape(str(k))+'</th><td>'+html.escape(str(v))+'</td></tr>' for k,v in mapping.items())+'</tbody></table>'
metrics={k:c[k] for k in ['Model age (days)','Release to received (days)','Received to accepted (days)','Accepted to online (days)','Received to online (days)']}
body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Papers7 — Analysis guide</title>
<style>body{{font:17px/1.6 system-ui,sans-serif;color:#193047;background:#edf2f6;margin:0}}main{{max-width:1000px;margin:auto;background:white;padding:48px}}h1{{font-size:38px;line-height:1.15}}h2{{margin-top:38px}}.eyebrow{{color:#267985;font-weight:700;letter-spacing:.12em}}.cards{{display:flex;gap:18px;flex-wrap:wrap}}.card{{background:#eaf4f4;padding:18px;flex:1;min-width:160px}}.n{{font-size:32px;font-weight:750}}table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #d9e1e7;padding:10px;text-align:left}}th{{font-weight:500}}.note{{border-left:4px solid #ce8a37;background:#fff8ed;padding:18px}}pre{{white-space:pre-wrap;font:15px/1.55 system-ui}}a{{color:#126674}}@media print{{body{{background:white}}main{{padding:0}}}}</style><main>
<div class="eyebrow">PUBLICATION TIMING • 2 NOVEMBER 2026</div><h1>Model age, publication history<br>and defensible comparisons</h1>
<p>The processed dataset keeps the requested source fields and separates timing arithmetic from judgments about model suitability.</p>
<div class="cards"><div class="card"><div class="n">{s['records']:,}</div>records preserved</div><div class="card"><div class="n">{s['received_dates']:,}</div>received dates available</div><div class="card"><div class="n">{s['bert_screened']:,}</div>BERT-related screens</div></div>
<h2>CulturalProbe: the corrected clock</h2><p>DOI 10.1016/j.ipm.2026.105123. Source field: 1 February 2027. Analysis online date: 8 September 2026, based on the history supplied by the user. The original citation and source date remain preserved.</p>{table(metrics)}
<p>These figures assume the mapped GPT-4 release of 14 March 2023 and the recorded model identity. The pre-receipt interval does not establish when the experiment ran or why that model was chosen.</p>
<h2>Retrieval coverage</h2>{table(s['history_status'])}<p>All nonempty DOI strings were queried against Europe PMC; 707 open-access XML records were identified for retrieval. The acquired subset is not representative of all publishers or fields. A missing date is not zero and does not prove the publisher never reports it.</p>
<h2>Separate BERT use before interpreting age</h2>{table(s['bert_roles'])}<div class="note">These are provisional citation/model screens, not verified full-text annotations. A method cue does not prove innovation; an application cue does not prove ignorance. Every BERT review row has a place for evidence and a final reviewer decision.</div>
<h2>Fields ready for grouping</h2>{table(s['field_groups'])}<p>Field memberships are also supplied in long format with fractional weights. Sampling origin, publication type and model class are separate dimensions.</p>
<h2>Read before plotting</h2><p>Use the unique Record key for joins: original IDs contain 816 repeated occurrences. The model-age and successor eligibility flags are arithmetic and provisional lineage screens, not external validation. Use one successor scenario per paper at a time.</p>
<h2>Full definitions, workflow and sources</h2><pre>{html.escape(readme)}</pre></main></html>'''
(O/'Papers7_Analysis_Guide.html').write_text(body,encoding='utf-8')
bundle=O/'Papers7_Analysis_Package.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for p in O.iterdir():
  if p.suffix in ['.csv','.md','.json','.html']:z.write(p,p.name)
 for name in ['harvest_history.py','process_papers.py','package_analysis.py','history.json']:z.write(R/name,name)
 z.write(R/'current/Papers7.csv','current/Papers7.csv')
print('Packaged',bundle, 'bytes',bundle.stat().st_size)
