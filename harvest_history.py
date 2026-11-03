"""DOI -> Europe PMC -> open JATS history. Python 3 standard library only.
Usage: python harvest_history.py Papers7.csv history.json --xml-limit 80
Use --xml-limit 0 for all eligible XML records. Requests cached; 2 requests/sec.
Does not treat repository, indexing, Crossref deposit or revision dates as editorial dates.
"""
import argparse,csv,json,pathlib,urllib.request,urllib.parse,time,hashlib,threading,concurrent.futures,xml.etree.ElementTree as ET,datetime,re
BASE='https://www.ebi.ac.uk/europepmc/webservices/rest/'
lock=threading.Lock(); last=[0.0]
def get(url,cache):
    p=cache/(hashlib.sha256(url.encode()).hexdigest()+'.cache')
    if p.exists():return p.read_bytes()
    for attempt in range(3):
        with lock:
            time.sleep(max(0,0.5-(time.monotonic()-last[0])));last[0]=time.monotonic()
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'PublicationHistoryResearch/1.0'})
            with urllib.request.urlopen(req,timeout=25) as r: data=r.read()
            p.write_bytes(data);return data
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504):raise
            time.sleep(min(15,float(e.headers.get('Retry-After','2'))*(attempt+1)))
        except (TimeoutError,urllib.error.URLError):
            if attempt==2:raise
            time.sleep(2*(attempt+1))
    raise RuntimeError('Retries exhausted')
def iso_date(el):
    v=el.get('iso-8601-date','')
    if len(v)==10:
        try:return datetime.date.fromisoformat(v).isoformat()
        except ValueError:pass
    try:return datetime.date(int(el.findtext('year')),int(el.findtext('month')),int(el.findtext('day'))).isoformat()
    except (TypeError,ValueError):return ''
def parse_history(data):
    root=ET.fromstring(data)
    for e in root.iter():e.tag=e.tag.split('}')[-1]
    meta=root.find('./front/article-meta')
    if meta is None:raise ValueError('No article metadata')
    dates={}
    for e in meta.findall('./history/date'):
        typ=e.get('date-type',''); value=iso_date(e)
        if value:dates.setdefault(typ,[]).append(value)
    # Some PMC conversions move editorial history into explicitly tagged front notes.
    # Scope to history sections, never scan article body, references or repository dates.
    for sec in root.findall('./front/notes/sec'):
        if sec.get('sec-type')!='history':continue
        text=' '.join(sec.itertext())
        for label,raw in re.findall(r'\b(Received|Revised|Accepted)\s+(\d{4}\s+[A-Za-z]+\s+\d{1,2})\b',text):
            for fmt in ('%Y %b %d','%Y %B %d'):
                try:
                    val=datetime.datetime.strptime(raw,fmt).date().isoformat()
                    dates.setdefault({'Received':'received','Revised':'rev-recd','Accepted':'accepted'}[label],[]).append(val);break
                except ValueError:pass
    online=[]
    for e in meta.findall('./pub-date'):
        if e.get('pub-type') in ('epub','epub-ppub') or (e.get('publication-format')=='electronic' and e.get('date-type','pub')=='pub'):
            v=iso_date(e)
            if v:online.append(v)
    return {'received':min(dates.get('received',[]),default=''),'revised':max(dates.get('rev-recd',[])+dates.get('revised',[]),default=''),'accepted':max(dates.get('accepted',[]),default=''),'online':min(online,default=''),'history_events':dates}
def run(args):
    cache=pathlib.Path(args.cache);cache.mkdir(exist_ok=True,parents=True)
    with open(args.input,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    dois=sorted({r.get('DOI','').strip().lower().removeprefix('https://doi.org/') for r in rows if r.get('DOI','').strip()})
    out={d:{'status':'not_found_in_europe_pmc','source':'','retrieved_on':datetime.date.today().isoformat()} for d in dois}
    chunks=[dois[i:i+40] for i in range(0,len(dois),40)]
    def search(chunk):
        q=' OR '.join('DOI:"'+d+'"' for d in chunk)
        url=BASE+'search?'+urllib.parse.urlencode({'query':q,'format':'json','resultType':'core','pageSize':1000})
        try:return chunk,json.loads(get(url,cache)).get('resultList',{}).get('result',[]),''
        except Exception as e:return chunk,[],type(e).__name__+': '+str(e)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        for i,(chunk,records,error) in enumerate(ex.map(search,chunks),1):
            if error:
                for d in chunk:out[d].update(status='metadata_request_failed',error=error)
            for r in records:
                d=r.get('doi','').lower()
                if d not in out:continue
                # Prefer a record with accessible full text if DOI resolves to multiple records.
                if out[d].get('pmcid') and not r.get('pmcid'):continue
                out[d].update(status='metadata_only',pmcid=r.get('pmcid',''),open_access=r.get('isOpenAccess',''),title=r.get('title',''),metadata_online=r.get('electronicPublicationDate',''),source=BASE+'search?'+urllib.parse.urlencode({'query':'DOI:"'+d+'"','format':'json'}))
            if i%10==0:print('Metadata batches',i,'/',len(chunks),flush=True)
    # Round robin across DOI prefixes rather than selecting only the first publisher.
    groups={}
    for d,r in out.items():
        if r.get('pmcid') and r.get('open_access')=='Y':groups.setdefault(d.split('/')[0],[]).append(d)
    selected=[]
    while any(groups.values()):
        for g in sorted(groups):
            if groups[g]:selected.append(groups[g].pop(0))
    if args.xml_limit:selected=selected[:args.xml_limit]
    def xml(d):
        url=BASE+out[d]['pmcid']+'/fullTextXML'
        try:
            h=parse_history(get(url,cache));h.update(status='history_retrieved' if h['received'] or h['accepted'] else 'xml_history_not_reported',source=url)
        except Exception as e:h={'status':'xml_request_failed','error':type(e).__name__+': '+str(e),'source':url}
        return d,h
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for i,(d,h) in enumerate(ex.map(xml,selected),1):
            out[d].update(h)
            if i%20==0:print('XML records',i,'/',len(selected),flush=True)
    pathlib.Path(args.output).write_text(json.dumps(out,indent=2),encoding='utf-8')
    from collections import Counter
    print('Finished:',dict(Counter(r['status'] for r in out.values())),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');p.add_argument('--cache',default='history_cache');p.add_argument('--xml-limit',type=int,default=80)
    run(p.parse_args())
