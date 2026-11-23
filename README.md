# Scientometrics
Focus on Decay, Half-Life &amp; Obsolescence of Academic Publications


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

## Cited Papers on github
[GenAI-Powered Postsecondary Computer Science Education Tools](https://github.com/owensizemore/genai-powered-postsecondary-csed-tools-supplementary)
