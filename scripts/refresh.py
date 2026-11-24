#!/usr/bin/env python3
"""Capture a modest set of OSM toilet extracts, never one query per visitor."""
import argparse, datetime as dt, hashlib, json, math, os, re, tempfile, time
from urllib.error import HTTPError, URLError
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]
ALLOWED_TAGS={'name','name:en','operator','access','fee','charge','wheelchair','wheelchair:description','opening_hours','changing_table','changing_table:location','unisex','female','male','toilets:disposal','toilets:position','drinking_water','indoor','level','description','note','check_date','check_date:opening_hours','survey:date','addr:street','addr:housenumber','addr:city'}
def iso_now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def valid_config(config):
 regions=config.get('regions')
 if not isinstance(regions,list) or not 1<=len(regions)<=10:raise ValueError('Configure 1–10 bounded regions.')
 seen=set()
 for r in regions:
  if not isinstance(r,dict) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',r.get('id','')) or r['id'] in seen:raise ValueError('Invalid/duplicate region ID.')
  seen.add(r['id'])
  b=r.get('bbox',[])
  if len(b)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in b):raise ValueError('Invalid bounds.')
  s,w,n,e=b
  if not (-85<=s<n<=85 and -180<=w<e<=180) or (n-s)*(e-w)>4:raise ValueError('Keep each extract below four square degrees.')
  if not isinstance(r.get('name'),str) or not r['name']:raise ValueError('Region needs a name.')
  c=r.get('center',[])
  if len(c)!=2 or not s<=c[0]<=n or not w<=c[1]<=e:raise ValueError('Region center must be within bounds.')
 if config.get('defaultRegion') not in seen:raise ValueError('Default region missing.')
 if not 1<=config.get('minimumRecordsPerRegion',0)<=config.get('maximumRecords',0)<=25000:raise ValueError('Invalid record safeguards.')
 if not 0<=config.get('maximumDropFraction',-1)<1 or not 1<=config.get('retainedCaptures',0)<=52:raise ValueError('Invalid retention/drop safeguard.')
 url=urlsplit(config.get('sourceUrl',''))
 if url.scheme!='https' or not url.hostname or url.username:raise ValueError('Source needs a public HTTPS endpoint.')
 return regions

def query_for(regions):return '[out:json][timeout:90];('+''.join('nwr["amenity"="toilets"]('+','.join(str(v) for v in r['bbox'])+');' for r in regions)+');out center meta;'
def fetch_region(endpoint, region, opener=urlopen, sleep=time.sleep):
 req=Request(endpoint, data=urlencode({'data':query_for([region])}).encode(),
             headers={'User-Agent':'CoolCode RestroomReach/1.1 (+https://github.com/jsdyer/restroomreach)',
                      'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'})
 for attempt in range(2):
  try:
   with opener(req,timeout=120) as response:
    body=response.read(16*1024*1024+1)
    if len(body)>16*1024*1024:raise ValueError('Source exceeds response size limit for '+region['id'])
    source=json.loads(body)
   if not isinstance(source,dict) or source.get('remark') or not isinstance(source.get('elements'),list):
    raise ValueError('Overpass returned an incomplete/error response for '+region['id'])
   return source
  except HTTPError as exc:
   if attempt or exc.code not in (500,502,503,504):raise
  except (TimeoutError,URLError,ConnectionError):
   if attempt:raise
  print('Temporary download failure for '+region['id']+'; retrying once in 5 seconds',flush=True)
  sleep(5)

def collect_regions(config, opener=urlopen, sleep=time.sleep):
 elements={};editions=[]
 for region in valid_config(config):
  print('Collecting '+region['id'],flush=True)
  source=fetch_region(config['sourceUrl'],region,opener,sleep)
  base=source.get('osm3s',{}).get('timestamp_osm_base')
  try: edition=dt.datetime.fromisoformat(base.replace('Z','+00:00'))
  except (TypeError,AttributeError,ValueError):raise ValueError('Missing OSM database timestamp for '+region['id'])
  if edition.tzinfo is None:raise ValueError('OSM database timestamp needs a timezone')
  editions.append((edition,base))
  for element in source['elements']:
   key=(element.get('type'),element.get('id'))
   if key in elements and elements[key]!=element:raise ValueError('Conflicting OSM records between regional extracts')
   elements[key]=element
 return {'osm3s':{'timestamp_osm_base':min(editions)[1]},'elements':list(elements.values())}

def normalize(source,config,captured_at):
 regions=valid_config(config)
 if not isinstance(source,dict) or source.get('remark') or not isinstance(source.get('elements'),list):raise ValueError('Overpass returned an incomplete/error response.')
 base=source.get('osm3s',{}).get('timestamp_osm_base')
 try:dt.datetime.fromisoformat(base.replace('Z','+00:00'))
 except (TypeError,AttributeError,ValueError):raise ValueError('Missing OSM database timestamp.')
 records=[];seen=set()
 for item in source['elements']:
  kind=item.get('type');ident=item.get('id');tags=item.get('tags',{})
  if kind not in ('node','way','relation') or type(ident)!=int or ident<=0 or not isinstance(tags,dict) or tags.get('amenity')!='toilets':raise ValueError('Unexpected OSM element.')
  key=f'{kind}/{ident}'
  if key in seen:raise ValueError('Duplicate OSM identity.')
  seen.add(key)
  point=item if kind=='node' else item.get('center',{})
  lat,lon=point.get('lat'),point.get('lon')
  if any(type(x) not in (int,float) or not math.isfinite(x) for x in (lat,lon)) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Missing valid element center.')
  coverage=[r['id'] for r in regions if r['bbox'][0]<=lat<=r['bbox'][2] and r['bbox'][1]<=lon<=r['bbox'][3]]
  if not coverage:continue # A crossing way's center may lie outside the requested rectangle.
  trimmed={k:v for k,v in tags.items() if k in ALLOWED_TAGS and isinstance(v,str) and len(v)<=4000}
  records.append({'id':key,'lat':lat,'lon':lon,'regions':coverage,'tags':trimmed,'osmUpdatedAt':item.get('timestamp'),'version':item.get('version')})
 if not records or len(records)>config['maximumRecords']:raise ValueError('Record count outside configured safeguards.')
 for r in regions:
  if sum(r['id'] in x['regions'] for x in records)<config['minimumRecordsPerRegion']:raise ValueError('Insufficient records for '+r['id'])
 records.sort(key=lambda x:x['id'])
 scope=hashlib.sha256(json.dumps([(r['id'],r['bbox']) for r in regions],separators=(',',':')).encode()).hexdigest()[:16]
 return {'schema':'coolcode.restroomreach.v1','capturedAt':captured_at,'sourceUpdatedAt':base,'source':config['sourceUrl'],'license':'ODbL-1.0','attribution':'© OpenStreetMap contributors','scope':scope,'regions':regions,'records':records}

def check_drop(old,new,config):
 if old and old.get('scope')==new['scope']:
  for r in new['regions']:
   before=sum(r['id'] in x['regions'] for x in old['records']);after=sum(r['id'] in x['regions'] for x in new['records'])
   if before and after<before*(1-config['maximumDropFraction']):raise ValueError('Unexpected regional record drop; previous capture retained.')

def atomic_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,encoding='utf8',delete=False) as f:
  json.dump(value,f,ensure_ascii=False,separators=(',',':'));f.write('\n');temp=Path(f.name)
 temp.replace(path)

def run(root=ROOT,input_path=None):
 config=json.loads((root/'web/config.json').read_text());regions=valid_config(config)
 if input_path:source=json.loads(Path(input_path).read_text())
 else:source=collect_regions(config)
 data=root/'web/data';index_path=data/'index.json';old_index=json.loads(index_path.read_text()) if index_path.exists() else {'captures':[]}
 old=None
 if old_index['captures']:old=json.loads((data/old_index['captures'][0]['file']).read_text())
 capture=normalize(source,config,iso_now());check_drop(old,capture,config)
 stamp=capture['capturedAt'].replace('-','').replace(':','');filename='captures/'+stamp+'.json'
 atomic_json(data/filename,capture)
 entry={'file':filename,'capturedAt':capture['capturedAt'],'sourceUpdatedAt':capture['sourceUpdatedAt'],'count':len(capture['records']),'scope':capture['scope']}
 entries=[entry]+[e for e in old_index['captures'] if e['file']!=filename]
 keep=entries[:config['retainedCaptures']]
 atomic_json(index_path,{'schema':'coolcode.restroomreach.index.v1','capturedAt':capture['capturedAt'],'sourceUpdatedAt':capture['sourceUpdatedAt'],'count':len(capture['records']),'regions':len(regions),'captures':keep})
 for e in entries[len(keep):]:
  p=data/e['file']
  if p.exists() and p.parent==data/'captures':p.unlink()
 print(f"Captured {len(capture['records'])} toilet records across {len(regions)} regions at {capture['capturedAt']}")
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',help='Previously downloaded Overpass JSON, for reproducible imports');args=p.parse_args()
 try:run(input_path=args.input)
 except (OSError,ValueError,KeyError) as exc:raise SystemExit('Refresh failed; prior index preserved: '+str(exc))
